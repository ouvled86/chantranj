/** Everything the coach is allowed to show at the current level. */

import { BoltIcon, TakebackIcon } from '../../components/icons';
import {
  confirmPendingMove,
  requestHint,
  requestTakeback,
  toggleEval,
  usePlayState,
} from './gameStore';

/* verdict classes live in styles/index.css (.verdict-*) */
const TAG_CLASS: Record<string, string> = {
  great: 'verdict-great',
  good: 'verdict-good',
  inaccuracy: 'verdict-inaccuracy',
  mistake: 'verdict-mistake',
  blunder: 'verdict-blunder',
};
const TAG_DOT: Record<string, string> = {
  great: '#8cb65e',
  good: '#b3a289',
  inaccuracy: '#d9a441',
  mistake: '#d97a63',
  blunder: '#c8503c',
};

export function EvalBar({ evalCp }: { evalCp: number | null }) {
  const cp = evalCp ?? 0;
  const winPct = 50 + 50 * (2 / (1 + Math.exp(-0.00368208 * cp)) - 1);
  // self-stretch, not h-full: the flex row has no definite height, so a
  // percentage height collapses the bar to a sliver.
  return (
    <div
      className="w-3 self-stretch overflow-hidden rounded-[4px] border border-walnut-edge bg-[#171008] shadow-[inset_0_0_6px_rgba(0,0,0,.6)]"
      title={evalCp === null ? 'evaluating…' : `${cp > 0 ? '+' : ''}${(cp / 100).toFixed(1)}`}
    >
      <div
        className="w-full bg-gradient-to-b from-[#241a0f] to-walnut-800 transition-all duration-500"
        style={{ height: `${100 - winPct}%` }}
      />
      <div className="w-full bg-gradient-to-b from-parchment to-parchment-deep" style={{ height: `${winPct}%` }} />
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
  const evalPct = coach.evalCp === null ? 50 : 50 + 50 * (2 / (1 + Math.exp(-0.00368208 * coach.evalCp)) - 1);

  return (
    <div className="card-rise mb-4 rounded-[8px] border border-gold/35 p-4 shadow-e2 [background:linear-gradient(180deg,rgba(217,164,65,.08),rgba(217,164,65,.02)),linear-gradient(180deg,#2a2014,#241a0f)]">
      <div className="mb-3 flex items-center justify-between">
        <span className="font-mono text-[10.5px] uppercase tracking-[.18em] text-gold-soft">
          Coach · Level {level}
        </span>
        <span className="font-mono text-[9.5px] uppercase tracking-[.1em] text-parchment-muted">
          {coach.hintsLeft !== null && `${coach.hintsLeft} hints`}
          {coach.takebacksLeft !== null && ` · ${coach.takebacksLeft} takebacks`}
          {level === 3 && (
            <button onClick={toggleEval} className="ml-2 underline">
              {coach.showEval ? 'hide eval' : 'show eval'}
            </button>
          )}
        </span>
      </div>

      {showBar && coach.evalCp !== null && (
        <div className="mb-3 flex items-center gap-3">
          <span className="font-mono text-[22px] tabular-nums text-cream">
            {coach.evalCp >= 0 ? '+' : ''}
            {(coach.evalCp / 100).toFixed(1)}
          </span>
          <div className="flex h-2 flex-1 overflow-hidden rounded-full border border-walnut-edge bg-[#1c150d]">
            <div
              className="bg-gradient-to-r from-parchment-deep to-parchment transition-all duration-500"
              style={{ width: `${evalPct}%` }}
            />
          </div>
        </div>
      )}

      {coach.tag && (
        <div className={`verdict mb-3 ${TAG_CLASS[coach.tag] ?? TAG_CLASS.good}`}>
          <span className="verdict-dot" style={{ background: TAG_DOT[coach.tag] ?? TAG_DOT.good }} />
          {coach.tag}
          {coach.note && <span className="ml-1.5 font-body normal-case">{coach.note}</span>}
        </div>
      )}
      {coach.critical && (
        <div className="verdict verdict-inaccuracy mb-3">
          <span className="verdict-dot bg-gold" />
          critical moment — look closer
        </div>
      )}

      {coach.pendingConfirm && (
        <div className="card-rise mb-3 rounded-[6px] border border-wrong/60 bg-wrong/15 p-3 text-sm">
          The coach winces — that looks like a {coach.pendingConfirm.tag ?? 'mistake'}.
          <div className="mt-2 flex gap-2">
            <button
              onClick={() => confirmPendingMove(false)}
              className="btn-primary rounded-[5px] px-3.5 py-1 text-xs"
            >
              Rethink
            </button>
            <button
              onClick={() => confirmPendingMove(true)}
              className="btn-secondary px-3.5 py-1 text-xs"
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
            className="btn-secondary inline-flex items-center gap-1.5 px-3.5 py-1.5 text-[13px]"
          >
            <BoltIcon size={13} />
            Hint{coach.hintsLeft !== null ? ` (${coach.hintsLeft})` : ''}
          </button>
        )}
        {level <= 3 && (
          <button
            onClick={requestTakeback}
            disabled={!canTakeback}
            className="btn-secondary inline-flex items-center gap-1.5 px-3.5 py-1.5 text-[13px]"
          >
            <TakebackIcon size={13} />
            Takeback{coach.takebacksLeft !== null ? ` (${coach.takebacksLeft})` : ''}
          </button>
        )}
      </div>
    </div>
  );
}
