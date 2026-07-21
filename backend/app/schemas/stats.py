from pydantic import BaseModel


class RatingBlock(BaseModel):
    value: int
    games: int
    provisional: bool


class MeStats(BaseModel):
    level: int
    total_xp: int
    xp_into_level: int
    xp_for_next: int
    streak: int
    best_streak: int
    freezes_left: int
    ratings: dict[str, RatingBlock]
    games_played: int
    wins: int
    items_done: int
    achievements_unlocked: int
    achievements_total: int


class RatingPoint(BaseModel):
    time: str
    value: int


class AchievementView(BaseModel):
    slug: str
    title: str
    description: str
    icon: str
    category: str
    xp: int
    unlocked: bool
    unlocked_at: str | None
