import { describe, expect, it, vi } from 'vitest';
import { render } from '@testing-library/react';
import Board from './Board';
import { parseFEN, sqToIdx, START_FEN } from '../lib/chess';

describe('Board', () => {
  it('renders 64 squares and 32 pieces from the start position', () => {
    const { container } = render(<Board pos={parseFEN(START_FEN)} />);
    expect(container.querySelectorAll('.sq')).toHaveLength(64);
    expect(container.querySelectorAll('.piece')).toHaveLength(32);
    expect(container.querySelectorAll('.piece.wp')).toHaveLength(16);
  });

  it('flips orientation for black', () => {
    const { container } = render(
      <Board pos={parseFEN(START_FEN)} orientation="black" />,
    );
    // First rendered square is h1 (index 63) when flipped: white rook.
    const first = container.querySelector('.sq .piece');
    expect(first?.textContent).toBe('♜');
    expect(first?.classList.contains('wp')).toBe(true);
  });

  it('reports square clicks by board index', () => {
    const onClick = vi.fn();
    const { container } = render(
      <Board pos={parseFEN(START_FEN)} onSquareClick={onClick} />,
    );
    (container.querySelectorAll('.sq')[0] as HTMLElement).click();
    expect(onClick).toHaveBeenCalledWith(0); // a8
  });

  it('marks and highlights squares', () => {
    const { container } = render(
      <Board pos={parseFEN(START_FEN)} marks={['e4']} lastMove="e2e4" />,
    );
    const squares = container.querySelectorAll('.sq');
    expect(squares[sqToIdx('e4')].classList.contains('marked')).toBe(true);
    expect(squares[sqToIdx('e2')].classList.contains('last-from')).toBe(true);
  });
});
