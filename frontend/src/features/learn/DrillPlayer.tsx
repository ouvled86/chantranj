import { useEffect, useRef, useState } from 'react';
import Board from '../../components/Board';
import {
  applyMove,
  idxToSq,
  isWhitePiece,
  parseFEN,
  pseudoMoves,
  START_FEN,
} from '../../lib/chess';
import type { ItemContent } from '../../lib/api';
import { NoteCard, PlayerButton } from './player-ui';

export default function DrillPlayer({
  content,
  onComplete,
}: {
  content: ItemContent;
  onComplete: () => void;
}) {
  const line = content.line ?? [];
  const [pos, setPos] = useState(() => parseFEN(content.fen ?? START_FEN));
  const [lineIdx, setLineIdx] = useState(0);
  const [selected, setSelected] = useState<number | null>(null);
  const [hintLevel, setHintLevel] = useState(0);
  const [feedback, setFeedback] = useState<string | null>(null);
  const [shakeSignal, setShakeSignal] = useState(0);
  const timer = useRef<ReturnType<typeof setTimeout>>(null);

  const solved = lineIdx >= line.length;
  const userToPlay = lineIdx % 2 === 0 && !solved;
  const lastPlayed = lineIdx > 0 ? line[lineIdx - 1] : null;
  const expected = !solved ? line[lineIdx] : null;

  useEffect(() => {
    if (solved) onComplete();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [solved]);

  useEffect(() => () => clearTimeout(timer.current ?? undefined), []);

  const reset = () => {
    clearTimeout(timer.current ?? undefined);
    setPos(parseFEN(content.fen ?? START_FEN));
    setLineIdx(0);
    setSelected(null);
    setHintLevel(0);
    setFeedback(null);
  };

  const onSquareClick = (i: number) => {
    if (!userToPlay || !expected) return;
    const piece = pos.board[i];
    const whiteToMove = pos.turn === 'w';

    if (selected === null) {
      if (piece && isWhitePiece(piece) === whiteToMove) setSelected(i);
      return;
    }
    if (i === selected) {
      setSelected(null);
      return;
    }
    if (piece && isWhitePiece(piece) === whiteToMove) {
      setSelected(i);
      return;
    }

    const attempt = idxToSq(selected) + idxToSq(i);
    setSelected(null);
    if (attempt === expected.move.slice(0, 4)) {
      setFeedback(null);
      const afterUser = applyMove(pos, expected.move);
      setPos(afterUser);
      const nextIdx = lineIdx + 1;
      setLineIdx(nextIdx);
      if (nextIdx < line.length && nextIdx % 2 === 1) {
        timer.current = setTimeout(() => {
          setPos(applyMove(afterUser, line[nextIdx].move));
          setLineIdx(nextIdx + 1);
        }, 650);
      }
    } else {
      setFeedback('Not this one. Run the scan again: checks, captures, threats.');
      setShakeSignal((s) => s + 1);
    }
  };

  const hintArrow: [string, string][] =
    hintLevel >= 2 && expected
      ? [[expected.move.slice(0, 2), expected.move.slice(2, 4)]]
      : [];

  return (
    <div className="grid gap-8 lg:grid-cols-[minmax(320px,560px)_minmax(300px,1fr)] items-start">
      <div>
        <div
          className={`inline-block mb-2 rounded-full px-3 py-0.5 font-mono text-[11.5px] tracking-wider ${
            solved
              ? 'bg-correct text-walnut-950'
              : pos.turn === 'w'
                ? 'bg-cream text-walnut-950'
                : 'bg-walnut-950 text-cream border border-walnut-line'
          }`}
        >
          {solved ? 'Solved' : pos.turn === 'w' ? 'White to move' : 'Black to move'}
        </div>
        <Board
          pos={pos}
          orientation={content.orientation}
          dots={selected !== null ? pseudoMoves(pos, selected) : []}
          selected={selected}
          lastMove={lastPlayed?.move ?? null}
          arrows={hintArrow}
          onSquareClick={onSquareClick}
          shakeSignal={shakeSignal}
        />
        {content.goal && (
          <p className="mt-2 font-mono text-xs text-muted">Goal: {content.goal}</p>
        )}
      </div>

      <div>
        <NoteCard
          label={solved ? 'Solved ✦' : (lastPlayed?.san ?? 'Your move')}
          body={
            solved
              ? (lastPlayed?.note ?? '')
              : lineIdx === 0
                ? content.intro
                : (lastPlayed?.note ?? 'Keep going — find the next move.')
          }
          takeaway={solved ? content.outro : undefined}
          cue={lineIdx === 0 && !solved ? 'Click a piece, then its destination.' : undefined}
        />

        {feedback && (
          <div className="mt-3 rounded-xs border border-wrong/50 bg-wrong/15 px-3 py-2 text-sm text-[#eba38f]">
            {feedback}
          </div>
        )}
        {hintLevel === 1 && content.hint && (
          <div className="mt-3 rounded-xs border border-gold/45 bg-gold/15 px-3 py-2 text-sm text-[#e8c477]">
            {content.hint}
          </div>
        )}

        <div className="mt-4 flex flex-wrap gap-2">
          <PlayerButton onClick={reset}>↺</PlayerButton>
          {!solved && (
            <PlayerButton onClick={() => setHintLevel((h) => Math.min(h + 1, 2))}>
              {hintLevel === 0 ? 'Hint' : 'Show the move'}
            </PlayerButton>
          )}
        </div>

        {lineIdx > 0 && (
          <div className="mt-5">
            <div className="font-mono text-[10.5px] uppercase tracking-widest text-muted mb-2">
              Moves
            </div>
            <div className="flex flex-wrap gap-1.5">
              {line.slice(0, lineIdx).map((s, idx) => (
                <span
                  key={idx}
                  className={`font-mono text-xs px-2 py-1 rounded-xs border ${
                    idx === lineIdx - 1
                      ? 'border-gold text-gold bg-gold/15 font-semibold'
                      : 'border-walnut-line bg-walnut-800 text-muted'
                  }`}
                >
                  {s.san}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
