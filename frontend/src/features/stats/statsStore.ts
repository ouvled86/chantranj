/** Player stats (XP/level/streak/ratings) — fetched once, refreshed after any
 *  XP-earning action so the sidebar chip and profile stay current. */

import { useSyncExternalStore } from 'react';
import { api } from '../../lib/api';

export interface RatingBlock {
  value: number;
  games: number;
  provisional: boolean;
}

export interface MeStats {
  level: number;
  total_xp: number;
  xp_into_level: number;
  xp_for_next: number;
  streak: number;
  best_streak: number;
  freezes_left: number;
  ratings: Record<string, RatingBlock>;
  games_played: number;
  wins: number;
  items_done: number;
  achievements_unlocked: number;
  achievements_total: number;
}

let stats: MeStats | null = null;
const listeners = new Set<() => void>();

function emit() {
  listeners.forEach((l) => l());
}

export function useStats(): MeStats | null {
  return useSyncExternalStore(
    (cb) => {
      listeners.add(cb);
      return () => listeners.delete(cb);
    },
    () => stats,
  );
}

export async function refreshStats(): Promise<void> {
  try {
    stats = await api.get<MeStats>('/api/v1/users/me/stats');
    emit();
  } catch {
    /* not logged in yet */
  }
}

export function clearStats(): void {
  stats = null;
  emit();
}
