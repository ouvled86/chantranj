/** Online-play state: one socket, one store, plain React subscription. */

import { useSyncExternalStore } from 'react';
import { api, type RewardSummary } from '../../lib/api';
import { showReward } from '../stats/rewardToast';

export interface ServerGameState {
  game_id: number;
  fen: string;
  turn: 'w' | 'b';
  clocks: { w: number | null; b: number | null };
  last_move: string | null;
  moves: { uci: string; san: string }[];
  status: string;
  draw_offer_by: number | null;
  white_id: number;
  black_id: number | null;
  bot_level?: number | null;
  coach_level?: number | null;
  hints_used?: number;
  takebacks_used?: number;
}

export interface GameOver {
  result: 'WHITE' | 'BLACK' | 'DRAW' | 'ABORTED';
  reason: string;
  rating_delta: { w: number | null; b: number | null };
}

export interface CoachState {
  evalCp: number | null;
  tag: string | null;
  note: string | null;
  critical: boolean;
  hintMove: string | null;
  hintsLeft: number | null; // null = unlimited
  takebacksLeft: number | null;
  pendingConfirm: { from: string; to: string; promo: string; tag?: string } | null;
  showEval: boolean; // L3 on-demand toggle
}

const COACH_INIT: CoachState = {
  evalCp: null,
  tag: null,
  note: null,
  critical: false,
  hintMove: null,
  hintsLeft: null,
  takebacksLeft: null,
  pendingConfirm: null,
  showEval: true,
};

export interface PlayState {
  connection: 'closed' | 'connecting' | 'open';
  phase: 'idle' | 'queued' | 'playing' | 'over';
  myColor: 'w' | 'b' | null;
  opponent: { username: string; rating: number } | null;
  game: ServerGameState | null;
  over: GameOver | null;
  opponentConnected: boolean;
  clockSyncAt: number; // Date.now() when clocks last arrived
  error: string | null;
  coach: CoachState;
}

let state: PlayState = {
  connection: 'closed',
  phase: 'idle',
  myColor: null,
  opponent: null,
  game: null,
  over: null,
  opponentConnected: true,
  clockSyncAt: 0,
  error: null,
  coach: COACH_INIT,
};

const listeners = new Set<() => void>();
let socket: WebSocket | null = null;

function setState(patch: Partial<PlayState>) {
  state = { ...state, ...patch };
  listeners.forEach((l) => l());
}

export function usePlayState(): PlayState {
  return useSyncExternalStore(
    (cb) => {
      listeners.add(cb);
      return () => listeners.delete(cb);
    },
    () => state,
  );
}

function wsUrl(): string {
  const proto = location.protocol === 'https:' ? 'wss' : 'ws';
  return `${proto}://${location.host}/ws/game`;
}

