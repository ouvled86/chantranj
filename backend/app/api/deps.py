"""Shared dependencies: current user, admin gate, audit helper."""

from typing import Annotated

import jwt as pyjwt
from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.core.security import decode_token
from app.db.session import get_db
from app.models.user import AuditLog, Role, User

DbDep = Annotated[AsyncSession, Depends(get_db)]


def _extract_token(request: Request) -> str:
    token = request.cookies.get("access_token")
    if not token:
        auth = request.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            token = auth.removeprefix("Bearer ")
    if not token:
        raise AppError(401, "not_authenticated", "Sign in required")
    return token


async def get_current_user(request: Request, db: DbDep) -> User:
    try:
        payload = decode_token(_extract_token(request))
    except pyjwt.InvalidTokenError as exc:
        raise AppError(401, "invalid_token", "Invalid or expired session") from exc
    if payload.get("type") != "access":
        raise AppError(401, "invalid_token", "Invalid or expired session")
    user = await db.get(User, int(payload["sub"]))
    if user is None or user.banned:
        raise AppError(401, "invalid_token", "Account unavailable")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


async def require_admin(user: CurrentUser) -> User:
    if user.role != Role.ADMIN:
        raise AppError(403, "forbidden", "Admin access required")
    return user


AdminUser = Annotated[User, Depends(require_admin)]


async def audit(
    db: AsyncSession,
    request: Request,
    actor_id: int | None,
    action: str,
    target: str | None = None,
    **meta: object,
) -> None:
    db.add(
        AuditLog(
            actor_id=actor_id,
            action=action,
            target=target,
            ip=request.client.host if request.client else None,
            meta=dict(meta),
        )
    )
    await db.commit()
