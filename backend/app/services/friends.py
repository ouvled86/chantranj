"""Friend graph: one Friendship row per pair (either direction), with a status.

BLOCKED takes precedence over everything — a block hides the blocker from the
blocked user and forbids new requests in both directions.
"""

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.models import Friendship, FriendshipStatus, User


async def relationship(db: AsyncSession, a: int, b: int) -> Friendship | None:
    result: Friendship | None = await db.scalar(
        select(Friendship).where(
            or_(
                and_(Friendship.requester_id == a, Friendship.addressee_id == b),
                and_(Friendship.requester_id == b, Friendship.addressee_id == a),
            )
        )
    )
    return result


async def send_request(db: AsyncSession, me: int, target_username: str) -> Friendship:
    target = await db.scalar(select(User).where(User.username == target_username))
    if target is None or target.banned:
        raise AppError(404, "not_found", "No such player")
    if target.id == me:
        raise AppError(400, "self_friend", "You can't befriend yourself")

    existing = await relationship(db, me, target.id)
    if existing is not None:
        if existing.status == FriendshipStatus.BLOCKED:
            raise AppError(403, "blocked", "Unavailable")
        if existing.status == FriendshipStatus.ACCEPTED:
            raise AppError(409, "already_friends", "You're already friends")
        # A pending request already exists.
        if existing.requester_id == target.id:
            # They already asked you — accept it instead of duplicating.
            existing.status = FriendshipStatus.ACCEPTED
            await db.commit()
            await db.refresh(existing)
            return existing
        raise AppError(409, "already_requested", "Request already sent")

    friendship = Friendship(
        requester_id=me, addressee_id=target.id, status=FriendshipStatus.PENDING
    )
    db.add(friendship)
    await db.commit()
    await db.refresh(friendship)
    return friendship


async def respond(db: AsyncSession, me: int, friendship_id: int, accept: bool) -> None:
    fr = await db.get(Friendship, friendship_id)
    if fr is None or fr.status != FriendshipStatus.PENDING:
        raise AppError(404, "not_found", "No such request")
    if fr.addressee_id != me:
        raise AppError(403, "forbidden", "That request isn't addressed to you")
    if accept:
        fr.status = FriendshipStatus.ACCEPTED
        await db.commit()
    else:
        await db.delete(fr)
        await db.commit()


async def remove(db: AsyncSession, me: int, other_id: int) -> None:
    fr = await relationship(db, me, other_id)
    if fr is None or fr.status == FriendshipStatus.BLOCKED:
        raise AppError(404, "not_found", "Not friends")
    await db.delete(fr)
    await db.commit()


async def block(db: AsyncSession, me: int, other_id: int) -> None:
    if other_id == me:
        raise AppError(400, "self_block", "You can't block yourself")
    fr = await relationship(db, me, other_id)
    if fr is not None:
        await db.delete(fr)
        await db.flush()
    db.add(
        Friendship(requester_id=me, addressee_id=other_id, status=FriendshipStatus.BLOCKED)
    )
    await db.commit()


async def unblock(db: AsyncSession, me: int, other_id: int) -> None:
    fr = await db.scalar(
        select(Friendship).where(
            Friendship.requester_id == me,
            Friendship.addressee_id == other_id,
            Friendship.status == FriendshipStatus.BLOCKED,
        )
    )
    if fr is None:
        raise AppError(404, "not_found", "Not blocked")
    await db.delete(fr)
    await db.commit()


async def are_friends(db: AsyncSession, a: int, b: int) -> bool:
    fr = await relationship(db, a, b)
    return fr is not None and fr.status == FriendshipStatus.ACCEPTED


async def is_blocked_between(db: AsyncSession, a: int, b: int) -> bool:
    fr = await relationship(db, a, b)
    return fr is not None and fr.status == FriendshipStatus.BLOCKED


async def list_friend_ids(db: AsyncSession, me: int) -> list[int]:
    rows = (
        await db.scalars(
            select(Friendship).where(
                Friendship.status == FriendshipStatus.ACCEPTED,
                or_(Friendship.requester_id == me, Friendship.addressee_id == me),
            )
        )
    ).all()
    return [r.addressee_id if r.requester_id == me else r.requester_id for r in rows]
