# Shantranj — redesign handoff

> **STATUS (synced 2026-07-26):** the package below is **merged into `frontend/`** and verified
> (tsc -b, eslint, 9 unit tests, 2 Playwright e2e, live browser). The staging folder
> `frontend-v2/` has been deleted — this file survives for the **"Applying the system to the
> remaining screens"** recipes at the bottom, which are still TODO.
>
> Two fixes were needed on top of the package as delivered:
> 1. `PlayPage.tsx` — `game.coach_level !== null` failed `tsc -b` (TS18048): the field is
>    optional, so `undefined` survives the guard. Changed to `!= null`. (The package's
>    "compiles under tsc --strict" claim didn't hold; note `tsc -p tsconfig.json` is a no-op
>    here because the root config is `files: []` + references — the real gate is `tsc -b`.)
> 2. `CoachPanel.tsx` `EvalBar` — `h-full` collapsed the bar to 12×2px because the flex row
>    has no definite height. Changed to `self-stretch`; now 12×561 beside the board.
>
> Also renamed the app "The Study" → **Shantranj** repo-wide (owner decision): browser title,
> README/CLAUDE/docs, backend `app_name` + PGN `Event` header, engine service title, Grafana
> dashboard title/folder. Machine identifiers (package slugs `the-study-backend`/`-engine`,
> Grafana dashboard `uid`/provider slug, compose container prefix) were deliberately left
> alone — renaming them breaks provisioning identity for no user-visible gain.

Restyle-only package for the four highest-impact surfaces plus foundations, exactly per
`DESIGN_BRIEF.md`. Every file mirrors its path under `frontend/` — sync is a straight copy.
No new dependencies, no CDN assets, no store/socket/routing changes.

## What's in the package

| File | Replaces | What changed |
|---|---|---|
| `frontend/src/styles/index.css` | same path | All original `@theme` tokens preserved verbatim; **adds** walnut/gold/parchment ramp extensions, 3-level elevation shadows (`shadow-e1/e2/e3`), brass button shadow, radius tokens, and shared component classes (`.panel`, `.parchment-card`, `.btn-*`, `.chip`, `.verdict-*`, `.medal`, `.seal`, `.xp-*`, inputs). Includes `prefers-reduced-motion` handling. |
| `frontend/src/styles/board.css` | same path | The framed-centrepiece board: walnut-gradient frame with brass inset, refined last-move/selected/dot states, arrow drop-shadow. Same class hooks — `Board.tsx` logic untouched. |
| `frontend/src/components/icons.tsx` | **new file** | The engraved 1.5px inline-SVG icon set replacing the `§ ⚔ ⚡ ☰ ↑ ☗ ◆ ❦ ⚙ ✎` glyphs. Additive — no module-graph reshuffle. |
| `frontend/src/components/Layout.tsx` | same path | Bookplate lockup (**"Shantranj"**), icon nav with gradient active state, XP footer with flame + track, avatar chip, knight FAB + redesigned drawer, restyled challenge banner. All hooks/effects/handlers identical. |
| `frontend/src/pages/AuthPages.tsx` | same path | Lamplit hero backdrop, knight watermark, parchment card with brass rule. Form logic identical. |
| `frontend/src/features/learn/PathPage.tsx` | same path | Manuscript index: stage medallions + connecting rule, panel item lists, wax-seal bosses, `Begin` / `Face the boss` CTAs, lock/check icons. Same API call, same route links. |
| `frontend/src/features/play/PlayPage.tsx` | same path | Lobby mode cards + pill chips with CTA sub-caption; game screen with presence dot, eval bar beside the board (L1–L2), move ledger, restyled result card. **All state, handlers, `sendMoveSmart`/queue/draw/resign calls are byte-identical logic.** |
| `frontend/src/features/play/CoachPanel.tsx` | same path | Verdict chips as `.verdict-*` jewels, eval readout + horizontal bar, icon buttons, wince dialog. `EvalBar` still exported; level-gating logic unchanged. |
| `frontend/src/features/play/Clock.tsx` | same path | Brass active plate with glow, low-time red state. Timing logic unchanged. |

## How to sync

1. Copy each file over its counterpart (identical relative paths under `frontend/`);
   `icons.tsx` is new — just add it.
2. Rename the app shell strings (the only other places "The Study" is user-visible):
   - `frontend/index.html` → `<title>Shantranj</title>` (fonts already loaded there — no change needed).
   - Optional flavor: `GamesPage.tsx` PGN filename `the-study-game-` → `shantranj-game-`.
3. `npm run build` — compiles under `tsc --strict`; no new eslint surface
   (icons are plain function components, classNames only elsewhere).
4. Run the Playwright smoke: selectors keyed to text ("Sign in", "Find an opponent",
   "Offer draw", nav labels) are preserved.

## Constraint compliance checklist

- ✅ No changes to `gameStore.ts`, `socialStore.ts`, `duelStore.ts`, `statsStore.ts`,
  `rewardToast.tsx` exports, `lib/api.ts`, `lib/auth.tsx`, any `api.*()` call or ws message type.
