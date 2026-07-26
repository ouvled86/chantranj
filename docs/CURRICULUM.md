# CURRICULUM — Shantranj learning path

The redesigned educative content: a **single gated path**, easy → hard, that a normal user
walks linearly (finish an item to unlock the next; beat the stage **boss** to unlock the next
stage). Admins author/manage all of it via the CMS (TASKS Phase 6) and bypass gating.

Design targets: cover the skills that actually move a casual player's strength and Elo —
board vision → tactics → openings → endgames → strategy → calculation → attack/defense →
practical tournament skills. Every stage mixes lesson (§) and drill (⚔) items and ends with
a boss fight (👑) played against a bot with a verified objective.

**Reused v1 items are marked `(v1:id)` — their content ships as-is in seeds.**
Unmarked items are the authoring backlog (Phase 6.8–6.10). Target ≈ 70 items total.

---

## Stage 1 — Board Vision & Mating Fundamentals
*Goal: never miss what's on the board; finish won games.*
1. § Reading the board: lines, diagonals, knight webs (new)
2. ⚔ Vision drills: find all checks / all captures in 3 positions (new)
3. § Mating with king & queen — box method `(v1:kq-mate)`
4. § Mating with king & rook — the fence method (new)
5. ⚔ Stalemate traps: 3 "don't blow it" drills (new)
6. § The back-rank mate `(v1:backrank →` converted to lesson intro `)` + ⚔ drill `(v1:backrank)`
7. 👑 **Boss:** K+Q vs K vs bot — mate in ≤20 moves, stalemate = fail

## Stage 2 — Tactics I: The Big Four
*Goal: fork, pin, skewer, discovery — see them instantly.*
1. ⚔ The knight fork `(v1:fork)`
2. ⚔ The pin — then pile on `(v1:pin)`
3. ⚔ The skewer `(v1:skewer)`
4. ⚔ The discovered attack `(v1:discovered)`
5. § Loose pieces & LPDO (expanded from `v1:signals` signal 2) (new)
6. ⚔ Mixed-motif set: 6 puzzles, motif unlabeled (new)
7. 👑 **Boss:** beat Bot 1, any time control ≥5+0

## Stage 3 — Opening Principles & First Repertoire (White)
*Goal: reach a playable middlegame every game as White.*
1. § The three opening promises `(v1:principles)`
2. § The Italian Game `(v1:italian)`
3. § The London System `(v1:london)`
4. § Traps you must know `(v1:traps)`
5. ⚔ Punish 2...f6 `(v1:damiano)`
6. ⚔ Opening quiz: find the principled move ×5 (new)
7. 👑 **Boss:** beat Bot 2 as White from the standard start

## Stage 4 — Endgames I: Pawns & Promotion
*Goal: convert extra material; hold worse endings.*
1. § King & pawn: the opposition `(v1:opposition)`
2. ⚔ Only one move wins `(v1:oppo-drill)`
3. ⚔ Rule of the square `(v1:square-rule)`
4. ⚔ Win the pawn race `(v1:skewer-race)`
5. § Outside passed pawns & king activity (new)
6. ⚔ Pawn endgame decision drills ×4 (new)
7. 👑 **Boss:** convert K+P vs K (winning setup) vs bot — promote or mate, draw = fail

## Stage 5 — Tactics II: Combinations
*Goal: chain motifs into 2–3 move combinations.*
1. ⚔ Deflection: the overworked defender `(v1:deflection)`
2. § The smothered mate `(v1:smothered)`
3. § Zwischenzug — the in-between move (new)
4. § Removing the defender & overloading (new)
5. ⚔ X-ray, clearance and interference set (new)
6. ⚔ Trapped pieces: hunt set ×4 (new)
7. 👑 **Boss:** beat Bot 3, OR win 3 puzzle-duel games vs bot pacer (decide in implementation)

## Stage 6 — Counter-Openings (Black) & Opening Understanding
*Goal: a complete answer to 1.e4 and 1.d4; understand *why* openings work.*
1. § The Ruy Lopez, demystified `(v1:ruy)`
2. § The Queen's Gambit `(v1:queens-gambit)`
3. § Countering 1.e4: the Sicilian `(v1:sicilian)`
4. § Countering 1.e4: the Caro-Kann `(v1:caro)`
5. § Meeting 1.d4: QGD triangle basics (new)
6. § Pawn structures your openings create (new)
7. 👑 **Boss:** beat Bot 3 as Black

