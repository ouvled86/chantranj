import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api, type ItemDetail, type RewardSummary } from '../../lib/api';
import { showReward } from '../stats/rewardToast';
import { GameScreen } from '../play/PlayPage';
import { activeBossSlug, backToLobby, clearBoss, startBossGame, usePlayState } from '../play/gameStore';

const OBJECTIVE_TEXT: Record<string, string> = {
  win: 'Win the game',
  checkmate: 'Win by checkmate',
  draw: 'Hold the draw',
  convert: 'Convert the advantage into a win',
};

export default function BossChallenge({ item }: { item: ItemDetail }) {
  const play = usePlayState();
  const boss = item.boss!;
  const isThisBoss = activeBossSlug() === item.slug;
  const intro = (item.content as { intro?: string }).intro ?? '';
  const outro = (item.content as { outro?: string }).outro ?? '';

  // Leaving a previous game lingering? Only show live UI for THIS boss.
  const inGame = isThisBoss && (play.phase === 'playing' || play.phase === 'over');

  if (inGame && play.phase === 'playing') return <GameScreen />;
  if (inGame && play.phase === 'over') {
    return <BossResult slug={item.slug} outro={outro} />;
  }

  return (
    <div className="max-w-xl">
      <div className="relative rounded-xs bg-parchment p-6 text-parchment-ink shadow-xl">
        <div className="absolute left-6 right-6 top-0 h-[3px] rounded-b-xs bg-gold" />
        <div className="mb-2 font-mono text-[11px] uppercase tracking-[0.14em] text-[#8c5f22]">
          👑 Boss Checkpoint
        </div>
        <p className="text-[15px] leading-relaxed">{intro}</p>

        <dl className="mt-4 grid grid-cols-2 gap-x-4 gap-y-2 border-t border-dashed border-[#c9b78d] pt-4 font-mono text-xs">
          <dt className="text-parchment-muted">Objective</dt>
          <dd>
            {OBJECTIVE_TEXT[boss.objective] ?? boss.objective}
            {boss.move_limit ? ` in ≤${boss.move_limit} moves` : ''}
          </dd>
          <dt className="text-parchment-muted">You play</dt>
          <dd className="capitalize">{boss.player_color}</dd>
          <dt className="text-parchment-muted">Opponent</dt>
          <dd>Bot {boss.bot_level}</dd>
        </dl>

        <button
          onClick={() =>
            startBossGame(
              item.slug,
              boss.player_color as 'white' | 'black',
              `Boss — ${item.title}`,
            )
          }
          className="mt-5 rounded-xs bg-gold px-6 py-3 font-bold text-walnut-950 hover:bg-[#e5b458]"
        >
          Begin the challenge
        </button>
      </div>

      <Link to="/learn" className="mt-6 inline-block text-sm text-muted hover:text-cream">
        ◂ Back to the path
      </Link>
    </div>
  );
}

function BossResult({ slug, outro }: { slug: string; outro: string }) {
  const play = usePlayState();
  const [verdict, setVerdict] = useState<{ passed: boolean; reason: string } | null>(null);
  const [checking, setChecking] = useState(true);

  useEffect(() => {
    const gameId = play.game?.game_id;
    if (!gameId) return;
    api
      .post<{ passed: boolean; reason: string; reward: RewardSummary | null }>(
        `/api/v1/learn/items/${slug}/boss/verify`,
        { game_id: gameId },
      )
      .then((v) => {
        setVerdict(v);
        showReward(v.reward);
      })
      .catch(() => setVerdict({ passed: false, reason: 'Could not verify the result.' }))
      .finally(() => setChecking(false));
  }, [slug, play.game?.game_id]);

  return (
    <div className="max-w-xl">
      <div className="relative rounded-xs bg-parchment p-6 text-parchment-ink shadow-xl">
        <div className="absolute left-6 right-6 top-0 h-[3px] rounded-b-xs bg-gold" />
        {checking ? (
          <p className="font-display italic text-parchment-muted">Judging your performance…</p>
        ) : (
          <>
            <h2 className="font-display text-2xl font-bold">
              {verdict?.passed ? '👑 Checkpoint cleared!' : 'Not yet.'}
            </h2>
            <p className="mt-2 text-[15px] leading-relaxed">{verdict?.reason}</p>
            {verdict?.passed && (
              <p className="mt-3 border-t border-dashed border-[#c9b78d] pt-3 text-[15px] italic">
                {outro}
              </p>
            )}
            <div className="mt-5 flex gap-2">
              {verdict?.passed ? (
                <Link
                  to="/learn"
                  onClick={() => {
                    clearBoss();
                    backToLobby();
                  }}
                  className="rounded-xs bg-gold px-4 py-2 text-sm font-bold text-walnut-950 hover:bg-[#e5b458]"
                >
                  Onward ▸
                </Link>
              ) : (
                <button
                  onClick={() => {
                    clearBoss();
                    backToLobby();
                  }}
                  className="rounded-xs bg-gold px-4 py-2 text-sm font-bold text-walnut-950 hover:bg-[#e5b458]"
                >
                  Try again
                </button>
              )}
            </div>
          </>
        )}
      </div>
    </div>
  );
}
