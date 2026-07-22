# Claude Design brief — "The Study" visual redesign

> Paste everything under the line into Claude Design. It is written as a direct instruction to
> the designer. It is deliberately strict about **what not to touch** so the redesign can't break
> the working backend/socket logic. Keep this file in sync if the design direction changes.

---

You are redesigning the front-end of **The Study**, a production chess-training web app, to make it
genuinely beautiful. The engineering is done and working — your job is **visual and interaction
polish only**. Treat this as an art-direction and CSS/markup pass, not a rewrite.

## What the product is

A single-page app where people learn and play chess: a gated 12-stage **learning path** with boss
checkpoints, **online play** vs humans, **bot games with a 5-level live coach**, **puzzle duels**,
friends/presence, leaderboards, achievements, XP and streaks. It is a solo **portfolio piece** — it
needs to look like the work of someone who sweats craft. Right now it is functional but flat and
sloppy: weak hierarchy, monotone slabs, uniform spacing, sharp corners, no depth, no texture, and a
grab-bag of Unicode-glyph icons that read as placeholder. Fix that.

## The identity to amplify (don't reinvent it)

The brand is **"a 19th-century chess study / gentleman's reading room."** Tagline: *"Chess beyond
the rules."* Think walnut wood, aged parchment, brass fittings, letterpress typography, engraved
diagrams from an old chess manual, leather and lamplight. It is **dark-first** (walnut room) with
**parchment as the lit surface**. Refine and enrich this — do **not** switch to a generic
SaaS/neon/glassmorphism look.

### Exact design tokens — preserve these, extend around them

These live in `frontend/src/styles/index.css` as a Tailwind v4 `@theme` block (CSS-first config, no
`tailwind.config.js`). Keep every token name; you may **add** tokens (e.g. elevation, richer
parchment ramp, wood-grain gradients) but do not delete or repurpose the existing ones.

```
walnut-950 #1a140e   walnut-900 #221a12   walnut-800 #2e2418   walnut-700 #372c1e
walnut-line #4a3b28  (borders/hairlines)
parchment #f3e9d2    parchment-ink #33281a   parchment-muted #7a6a50
cream #efe6d6        muted #b3a289
gold #d9a441         correct #8cb65e         wrong #c8503c
board-light #e9d7b4  board-dark #a97a4c
Fonts: Fraunces (display serif), Atkinson Hyperlegible (body), JetBrains Mono (labels/numerals)
```

Accessibility is part of the brand: Atkinson Hyperlegible was chosen on purpose. Keep body text at
**WCAG AA contrast**, keep numerals/labels in JetBrains Mono, never sacrifice legibility for mood.

## Design direction — how to make it beautiful

1. **Give surfaces depth and material.** Replace flat single-fill panels with layered walnut: soft
   top-lit gradients, a barely-there wood/paper grain (subtle SVG or CSS noise, ≤3% opacity),
   hairline `walnut-line` borders, and a real **elevation system** (define 3–4 shadow levels; the
   room is lit from above). Parchment cards should feel like paper laid on a desk — warm inner
   glow, faint deckled edge, a thin darker keyline.
2. **Typography as the hero.** Fraunces is a gorgeous display serif — use its optical sizes and
   italics. Establish a real type scale (display / H1 / H2 / body / caption / mono-label). Page
   titles should feel *engraved*: generous size, tight leading, small-caps or letterspaced mono
   eyebrows above them. Numbers (clocks, Elo, XP, accuracy) always JetBrains Mono, tabular.
3. **Replace the Unicode-glyph icons with one coherent icon set.** The nav currently uses `§ ⚔ ⚡ ☰
   ↑ ☗ ◆ ❦ ⚙ ✎` — inconsistent weights and baselines. Commission a single **inline-SVG** set,
   stroke-based, ~1.5px, in a refined engraved style (or a curated line set). Chess-flavored where
   it helps (path = pawn-to-crown, duel = crossed swords, achievements = a rosette/medal). Inline
   the SVGs — **no external icon CDN** (CSP-safe, offline-safe).
4. **Elevate the chessboard into a framed centrepiece.** Give it a turned-wood / brass frame with
   file–rank engraving in the margin, a soft drop shadow onto the desk, and refined last-move /
   check / selected / legal-target states (the current dots and gold arrows are fine conceptually —
   make them elegant). The board is the emotional center of Play, Learn, Duel and Boss screens.
5. **Rhythm and spacing.** Adopt a consistent spacing scale and vertical rhythm. Add breathing room;
   group related controls; use dividers and eyebrow labels instead of cramming. Soften the pervasive
   `rounded-xs` into a considered radius system (cards a touch rounder, chips pill-shaped, the board
   frame square). 
6. **Motion, restrained and tasteful.** 150–250ms ease transitions on hover/press/nav-active; a
   gentle rise on card mount; the eval bar animates; the level-up toast has a single elegant shimmer
   (no confetti). Respect `prefers-reduced-motion`.
7. **States are not optional.** Design **empty**, **loading** (skeletons in parchment/walnut, not
   spinners where avoidable), **error**, and **disabled** states for every list and panel. A learner
   with no games yet should still see a beautiful screen.

## Screen-by-screen (every route needs a pass)

- **App shell / sidebar** (`components/Layout.tsx`): the fixed left rail (♞ "The Study" lockup,
  nav, the **Lv / 🔥streak / XP-bar** footer, user chip + Sign out). Make the lockup feel like a
  bookplate; make the active-nav treatment richer than the current left-border. Mobile is a bottom-
  left FAB → drawer — redesign both. Also style the floating **reward toasts** and the **incoming-
  challenge banner** (parchment card, bottom-right).
