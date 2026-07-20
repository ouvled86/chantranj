import { useEffect, useState } from 'react';
import Board from '../../components/Board';
import { idxToSq, isWhitePiece, parseFEN, pseudoMoves } from '../../lib/chess';
import {
  connectDuel,
  leaveDuelQueue,
  queueDuel,
  resetDuel,
  submitDuelMove,
  useDuel,
} from './duelStore';

export default function DuelPage() {
  const duel = useDuel();
  useEffect(() => {
    connectDuel();
  }, []);

  if (duel.phase === 'racing') return <DuelBoard />;
  if (duel.phase === 'over') return <DuelResult />;
  return <DuelLobby />;
}

function DuelLobby() {
  const duel = useDuel();
  return (
    <div className="max-w-xl">
      <h1 className="font-display mb-1 text-3xl font-bold">Puzzle Duel</h1>
      <p className="mb-6 font-display italic text-muted">
        Same gauntlet, same clock, head to head. Solve fast, keep the combo alive — highest
        score in three minutes wins.
      </p>
      {duel.phase === 'queued' ? (
        <div className="flex items-center gap-4">
          <span className="animate-pulse font-display italic text-gold">
            Finding a challenger…
          </span>
          <button
            onClick={leaveDuelQueue}
            className="rounded-xs border border-walnut-line px-4 py-2 text-sm text-muted hover:text-cream"
          >
            Cancel
          </button>
        </div>
      ) : (
        <button
          onClick={queueDuel}
          className="rounded-xs bg-gold px-6 py-3 font-bold text-walnut-950 hover:bg-[#e5b458]"
        >
          Find a duel
        </button>
      )}
    </div>
  );
}

function Countdown({ seconds }: { seconds: number }) {
  const [s, setS] = useState(seconds);
  useEffect(() => {
    const id = setInterval(() => setS((v) => Math.max(0, v - 1)), 1000);
    return () => clearInterval(id);
  }, []);
  const low = s <= 20;
  return (
    <span
      className={`rounded-xs px-3 py-1 font-mono text-lg tabular-nums ${
        low ? 'bg-wrong/25 text-wrong' : 'bg-gold/20 text-gold'
      }`}
    >
      {Math.floor(s / 60)}:{String(s % 60).padStart(2, '0')}
    </span>
  );
}

function DuelBoard() {
  const duel = useDuel();
  const [selected, setSelected] = useState<number | null>(null);

  if (!duel.fen) {
    return (
      <div className="max-w-md">
        <p className="font-display italic text-muted">
          Gauntlet complete — waiting for your opponent to finish…
        </p>
        <p className="mt-2 font-mono text-sm text-gold">Your score: {duel.score}</p>
      </div>
    );
  }

  const pos = parseFEN(duel.fen);
  const myColor = pos.turn === 'w' ? 'white' : 'black';

  const onSquareClick = (i: number) => {
    const piece = pos.board[i];
    const mine = piece !== null && isWhitePiece(piece) === (pos.turn === 'w');
    if (selected === null || mine) {
      setSelected(mine ? i : null);
      return;
    }
    if (i === selected) {
      setSelected(null);
      return;
    }
    const from = idxToSq(selected);
    const to = idxToSq(i);
    const p = pos.board[selected];
    const promo = p?.toLowerCase() === 'p' && (to[1] === '8' || to[1] === '1') ? 'q' : '';
    submitDuelMove(from, to, promo);
    setSelected(null);
  };

  return (
    <div className="grid items-start gap-8 lg:grid-cols-[minmax(320px,520px)_1fr]">
      <div>
        <div className="mb-2 flex items-center justify-between">
          <Countdown key={duel.secondsLeft} seconds={duel.secondsLeft} />
          <span className="font-mono text-sm text-muted">
            puzzle {Math.min(duel.puzzleIdx + 1, duel.total)}/{duel.total}
          </span>
        </div>
        <Board
          key={duel.flash}
          pos={pos}
          orientation={myColor}
          dots={selected !== null ? pseudoMoves(pos, selected) : []}
          selected={selected}
          onSquareClick={onSquareClick}
          shakeSignal={duel.lastResult === 'wrong' ? duel.flash : 0}
        />
        <p className="mt-2 font-mono text-xs text-muted">
          {pos.turn === 'w' ? 'White' : 'Black'} to move — find the winning idea
        </p>
      </div>

      <div className="space-y-4">
        <ScoreCard label="You" score={duel.score} combo={duel.combo} highlight />
        <ScoreCard
          label={duel.opponent}
          score={duel.oppScore}
          combo={duel.oppCombo}
          solved={duel.oppSolved}
        />
        {duel.lastResult && (
          <div
            className={`rounded-xs border px-3 py-2 text-sm ${
              duel.lastResult === 'solved'
                ? 'border-correct/50 bg-correct/10 text-correct'
                : duel.lastResult === 'wrong'
                  ? 'border-wrong/50 bg-wrong/10 text-wrong'
                  : 'border-walnut-line bg-walnut-800 text-muted'
            }`}
          >
            {duel.lastResult === 'solved'
              ? `Solved! +combo ${duel.combo}`
              : duel.lastResult === 'wrong'
                ? 'Missed — combo reset, next puzzle'
                : 'Keep going…'}
          </div>
        )}
      </div>
    </div>
  );
}

function ScoreCard({
  label,
  score,
  combo,
  solved,
  highlight,
}: {
  label: string;
  score: number;
  combo: number;
  solved?: number;
  highlight?: boolean;
}) {
  return (
    <div
      className={`rounded-xs border p-3 ${
        highlight ? 'border-gold bg-gold/10' : 'border-walnut-line bg-walnut-800'
      }`}
    >
      <div className="flex items-center justify-between">
        <span className="text-sm font-semibold">{label}</span>
        <span className="font-mono text-2xl tabular-nums text-gold">{score}</span>
      </div>
      <div className="mt-1 font-mono text-[11px] text-muted">
        {combo > 0 && <span className="text-gold">🔥 {combo} combo</span>}
        {solved !== undefined && <span className="ml-2">{solved} solved</span>}
      </div>
    </div>
  );
}

function DuelResult() {
  const duel = useDuel();
  const r = duel.result;
  const won = r ? r.your_score > r.opp_score : false;
  const drew = r ? r.your_score === r.opp_score : false;
  return (
    <div className="max-w-md">
      <div className="relative rounded-xs bg-parchment p-6 text-parchment-ink shadow-xl">
        <div className="absolute left-6 right-6 top-0 h-[3px] rounded-b-xs bg-gold" />
        <h1 className="font-display text-3xl font-bold">
          {drew ? 'Dead heat!' : won ? 'You win the duel! ⚡' : 'Outraced.'}
        </h1>
        {r && (
          <>
            <p className="mt-2 font-mono text-lg">
              {r.your_score} — {r.opp_score}
            </p>
            <p className="mt-1 font-mono text-sm text-parchment-muted">
              Duel rating {r.rating_delta >= 0 ? '+' : ''}
              {r.rating_delta}
            </p>
          </>
        )}
        <button
          onClick={resetDuel}
          className="mt-5 rounded-xs bg-gold px-4 py-2 text-sm font-bold text-walnut-950 hover:bg-[#e5b458]"
        >
          Duel again
        </button>
      </div>
    </div>
  );
}
