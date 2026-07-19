import { describe, expect, it } from 'vitest';
import { applyMove, parseFEN, pseudoMoves, sqToIdx, START_FEN } from './chess';

describe('chess lib', () => {
  it('parses the start position', () => {
    const pos = parseFEN(START_FEN);
    expect(pos.board[sqToIdx('e1')]).toBe('K');
    expect(pos.board[sqToIdx('e8')]).toBe('k');
    expect(pos.turn).toBe('w');
  });

  it('applies moves and flips the turn', () => {
    const pos = applyMove(parseFEN(START_FEN), 'e2e4');
    expect(pos.board[sqToIdx('e4')]).toBe('P');
    expect(pos.board[sqToIdx('e2')]).toBeNull();
    expect(pos.turn).toBe('b');
  });

  it('handles kingside castling (rook jumps too)', () => {
    const pos = applyMove(
      parseFEN('rnbqk2r/pppp1ppp/5n2/2b1p3/2B1P3/5N2/PPPP1PPP/RNBQK2R w KQkq - 4 4'),
      'e1g1',
    );
    expect(pos.board[sqToIdx('g1')]).toBe('K');
    expect(pos.board[sqToIdx('f1')]).toBe('R');
    expect(pos.board[sqToIdx('h1')]).toBeNull();
  });

  it('auto-queens promotions', () => {
    const pos = applyMove(parseFEN('8/1P6/8/8/8/2k5/8/6K1 w - - 0 1'), 'b7b8');
    expect(pos.board[sqToIdx('b8')]).toBe('Q');
  });

  it('generates pawn double-step and knight jumps', () => {
    const pos = parseFEN(START_FEN);
    expect(pseudoMoves(pos, sqToIdx('e2'))).toContain(sqToIdx('e4'));
    expect(pseudoMoves(pos, sqToIdx('g1'))).toContain(sqToIdx('f3'));
    expect(pseudoMoves(pos, sqToIdx('g1'))).not.toContain(sqToIdx('e1'));
  });
});