## Stage 7 — Thinking Ahead: The Calculation Habit
*Goal: a repeatable per-move routine; 3-move depth.*
1. § Checks, Captures, Threats `(v1:cct)`
2. § Reading the attack signals `(v1:signals)`
3. ⚔ See their threat first `(v1:defend)`
4. § Counting: attackers vs defenders arithmetic (new)
5. ⚔ Calculate three moves deep `(v1:anastasia)`
6. ⚔ Visualization: play 3 moves blind, then answer a question (new)
7. 👑 **Boss:** beat Bot 4 in Learn mode at coach level L3+ (coach usage tracked)

## Stage 8 — Strategy I: Pieces & Squares
*Goal: know what to do when there's no tactic.*
1. § Weak squares & outposts (new)
2. § Good bishop, bad bishop, and the bishop pair (new)
3. § Open files, the 7th rank, and rook lifts (new)
4. § Knights vs bishops: closed vs open positions (new)
5. ⚔ "Find the plan" positional quiz ×5 (new)
6. 👑 **Boss:** beat Bot 4 without training wheels (Arena)

## Stage 9 — Endgames II: Rook Endings & Technique
*Goal: master the endings that actually occur.*
1. § Rook endgame I: the Lucena `(v1:lucena)`
2. § Rook endgame II: the Philidor draw `(v1:philidor)`
3. § Rook activity: cut-offs and checking distance (new)
4. § Two connected passers; R vs pawns races (new)
5. ⚔ Rook endgame decision drills ×4 (new)
6. 👑 **Boss:** hold the Philidor draw vs Bot 6 (draw = pass, loss = fail)

## Stage 10 — Attack & Defense
*Goal: attack a king correctly; survive when attacked.*
1. § When to attack: the three preconditions (new)
2. § The Greek Gift sacrifice (Bxh7+) — when it works and when it fails (new)
3. § Pawn storms vs piece attacks; opposite-side castling (new)
4. § Defensive technique: trades, luft, counterplay (new)
5. ⚔ Attack/defense mixed set ×6 (new)
6. 👑 **Boss:** beat Bot 5 in Arena

## Stage 11 — Practical Play: Winning Real Games
*Goal: convert skill into rating.*
1. § Clock management by time control (new)
2. § When to accept/offer draws; playing for two results (new)
3. § How to review your own games (the app's review tools as method) (new)
4. § Openings maintenance: building your personal file (new)
5. ⚔ "Worst move on the board" — avoid the practical blunder ×5 (new)
6. 👑 **Boss:** win 2 of 3 rated games vs Bot 5 (arena, 10+5)

## Stage 12 — Mastery Capstone
*Goal: prove it all.*
1. ⚔ Grand tactics gauntlet: 12 puzzles across all motifs (new)
2. ⚔ Endgame gauntlet: 4 conversions vs bot back-to-back (new)
3. § Where to go from here: study plan beyond Shantranj (new)
4. 👑 **Final Boss:** beat Bot 6 without assistance → unlocks "Graduate of the Study" achievement + profile flair

---

## Authoring backlog summary

| Batch (TASKS ref) | Items | Stages |
|---|---|---|
| 6.8  | ~15 new items | 1–4 |
| 6.9  | ~15 new items | 5–8 |
| 6.10 | ~12 new items + capstone | 9–12 |

Authoring rules (enforced by CMS validator):
- Every FEN parses; every step/line move is legal from its position (python-chess replay).
- Drills: every user move must be uniquely best or the intro must acknowledge alternatives.
- Lessons ≤ 20 steps; drills ≤ 5 user moves; every item has intro + takeaway (outro).
- Voice: the v1 tone — concrete, warm, no fluff, one idea per step, "takeaway" generalizes.

## Gating rules (implemented in Phase 6)

- Item N+1 unlocks when item N is `DONE` (lessons: reached last step; drills: line completed;
  boss: objective verified server-side from the actual game record).
- Stage N+1 unlocks when Stage N boss is `DONE`.
- Admins see and can complete anything; testers can be granted `unlockAll` flag in settings.
- Completion is idempotent; replaying is always allowed (and re-awards no XP except first time).