- ✅ `App.tsx` routing untouched (not included — nothing to change).
- ✅ `Board.tsx` move-input logic untouched (only `board.css` restyled).
- ✅ Prop shapes, exported names, file locations preserved; one additive file (`icons.tsx`).
- ✅ Tailwind v4 CSS-first; no `tailwind.config.js`, no UI kits, no runtime assets beyond
  the existing Google Fonts link.
- ✅ Single dark walnut theme; parchment stays a surface, not a mode.
- ✅ Responsive: rail ≥ md, knight FAB + drawer below; board column uses
  `minmax(360px,600px)` so no horizontal body scroll.

## Applying the system to the remaining screens

The mockups (`Shantranj Redesign.dc.html`, sections 2f–4d) are the spec; these recipes map
them to the shared classes so each page is a mechanical pass:

- **Page headers everywhere**: `.eyebrow-gold` kicker → `.page-title` → `.page-sub`,
  then content. Replace every `text-3xl font-bold` h1 with this stack.
- **ProfilePage**: stat tiles and rating cards = `.panel p-3.5` with `.eyebrow` labels and
  `font-mono text-[26px] tabular-nums` values; level ring = two SVG circles
  (`stroke #2a2014` track, `stroke #d9a441` progress, `strokeDasharray 238.8`,
  offset `238.8 * (1 - pct)`); XP bar = `.xp-track`/`.xp-fill`; showcase tiles =
  `.panel` + `.medal h-[46px] w-[46px]`.
- **AchievementsPage**: row = `.panel flex items-center gap-3.5 p-3` +
  `.medal`/`.medal-locked` (locked rows also `opacity-70`); right column
  `earned` in gold vs `+{xp} xp` muted mono; category headers = `.eyebrow` with an
  `h-px bg-walnut-line/60 flex-1` rule.
- **DuelPage**: your ScoreCard = `.panel` with `chip-active`-style gold border + glow;
  combo = `FlameIcon` + gold dots; opponent ticker = flex row of `h-[5px] flex-1 rounded`
  spans (correct/wrong/walnut-edge); countdown reuses `Clock`'s brass plate classes.
- **BossChallenge**: briefing/verdict = `.parchment-card p-6` + `.rule-gold`, `.seal`
  badge (44px, `CrownIcon`) overlapping the top-right corner; specs table stays the
  dashed-border `dl`, with a red "Failure" row.
- **FriendsPage**: rows = `.panel flex items-center gap-3 px-3.5 py-2.5`; presence dot
  gets `shadow-[0_0_6px_...]` glow when online/in-game; Challenge = gold-outline chip,
  disabled at `opacity-40`; search = `.input-dark` with `SearchIcon`.
- **LeaderboardPage**: keep the `<table>`; top-3 rank cells get 26px `.medal`
  (gold/silver `#a9a294`/bronze `#a06636` radial variants); `is_me` row =
  `bg-gradient-to-r from-gold/[.12] to-transparent` + `border-l-2 border-gold`.
- **GamesPage**: rows = `.panel px-4 py-3`; outcome word stays mono/uppercase colored;
  review panel = inner `rounded-[6px] bg-[#14100a] border-walnut-line/60`; move tags keep
  the existing `TAG_COLOR` map (colors match `.verdict-*`).
- **Lesson/Drill players (`player-ui.tsx`)**: `NoteCard` → `.parchment-card` +
  `.rule-gold`; `PlayerButton` → `.btn-primary` / `.btn-secondary`; hint banner =
  gold `.verdict-inaccuracy`-toned box with `BoltIcon`; wrong feedback = wrong-toned box.
- **AdminPage**: three columns become `.panel`-backed lists with the nav active-gradient
  treatment; live/draft = bordered mono micro-badges (correct/wrong); JSON textarea =
  `bg-[#14100a] border-walnut-edge rounded-[6px] shadow-inner`; keep the preview `Board`.
- **SettingsPage**: form in `.panel p-5` with `.input-dark`; add the dashed-border
  "board room" panel (theme swatches + sound toggle, `coming soon` badge) as reserved space.
- **rewardToast.tsx** (markup only): toast = dark `.panel` with `border-gold/40`,
  `RosetteIcon` + gold mono `+XP`; level-up gets a one-shot `toast-shimmer` gradient sweep
  (keyframes already in `index.css`). Do not touch `showReward`/`useToasts`.

## Design rules to hold the line on

- Numerals (clocks, Elo, XP, accuracy) are always JetBrains Mono `tabular-nums`.
- Max two background colors per screen: the desk gradient + `.panel`. Parchment only for
  "documents": auth, notes, briefings, results, challenge banner.
- Radius system: chips pill (999px), controls 6px, cards 8px, board frame square.
- Motion 150–250ms ease only; `prefers-reduced-motion` is already global.
- Body text ≥ 14px on `#221a12` uses `#c9bda6` or lighter (AA); gold text is `#e0b464`+.
