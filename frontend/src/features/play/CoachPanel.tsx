/** Everything the coach is allowed to show at the current level. */

import {
  confirmPendingMove,
  requestHint,
  requestTakeback,
  toggleEval,
  usePlayState,
} from './gameStore';

const TAG_STYLE: Record<string, string> = {
  great: 'bg-correct/20 text-correct border-correct/50',
  good: 'bg-walnut-800 text-cream border-walnut-line',
  inaccuracy: 'bg-gold/15 text-gold border-gold/50',
  mistake: 'bg-wrong/15 text-[#eba38f] border-wrong/50',
  blunder: 'bg-wrong/25 text-wrong border-wrong/70',
};

export function EvalBar({ evalCp }: { evalCp: number | null }) {
  const cp = evalCp ?? 0;
  const winPct = 50 + 50 * (2 / (1 + Math.exp(-0.00368208 * cp)) - 1);
  return (
    <div
      className="h-full w-3 overflow-hidden rounded-xs border border-walnut-line bg-walnut-950"
      title={evalCp === null ? 'evaluating…' : `${cp > 0 ? '+' : ''}${(cp / 100).toFixed(1)}`}
    >
      <div
        className="w-full bg-cream transition-all duration-500"
        style={{ height: `${100 - winPct}%`, backgroundColor: '#2a1f13' }}
      />
      <div className="w-full bg-cream" style={{ height: `${winPct}%` }} />
    </div>
  );
}

export default function CoachPanel() {
  const { game, coach, phase } = usePlayState();
  const level = game?.coach_level;
  if (!level || phase !== 'playing') return null;

  const showBar =
    (level <= 2 || (level === 3 && coach.showEval)) && coach.evalCp !== null;
  const canHint = coach.hintsLeft === null || coach.hintsLeft > 0;
  const canTakeback = coach.takebacksLeft === null || coach.takebacksLeft > 0;

  return (
    <div className="mb-4 rounded-xs border border-gold/40 bg-gold/5 p-3">
      <div className="mb-2 flex items-center justify-between">
        <span className="font-mono text-[10px] uppercase tracking-widest text-gold">
          Coach · Level {level}
        </span>
        {level === 3 && (
          <button onClick={toggleEval} className="font-mono text-[10px] text-muted underline">
            {coach.showEval ? 'hide eval' : 'show eval'}
          </button>
        )}
      </div>

      {showBar && coach.evalCp !== null && (
        <p className="mb-2 font-mono text-xs text-muted">
          eval{' '}
          <span className={coach.evalCp >= 0 ? 'text-cream' : 'text-wrong'}>
            {coach.evalCp >= 0 ? '+' : ''}
            {(coach.evalCp / 100).toFixed(1)}
          </span>
        </p>
      )}

      {coach.tag && (
        <div
          className={`mb-2 inline-block rounded-xs border px-2 py-1 font-mono text-xs ${TAG_STYLE[coach.tag] ?? TAG_STYLE.good}`}
        >
          {coach.tag}
          {coach.note && <span className="ml-2 font-sans normal-case">{coach.note}</span>}
        </div>
      )}
      {coach.critical && (
        <div className="mb-2 rounded-xs border border-gold/60 bg-gold/15 px-2 py-1 font-mono text-xs text-gold">
          ⚠ critical moment — look closer
        </div>
      )}

      {coach.pendingConfirm && (
        <div className="mb-2 rounded-xs border border-wrong/60 bg-wrong/15 p-2 text-sm">
          The coach winces — that looks like a {coach.pendingConfirm.tag ?? 'mistake'}.
          <div className="mt-2 flex gap-2">
            <button
              onClick={() => confirmPendingMove(false)}
              className="rounded-xs bg-gold px-3 py-1 text-xs font-bold text-walnut-950"
            >
              Rethink
            </button>
            <button
              onClick={() => confirmPendingMove(true)}
              className="rounded-xs border border-walnut-line px-3 py-1 text-xs text-muted"
            >
              Play it anyway
            </button>
          </div>
        </div>
      )}

      <div className="flex gap-2">
        {(coach.hintsLeft === null || coach.hintsLeft !== 0 || level <= 3) && level <= 3 && (
          <button
            onClick={requestHint}
            disabled={!canHint}
            className="rounded-xs border border-walnut-line px-3 py-1 text-xs text-cream hover:border-gold disabled:opacity-40"
          >
            Hint{coach.hintsLeft !== null ? ` (${coach.hintsLeft})` : ''}
          </button>
        )}
        {level <= 3 && (
          <button
            onClick={requestTakeback}
            disabled={!canTakeback}
            className="rounded-xs border border-walnut-line px-3 py-1 text-xs text-cream hover:border-gold disabled:opacity-40"
          >
            Takeback{coach.takebacksLeft !== null ? ` (${coach.takebacksLeft})` : ''}
          </button>
        )}
      </div>
    </div>
  );
}
