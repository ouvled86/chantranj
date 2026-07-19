import { useEffect, useState } from 'react';
import { api } from '../lib/api';
import { useAuth } from '../lib/auth';

interface GameRow {
  id: number;
  mode: string;
  white_id: number | null;
  black_id: number | null;
  time_control: { base_min: number | null; inc_sec: number };
  result: string | null;
  end_reason: string | null;
  rated: boolean;
  rating_delta_w: number | null;
  rating_delta_b: number | null;
  started_at: string;
}

export default function GamesPage() {
  const { user } = useAuth();
  const [games, setGames] = useState<GameRow[] | null>(null);

  useEffect(() => {
    api.get<GameRow[]>('/api/v1/games').then(setGames).catch(() => setGames([]));
  }, []);

  const downloadPgn = async (id: number) => {
    const detail = await api.get<{ pgn: string }>(`/api/v1/games/${id}`);
    const blob = new Blob([detail.pgn], { type: 'application/x-chess-pgn' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = `the-study-game-${id}.pgn`;
    a.click();
    URL.revokeObjectURL(a.href);
  };

  if (!games) return <p className="font-display italic text-muted">Opening the archive…</p>;

  return (
    <div className="max-w-2xl">
      <h1 className="font-display mb-6 text-3xl font-bold">Game Archive</h1>
      {games.length === 0 ? (
        <p className="text-muted">No games yet — visit the Play room.</p>
      ) : (
        <ul className="space-y-2">
          {games.map((g) => {
            const iAmWhite = g.white_id === user?.id;
            const myDelta = iAmWhite ? g.rating_delta_w : g.rating_delta_b;
            const outcome =
              g.result === 'DRAW'
                ? 'draw'
                : g.result === 'ABORTED' || g.result === null
                  ? 'aborted'
                  : (g.result === 'WHITE') === iAmWhite
                    ? 'won'
                    : 'lost';
            return (
              <li
                key={g.id}
                className="flex items-center gap-4 rounded-xs border border-walnut-line bg-walnut-800 px-4 py-3"
              >
                <span
                  className={`w-14 font-mono text-xs font-bold uppercase ${
                    outcome === 'won'
                      ? 'text-correct'
                      : outcome === 'lost'
                        ? 'text-wrong'
                        : 'text-muted'
                  }`}
                >
                  {outcome}
                </span>
                <span className="flex-1 text-sm">
                  {g.mode.toLowerCase()} ·{' '}
                  {g.time_control.base_min === null
                    ? 'untimed'
                    : `${g.time_control.base_min}+${g.time_control.inc_sec}`}
                  {g.end_reason ? ` · by ${g.end_reason}` : ''}
                </span>
                {myDelta !== null && (
                  <span className="font-mono text-xs text-muted">
                    {myDelta >= 0 ? '+' : ''}
                    {myDelta}
                  </span>
                )}
                <span className="font-mono text-xs text-muted">
                  {new Date(g.started_at).toLocaleDateString()}
                </span>
                <button
                  onClick={() => downloadPgn(g.id)}
                  className="rounded-xs border border-walnut-line px-2 py-1 font-mono text-[10px] uppercase text-muted hover:text-cream"
                >
                  pgn
                </button>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
