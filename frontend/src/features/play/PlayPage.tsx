import { useState } from 'react';
import Board from '../../components/Board';
import { idxToSq, isWhitePiece, parseFEN, pseudoMoves } from '../../lib/chess';
import { useAuth } from '../../lib/auth';
import { PathIcon, ProfileIcon, SettingsIcon } from '../../components/icons';
import Clock from './Clock';
import CoachPanel, { EvalBar } from './CoachPanel';
import {
  BOT_ANCHORS,
  backToLobby,
  joinQueue,
  leaveQueue,
  offerDraw,
  resign,
  respondDraw,
  sendMoveSmart,
  startBotGame,
  usePlayState,
} from './gameStore';

const COACH_NAMES: Record<number, string> = {
  1: 'Full Coach',
  2: 'Guided',
  3: 'Balanced',
  4: 'Whisper',
  5: 'Shadow',
};

const TIME_CONTROLS: { label: string; base: number | null; inc: number; tag: string }[] = [
  { label: '1+0', base: 1, inc: 0, tag: 'bullet' },
  { label: '3+2', base: 3, inc: 2, tag: 'blitz' },
  { label: '5+0', base: 5, inc: 0, tag: 'blitz' },
  { label: '10+5', base: 10, inc: 5, tag: 'rapid' },
  { label: '15+10', base: 15, inc: 10, tag: 'rapid' },
  { label: '30+0', base: 30, inc: 0, tag: 'classical' },
  { label: '∞', base: null, inc: 0, tag: 'untimed' },
];

const MODES = [
  { key: 'human', title: 'Human', desc: 'No engines, no hints.', Icon: ProfileIcon },
  { key: 'learn', title: 'Learn', desc: 'A coach at your shoulder.', Icon: PathIcon },
  { key: 'bot', title: 'Bot Arena', desc: 'Rated against the ladder.', Icon: SettingsIcon },
] as const;

export default function PlayPage() {
  const play = usePlayState();
  if (play.phase === 'playing' || play.phase === 'over') return <GameScreen />;
  return <Lobby />;
}

