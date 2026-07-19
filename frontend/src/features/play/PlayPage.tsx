import { useState } from 'react';
import Board from '../../components/Board';
import { idxToSq, isWhitePiece, parseFEN, pseudoMoves } from '../../lib/chess';
import { useAuth } from '../../lib/auth';
import Clock from './Clock';
import {
  backToLobby,
  joinQueue,
  leaveQueue,
  offerDraw,
  resign,
  respondDraw,
  sendMove,
  usePlayState,
} from './gameStore';

const TIME_CONTROLS: { label: string; base: number | null; inc: number; tag: string }[] = [
  { label: '1+0', base: 1, inc: 0, tag: 'bullet' },
  { label: '3+2', base: 3, inc: 2, tag: 'blitz' },
  { label: '5+0', base: 5, inc: 0, tag: 'blitz' },
  { label: '10+5', base: 10, inc: 5, tag: 'rapid' },
  { label: '15+10', base: 15, inc: 10, tag: 'rapid' },
  { label: '30+0', base: 30, inc: 0, tag: 'classical' },
  { label: '∞', base: null, inc: 0, tag: 'untimed' },
];

export default function PlayPage() {
  const play = usePlayState();
  if (play.phase === 'playing' || play.phase === 'over') return <GameScreen />;
  return <Lobby />;
}

function Lobby() {
  const play = usePlayState();
  const [tcIdx, setTcIdx] = useState(2); // 5+0
  const [rated, setRated] = useState(true);
  const tc = TIME_CONTROLS[tcIdx];

  return (
    <div className="max-w-xl">
      <h1 className="font-display mb-1 text-3xl font-bold">Play Online</h1>
      <p className="mb-6 font-display italic text-muted">
        Human vs human — no engines, no hints. Post-game review arrives in Phase 5.
      </p>

      <div className="mb-5">
        <div className="mb-2 font-mono text-[11px] uppercase tracking-widest text-muted">
          Time control
        </div>
        <div className="flex flex-wrap gap-2">
          {TIME_CONTROLS.map((t, i) => (
            <button
              key={t.label}
              onClick={() => setTcIdx(i)}
              className={`rounded-xs border px-4 py-2 font-mono text-sm ${
                i === tcIdx
                  ? 'border-gold bg-gold/15 text-gold'
                  : 'border-walnut-line bg-walnut-800 text-cream hover:border-muted'
              }`}
            >
              {t.label}
              <span className="ml-2 text-[10px] uppercase text-muted">{t.tag}</span>
            </button>
          ))}
        </div>
      </div>

      <label className="mb-6 flex items-center gap-2 text-sm">
        <input type="checkbox" checked={rated} onChange={(e) => setRated(e.target.checked)} />
        Rated (affects your online Elo)
      </label>

      {play.phase === 'queued' ? (
        <div className="flex items-center gap-4">
          <span className="animate-pulse font-display italic text-gold">
            Searching for an opponent…
          </span>
          <button
            onClick={leaveQueue}
            className="rounded-xs border border-walnut-line px-4 py-2 text-sm text-muted hover:text-cream"
          >
            Cancel
          </button>
        </div>
      ) : (
        <button
          onClick={() => joinQueue(tc.base, tc.inc, rated)}
          className="rounded-xs bg-gold px-6 py-3 font-bold text-walnut-950 hover:bg-[#e5b458]"
        >
          Find an opponent
        </button>
      )}
      {play.error && <p className="mt-4 text-sm text-wrong">{play.error}</p>}
    </div>
  );
}

