/** Client-side board state for rendering & optimistic input.
 *  Port of legacy-v1/js/engine.js — the SERVER (python-chess) stays authoritative. */

export const FILES = 'abcdefgh';
export const START_FEN = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1';

export interface Pos {
  board: (string | null)[];
  turn: 'w' | 'b';
}

export function sqToIdx(sq: string): number {
  return (8 - parseInt(sq[1], 10)) * 8 + FILES.indexOf(sq[0]);
}

export function idxToSq(i: number): string {
  return FILES[i % 8] + (8 - Math.floor(i / 8));
}

export function isWhitePiece(p: string | null): boolean {
  return !!p && p === p.toUpperCase();
}

export function parseFEN(fen: string): Pos {
  const parts = fen.split(' ');
  const board: (string | null)[] = new Array(64).fill(null);
  let i = 0;
  for (const ch of parts[0]) {
    if (ch === '/') continue;
    if (/\d/.test(ch)) i += parseInt(ch, 10);
    else board[i++] = ch;
  }
  return { board, turn: (parts[1] as 'w' | 'b') || 'w' };
}

/** Apply 'e2e4' / 'e7e8q'. Handles castling, en passant, auto-queen. */
export function applyMove(pos: Pos, mv: string): Pos {
  const from = sqToIdx(mv.slice(0, 2));
  const to = sqToIdx(mv.slice(2, 4));
  const board = pos.board.slice();
  const piece = board[from];

  if ((piece === 'K' || piece === 'k') && Math.abs((from % 8) - (to % 8)) === 2) {
    const rank = Math.floor(from / 8) * 8;
    if (to % 8 === 6) {
      board[rank + 5] = board[rank + 7];
      board[rank + 7] = null;
    } else {
      board[rank + 3] = board[rank];
      board[rank] = null;
    }
  }

  if ((piece === 'P' || piece === 'p') && from % 8 !== to % 8 && !board[to]) {
    board[Math.floor(from / 8) * 8 + (to % 8)] = null;
  }

  let placed = piece;
  if (mv.length > 4) {
    placed = piece === 'P' ? mv[4].toUpperCase() : mv[4].toLowerCase();
  } else if (piece === 'P' && to < 8) {
    placed = 'Q';
  } else if (piece === 'p' && to >= 56) {
    placed = 'q';
  }
  board[to] = placed;
  board[from] = null;
  return { board, turn: pos.turn === 'w' ? 'b' : 'w' };
}

/** Pseudo-legal targets (no check test) — candidate dots for drills. */
export function pseudoMoves(pos: Pos, from: number): number[] {
  const b = pos.board;
  const p = b[from];
  if (!p) return [];
  const white = isWhitePiece(p);
  const out: number[] = [];
  const f = from % 8;
  const r = Math.floor(from / 8);
  const push = (ff: number, rr: number): boolean => {
    if (ff < 0 || ff > 7 || rr < 0 || rr > 7) return false;
    const i = rr * 8 + ff;
    if (!b[i]) {
      out.push(i);
      return true;
    }
    if (isWhitePiece(b[i]) !== white) out.push(i);
    return false;
  };
  const slide = (dirs: [number, number][]) => {
    for (const [df, dr] of dirs) {
      let ff = f + df;
      let rr = r + dr;
      while (push(ff, rr)) {
        ff += df;
        rr += dr;
      }
    }
  };
  const type = p.toLowerCase();
  if (type === 'n') {
    for (const [df, dr] of [
      [1, 2], [2, 1], [2, -1], [1, -2], [-1, -2], [-2, -1], [-2, 1], [-1, 2],
    ] as [number, number][])
      push(f + df, r + dr);
  } else if (type === 'k') {
    for (const [df, dr] of [
      [1, 0], [1, 1], [0, 1], [-1, 1], [-1, 0], [-1, -1], [0, -1], [1, -1],
    ] as [number, number][])
      push(f + df, r + dr);
  } else if (type === 'r') slide([[1, 0], [-1, 0], [0, 1], [0, -1]]);
  else if (type === 'b') slide([[1, 1], [1, -1], [-1, 1], [-1, -1]]);
  else if (type === 'q')
    slide([[1, 0], [-1, 0], [0, 1], [0, -1], [1, 1], [1, -1], [-1, 1], [-1, -1]]);
  else if (type === 'p') {
    const dir = white ? -1 : 1;
    const oneUp = (r + dir) * 8 + f;
    if (oneUp >= 0 && oneUp < 64 && !b[oneUp]) {
      out.push(oneUp);
      const startRank = white ? 6 : 1;
      const twoUp = (r + 2 * dir) * 8 + f;
      if (r === startRank && !b[twoUp]) out.push(twoUp);
    }
    for (const df of [-1, 1]) {
      const ff = f + df;
      const rr = r + dir;
      if (ff < 0 || ff > 7 || rr < 0 || rr > 7) continue;
      const i = rr * 8 + ff;
      if (b[i] && isWhitePiece(b[i]) !== white) out.push(i);
    }
  }
  return out;
}
