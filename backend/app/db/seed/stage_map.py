"""The 12-stage learning path (docs/CURRICULUM.md) and where v1 items land.

Items not listed here (future authored content, bosses) arrive via the admin
CMS in Phase 6. order_idx values leave gaps for them on purpose.
"""

from typing import TypedDict


class StageSpec(TypedDict):
    slug: str
    title: str
    order_idx: int
    intro: str


STAGES: list[StageSpec] = [
    {"slug": "board-vision", "title": "Board Vision & Mating Fundamentals", "order_idx": 1,
     "intro": "Never miss what's on the board; finish won games."},
    {"slug": "tactics-1", "title": "Tactics I: The Big Four", "order_idx": 2,
     "intro": "Fork, pin, skewer, discovery — see them instantly."},
    {"slug": "openings-white", "title": "Opening Principles & First Repertoire", "order_idx": 3,
     "intro": "Reach a playable middlegame every game as White."},
    {"slug": "endgames-1", "title": "Endgames I: Pawns & Promotion", "order_idx": 4,
     "intro": "Convert extra material; hold worse endings."},
    {"slug": "tactics-2", "title": "Tactics II: Combinations", "order_idx": 5,
     "intro": "Chain motifs into 2-3 move combinations."},
    {"slug": "counter-openings", "title": "Counter-Openings & Understanding", "order_idx": 6,
     "intro": "A complete answer to 1.e4 and 1.d4 — and the why behind openings."},
    {"slug": "calculation", "title": "Thinking Ahead: The Calculation Habit", "order_idx": 7,
     "intro": "A repeatable per-move routine; three moves deep."},
    {"slug": "strategy-1", "title": "Strategy I: Pieces & Squares", "order_idx": 8,
     "intro": "Know what to do when there's no tactic."},
    {"slug": "endgames-2", "title": "Endgames II: Rook Endings & Technique", "order_idx": 9,
     "intro": "Master the endings that actually occur."},
    {"slug": "attack-defense", "title": "Attack & Defense", "order_idx": 10,
     "intro": "Attack a king correctly; survive when attacked."},
    {"slug": "practical", "title": "Practical Play: Winning Real Games", "order_idx": 11,
     "intro": "Convert skill into rating."},
    {"slug": "capstone", "title": "Mastery Capstone", "order_idx": 12,
     "intro": "Prove it all."},
]

# v1 item id -> (stage_slug, order_idx within stage)
V1_PLACEMENT: dict[str, tuple[str, int]] = {
    # Stage 1
    "kq-mate": ("board-vision", 3),
    "backrank": ("board-vision", 6),
    # Stage 2
    "fork": ("tactics-1", 1),
    "pin": ("tactics-1", 2),
    "skewer": ("tactics-1", 3),
    "discovered": ("tactics-1", 4),
    # Stage 3
    "principles": ("openings-white", 1),
    "italian": ("openings-white", 2),
    "london": ("openings-white", 3),
    "traps": ("openings-white", 4),
    "damiano": ("openings-white", 5),
    # Stage 4
    "opposition": ("endgames-1", 1),
    "oppo-drill": ("endgames-1", 2),
    "square-rule": ("endgames-1", 3),
    "skewer-race": ("endgames-1", 4),
    # Stage 5
    "deflection": ("tactics-2", 1),
    "smothered": ("tactics-2", 2),
    # Stage 6
    "ruy": ("counter-openings", 1),
    "queens-gambit": ("counter-openings", 2),
    "sicilian": ("counter-openings", 3),
    "caro": ("counter-openings", 4),
    # Stage 7
    "cct": ("calculation", 1),
    "signals": ("calculation", 2),
    "defend": ("calculation", 3),
    "anastasia": ("calculation", 5),
    # Stage 9
    "lucena": ("endgames-2", 1),
    "philidor": ("endgames-2", 2),
}
