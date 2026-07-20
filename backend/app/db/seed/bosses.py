"""The 12 stage-boss checkpoints (docs/CURRICULUM.md). Each is a BOSS LearnItem
placed last in its stage (order_idx 90), so linear gating already enforces
"beat the boss to reach the next stage." Untimed to stay approachable."""

from typing import Any

UNTIMED = {"base_min": None, "inc_sec": 0}


def _boss(
    slug: str,
    stage: str,
    title: str,
    sub: str,
    intro: str,
    outro: str,
    *,
    bot_level: int,
    objective: str,
    player_color: str = "white",
    start_fen: str | None = None,
    move_limit: int | None = None,
) -> dict[str, Any]:
    return {
        "slug": slug,
        "stage_slug": stage,
        "title": title,
        "sub": sub,
        "intro": intro,
        "outro": outro,
        "boss_config": {
            "bot_level": bot_level,
            "objective": objective,
            "player_color": player_color,
            "start_fen": start_fen,
            "move_limit": move_limit,
            "time_control": UNTIMED,
        },
    }


BOSSES: list[dict[str, Any]] = [
    _boss(
        "boss-board-vision", "board-vision", "Boss: the lone king hunt",
        "Deliver checkmate with king and queen — in 20 moves, no stalemate.",
        "You have king and queen against a bare king. Box him to the edge and finish "
        "cleanly — remember the technique, and never stalemate. You have 20 moves.",
        "Clean mating technique. The board holds no more surprises for you.",
        bot_level=1, objective="checkmate", move_limit=20,
        start_fen="4k3/8/8/8/8/8/8/3QK3 w - - 0 1",
    ),
    _boss(
        "boss-tactics-1", "tactics-1", "Boss: first blood",
        "Beat Bot 1 in a full game.",
        "Your first full-game test. Bot 1 is a beginner — spot the loose pieces and the "
        "forks you just learned, and convert.",
        "First scalp taken. The Big Four are yours to wield.",
        bot_level=1, objective="win",
    ),
    _boss(
        "boss-openings-white", "openings-white", "Boss: open with purpose",
        "Beat Bot 2 as White from the standard start.",
        "Play the opening you just studied — center, develop, castle — and punish Bot 2's "
        "loose play.",
        "A principled opening carried you to a win. Repertoire earned.",
        bot_level=2, objective="win",
    ),
    _boss(
        "boss-endgames-1", "endgames-1", "Boss: shepherd the pawn",
        "Convert king and pawn versus king into a win.",
        "One pawn, one king, one job: promote it. Use the opposition and keep your king in "
        "front of the pawn. A draw here is a loss.",
        "Converted. You'll never fumble a winning pawn ending again.",
        bot_level=2, objective="win",
        start_fen="8/8/8/4k3/8/8/4P3/4K3 w - - 0 1",
    ),
    _boss(
        "boss-tactics-2", "tactics-2", "Boss: the combinationalist",
        "Beat Bot 3 in a full game.",
        "Bot 3 defends better. You'll need to chain motifs — deflect a defender, then "
        "strike. Calculate before you commit.",
        "Multi-move combinations land. Your tactical vision is sharpening fast.",
        bot_level=3, objective="win",
    ),
    _boss(
        "boss-counter-openings", "counter-openings", "Boss: fight from the black side",
        "Beat Bot 3 playing Black.",
        "Now defend and counter-attack as Black. Reach a sound structure out of the opening "
        "and turn the tables.",
        "You can win with either colour now. That's a complete player.",
        bot_level=3, objective="win", player_color="black",
    ),
    _boss(
        "boss-calculation", "calculation", "Boss: see it before you play it",
        "Beat Bot 4 in a full game.",
        "Bot 4 punishes loose calculation. Run checks-captures-threats on every move and "
        "look three deep before you commit.",
        "Disciplined calculation beats a real opponent. This is the habit that raises ratings.",
        bot_level=4, objective="win",
    ),
    _boss(
        "boss-strategy-1", "strategy-1", "Boss: the quiet win",
        "Beat Bot 4 with no tactics handed to you.",
        "When there's no combination, improve your worst piece and target weak squares. "
        "Out-position Bot 4 and the tactics will come.",
        "You won a game on understanding, not just tactics. Real strength.",
        bot_level=4, objective="win",
    ),
    _boss(
        "boss-endgames-2", "endgames-2", "Boss: hold the draw",
        "Defend king and pawn versus king — and hold the draw as Black.",
        "You're a pawn down as Black, but the position is a fortress. Take the opposition, "
        "keep your king in front of the pawn, and do NOT lose. A draw is a win here.",
        "You held a dead-equal ending under pressure. Defensive technique: unlocked.",
        bot_level=6, objective="draw", player_color="black",
        start_fen="8/8/8/3k4/8/8/3P4/3K4 b - - 0 1",
    ),
    _boss(
        "boss-attack-defense", "attack-defense", "Boss: storm the castle",
        "Beat Bot 5 in a full game.",
        "Bot 5 is a real test. Build an attack against the king when the conditions are "
        "right — and defend soundly when they aren't.",
        "You out-attacked a strong bot. The initiative is your weapon now.",
        bot_level=5, objective="win",
    ),
    _boss(
        "boss-practical", "practical", "Boss: win the must-win",
        "Beat Bot 5 again — prove the first win wasn't luck.",
        "Consistency is the mark of a rated player. Beat Bot 5 once more, cleanly.",
        "Repeatable results against strong opposition. You're ready for the capstone.",
        bot_level=5, objective="win",
    ),
    _boss(
        "capstone-final-boss", "capstone", "FINAL BOSS: Graduate of the Study",
        "Beat Bot 6 with no assistance. Everything you've learned, one game.",
        "This is it. Bot 6 plays genuinely well. No hints, no coach — just you and the "
        "board. Win, and you graduate.",
        "You beat Bot 6 unaided. You are a Graduate of the Study. Go climb.",
        bot_level=6, objective="win",
    ),
]