function Lobby() {
  const play = usePlayState();
  const [tcIdx, setTcIdx] = useState(2); // 5+0
  const [rated, setRated] = useState(true);
  const [opponent, setOpponent] = useState<'human' | 'bot' | 'learn'>('human');
  const [botLevel, setBotLevel] = useState(3);
  const [coachLevel, setCoachLevel] = useState(2);
  const [starting, setStarting] = useState(false);
  const tc = TIME_CONTROLS[tcIdx];

  return (
    <div className="max-w-[640px]">
      <div className="eyebrow-gold">Play</div>
      <h1 className="page-title mt-1">Take a seat</h1>
      <p className="page-sub mb-7 mt-1">
        {opponent === 'human'
          ? 'Human vs human — no engines, no hints.'
          : opponent === 'bot'
            ? 'The Bot Arena — no training wheels, rated against the ladder.'
            : 'Learn by playing — a bot to beat, a coach at your shoulder. Unrated.'}
      </p>

      <div className="mb-6">
        <div className="eyebrow mb-2.5">Opponent</div>
        <div className="grid grid-cols-1 gap-2.5 sm:grid-cols-3">
          {MODES.map((m) => (
            <button
              key={m.key}
              onClick={() => setOpponent(m.key)}
              className={`rounded-[8px] border p-3.5 text-left transition-all duration-150 ${
                opponent === m.key
                  ? 'border-gold/55 bg-gradient-to-b from-gold/[.14] to-gold/[.04] shadow-[0_0_20px_-8px_rgba(217,164,65,.5)]'
                  : 'panel hover:border-[#8a6f4a]'
              }`}
            >
              <m.Icon size={20} className={opponent === m.key ? 'text-gold-soft' : 'text-[#a8895a]'} />
              <div className={`mt-2 text-[15px] font-bold ${opponent === m.key ? 'text-gold-soft' : 'text-cream'}`}>
                {m.title}
              </div>
              <div className="mt-0.5 text-xs text-muted">{m.desc}</div>
            </button>
          ))}
        </div>
      </div>

      {opponent === 'learn' && (
        <div className="mb-6">
          <div className="eyebrow mb-2.5">Coaching intensity</div>
          <div className="flex flex-wrap gap-2">
            {[1, 2, 3, 4, 5].map((lvl) => (
              <button
                key={lvl}
                onClick={() => setCoachLevel(lvl)}
                className={`chip px-4 py-1.5 text-[13px] ${lvl === coachLevel ? 'chip-active' : ''}`}
              >
                L{lvl}
                <span className="ml-1.5 font-mono text-[10px] opacity-70">{COACH_NAMES[lvl]}</span>
              </button>
            ))}
          </div>
        </div>
      )}

      {opponent !== 'human' && (
        <div className="mb-6">
          <div className="eyebrow mb-2.5">Bot strength</div>
          <div className="flex flex-wrap gap-2">
            {[1, 2, 3, 4, 5, 6, 7, 8].map((lvl) => (
              <button
                key={lvl}
                onClick={() => setBotLevel(lvl)}
                className={`chip px-3.5 py-1.5 font-mono text-[13px] ${lvl === botLevel ? 'chip-active' : ''}`}
              >
                {lvl}
                <span className="ml-1.5 text-[10px] opacity-70">≈{BOT_ANCHORS[lvl]}</span>
              </button>
            ))}
          </div>
        </div>
      )}

      <div className="mb-6">
        <div className="eyebrow mb-2.5">Time control</div>
        <div className="flex flex-wrap gap-2">
          {TIME_CONTROLS.map((t, i) => (
            <button
              key={t.label}
              onClick={() => setTcIdx(i)}
              className={`chip px-4 py-1.5 font-mono text-[13px] ${i === tcIdx ? 'chip-active' : ''}`}
            >
              {t.label}
              <span className="ml-2 text-[9px] uppercase opacity-70">{t.tag}</span>
            </button>
          ))}
        </div>
      </div>

      <label className="mb-7 flex cursor-pointer items-center gap-2.5 text-sm text-cream-dim">
        <input type="checkbox" checked={rated} onChange={(e) => setRated(e.target.checked)} className="accent-[#d9a441]" />
        Rated — affects your online Elo
      </label>

      {play.phase === 'queued' ? (
        <div className="flex items-center gap-4">
          <span className="page-sub animate-pulse text-gold">Searching for an opponent…</span>
          <button onClick={leaveQueue} className="btn-secondary px-4 py-2 text-sm">
            Cancel
          </button>
        </div>
      ) : opponent === 'human' ? (
        <button onClick={() => joinQueue(tc.base, tc.inc, rated)} className="btn-primary px-7 py-3 text-base">
          Find an opponent
        </button>
      ) : (
        <div className="inline-flex flex-col gap-1.5">
          <button
            disabled={starting}
            onClick={async () => {
              setStarting(true);
              try {
                await startBotGame(
                  botLevel,
                  tc.base,
                  tc.inc,
                  opponent === 'bot' && rated,
                  opponent === 'learn' ? coachLevel : null,
                );
              } finally {
                setStarting(false);
              }
            }}
            className="btn-primary px-7 py-3 text-base"
          >
            {starting ? 'Setting up…' : opponent === 'learn' ? 'Begin lesson game' : `Challenge Bot ${botLevel}`}
          </button>
          <span className="text-center font-mono text-[10.5px] text-parchment-muted">
            Bot {botLevel} (≈{BOT_ANCHORS[botLevel]})
            {opponent === 'learn' ? ` · Coach: ${COACH_NAMES[coachLevel]}` : ''} · {tc.label} ·{' '}
            {opponent === 'learn' || !rated ? 'unrated' : 'rated'}
          </span>
        </div>
      )}
      {play.error && <p className="mt-4 text-sm text-wrong">{play.error}</p>}
    </div>
  );
}