function handleMessage(msg: { type: string; data: Record<string, unknown> }) {
  const d = msg.data as never;
  switch (msg.type) {
    case 'queue:waiting':
      setState({ phase: 'queued' });
      break;
    case 'queue:matched': {
      const m = d as { game_id: number; color: 'w' | 'b'; opponent: PlayState['opponent'] };
      sessionStorage.setItem('activeGameId', String(m.game_id));
      setState({
        phase: 'playing',
        myColor: m.color,
        opponent: m.opponent,
        over: null,
        coach: { ...COACH_INIT },
      });
      break;
    }
    case 'game:state':
    case 'game:move': {
      const g = d as ServerGameState;
      // The final move can arrive right after game:over — update the board
      // but never resurrect a finished game.
      setState({
        game: g,
        clockSyncAt: Date.now(),
        ...(state.phase !== 'over' ? { phase: 'playing' as const } : {}),
      });
      break;
    }
    case 'game:draw_offer': {
      const g = state.game;
      if (g) setState({ game: { ...g, draw_offer_by: (d as { by: number }).by } });
      break;
    }
    case 'game:draw_declined': {
      const g = state.game;
      if (g) setState({ game: { ...g, draw_offer_by: null } });
      break;
    }
    case 'game:over':
      sessionStorage.removeItem('activeGameId');
      setState({ phase: 'over', over: d as GameOver });
      break;
    case 'game:opponent_connection':
      setState({ opponentConnected: (d as { connected: boolean }).connected });
      break;
    case 'xp:update':
      showReward(d as RewardSummary);
      break;
    case 'coach:info': {
      const info = d as {
        eval_cp?: number;
        tag?: string;
        note?: string;
        critical?: boolean;
        hints_left?: number | null;
        takebacks_left?: number | null;
        moved_by?: 'w' | 'b';
      };
      // Only the human's own move produces a verdict. The bot's reply sends a
      // tagless refresh (moved_by === 'b') that must update the eval bar WITHOUT
      // wiping the verdict/hint the player is still reading.
      const afterHuman = info.moved_by !== 'b';
      setState({
        coach: {
          ...state.coach,
          evalCp: info.eval_cp ?? state.coach.evalCp,
          hintsLeft: info.hints_left ?? null,
          takebacksLeft: info.takebacks_left ?? null,
          ...(afterHuman
            ? {
                tag: info.tag ?? null,
                note: info.note ?? null,
                critical: info.critical ?? false,
                hintMove: null, // the human just moved — the old hint arrow is stale
              }
            : {}),
        },
      });
      break;
    }
    case 'coach:hint': {
      const h = d as { move: string; hints_left: number | null };
      setState({
        coach: { ...state.coach, hintMove: h.move, hintsLeft: h.hints_left ?? null },
      });
      break;
    }
    case 'coach:premove_verdict': {
      const v = d as { from: string; to: string; promo: string; ok: boolean; tag?: string };
      if (v.ok) {
        send('game:move', {
          game_id: state.game?.game_id,
          from: v.from,
          to: v.to,
          promo: v.promo,
        });
        setState({ coach: { ...state.coach, pendingConfirm: null } });
      } else {
        setState({
          coach: {
            ...state.coach,
            pendingConfirm: { from: v.from, to: v.to, promo: v.promo, tag: v.tag },
          },
        });
      }
      break;
    }
    case 'error':
      setState({ error: (d as { message: string }).message });
      setTimeout(() => setState({ error: null }), 3500);
      break;
  }
}

function send(type: string, data: Record<string, unknown> = {}) {
  if (socket?.readyState === WebSocket.OPEN) socket.send(JSON.stringify({ type, data }));
}

export function connect(): void {
  if (socket && socket.readyState <= WebSocket.OPEN) return;
  setState({ connection: 'connecting' });
  socket = new WebSocket(wsUrl());
  socket.onopen = () => {
    setState({ connection: 'open' });
    const activeId = sessionStorage.getItem('activeGameId');
    if (activeId) send('game:rejoin', { game_id: Number(activeId) });
  };
  socket.onmessage = (ev) => handleMessage(JSON.parse(ev.data));
  socket.onclose = () => {
    setState({ connection: 'closed' });
    socket = null;
    // Auto-reconnect while a game is (or may be) running.
    if (state.phase === 'playing' || sessionStorage.getItem('activeGameId')) {
      setTimeout(connect, 1000);
    }
  };
}

export const BOT_ANCHORS: Record<number, number> = {
  1: 600, 2: 800, 3: 1000, 4: 1200, 5: 1400, 6: 1700, 7: 2000, 8: 2300,
};

/** Boss games route through the learn endpoint; the store tracks which boss so
 *  the challenge screen can verify the objective when the game ends. */
export async function startBossGame(
  slug: string,
  playerColor: 'white' | 'black',
  label: string,
): Promise<void> {
  const r = await api.post<{ game_id: number }>(`/api/v1/learn/items/${slug}/boss/start`);
  sessionStorage.setItem('activeGameId', String(r.game_id));
  bossSlug = slug;
  setState({
    phase: 'playing',
    myColor: playerColor === 'white' ? 'w' : 'b',
    opponent: { username: label, rating: 0 },
    over: null,
    game: null,
    coach: { ...COACH_INIT },
  });
  connect();
  rejoinActive();
}