function GameScreen() {
  const play = usePlayState();
  const { user } = useAuth();
  const [selected, setSelected] = useState<number | null>(null);
  const game = play.game;

  if (!game || !user) return <p className="font-display italic text-muted">Setting up…</p>;

  const pos = parseFEN(game.fen);
  const myColor = play.myColor ?? 'w';
  const myTurn = game.turn === myColor && play.phase === 'playing';
  const iOfferedDraw = game.draw_offer_by === user.id;
  const oppOfferedDraw = game.draw_offer_by !== null && !iOfferedDraw;

  const onSquareClick = (i: number) => {
    if (!myTurn) return;
    const piece = pos.board[i];
    const mine = piece !== null && isWhitePiece(piece) === (myColor === 'w');
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
    const piece2 = pos.board[selected];
    const promo =
      piece2?.toLowerCase() === 'p' && (to[1] === '8' || to[1] === '1') ? 'q' : '';
    sendMove(from, to, promo);
    setSelected(null);
  };

  const myClock = myColor === 'w' ? game.clocks.w : game.clocks.b;
  const oppClock = myColor === 'w' ? game.clocks.b : game.clocks.w;
  const running = play.phase === 'playing';

  return (
    <div className="grid items-start gap-8 lg:grid-cols-[minmax(320px,560px)_minmax(280px,1fr)]">
      <div>
        <div className="mb-2 flex items-center justify-between">
          <div className="text-sm">
            <span className="font-semibold">{play.opponent?.username ?? 'Opponent'}</span>
            <span className="ml-2 font-mono text-xs text-muted">
              {play.opponent ? `(${play.opponent.rating})` : ''}
            </span>
            {!play.opponentConnected && (
              <span className="ml-2 font-mono text-[10px] uppercase text-wrong">
                disconnected — 30s to forfeit
              </span>
            )}
          </div>
          <Clock
            ms={oppClock}
            running={running && game.turn !== myColor}
            syncedAt={play.clockSyncAt}
          />
        </div>

        <Board
          pos={pos}
          orientation={myColor === 'w' ? 'white' : 'black'}
          dots={selected !== null ? pseudoMoves(pos, selected) : []}
          selected={selected}
          lastMove={game.last_move}
          onSquareClick={onSquareClick}
        />

        <div className="mt-2 flex items-center justify-between">
          <div className="text-sm">
            <span className="font-semibold">{user.username}</span>
            <span className="ml-2 font-mono text-[10px] uppercase text-muted">
              {myTurn ? '· your move' : ''}
            </span>
          </div>
          <Clock
            ms={myClock}
            running={running && game.turn === myColor}
            syncedAt={play.clockSyncAt}
          />
        </div>
      </div>

      <div>
        {oppOfferedDraw && play.phase === 'playing' && (
          <div className="mb-4 rounded-xs border border-gold/45 bg-gold/15 p-3 text-sm">
            Your opponent offers a draw.
            <div className="mt-2 flex gap-2">
              <button
                onClick={() => respondDraw(true)}
                className="rounded-xs bg-gold px-3 py-1 text-sm font-bold text-walnut-950"
              >
                Accept
              </button>
              <button
                onClick={() => respondDraw(false)}
                className="rounded-xs border border-walnut-line px-3 py-1 text-sm"
              >
                Decline
              </button>
            </div>
          </div>
        )}

        <div className="mb-4">
          <div className="mb-2 font-mono text-[10.5px] uppercase tracking-widest text-muted">
            Moves
          </div>
          <div className="flex max-h-64 flex-wrap content-start gap-1.5 overflow-y-auto">
            {game.moves.map((m, i) => (
              <span
                key={i}
                className="rounded-xs border border-walnut-line bg-walnut-800 px-2 py-0.5 font-mono text-xs text-muted"
              >
                {i % 2 === 0 ? `${i / 2 + 1}. ` : ''}
                {m.san}
              </span>
            ))}
          </div>
        </div>

        {play.phase === 'playing' && (
          <div className="flex gap-2">
            <button
              onClick={offerDraw}
              disabled={iOfferedDraw}
              className="rounded-xs border border-walnut-line px-4 py-2 text-sm text-muted hover:text-cream disabled:opacity-40"
            >
              {iOfferedDraw ? 'Draw offered…' : 'Offer draw'}
            </button>
            <button
              onClick={() => {
                if (confirm('Resign this game?')) resign();
              }}
              className="rounded-xs border border-wrong/50 px-4 py-2 text-sm text-wrong hover:bg-wrong/10"
            >
              Resign
            </button>
          </div>
        )}

        {play.phase === 'over' && play.over && (
          <ResultCard
            over={play.over}
            myColor={myColor}
            opponent={play.opponent?.username ?? 'Opponent'}
          />
        )}
        {play.error && <p className="mt-3 text-sm text-wrong">{play.error}</p>}
      </div>
    </div>
  );
}

function ResultCard({
  over,
  myColor,
  opponent,
}: {
  over: NonNullable<ReturnType<typeof usePlayState>['over']>;
  myColor: 'w' | 'b';
  opponent: string;
}) {
  const iWon =
    (over.result === 'WHITE' && myColor === 'w') || (over.result === 'BLACK' && myColor === 'b');
  const headline =
    over.result === 'DRAW'
      ? 'Draw'
      : over.result === 'ABORTED'
        ? 'Game aborted'
        : iWon
          ? 'You win!'
          : `${opponent} wins`;
  const myDelta = myColor === 'w' ? over.rating_delta.w : over.rating_delta.b;

  return (
    <div className="relative rounded-xs bg-parchment p-5 text-parchment-ink shadow-xl">
      <div className="absolute left-5 right-5 top-0 h-[3px] rounded-b-xs bg-gold" />
      <h2 className="font-display text-2xl font-bold">{headline}</h2>
      <p className="mt-1 text-sm text-parchment-muted">by {over.reason}</p>
      {myDelta !== null && (
        <p className="mt-2 font-mono text-sm">
          Rating: {myDelta >= 0 ? '+' : ''}
          {myDelta}
        </p>
      )}
      <button
        onClick={backToLobby}
        className="mt-4 rounded-xs bg-gold px-4 py-2 text-sm font-bold text-walnut-950 hover:bg-[#e5b458]"
      >
        Back to lobby
      </button>
    </div>
  );
}
