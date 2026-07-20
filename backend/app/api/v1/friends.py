"""Friend management REST. Live presence + challenges ride /ws/social."""

from fastapi import APIRouter, Query, Request
from sqlalchemy import or_, select

from app.api.deps import CurrentUser, DbDep, audit
from app.models import Friendship, FriendshipStatus, User
from app.schemas.social import (
    FriendRequestIn,
    FriendSummary,
    FriendsView,
    UserSearchResult,
)
from app.services import friends as friend_service
from app.services import presence

router = APIRouter(prefix="/friends", tags=["friends"])


def _summary(fr: Friendship, other: User) -> FriendSummary:
    return FriendSummary(
        friendship_id=fr.id,
        user_id=other.id,
        username=other.username,
        avatar_url=other.avatar_url,
        presence=presence.status_of(other.id),
    )


@router.get("")
async def list_friends(user: CurrentUser, db: DbDep) -> FriendsView:
    rows = (
        await db.scalars(
            select(Friendship).where(
                or_(Friendship.requester_id == user.id, Friendship.addressee_id == user.id),
                Friendship.status != FriendshipStatus.BLOCKED,
            )
        )
    ).all()
    other_ids = {
        (r.addressee_id if r.requester_id == user.id else r.requester_id) for r in rows
    }
    users = {
        u.id: u
        for u in (await db.scalars(select(User).where(User.id.in_(other_ids)))).all()
    }

    friends: list[FriendSummary] = []
    incoming: list[FriendSummary] = []
    outgoing: list[FriendSummary] = []
    for r in rows:
        other = users.get(r.addressee_id if r.requester_id == user.id else r.requester_id)
        if other is None:
            continue
        summary = _summary(r, other)
        if r.status == FriendshipStatus.ACCEPTED:
            friends.append(summary)
        elif r.addressee_id == user.id:
            incoming.append(summary)
        else:
            outgoing.append(summary)
    friends.sort(key=lambda f: (f.presence == "offline", f.username.lower()))
    return FriendsView(friends=friends, incoming=incoming, outgoing=outgoing)


@router.get("/search")
async def search_users(
    user: CurrentUser, db: DbDep, q: str = Query(min_length=1, max_length=32)
) -> list[UserSearchResult]:
    rows = (
        await db.scalars(
            select(User)
            .where(User.username.ilike(f"%{q}%"), User.banned.is_(False))
            .limit(10)
        )
    ).all()
    results: list[UserSearchResult] = []
    for u in rows:
        if u.id == user.id:
            relation = "self"
        else:
            fr = await friend_service.relationship(db, user.id, u.id)
            if fr is None:
                relation = "none"
            elif fr.status == FriendshipStatus.ACCEPTED:
                relation = "friends"
            elif fr.status == FriendshipStatus.BLOCKED:
                relation = "blocked" if fr.requester_id == user.id else "none"
            elif fr.requester_id == user.id:
                relation = "outgoing"
            else:
                relation = "incoming"
        results.append(
            UserSearchResult(username=u.username, avatar_url=u.avatar_url, relation=relation)
        )
    return results


@router.post("/requests", status_code=201)
async def send_request(
    data: FriendRequestIn, user: CurrentUser, request: Request, db: DbDep
) -> dict[str, str]:
    fr = await friend_service.send_request(db, user.id, data.username)
    await audit(db, request, user.id, "friend.request", target=data.username)
    await _notify_social(fr.addressee_id, "friend:update")
    return {"status": "accepted" if fr.status == FriendshipStatus.ACCEPTED else "pending"}


@router.post("/requests/{friendship_id}/accept")
async def accept_request(
    friendship_id: int, user: CurrentUser, db: DbDep
) -> dict[str, str]:
    fr = await db.get(Friendship, friendship_id)
    requester = fr.requester_id if fr else None
    await friend_service.respond(db, user.id, friendship_id, accept=True)
    if requester:
        await _notify_social(requester, "friend:update")
    return {"status": "ok"}


@router.post("/requests/{friendship_id}/decline")
async def decline_request(
    friendship_id: int, user: CurrentUser, db: DbDep
) -> dict[str, str]:
    await friend_service.respond(db, user.id, friendship_id, accept=False)
    return {"status": "ok"}


@router.delete("/{other_id}", status_code=204)
async def remove_friend(other_id: int, user: CurrentUser, db: DbDep) -> None:
    await friend_service.remove(db, user.id, other_id)
    await _notify_social(other_id, "friend:update")


@router.post("/{other_id}/block")
async def block_user(
    other_id: int, user: CurrentUser, request: Request, db: DbDep
) -> dict[str, str]:
    await friend_service.block(db, user.id, other_id)
    await audit(db, request, user.id, "friend.block", target=str(other_id))
    return {"status": "ok"}


@router.post("/{other_id}/unblock")
async def unblock_user(other_id: int, user: CurrentUser, db: DbDep) -> dict[str, str]:
    await friend_service.unblock(db, user.id, other_id)
    return {"status": "ok"}


async def _notify_social(user_id: int, event: str) -> None:
    """Nudge a user's social sockets to refetch. Imported lazily to avoid a
    circular import with the ws layer at module load."""
    from app.ws.social import social_manager

    await social_manager.send_user(user_id, {"type": event, "data": {}})
