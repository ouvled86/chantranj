"""Auth endpoints: register/login/logout/refresh + Google OAuth (manual flow)."""

import secrets
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import RedirectResponse
from itsdangerous import BadSignature, URLSafeTimedSerializer
from sqlalchemy import select

from app.api.deps import DbDep, audit
from app.core.config import get_settings
from app.core.errors import AppError
from app.core.ratelimit import RateLimiter
from app.core.security import create_access_token, new_csrf_token
from app.models.user import User
from app.schemas.auth import LoginIn, RegisterIn
from app.schemas.user import UserOut
from app.services import auth as auth_service

router = APIRouter(prefix="/auth", tags=["auth"])

REFRESH_COOKIE_PATH = "/api/v1/auth"

login_limiter = RateLimiter(times=5, seconds=60, scope="login")
register_limiter = RateLimiter(times=5, seconds=60, scope="register")


def _set_auth_cookies(response: Response, user: User, refresh_raw: str) -> None:
    settings = get_settings()
    common = {"httponly": True, "samesite": "lax", "secure": settings.cookie_secure}
    response.set_cookie(
        "access_token",
        create_access_token(user.id, user.role.value),
        max_age=settings.access_token_ttl_min * 60,
        path="/",
        **common,  # type: ignore[arg-type]
    )
    response.set_cookie(
        "refresh_token",
        refresh_raw,
        max_age=settings.refresh_token_ttl_days * 86400,
        path=REFRESH_COOKIE_PATH,
        **common,  # type: ignore[arg-type]
    )
    response.set_cookie(
        "csrf_token",
        new_csrf_token(),
        max_age=settings.refresh_token_ttl_days * 86400,
        path="/",
        httponly=False,
        samesite="lax",
        secure=settings.cookie_secure,
    )


def _clear_auth_cookies(response: Response) -> None:
    response.delete_cookie("access_token", path="/")
    response.delete_cookie("refresh_token", path=REFRESH_COOKIE_PATH)
    response.delete_cookie("csrf_token", path="/")


@router.post("/register", status_code=201, dependencies=[Depends(register_limiter)])
async def register(data: RegisterIn, response: Response, db: DbDep) -> UserOut:
    user = await auth_service.register_user(db, data.email, data.username, data.password)
    refresh = await auth_service.issue_refresh_token(db, user)
    _set_auth_cookies(response, user, refresh)
    return UserOut.model_validate(user)


@router.post("/login", dependencies=[Depends(login_limiter)])
async def login(data: LoginIn, request: Request, response: Response, db: DbDep) -> UserOut:
    user = await auth_service.authenticate(db, data.identifier, data.password)
    refresh = await auth_service.issue_refresh_token(db, user)
    _set_auth_cookies(response, user, refresh)
    await audit(db, request, user.id, "auth.login")
    return UserOut.model_validate(user)


@router.post("/refresh")
async def refresh(request: Request, response: Response, db: DbDep) -> UserOut:
    raw = request.cookies.get("refresh_token")
    if not raw:
        raise AppError(401, "no_refresh", "No session to refresh")
    user, new_raw = await auth_service.rotate_refresh_token(db, raw)
    _set_auth_cookies(response, user, new_raw)
    return UserOut.model_validate(user)


@router.post("/logout")
async def logout(request: Request, response: Response, db: DbDep) -> dict[str, str]:
    raw = request.cookies.get("refresh_token")
    if raw:
        await auth_service.revoke_refresh_token(db, raw)
    _clear_auth_cookies(response)
    return {"status": "ok"}


# ---------- Google OAuth (manual code flow; disabled until creds configured) ----------

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://openidconnect.googleapis.com/v1/userinfo"


def _google_enabled() -> None:
    s = get_settings()
    if not (s.google_client_id and s.google_client_secret and s.google_redirect_uri):
        raise AppError(503, "oauth_not_configured", "Google sign-in is not configured")


def _state_serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(get_settings().secret_key, salt="google-oauth-state")


@router.get("/google")
async def google_start() -> RedirectResponse:
    _google_enabled()
    s = get_settings()
    state = _state_serializer().dumps({"n": secrets.token_urlsafe(16)})
    params = {
        "client_id": s.google_client_id,
        "redirect_uri": s.google_redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "prompt": "select_account",
    }
    return RedirectResponse(f"{GOOGLE_AUTH_URL}?{urlencode(params)}")


@router.get("/google/callback")
async def google_callback(code: str, state: str, request: Request, db: DbDep) -> RedirectResponse:
    _google_enabled()
    s = get_settings()
    try:
        _state_serializer().loads(state, max_age=600)
    except BadSignature as exc:
        raise AppError(400, "oauth_state_invalid", "OAuth state check failed") from exc

    async with httpx.AsyncClient(timeout=10) as client:
        token_resp = await client.post(
            GOOGLE_TOKEN_URL,
            data={
                "code": code,
                "client_id": s.google_client_id,
                "client_secret": s.google_client_secret,
                "redirect_uri": s.google_redirect_uri,
                "grant_type": "authorization_code",
            },
        )
        if token_resp.status_code != 200:
            raise AppError(502, "oauth_exchange_failed", "Google token exchange failed")
        access = token_resp.json()["access_token"]
        info_resp = await client.get(
            GOOGLE_USERINFO_URL, headers={"Authorization": f"Bearer {access}"}
        )
        if info_resp.status_code != 200:
            raise AppError(502, "oauth_userinfo_failed", "Google userinfo failed")
        info = info_resp.json()

    google_id: str = info["sub"]
    email: str = info.get("email", "").lower()
    user = await db.scalar(select(User).where(User.google_id == google_id))
    if user is None and email:
        user = await db.scalar(select(User).where(User.email == email))
        if user is not None:
            user.google_id = google_id  # link existing account by verified email
    if user is None:
        base = (email.split("@")[0] or "player")[:14] or "player"
        username = base
        while await db.scalar(select(User).where(User.username == username)) is not None:
            username = f"{base}_{secrets.token_hex(2)}"
        user = User(
            email=email,
            username=username,
            google_id=google_id,
            avatar_url=info.get("picture"),
        )
        db.add(user)
    if user.banned:
        raise AppError(403, "banned", "This account is banned")
    await db.commit()
    await db.refresh(user)

    refresh_raw = await auth_service.issue_refresh_token(db, user)
    await audit(db, request, user.id, "auth.google_login")
    response = RedirectResponse("/")
    _set_auth_cookies(response, user, refresh_raw)
    return response
