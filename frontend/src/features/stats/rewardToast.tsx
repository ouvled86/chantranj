/** A small global queue for XP / achievement toasts, rendered once in Layout. */

import { useSyncExternalStore } from 'react';
import type { RewardSummary } from '../../lib/api';
import { refreshStats } from './statsStore';

interface Toast {
  id: number;
  xp: number;
  leveledUp: boolean;
  level: number;
  unlocked: RewardSummary['unlocked'];
}

let toasts: Toast[] = [];
let nextId = 1;
const listeners = new Set<() => void>();

function emit() {
  listeners.forEach((l) => l());
}

export function useToasts(): Toast[] {
  return useSyncExternalStore(
    (cb) => {
      listeners.add(cb);
      return () => listeners.delete(cb);
    },
    () => toasts,
  );
}

/** Show a reward (from a REST response or a ws xp:update). No-op if empty. */
export function showReward(reward: RewardSummary | null | undefined): void {
  if (!reward || (reward.xp_gained <= 0 && reward.unlocked.length === 0)) return;
  const toast: Toast = {
    id: nextId++,
    xp: reward.xp_gained,
    leveledUp: reward.leveled_up,
    level: reward.level,
    unlocked: reward.unlocked,
  };
  toasts = [...toasts, toast];
  emit();
  refreshStats();
  const ttl = 4000 + reward.unlocked.length * 1500;
  setTimeout(() => {
    toasts = toasts.filter((t) => t.id !== toast.id);
    emit();
  }, ttl);
}

export function RewardToasts() {
  const items = useToasts();
  if (items.length === 0) return null;
  return (
    <div className="fixed bottom-4 left-1/2 z-50 flex -translate-x-1/2 flex-col items-center gap-2">
      {items.map((t) => (
        <div
          key={t.id}
          className="rounded-xs border border-gold/50 bg-walnut-900/95 px-4 py-2 text-center shadow-2xl"
        >
          {t.xp > 0 && (
            <div className="font-mono text-sm text-gold">
              +{t.xp} XP{t.leveledUp && <span className="ml-2 font-bold">· Level {t.level}! ✦</span>}
            </div>
          )}
          {t.unlocked.map((u) => (
            <div key={u.slug} className="mt-1 text-sm text-cream">
              <span className="mr-1">{u.icon}</span>
              Achievement unlocked: <b>{u.title}</b>{' '}
              <span className="font-mono text-xs text-gold">+{u.xp}</span>
            </div>
          ))}
        </div>
      ))}
    </div>
  );
}
