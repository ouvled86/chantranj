/** /ws/duel client: matchmaking + the live puzzle-race loop. */

import { useSyncExternalStore } from 'react';
import type { RewardSummary } from '../../lib/api';
import { showReward } from '../stats/rewardToast';

export interface DuelState {
  phase: 'idle' | 'queued' | 'racing' | 'over';
  duelId: number | null;
  opponent: string;
  fen: string | null;
  puzzleIdx: number;
  total: number;
  score: number;
  combo: number;
  secondsLeft: number;
  lastResult: 'solved' | 'wrong' | 'progress' | null;
  oppScore: number;
  oppCombo: number;
  oppSolved: number;
  result: { your_score: number; opp_score: number; rating_delta: number } | null;
  flash: number; // bump to trigger UI feedback (shake/glow)
}

const INIT: DuelState = {
  phase: 'idle',
  duelId: null,
  opponent: '',
  fen: null,
  puzzleIdx: 0,
  total: 0,
  score: 0,
  combo: 0,
  secondsLeft: 0,
  lastResult: null,
  oppScore: 0,
  oppCombo: 0,
  oppSolved: 0,
  result: null,
  flash: 0,
};

let state: DuelState = { ...INIT };
const listeners = new Set<() => void>();
let socket: WebSocket | null = null;

function setState(patch: Partial<DuelState>) {
  state = { ...state, ...patch };
  listeners.forEach((l) => l());
}

export function useDuel(): DuelState {
  return useSyncExternalStore(
    (cb) => {
      listeners.add(cb);
      return () => listeners.delete(cb);
    },
    () => state,
  );
}

function send(type: string, data: Record<string, unknown> = {}) {
  if (socket?.readyState === WebSocket.OPEN) socket.send(JSON.stringify({ type, data }));
}

function applyProgress(d: {
  fen: string | null;
  puzzle_idx: number;
  total: number;
  score: number;
  combo: number;
  seconds_left: number;
  result?: string;
}) {
  setState({
    fen: d.fen,
    puzzleIdx: d.puzzle_idx,
    total: d.total,
    score: d.score,
    combo: d.combo,
    secondsLeft: d.seconds_left,
    lastResult: (d.result as DuelState['lastResult']) ?? state.lastResult,
    flash: state.flash + 1,
  });
}

function handle(msg: { type: string; data: Record<string, unknown> }) {
  const d = msg.data as never;
  switch (msg.type) {
    case 'duel:waiting':
      setState({ phase: 'queued' });
      break;
    case 'duel:start': {
      const s = d as {
        duel_id: number;
        opponent: string;
        fen: string;
        puzzle_idx: number;
        total: number;
        seconds_left: number;
      };
      setState({
        ...INIT,
        phase: 'racing',
        duelId: s.duel_id,
        opponent: s.opponent,
        fen: s.fen,
        total: s.total,
        secondsLeft: s.seconds_left,
      });
      break;
    }
    case 'duel:progress':
      applyProgress(d);
      break;
    case 'duel:opponent_progress': {
      const o = d as { score: number; combo: number; solved: number };
      setState({ oppScore: o.score, oppCombo: o.combo, oppSolved: o.solved });
      break;
    }
    case 'duel:over': {
      const over = d as { your_score: number; opp_score: number; rating_delta: number; reward?: RewardSummary };
      setState({ phase: 'over', result: over });
      showReward(over.reward);
      break;
    }
  }
}

export function connectDuel(): void {
  if (socket && socket.readyState <= WebSocket.OPEN) return;
  const proto = location.protocol === 'https:' ? 'wss' : 'ws';
  socket = new WebSocket(`${proto}://${location.host}/ws/duel`);
  socket.onmessage = (ev) => handle(JSON.parse(ev.data));
  socket.onclose = () => {
    socket = null;
  };
}

export function queueDuel(): void {
  connectDuel();
  const go = () => send('duel:queue');
  if (socket?.readyState === WebSocket.OPEN) go();
  else socket?.addEventListener('open', go, { once: true });
  setState({ phase: 'queued' });
}

export function leaveDuelQueue(): void {
  send('duel:leave');
  setState({ phase: 'idle' });
}

export function submitDuelMove(from: string, to: string, promo = ''): void {
  if (state.duelId) send('duel:submit', { duel_id: state.duelId, from, to, promo });
}

export function resetDuel(): void {
  setState({ ...INIT });
}
