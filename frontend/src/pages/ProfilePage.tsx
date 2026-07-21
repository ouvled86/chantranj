import { useEffect, useState } from 'react';
import { api, type AchievementView } from '../lib/api';
import { useAuth } from '../lib/auth';
import { refreshStats, useStats } from '../features/stats/statsStore';

interface RatingPoint {
  time: string;
  value: number;
}

export default function ProfilePage() {
  const { user } = useAuth();
  const stats = useStats();
  const [achievements, setAchievements] = useState<AchievementView[]>([]);
  const [history, setHistory] = useState<RatingPoint[]>([]);
  const [graphMode, setGraphMode] = useState('online');

  useEffect(() => {
    refreshStats();
    api.get<AchievementView[]>('/api/v1/achievements').then(setAchievements);
  }, []);

  useEffect(() => {
    api.get<RatingPoint[]>(`/api/v1/users/me/ratings/${graphMode}`).then(setHistory);
  }, [graphMode]);

  if (!stats || !user) return <p className="font-display italic text-muted">Loading profile…</p>;

  const pct = stats.xp_for_next ? Math.round((stats.xp_into_level / stats.xp_for_next) * 100) : 0;
  const showcase = achievements.filter((a) => a.unlocked).slice(0, 6);

  return (
    <div className="max-w-3xl">
      <div className="mb-8 flex items-center gap-5">
        <div className="flex h-20 w-20 flex-col items-center justify-center rounded-full border-2 border-gold bg-walnut-800">
          <span className="font-mono text-[9px] uppercase text-muted">level</span>
          <span className="font-display text-3xl font-bold text-gold">{stats.level}</span>
        </div>
        <div className="flex-1">
          <h1 className="font-display text-3xl font-bold">{user.username}</h1>
          <div className="mt-2 h-2 w-full max-w-sm overflow-hidden rounded-full bg-walnut-800">
            <div className="h-full rounded-full bg-gold transition-all" style={{ width: `${pct}%` }} />
          </div>
          <p className="mt-1 font-mono text-xs text-muted">
            {stats.xp_into_level} / {stats.xp_for_next} XP to level {stats.level + 1} ·{' '}
            {stats.total_xp} total
          </p>
          <p className="mt-1 font-mono text-xs">
            <span className="text-gold">🔥 {stats.streak}-day streak</span>
            <span className="ml-3 text-muted">best {stats.best_streak}</span>
            <span className="ml-3 text-muted">❄ {stats.freezes_left} freeze</span>
          </p>
        </div>
      </div>

      <div className="mb-8 grid grid-cols-2 gap-3 sm:grid-cols-4">
        <Stat label="Games" value={stats.games_played} />
        <Stat label="Wins" value={stats.wins} />
        <Stat label="Lessons/drills" value={stats.items_done} />
        <Stat
          label="Achievements"
          value={`${stats.achievements_unlocked}/${stats.achievements_total}`}
        />
      </div>

      <section className="mb-8">
        <div className="mb-2 flex items-center justify-between">
          <h2 className="font-mono text-[11px] uppercase tracking-widest text-muted">Ratings</h2>
          <div className="flex gap-1">
            {['online', 'bot', 'duel'].map((m) => (
              <button
                key={m}
                onClick={() => setGraphMode(m)}
                className={`rounded-xs px-2 py-1 font-mono text-[10px] uppercase ${
                  graphMode === m ? 'text-gold' : 'text-muted hover:text-cream'
                }`}
              >
                {m}
              </button>
            ))}
          </div>
        </div>
        <div className="grid grid-cols-3 gap-3">
          {(['online', 'bot', 'duel'] as const).map((m) => (
            <div key={m} className="rounded-xs border border-walnut-line bg-walnut-800 p-3">
              <div className="font-mono text-[10px] uppercase text-muted">{m}</div>
              <div className="font-mono text-2xl text-gold">
                {stats.ratings[m]?.value ?? 1200}
                {stats.ratings[m]?.provisional && <span className="text-xs text-muted">?</span>}
              </div>
              <div className="font-mono text-[10px] text-muted">
                {stats.ratings[m]?.games ?? 0} games
              </div>
            </div>
          ))}
        </div>
        <Sparkline points={history} />
      </section>

      <section>
        <h2 className="mb-3 font-mono text-[11px] uppercase tracking-widest text-muted">
          Achievement showcase
        </h2>
        {showcase.length === 0 ? (
          <p className="text-sm text-muted">None yet — play and learn to earn them.</p>
        ) : (
          <div className="flex flex-wrap gap-3">
            {showcase.map((a) => (
              <div
                key={a.slug}
                className="flex w-28 flex-col items-center rounded-xs border border-gold/40 bg-gold/5 p-3 text-center"
                title={a.description}
              >
                <span className="text-2xl">{a.icon}</span>
                <span className="mt-1 text-xs">{a.title}</span>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: number | string }) {
  return (
    <div className="rounded-xs border border-walnut-line bg-walnut-800 p-3">
      <div className="font-mono text-[10px] uppercase text-muted">{label}</div>
      <div className="font-display text-2xl font-bold">{value}</div>
    </div>
  );
}

function Sparkline({ points }: { points: RatingPoint[] }) {
  if (points.length < 2) {
    return (
      <p className="mt-3 font-mono text-xs text-muted">
        Play a few rated games to see your rating trend.
      </p>
    );
  }
  const values = points.map((p) => p.value);
  const min = Math.min(...values);
  const max = Math.max(...values);
  const span = max - min || 1;
  const w = 600;
  const h = 80;
  const path = points
    .map((p, i) => {
      const x = (i / (points.length - 1)) * w;
      const y = h - ((p.value - min) / span) * h;
      return `${i === 0 ? 'M' : 'L'}${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(' ');
  return (
    <svg viewBox={`0 0 ${w} ${h}`} className="mt-3 w-full" preserveAspectRatio="none">
      <path d={path} fill="none" stroke="var(--color-gold)" strokeWidth="2" />
    </svg>
  );
}
