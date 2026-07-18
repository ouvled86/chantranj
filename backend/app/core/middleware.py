"""Request-id, security headers, and CSRF double-submit middleware."""

import uuid

import structlog
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

UNSAFE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
# Auth endpoints establish the session; they can't require an existing CSRF pair.
CSRF_EXEMPT_PREFIXES = ("/api/v1/auth/",)


class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        rid = request.headers.get("X-Request-ID") or uuid.uuid4().hex[:16]
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=rid)
        response = await call_next(request)
        response.headers["X-Request-ID"] = rid
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        return response


class CsrfMiddleware(BaseHTTPMiddleware):
    """Double-submit check: cookie-authenticated unsafe requests must echo the
    csrf_token cookie in the X-CSRF-Token header. Bearer-auth requests are exempt
    (no cookie = no CSRF surface)."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if (
            request.method in UNSAFE_METHODS
            and "access_token" in request.cookies
            and not request.url.path.startswith(CSRF_EXEMPT_PREFIXES)
        ):
            cookie = request.cookies.get("csrf_token")
            header = request.headers.get("X-CSRF-Token")
            if not cookie or not header or cookie != header:
                return JSONResponse(
                    status_code=403,
                    content={"error": {"code": "csrf_failed", "message": "CSRF check failed"}},
                )
        return await call_next(request)
