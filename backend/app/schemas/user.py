from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.user import Role


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    username: str
    avatar_url: str | None
    role: Role
    created_at: datetime


class PublicUser(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    username: str
    avatar_url: str | None
    created_at: datetime


class UserPatch(BaseModel):
    username: str | None = Field(
        default=None, min_length=3, max_length=20, pattern=r"^[a-zA-Z0-9_]+$"
    )
    avatar_url: str | None = Field(default=None, max_length=512)
    settings: dict[str, Any] | None = None


class AdminUserPatch(BaseModel):
    role: Role | None = None
    banned: bool | None = None


class PaginatedUsers(BaseModel):
    items: list[UserOut]
    total: int
    page: int
    size: int
