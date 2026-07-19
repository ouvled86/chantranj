import { useEffect, useMemo, useState } from 'react';
import Board from '../../components/Board';
import { applyMove, parseFEN, START_FEN, type Pos } from '../../lib/chess';
import type { ItemContent } from '../../lib/api';
import { NoteCard, PlayerButton } from './player-ui';

export default function LessonPlayer({
  content,
  onComplete,
}: {
  content: ItemContent;
  onComplete: () => void;
}) {
  const steps = content.steps ?? [];
  const [stepIdx, setStepIdx] = useState(-1);

  const { startPos, positions } = useMemo(() => {
    let pos = parseFEN(content.fen ?? START_FEN);
    const start = pos;
    const list: Pos[] = [];
    for (const step of steps) {
      if (step.fen) pos = parseFEN(step.fen);
      if (step.move) pos = applyMove(pos, step.move);
      list.push(pos);
    }
    return { startPos: start, positions: list };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [content]);

  const atEnd = stepIdx === steps.length - 1;
  const step = stepIdx >= 0 ? steps[stepIdx] : null;
  const pos = stepIdx >= 0 ? positions[stepIdx] : startPos;

  useEffect(() => {
    if (atEnd) onComplete();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [atEnd]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'ArrowRight') setStepIdx((i) => Math.min(i + 1, steps.length - 1));
      if (e.key === 'ArrowLeft') setStepIdx((i) => Math.max(i - 1, -1));
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [steps.length]);

  return (
    <div className="grid gap-8 lg:grid-cols-[minmax(320px,560px)_minmax(300px,1fr)] items-start">
      <div>
        <Board
          pos={pos}
          orientation={content.orientation}
          marks={step?.marks ?? []}
          arrows={step?.arrows ?? []}
          lastMove={step?.move ?? null}
        />
        {content.orientation === 'black' && (
          <p className="mt-2 font-mono text-xs text-muted">Playing as Black — board flipped</p>
        )}
      </div>

      <div>
        <NoteCard
          label={stepIdx < 0 ? 'Introduction' : (step?.san ?? `Step ${stepIdx + 1}`)}
          body={stepIdx < 0 ? content.intro : (step?.note ?? '…')}
          takeaway={atEnd ? content.outro : undefined}
          cue={stepIdx < 0 ? 'Use Next ▸ (or the → key) to step through.' : undefined}
        />

        <div className="mt-4 flex flex-wrap gap-2">
          <PlayerButton onClick={() => setStepIdx(-1)}>↺</PlayerButton>
          <PlayerButton disabled={stepIdx <= -1} onClick={() => setStepIdx((i) => i - 1)}>
            ◂ Back
          </PlayerButton>
          <PlayerButton
            primary
            disabled={atEnd}
            onClick={() => setStepIdx((i) => Math.min(i + 1, steps.length - 1))}
          >
            Next ▸
          </PlayerButton>
        </div>

        <div className="mt-5">
          <div className="font-mono text-[10.5px] uppercase tracking-widest text-muted mb-2">
            Moves
          </div>
          <div className="flex flex-wrap gap-1.5">
            {steps.map((s, idx) =>
              s.san ? (
                <button
                  key={idx}
                  onClick={() => setStepIdx(idx)}
                  className={`font-mono text-xs px-2 py-1 rounded-xs border ${
                    idx === stepIdx
                      ? 'border-gold text-gold bg-gold/15 font-semibold'
                      : 'border-walnut-line bg-walnut-800 text-muted hover:text-cream'
                  } ${s.isBad ? 'text-wrong' : ''}`}
                >
                  {s.san}
                </button>
              ) : null,
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
