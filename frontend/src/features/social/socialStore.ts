/** /ws/social client: live presence, friend challenges, and challenge→game handoff. */

import { useSyncExternalStore } from 'react';

export interface IncomingChallenge {
  challenge_id: string;
  from_user_id: number;
  from_username: string;
  time_control: { base_min: number | null; inc_sec: number };
  rated: boolean;
}

export interface SocialState {
  connected: boolean;
  presence: Record<number, string>; // user_id -> status
  friendsVersion: number; // bump → friend list refetch
  incoming: IncomingChallenge | null;
  pendingGameStart: { game_id: number; color: 'w' | 'b' } | null;
  toast: string | null;
}

let state: SocialState = {
  connected: false,
  presence: {},
  friendsVersion: 0,
  incoming: null,
  pendingGameStart: null,
  toast: null,
};

const listeners = new Set<() => void>();
let socket: WebSocket | null = null;

function setState(patch: Partial<SocialState>) {
  state = { ...state, ...patch };
  listeners.forEach((l) => l());
}

export function useSocial(): SocialState {
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

function handle(msg: { type: string; data: Record<string, unknown> }) {
  const d = msg.data as never;
  switch (msg.type) {
    case 'friend:presence': {
      const p = d as { user_id: number; status: string };
      setState({ presence: { ...state.presence, [p.user_id]: p.status } });
      break;
    }
    case 'friend:update':
      setState({ friendsVersion: state.friendsVersion + 1 });
      break;
    case 'challenge:receive':
      setState({ incoming: d as IncomingChallenge });
      break;
    case 'challenge:declined':
      setState({ toast: 'Challenge declined.' });
      setTimeout(() => setState({ toast: null }), 3000);
      break;
    case 'challenge:ready':
      setState({ pendingGameStart: d as { game_id: number; color: 'w' | 'b' } });
      break;
  }
}

export function connectSocial(): void {
  if (socket && socket.readyState <= WebSocket.OPEN) return;
  const proto = location.protocol === 'https:' ? 'wss' : 'ws';
  socket = new WebSocket(`${proto}://${location.host}/ws/social`);
  socket.onopen = () => setState({ connected: true });
  socket.onmessage = (ev) => handle(JSON.parse(ev.data));
  socket.onclose = () => {
    setState({ connected: false });
    socket = null;
    setTimeout(connectSocial, 2000); // stay present across blips
  };
}

export function disconnectSocial(): void {
  socket?.close();
  socket = null;
}

export function sendChallenge(
  toUserId: number,
  timeControl: { base_min: number | null; inc_sec: number },
  rated: boolean,
): void {
  send('challenge:send', { to_user_id: toUserId, time_control: timeControl, rated });
  setState({ toast: 'Challenge sent.' });
  setTimeout(() => setState({ toast: null }), 3000);
}

export function acceptChallenge(id: string): void {
  send('challenge:accept', { challenge_id: id });
  setState({ incoming: null });
}

export function declineChallenge(id: string): void {
  send('challenge:decline', { challenge_id: id });
  setState({ incoming: null });
}

export function clearPendingGameStart(): void {
  setState({ pendingGameStart: null });
}
