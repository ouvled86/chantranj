"""User endpoints: own profile (GET/PATCH) + public profiles."""

from fastapi import APIRouter
from sqlalchemy import select

from app.api.deps import CurrentUser, DbDep
from app.core.errors import AppError
from app.models.user import User
from app.schemas.user import PublicUser, UserOut, UserPatch

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me")
async def get_me(user: CurrentUser) -> UserOut:
    return UserOut.model_validate(user)


@router.patch("/me")
async def patch_me(data: UserPatch, user: CurrentUser, db: DbDep) -> UserOut:
    if data.username is not None and data.username != user.username:
        taken = await db.scalar(select(User).where(User.username == data.username))
        if taken is not None:
            raise AppError(409, "already_exists", "That username is already taken")
        user.username = data.username
    if data.avatar_url is not None:
        user.avatar_url = data.avatar_url
    if data.settings is not None:
        user.settings = data.settings
    await db.commit()
    await db.refresh(user)
    return UserOut.model_validate(user)


@router.get("/{username}")
async def public_profile(username: str, db: DbDep) -> PublicUser:
    user = await db.scalar(select(User).where(User.username == username))
    if user is None or user.banned:
        raise AppError(404, "not_found", "No such player")
    return PublicUser.model_validate(user)
