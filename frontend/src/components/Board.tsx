/** The walnut board — React port of the legacy-v1 renderer. */

import { useEffect, useRef } from 'react';
import { FILES, isWhitePiece, sqToIdx, type Pos } from '../lib/chess';

const GLYPHS: Record<string, string> = {
  k: '♚', q: '♛', r: '♜', b: '♝', n: '♞', p: '♟',
};

export interface BoardProps {
  pos: Pos;
  orientation?: 'white' | 'black';
  marks?: string[];
  arrows?: [string, string][];
  lastMove?: string | null;
  dots?: number[];
  selected?: number | null;
  onSquareClick?: (idx: number) => void;
  /** Increment to trigger the wrong-move shake. */
  shakeSignal?: number;
}

function center(i: number, flipped: boolean): { x: number; y: number } {
  const d = flipped ? 63 - i : i;
  return { x: (d % 8) * 100 + 50, y: Math.floor(d / 8) * 100 + 50 };
}

export default function Board({
  pos,
  orientation = 'white',
  marks = [],
  arrows = [],
  lastMove = null,
  dots = [],
  selected = null,
  onSquareClick,
  shakeSignal = 0,
}: BoardProps) {
  const flipped = orientation === 'black';
  const gridRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!shakeSignal || !gridRef.current) return;
    const el = gridRef.current;
    el.classList.remove('shake');
    void el.offsetWidth;
    el.classList.add('shake');
  }, [shakeSignal]);

  const markSet = new Set(marks.map(sqToIdx));
  const dotSet = new Set(dots);
  const lastFrom = lastMove ? sqToIdx(lastMove.slice(0, 2)) : -1;
  const lastTo = lastMove ? sqToIdx(lastMove.slice(2, 4)) : -1;

  const squares = [];
  for (let d = 0; d < 64; d++) {
    const i = flipped ? 63 - d : d;
    const f = i % 8;
    const r = Math.floor(i / 8);
    const df = d % 8;
    const dr = Math.floor(d / 8);
    const piece = pos.board[i];
    const cls = [
      'sq',
      (f + r) % 2 === 0 ? 'light' : 'dark',
      markSet.has(i) ? 'marked' : '',
      selected === i ? 'selected' : '',
      i === lastFrom ? 'last-from' : '',
      i === lastTo ? 'last-to' : '',
    ]
      .filter(Boolean)
      .join(' ');
    squares.push(
      <div key={i} className={cls} onClick={() => onSquareClick?.(i)}>
        {dr === 7 && (
          <span className="coord coord-file">{FILES[flipped ? 7 - df : df]}</span>
        )}
        {df === 0 && <span className="coord coord-rank">{flipped ? dr + 1 : 8 - dr}</span>}
        {piece && (
          <span className={`piece ${isWhitePiece(piece) ? 'wp' : 'bp'}`}>
            {GLYPHS[piece.toLowerCase()]}
          </span>
        )}
        {dotSet.has(i) && <span className={`dot${piece ? ' dot-capture' : ''}`} />}
      </div>,
    );
  }

  return (
    <div className="board-frame">
      <div className="board-grid" ref={gridRef}>
        {squares}
      </div>
      <svg className="board-overlay" viewBox="0 0 800 800" preserveAspectRatio="none">
        <defs>
          <marker
            id="arrowhead"
            markerWidth="3.2"
            markerHeight="3.2"
            refX="2.05"
            refY="1.6"
            orient="auto"
          >
            <path d="M0,0 L3.2,1.6 L0,3.2 z" fill="rgba(217,164,65,0.85)" />
          </marker>
        </defs>
        {arrows.map(([from, to], idx) => {
          const a = center(sqToIdx(from), flipped);
          const b = center(sqToIdx(to), flipped);
          const dx = b.x - a.x;
          const dy = b.y - a.y;
          const len = Math.hypot(dx, dy) || 1;
          const trim = 34;
          return (
            <line
              key={idx}
              className="arrow-line"
              x1={a.x}
              y1={a.y}
              x2={b.x - (dx / len) * trim}
              y2={b.y - (dy / len) * trim}
              markerEnd="url(#arrowhead)"
            />
          );
        })}
      </svg>
    </div>
  );
}
