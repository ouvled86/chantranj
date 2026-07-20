import { useEffect, useState } from 'react';
import { api, type LeaderRow } from '../lib/api';

const MODES = [
  { key: 'online', label: 'Online' },
  { key: 'bot', label: 'Bot Arena' },
  { key: 'duel', label: 'Puzzle Duel' },
];

export default function LeaderboardPage() {
  const [mode, setMode] = useState('online');
  const [scope, setScope] = useState<'global' | 'friends'>('global');
  const [rows, setRows] = useState<LeaderRow[] | null>(null);

  useEffect(() => {
    let alive = true;
    api
      .get<LeaderRow[]>(`/api/v1/leaderboards/${mode}?scope=${scope}`)
      .then((r) => alive && setRows(r));
    return () => {
      alive = false;
    };
  }, [mode, scope]);

  return (
    <div className="max-w-2xl">
      <h1 className="font-display mb-1 text-3xl font-bold">Leaderboards</h1>
      <p className="mb-6 font-display italic text-muted">Where you stand — climb it.</p>

      <div className="mb-4 flex flex-wrap items-center gap-2">
        {MODES.map((m) => (
          <button
            key={m.key}
            onClick={() => setMode(m.key)}
            className={`rounded-xs border px-4 py-2 text-sm ${
              mode === m.key
                ? 'border-gold bg-gold/15 text-gold'
                : 'border-walnut-line bg-walnut-800 hover:border-muted'
            }`}
          >
            {m.label}
          </button>
        ))}
        <div className="ml-auto flex gap-1">
          {(['global', 'friends'] as const).map((s) => (
            <button
              key={s}
              onClick={() => setScope(s)}
              className={`rounded-xs px-3 py-2 font-mono text-xs uppercase ${
                scope === s ? 'text-gold' : 'text-muted hover:text-cream'
              }`}
            >
              {s}
            </button>
          ))}
        </div>
      </div>

      {!rows ? (
        <p className="font-display italic text-muted">Tallying…</p>
      ) : rows.length === 0 ? (
        <p className="text-sm text-muted">
          No rated games yet {scope === 'friends' ? 'among your friends' : ''}. Go play some.
        </p>
      ) : (
        <table className="w-full text-sm">
          <thead>
            <tr className="font-mono text-[10px] uppercase tracking-widest text-muted">
              <th className="py-2 text-left">#</th>
              <th className="py-2 text-left">Player</th>
              <th className="py-2 text-right">Rating</th>
              <th className="py-2 text-right">Games</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr
                key={r.rank}
                className={`border-t border-walnut-line ${r.is_me ? 'bg-gold/10' : ''}`}
              >
                <td className="py-2 font-mono text-muted">{r.rank}</td>
                <td className="py-2">
                  {r.username}
                  {r.is_me && <span className="ml-2 font-mono text-[10px] text-gold">you</span>}
                </td>
                <td className="py-2 text-right font-mono text-gold">{r.value}</td>
                <td className="py-2 text-right font-mono text-muted">{r.games}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
