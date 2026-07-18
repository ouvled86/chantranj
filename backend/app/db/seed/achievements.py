"""The 40 launch achievements. condition_json is declarative; the Phase 8
achievement engine evaluates it against domain events."""

from typing import Any


def _a(
    slug: str, title: str, desc: str, icon: str, category: str, xp: int, **cond: Any
) -> dict[str, Any]:
    return {
        "slug": slug,
        "title": title,
        "description": desc,
        "icon": icon,
        "category": category,
        "xp": xp,
        "condition_json": cond,
    }


ACHIEVEMENTS: list[dict[str, Any]] = [
    # --- Learning ---
    _a("first-steps", "First Steps", "Complete your first lesson or drill", "§",
       "learning", 25, event="item_done", count=1),
    *[
        _a(f"stage-{i}-clear", f"Stage {i} Cleared", f"Finish every item in Stage {i}", "▣",
           "learning", 50 + 10 * i, event="stage_done", stage_order=i)
        for i in range(1, 13)
    ],
    _a("bookworm", "Bookworm", "Complete every lesson in the Study", "❦",
       "learning", 300, event="all_lessons_done"),
    # --- Tactics ---
    _a("first-blood", "First Blood", "Solve your first drill", "⚔",
       "tactics", 25, event="drill_done", count=1),
    _a("fork-master", "Fork Master", "Solve 10 fork puzzles", "♘",
       "tactics", 75, event="puzzle_theme", theme="fork", count=10),
    _a("pin-cushion", "Pin Cushion", "Solve 10 pin puzzles", "📌",
       "tactics", 75, event="puzzle_theme", theme="pin", count=10),
    _a("skewered", "Skewered", "Solve 10 skewer puzzles", "⇉",
       "tactics", 75, event="puzzle_theme", theme="skewer", count=10),
    _a("duel-wins-10", "Duelist", "Win 10 puzzle duels", "⚡",
       "tactics", 100, event="duel_win", count=10),
    _a("duel-wins-25", "Sharpshooter", "Win 25 puzzle duels", "⚡",
       "tactics", 200, event="duel_win", count=25),
    _a("duel-wins-50", "Tactician Supreme", "Win 50 puzzle duels", "⚡",
       "tactics", 400, event="duel_win", count=50),
    _a("combo-8", "Combo ×8", "Hit an 8-puzzle streak in a duel", "🔥",
       "tactics", 150, event="duel_combo", count=8),
    # --- Playing ---
    _a("first-win", "First Win", "Win your first game", "♔",
       "playing", 50, event="game_win", count=1),
    _a("giant-slayer", "Giant Slayer", "Beat Bot 8 in the Arena", "🗡",
       "playing", 500, event="bot_beaten", bot_level=8),
    _a("flagged", "Flagged!", "Win a game on time", "⏱",
       "playing", 75, event="game_win", reason="timeout"),
    _a("comeback", "The Comeback", "Win a game after being down -5 in eval", "↺",
       "playing", 150, event="game_win", comeback=True),
    _a("marathon", "Marathon", "Win a classical (30+ min) game", "🏛",
       "playing", 100, event="game_win", time_class="classical"),
    _a("century", "Centurion", "Play 100 games", "Ⅽ",
       "playing", 200, event="games_played", count=100),
    # --- Social ---
    _a("first-friend", "Study Partner", "Add your first friend", "🤝",
       "social", 25, event="friend_added", count=1),
    _a("challenger-10", "Challenger", "Play 10 friend challenges", "🎯",
       "social", 100, event="challenge_played", count=10),
    _a("spectator", "Spectator", "Watch a friend's game live", "👁",
       "social", 25, event="spectated", count=1),
    # --- Dedication ---
    _a("streak-7", "One Week Strong", "7-day activity streak", "🔥",
       "dedication", 75, event="streak", count=7),
    _a("streak-30", "Monthly Devotee", "30-day activity streak", "🔥",
       "dedication", 250, event="streak", count=30),
    _a("streak-100", "The Dedicated", "100-day activity streak", "🔥",
       "dedication", 750, event="streak", count=100),
    _a("night-owl", "Night Owl", "Finish a game between midnight and 5am", "🦉",
       "dedication", 25, event="game_done", hour_range=[0, 5]),
    _a("early-bird", "Early Bird", "Finish a lesson before 8am", "🐦",
       "dedication", 25, event="item_done", hour_range=[5, 8]),
    _a("level-10", "Level 10", "Reach level 10", "★",
       "dedication", 100, event="level", count=10),
    _a("level-25", "Level 25", "Reach level 25", "★",
       "dedication", 250, event="level", count=25),
    _a("level-50", "Level 50", "Reach level 50", "★",
       "dedication", 500, event="level", count=50),
    _a("graduate", "Graduate of the Study", "Beat the final capstone boss", "🎓",
       "learning", 1000, event="item_done", item="capstone-final-boss"),
]
