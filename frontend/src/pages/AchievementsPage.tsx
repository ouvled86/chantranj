import { useEffect, useState } from 'react';
import { api, type AchievementView } from '../lib/api';

const CATEGORIES = [
  { key: 'learning', label: 'Learning' },
  { key: 'tactics', label: 'Tactics' },
  { key: 'playing', label: 'Playing' },
  { key: 'social', label: 'Social' },
  { key: 'dedication', label: 'Dedication' },
];

export default function AchievementsPage() {
  const [items, setItems] = useState<AchievementView[] | null>(null);

  useEffect(() => {
    api.get<AchievementView[]>('/api/v1/achievements').then(setItems);
  }, []);

  if (!items) return <p className="font-display italic text-muted">Opening the trophy case…</p>;

  const unlocked = items.filter((a) => a.unlocked).length;

  return (
    <div className="max-w-3xl">
      <h1 className="font-display mb-1 text-3xl font-bold">Achievements</h1>
      <p className="mb-6 font-display italic text-muted">
        {unlocked} of {items.length} earned.
      </p>

      {CATEGORIES.map((cat) => {
        const group = items.filter((a) => a.category === cat.key);
        if (group.length === 0) return null;
        return (
          <section key={cat.key} className="mb-7">
            <h2 className="mb-3 font-mono text-[11px] uppercase tracking-widest text-muted">
              {cat.label}
            </h2>
            <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
              {group.map((a) => (
                <div
                  key={a.slug}
                  className={`flex items-center gap-3 rounded-xs border px-3 py-2 ${
                    a.unlocked
                      ? 'border-gold/40 bg-gold/5'
                      : 'border-walnut-line bg-walnut-800 opacity-55'
                  }`}
                >
                  <span className={`text-2xl ${a.unlocked ? '' : 'grayscale'}`}>{a.icon}</span>
                  <div className="flex-1">
                    <div className="text-sm font-semibold">{a.title}</div>
                    <div className="text-xs text-muted">{a.description}</div>
                  </div>
                  <span
                    className={`font-mono text-xs ${a.unlocked ? 'text-gold' : 'text-muted'}`}
                  >
                    {a.unlocked ? '✓' : `+${a.xp}`}
                  </span>
                </div>
              ))}
            </div>
          </section>
        );
      })}
    </div>
  );
}