- **The Path** (`features/learn/PathPage.tsx`): 12 stages, each item in DONE / AVAILABLE / LOCKED
  states, stage bosses marked 👑, a progress bar. This should feel like a **map / manuscript
  index** you climb — the signature screen. Make locked vs available unmistakable and enticing.
- **Lesson & Drill players** (`features/learn/`): board + step text + hint reveal + move list +
  takeaways. Editorial "open manual" feel.
- **Boss challenge** (`features/learn/BossChallenge.tsx`): the parchment **briefing card**
  (objective / your color / the bot) → the game → a pass/fail verdict. Make the briefing feel like
  a sealed challenge; make pass feel earned.
- **Play** (`features/play/`): the **lobby** (mode toggle Human/Learn/Bot Arena, coach-level L1–L5,
  bot-level 1–8, time-control presets `1+0 3+2 5+0 10+5 15+10 30+0 ∞`, rated switch, start button)
  and the **live game** (framed board, two **clocks** with active-side emphasis, move list, draw/
  resign, result card with Elo delta). The **CoachPanel** (`CoachPanel.tsx`) is special: eval
  readout + bar, move-verdict chips (great/good/inaccuracy/mistake/blunder — use `correct`/`gold`/
  `wrong`), the **hint** button + on-board gold arrow, **takeback**, and the L1 *"the coach winces"*
  blunder-confirm dialog. Design the verdict chips and the eval bar as jewels of the UI.
- **Puzzle Duel** (`features/duel/DuelPage.tsx`): head-to-head tactics race — shared 180s timer,
  your/opponent score cards with **combo flames**, opponent progress ticker, result screen. Make it
  feel live and competitive without leaving the walnut world.
- **Friends** (`pages/FriendsPage.tsx`): search, requests inbox, friend list with **presence dots**
  (online/in-game/in-duel/offline) and challenge/remove/block actions.
- **Leaderboards** (`pages/LeaderboardPage.tsx`): per-mode (online/bot/duel), global/friends
  scopes. Ranked table with a distinguished top-3.
- **Profile** (`pages/ProfilePage.tsx`): **level ring + XP bar**, per-mode ratings, a **rating
  sparkline**, streak, and an **achievement showcase**. This is the trophy room — make it shine.
- **Achievements** (`pages/AchievementsPage.tsx`): ~40 badges in locked/unlocked states. Design a
  gorgeous **medal/rosette** badge component; locked = embossed/desaturated, unlocked = gold.
- **Archive** (`pages/GamesPage.tsx`): finished-game rows (result / time-control / reason / Elo
  delta / PGN download) and the **review** view (per-move tags + accuracy). Ledger aesthetic.
- **Content Studio (admin)** (`pages/AdminPage.tsx`): stage/item lists with draft/live badges, the
  item editor (metadata form + JSON editor + **live board preview** + validate/publish). Make it
  feel like a professional CMS, still in-world.
- **Auth** (`pages/AuthPages.tsx`): login / register / Google button on a parchment card. This is
  the first impression — give it a hero-worthy walnut backdrop.
- **Settings** (`pages/SettingsPage.tsx`): account (username/avatar). (Board-theme + sound toggles
  are a planned addition — leave room for them.)

## Hard constraints — DO NOT BREAK THESE

**Restyle only. Do not change behavior, data flow, or contracts.** Specifically, do **not** modify:

- Any store logic or its public API: `features/play/gameStore.ts`, `features/social/socialStore.ts`,
  `features/duel/duelStore.ts`, `features/stats/statsStore.ts`, `features/stats/rewardToast.tsx`
  (you may restyle the toast's markup, not its exported functions/signals).
- The network layer: `lib/api.ts`, `lib/auth.tsx`, and **every** `api.*(...)` call and WebSocket
  `send(...)` / message-`type` string. The socket message contract is fixed (`game:move`,
  `coach:info`, `coach:hint`, `queue:*`, `xp:update`, `duel:*`, etc.). Don't rename, add, or drop
  message types or fields.
- Routing (`App.tsx`) — keep every route path and the route↔component mapping.
- `components/Board.tsx` **move-input logic** (square click handling, coordinate math, the `ref`
  hooks, orientation, auto-queen). You may restyle it and `styles/board.css` freely, but the
  interaction/prediction logic must keep working unchanged.
- Component **prop shapes, exported names, and file locations.** Add presentational subcomponents if
  useful, but don't reshuffle the module graph.

**Also:**
- Stack is **React 19 + TypeScript (strict) + Vite + Tailwind v4** (CSS-first `@theme`; no
  `tailwind.config.js`) + react-router 7. Output must compile under `tsc --strict` and `eslint`.
- **No external runtime assets**: inline SVGs, no icon/font CDNs beyond the existing Google Fonts
  `<link>` (Fraunces / Atkinson Hyperlegible / JetBrains Mono are already loaded in `index.html`).
- **No heavyweight UI kits** (no MUI/Chakra/AntD). Tailwind utilities + small local components +
  hand-authored CSS/SVG only. Keep the bundle lean.
- Single dark walnut theme — no light-mode variant needed (parchment is the light *surface*, not a
  light *mode*).
- Keep it responsive: the desktop rail collapses to the existing mobile drawer; the board and wide
  tables must never cause horizontal body scroll.

## How to deliver

Work screen-by-screen. For each: state the intent in a sentence, then provide the updated
`.tsx`/CSS. Start by proposing the **foundations** — the extended `@theme` tokens (elevation, grain,
parchment ramp), the type scale, the shared primitives (Card, Chip, Button, Badge, StatTile, the
board Frame, the inline-SVG icon set) — then apply them across the pages. Prioritize the four
highest-impact surfaces first: **Auth (first impression), The Path (signature), Play + CoachPanel
(the core loop), Profile/Achievements (the reward).**