let bossSlug: string | null = null;
export function activeBossSlug(): string | null {
  return bossSlug;
}
export function clearBoss(): void {
  bossSlug = null;
}

function rejoinActive(): void {
  const id = sessionStorage.getItem('activeGameId');
  if (id && socket?.readyState === WebSocket.OPEN) {
    send('game:rejoin', { game_id: Number(id) });
  }
}

export async function startBotGame(
  level: number,
  baseMin: number | null,
  incSec: number,
  rated: boolean,
  coachLevel: number | null = null,
): Promise<void> {
  const r = await api.post<{ game_id: number }>('/api/v1/games', {
    bot_level: level,
    coach_level: coachLevel,
    time_control: { base_min: baseMin, inc_sec: incSec },
    rated,
  });
  sessionStorage.setItem('activeGameId', String(r.game_id));
  setState({
    phase: 'playing',
    myColor: 'w',
    opponent: {
      username: coachLevel ? `Coach L${coachLevel} · Bot ${level}` : `Stockfish · Bot ${level}`,
      rating: BOT_ANCHORS[level],
    },
    over: null,
    game: null,
    coach: { ...COACH_INIT },
  });
  connect();
  rejoinActive();
}

/** Attach to a game created elsewhere (e.g. an accepted friend challenge). */
export function attachGame(gameId: number, color: 'w' | 'b', opponent: string): void {
  sessionStorage.setItem('activeGameId', String(gameId));
  setState({
    phase: 'playing',
    myColor: color,
    opponent: { username: opponent, rating: 0 },
    over: null,
    game: null,
    coach: { ...COACH_INIT },
  });
  connect();
  rejoinActive();
}

/** L1 routes through the blunder check; everyone else moves directly. */
export function sendMoveSmart(from: string, to: string, promo = ''): void {
  const coachLevel = state.game?.coach_level;
  if (coachLevel === 1) {
    send('coach:premove', { game_id: state.game?.game_id, from, to, promo });
  } else {
    sendMove(from, to, promo);
  }
}

export function confirmPendingMove(play: boolean): void {
  const pending = state.coach.pendingConfirm;
  setState({ coach: { ...state.coach, pendingConfirm: null } });
  if (play && pending) {
    sendMove(pending.from, pending.to, pending.promo);
  }
}

export function requestHint(): void {
  if (state.game) send('coach:hint', { game_id: state.game.game_id });
}

export function requestTakeback(): void {
  if (state.game) send('coach:takeback', { game_id: state.game.game_id });
}

export function toggleEval(): void {
  setState({ coach: { ...state.coach, showEval: !state.coach.showEval } });
}

export function joinQueue(baseMin: number | null, incSec: number, rated: boolean): void {
  connect();
  const doSend = () =>
    send('queue:join', { time_control: { base_min: baseMin, inc_sec: incSec }, rated });
  if (socket?.readyState === WebSocket.OPEN) doSend();
  else socket?.addEventListener('open', doSend, { once: true });
  setState({ phase: 'queued', over: null, game: null });
}

export function leaveQueue(): void {
  send('queue:leave');
  setState({ phase: 'idle' });
}

export function sendMove(from: string, to: string, promo = ''): void {
  if (state.game) send('game:move', { game_id: state.game.game_id, from, to, promo });
}

export function resign(): void {
  if (state.game) send('game:resign', { game_id: state.game.game_id });
}

export function offerDraw(): void {
  if (state.game) send('game:draw_offer', { game_id: state.game.game_id });
}

export function respondDraw(accept: boolean): void {
  if (state.game) send('game:draw_respond', { game_id: state.game.game_id, accept });
}

export function backToLobby(): void {
  setState({
    phase: 'idle',
    game: null,
    over: null,
    myColor: null,
    opponent: null,
    coach: { ...COACH_INIT },
  });
}
