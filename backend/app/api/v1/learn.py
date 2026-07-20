"""Learning path: strictly linear gating (finish an item to unlock the next).

Phase 6 extends this with boss verification and the admin CMS; the gating
contract here is already final: DONE items stay open, exactly one item is
AVAILABLE (the first unfinished), everything later is LOCKED. Admins bypass.
"""

from fastapi import APIRouter
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, DbDep
from app.core.errors import AppError
from app.core.security import now_utc
from app.models import ItemKind, ItemProgress, LearnItem, ProgressStatus, Role, Stage
from app.schemas.learn import ItemDetail, ItemSummary, StageOut

router = APIRouter(prefix="/learn", tags=["learn"])


async def _load_path(
    db: AsyncSession, user_id: int, is_admin: bool
) -> tuple[list[Stage], dict[int, list[LearnItem]], dict[int, str]]:
    stages = (
        await db.scalars(
            select(Stage).where(Stage.published.is_(True)).order_by(Stage.order_idx)
        )
    ).all()
    items = (
        await db.scalars(
            select(LearnItem).where(LearnItem.published.is_(True)).order_by(LearnItem.order_idx)
        )
    ).all()
    done_ids = set(
        (
            await db.scalars(
                select(ItemProgress.item_id).where(ItemProgress.user_id == user_id)
            )
        ).all()
    )

    by_stage: dict[int, list[LearnItem]] = {}
    for item in items:
        by_stage.setdefault(item.stage_id, []).append(item)

    statuses: dict[int, str] = {}
    available_given = False
    for stage in stages:
        for item in by_stage.get(stage.id, []):
            if item.id in done_ids:
                statuses[item.id] = "DONE"
            elif is_admin:
                statuses[item.id] = "AVAILABLE"
            elif not available_given:
                statuses[item.id] = "AVAILABLE"
                available_given = True
            else:
                statuses[item.id] = "LOCKED"
    return list(stages), by_stage, statuses


@router.get("/path")
async def get_path(user: CurrentUser, db: DbDep) -> list[StageOut]:
    stages, by_stage, statuses = await _load_path(db, user.id, user.role == Role.ADMIN)
    return [
        StageOut(
            slug=stage.slug,
            title=stage.title,
            intro=stage.intro,
            order_idx=stage.order_idx,
            items=[
                ItemSummary(
                    slug=item.slug,
                    kind=item.kind,
                    title=item.title,
                    sub=item.sub,
                    order_idx=item.order_idx,
                    status=statuses[item.id],
                )
                for item in by_stage.get(stage.id, [])
            ],
        )
        for stage in stages
    ]


async def _accessible_item(db: AsyncSession, user: CurrentUser, slug: str) -> tuple[LearnItem, str]:
    item = await db.scalar(
        select(LearnItem).where(LearnItem.slug == slug, LearnItem.published.is_(True))
    )
    if item is None:
        raise AppError(404, "not_found", "No such item")
    _, _, statuses = await _load_path(db, user.id, user.role == Role.ADMIN)
    status = statuses.get(item.id, "LOCKED")
    if status == "LOCKED":
        raise AppError(403, "locked", "Finish the previous material first")
    return item, status


@router.get("/items/{slug}")
async def get_item(slug: str, user: CurrentUser, db: DbDep) -> ItemDetail:
    item, status = await _accessible_item(db, user, slug)
    boss = None
    if item.kind == ItemKind.BOSS and item.boss_config:
        # Expose only what the client needs to frame + start the fight.
        cfg = item.boss_config
        boss = {
            "bot_level": cfg.get("bot_level"),
            "player_color": cfg.get("player_color", "white"),
            "objective": cfg.get("objective", "win"),
            "move_limit": cfg.get("move_limit"),
            "start_fen": cfg.get("start_fen"),
            "time_control": cfg.get("time_control", {"base_min": None, "inc_sec": 0}),
        }
    return ItemDetail(
        slug=item.slug,
        kind=item.kind,
        title=item.title,
        sub=item.sub,
        status=status,
        content=item.content_json,
        boss=boss,
    )


async def _mark_done(db: AsyncSession, user_id: int, item_id: int) -> None:
    if await db.get(ItemProgress, (user_id, item_id)) is None:
        db.add(
            ItemProgress(
                user_id=user_id,
                item_id=item_id,
                status=ProgressStatus.DONE,
                completed_at=now_utc(),
            )
        )
        await db.commit()


@router.post("/items/{slug}/complete")
async def complete_item(slug: str, user: CurrentUser, db: DbDep) -> dict[str, str]:
    item, _ = await _accessible_item(db, user, slug)
    if item.kind == ItemKind.BOSS:
        raise AppError(409, "boss_requires_win", "Beat the boss to complete this checkpoint")
    await _mark_done(db, user.id, item.id)
    return {"status": "ok"}


@router.post("/items/{slug}/boss/start", status_code=201)
async def start_boss(slug: str, user: CurrentUser, db: DbDep) -> dict[str, int]:
    from app.models import GameMode
    from app.services import games as game_service
    from app.ws.game import on_game_over

    item, _ = await _accessible_item(db, user, slug)
    if item.kind != ItemKind.BOSS or not item.boss_config:
        raise AppError(400, "not_a_boss", "This item is not a boss checkpoint")
    cfg = item.boss_config
    human_white = cfg.get("player_color", "white") == "white"
    tc = cfg.get("time_control", {"base_min": None, "inc_sec": 0})
    game = await game_service.create_game(
        white_id=user.id if human_white else None,
        black_id=None if human_white else user.id,
        rated=False,
        base_min=tc.get("base_min"),
        inc_sec=tc.get("inc_sec", 0),
        mode=GameMode.BOT,
        bot_level=cfg["bot_level"],
        start_fen=cfg.get("start_fen"),
        on_over=on_game_over,
    )
    return {"game_id": game.id}


@router.post("/items/{slug}/boss/verify")
async def verify_boss(
    slug: str, body: dict[str, int], user: CurrentUser, db: DbDep
) -> dict[str, object]:
    from app.models import Game
    from app.services import boss as boss_service

    item, _ = await _accessible_item(db, user, slug)
    if item.kind != ItemKind.BOSS or not item.boss_config:
        raise AppError(400, "not_a_boss", "This item is not a boss checkpoint")
    game = await db.get(Game, int(body.get("game_id", 0)))
    if game is None:
        raise AppError(404, "not_found", "No such game")
    passed, reason = boss_service.verify(game, item.boss_config, user.id)
    if passed:
        await _mark_done(db, user.id, item.id)
    return {"passed": passed, "reason": reason}