export function GameScreen() {
  const play = usePlayState();
  const { user } = useAuth();
  const [selected, setSelected] = useState<number | null>(null);
  const game = play.game;

  if (!game || !user) return <p className="page-sub">Setting up…</p>;

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
    sendMoveSmart(from, to, promo);
    setSelected(null);
  };

  const hintArrow: [string, string][] = play.coach.hintMove
    ? [[play.coach.hintMove.slice(0, 2), play.coach.hintMove.slice(2, 4)]]
    : [];

  const myClock = myColor === 'w' ? game.clocks.w : game.clocks.b;
  const oppClock = myColor === 'w' ? game.clocks.b : game.clocks.w;
  const running = play.phase === 'playing';
  const showEvalBar =
    game.coach_level != null && // optional on the wire: covers null AND undefined
    game.coach_level <= 2 &&
    play.coach.evalCp !== null &&
    play.phase === 'playing';

  return (
    <div className="grid items-start gap-9 lg:grid-cols-[minmax(360px,600px)_minmax(300px,1fr)]">
      <div>
        <div className="mb-2.5 flex items-center justify-between">
          <div className="flex items-center gap-2.5 text-[15px]">
            <span
              className={`h-2 w-2 rounded-full ${
                play.opponentConnected
                  ? 'bg-correct shadow-[0_0_6px_rgba(140,182,94,.8)]'
                  : 'bg-wrong'
              }`}
            />
            <span className="font-bold">{play.opponent?.username ?? 'Opponent'}</span>
            <span className="font-mono text-xs text-muted">
              {play.opponent ? play.opponent.rating : ''}
            </span>
            {!play.opponentConnected && (
              <span className="font-mono text-[10px] uppercase text-wrong">
                disconnected — 30s to forfeit
              </span>
            )}
          </div>
          <Clock ms={oppClock} running={running && game.turn !== myColor} syncedAt={play.clockSyncAt} />
        </div>

        <div className="flex items-stretch gap-3">
          {showEvalBar && <EvalBar evalCp={play.coach.evalCp} />}
          <div className="min-w-0 flex-1">
            <Board
              pos={pos}
              orientation={myColor === 'w' ? 'white' : 'black'}
              dots={selected !== null ? pseudoMoves(pos, selected) : []}
              selected={selected}
              lastMove={game.last_move}
              arrows={hintArrow}
              onSquareClick={onSquareClick}
            />
          </div>
        </div>

        <div className="mt-2.5 flex items-center justify-between">
          <div className="flex items-center gap-2.5 text-[15px]">
            <span className="font-bold">{user.username}</span>
            {myTurn && (
              <span className="font-mono text-[10px] uppercase tracking-[.14em] text-gold-soft">
                · your move
              </span>
            )}
          </div>
          <Clock ms={myClock} running={running && game.turn === myColor} syncedAt={play.clockSyncAt} />
        </div>
      </div>

      <div className="flex flex-col gap-4">
        <CoachPanel />
        {oppOfferedDraw && play.phase === 'playing' && (
          <div className="card-rise rounded-[6px] border border-gold/45 bg-gold/15 p-3 text-sm">
            Your opponent offers a draw.
            <div className="mt-2 flex gap-2">
              <button onClick={() => respondDraw(true)} className="btn-primary rounded-[5px] px-3.5 py-1 text-sm">
                Accept
              </button>
              <button onClick={() => respondDraw(false)} className="btn-secondary px-3.5 py-1 text-sm">
                Decline
              </button>
            </div>
          </div>
        )}

        <div className="panel px-4 py-3.5">
          <div className="eyebrow mb-2 text-[10.5px]">Moves</div>
          <div className="grid max-h-64 grid-cols-[30px_1fr_1fr] content-start overflow-y-auto font-mono text-[13px]">
            {Array.from({ length: Math.ceil(game.moves.length / 2) }, (_, n) => {
              const w = game.moves[n * 2];
              const b = game.moves[n * 2 + 1];
              const lastIdx = game.moves.length - 1;
              const cell = (m: typeof w, idx: number) =>
                m ? (
                  <span
                    className={`justify-self-start rounded px-1.5 py-0.5 ${
                      idx === lastIdx ? 'bg-gold/10 text-gold-soft' : 'text-[#e5d9c0]'
                    }`}
                  >
                    {m.san}
                  </span>
                ) : (
                  <span />
                );
              return (
                <div key={n} className="col-span-3 grid grid-cols-subgrid border-b border-walnut-line/35 py-1">
                  <span className="text-parchment-muted">{n + 1}</span>
                  {cell(w, n * 2)}
                  {cell(b, n * 2 + 1)}
                </div>
              );
            })}
          </div>
        </div>

        {play.phase === 'playing' && (
          <div className="flex gap-2">
            <button onClick={offerDraw} disabled={iOfferedDraw} className="btn-secondary px-4.5 py-2 text-sm">
              {iOfferedDraw ? 'Draw offered…' : 'Offer draw'}
            </button>
            <button
              onClick={() => {
                if (confirm('Resign this game?')) resign();
              }}
              className="btn-danger px-4.5 py-2 text-sm"
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
        {play.error && <p className="text-sm text-wrong">{play.error}</p>}
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
    <div className="parchment-card card-rise p-5">
      <div className="rule-gold" />
      <h2 className="font-display text-2xl font-bold">{headline}</h2>
      <p className="mt-1 text-sm text-parchment-muted">by {over.reason}</p>
      {myDelta !== null && (
        <p className="mt-2 font-mono text-sm">
          Rating: {myDelta >= 0 ? '+' : ''}
          {myDelta}
        </p>
      )}
      <button onClick={backToLobby} className="btn-primary mt-4 px-4.5 py-2 text-sm">
        Back to lobby
      </button>
    </div>
  );
}
