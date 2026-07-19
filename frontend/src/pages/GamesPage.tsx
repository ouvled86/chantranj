import { useEffect, useRef, useState } from 'react';
import { api, ApiError } from '../lib/api';
import { useAuth } from '../lib/auth';

interface Review {
  moves_analysis: { ply: number; side: string; san: string; tag: string }[];
  accuracy_w: number | null;
  accuracy_b: number | null;
}

const TAG_COLOR: Record<string, string> = {
  great: 'text-correct',
  good: 'text-muted',
  inaccuracy: 'text-gold',
  mistake: 'text-[#eba38f]',
  blunder: 'text-wrong',
};

function ReviewPanel({ gameId }: { gameId: number }) {
  const [review, setReview] = useState<Review | null>(null);
  const [status, setStatus] = useState<'idle' | 'working' | 'failed'>('idle');
  const polls = useRef(0);

  const fetchReview = async (): Promise<boolean> => {
    try {
      setReview(await api.get<Review>(`/api/v1/games/${gameId}/review`));
      setStatus('idle');
      return true;
    } catch (e) {
      if (e instanceof ApiError && e.code === 'no_review') return false;
      throw e;
    }
  };

  const start = async () => {
    setStatus('working');
    try {
      if (await fetchReview()) return;
      await api.post(`/api/v1/games/${gameId}/review`);
      polls.current = 0;
      const poll = async () => {
        if (await fetchReview()) return;
        if (polls.current++ > 40) {
          setStatus('failed');
          return;
        }
        setTimeout(poll, 2000);
      };
      await poll();
    } catch {
      setStatus('failed');
    }
  };

  if (review) {
    return (
      <div className="mt-2 rounded-xs border border-walnut-line bg-walnut-950 p-3">
        <p className="mb-2 font-mono text-xs text-muted">
          accuracy — white{' '}
          <span className="text-cream">{review.accuracy_w?.toFixed(1) ?? '—'}%</span> · black{' '}
          <span className="text-cream">{review.accuracy_b?.toFixed(1) ?? '—'}%</span>
        </p>
        <div className="flex flex-wrap gap-1">
          {review.moves_analysis.map((m) => (
            <span
              key={m.ply}
              title={m.tag}
              className={`font-mono text-[11px] ${TAG_COLOR[m.tag] ?? 'text-muted'}`}
            >
              {m.side === 'w' ? `${Math.ceil(m.ply / 2)}.` : ''}
              {m.san}
            </span>
          ))}
        </div>
      </div>
    );
  }
  return (
    <button
      onClick={start}
      disabled={status === 'working'}
      className="rounded-xs border border-walnut-line px-2 py-1 font-mono text-[10px] uppercase text-muted hover:text-cream disabled:opacity-50"
    >
      {status === 'working' ? 'analysing…' : status === 'failed' ? 'retry review' : 'review'}
    </button>
  );
}

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
                className="rounded-xs border border-walnut-line bg-walnut-800 px-4 py-3"
              >
                <div className="flex items-center gap-4">
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
                </div>
                {g.result !== null && g.result !== 'ABORTED' && <ReviewPanel gameId={g.id} />}
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
