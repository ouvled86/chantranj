"""Auth service: registration, login, rotating refresh-token families.

Reuse detection: every refresh token belongs to a family (one per login).
Rotation revokes the presented token and issues a successor in the same family.
If a REVOKED token is ever presented again, the whole family is revoked —
someone replayed a stolen token.
"""

import uuid
from datetime import timedelta

import structlog
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.errors import AppError
from app.core.security import (
    ensure_utc,
    hash_password,
    hash_token,
    new_refresh_token,
    now_utc,
    verify_password,
)
from app.models.user import RefreshToken, User

log = structlog.get_logger()


async def register_user(db: AsyncSession, email: str, username: str, password: str) -> User:
    email = email.lower()
    existing = await db.scalar(
        select(User).where((User.email == email) | (User.username == username))
    )
    if existing is not None:
        field = "email" if existing.email == email else "username"
        raise AppError(409, "already_exists", f"That {field} is already taken")
    user = User(email=email, username=username, password_hash=hash_password(password))
    db.add(user)
    await db.commit()
    await db.refresh(user)
    log.info("user_registered", user_id=user.id)
    return user


async def authenticate(db: AsyncSession, identifier: str, password: str) -> User:
    ident = identifier.lower() if "@" in identifier else identifier
    user = await db.scalar(
        select(User).where((User.email == ident) | (User.username == identifier))
    )
    # Verify against a dummy hash on miss to keep timing roughly constant.
    if user is None or user.password_hash is None:
        verify_password(password, hash_password("dummy-password-1"))
        raise AppError(401, "invalid_credentials", "Wrong email/username or password")
    if not verify_password(password, user.password_hash):
        raise AppError(401, "invalid_credentials", "Wrong email/username or password")
    if user.banned:
        raise AppError(403, "banned", "This account is banned")
    user.last_seen_at = now_utc()
    await db.commit()
    return user


async def issue_refresh_token(
    db: AsyncSession, user: User, family_id: str | None = None
) -> str:
    settings = get_settings()
    raw = new_refresh_token()
    db.add(
        RefreshToken(
            user_id=user.id,
            token_hash=hash_token(raw),
            family_id=family_id or str(uuid.uuid4()),
            expires_at=now_utc() + timedelta(days=settings.refresh_token_ttl_days),
        )
    )
    await db.commit()
    return raw


async def rotate_refresh_token(db: AsyncSession, raw: str) -> tuple[User, str]:
    """Returns (user, new_raw_refresh). Raises 401 on anything suspicious."""
    row = await db.scalar(select(RefreshToken).where(RefreshToken.token_hash == hash_token(raw)))
    if row is None:
        raise AppError(401, "invalid_refresh", "Unknown refresh token")

    if row.revoked_at is not None:
        # Replay of a rotated token → kill the whole family.
        await db.execute(
            update(RefreshToken)
            .where(RefreshToken.family_id == row.family_id, RefreshToken.revoked_at.is_(None))
            .values(revoked_at=now_utc())
        )
        await db.commit()
        log.warning("refresh_reuse_detected", user_id=row.user_id, family=row.family_id)
        raise AppError(401, "refresh_reused", "Session revoked — sign in again")

    if ensure_utc(row.expires_at) < now_utc():
        raise AppError(401, "refresh_expired", "Session expired — sign in again")

    user = await db.get(User, row.user_id)
    if user is None or user.banned:
        raise AppError(401, "invalid_refresh", "Account unavailable")

    row.revoked_at = now_utc()
    await db.commit()
    new_raw = await issue_refresh_token(db, user, family_id=row.family_id)
    return user, new_raw


async def revoke_refresh_token(db: AsyncSession, raw: str) -> None:
    await db.execute(
        update(RefreshToken)
        .where(RefreshToken.token_hash == hash_token(raw), RefreshToken.revoked_at.is_(None))
        .values(revoked_at=now_utc())
    )
    await db.commit()
