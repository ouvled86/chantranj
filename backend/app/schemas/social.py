from pydantic import BaseModel


class FriendRequestIn(BaseModel):
    username: str


class FriendSummary(BaseModel):
    friendship_id: int
    user_id: int
    username: str
    avatar_url: str | None
    presence: str  # online | in_game | in_duel | offline


class FriendsView(BaseModel):
    friends: list[FriendSummary]
    incoming: list[FriendSummary]  # requests awaiting my response
    outgoing: list[FriendSummary]  # requests I sent, still pending


class UserSearchResult(BaseModel):
    username: str
    avatar_url: str | None
    relation: str  # none | friends | incoming | outgoing | blocked | self
