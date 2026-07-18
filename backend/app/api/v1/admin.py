"""Admin endpoints: user management with audit logging."""

from fastapi import APIRouter, Query, Request
from sqlalchemy import func, select

from app.api.deps import AdminUser, DbDep, audit
from app.core.errors import AppError
from app.models.user import User
from app.schemas.user import AdminUserPatch, PaginatedUsers, UserOut

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/users")
async def list_users(
    admin: AdminUser,
    db: DbDep,
    query: str = Query(default="", max_length=64),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
) -> PaginatedUsers:
    stmt = select(User)
    if query:
        like = f"%{query}%"
        stmt = stmt.where(User.username.ilike(like) | User.email.ilike(like))
    total = await db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = (
        await db.scalars(stmt.order_by(User.id).offset((page - 1) * size).limit(size))
    ).all()
    return PaginatedUsers(
        items=[UserOut.model_validate(u) for u in rows], total=total, page=page, size=size
    )


@router.patch("/users/{user_id}")
async def patch_user(
    user_id: int,
    data: AdminUserPatch,
    admin: AdminUser,
    request: Request,
    db: DbDep,
) -> UserOut:
    user = await db.get(User, user_id)
    if user is None:
        raise AppError(404, "not_found", "No such user")
    changes: dict[str, object] = {}
    if data.role is not None and data.role != user.role:
        changes["role"] = data.role.value
        user.role = data.role
    if data.banned is not None and data.banned != user.banned:
        changes["banned"] = data.banned
        user.banned = data.banned
    if changes:
        await db.commit()
        await db.refresh(user)
        await audit(db, request, admin.id, "admin.user_patch", target=str(user_id), **changes)
    return UserOut.model_validate(user)
