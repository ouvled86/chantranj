import { useCallback, useEffect, useRef, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { api, ApiError, type ItemDetail, type RewardSummary } from '../../lib/api';
import { showReward } from '../stats/rewardToast';
import BossChallenge from './BossChallenge';
import DrillPlayer from './DrillPlayer';
import LessonPlayer from './LessonPlayer';

export default function ItemPage() {
  const { slug } = useParams<{ slug: string }>();
  // key remounts the loader on navigation — state resets for free.
  return <ItemLoader key={slug} slug={slug ?? ''} />;
}

function ItemLoader({ slug }: { slug: string }) {
  const [item, setItem] = useState<ItemDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [completed, setCompleted] = useState(false);
  const posted = useRef(false);

  useEffect(() => {
    api
      .get<ItemDetail>(`/api/v1/learn/items/${slug}`)
      .then(setItem)
      .catch((e: ApiError) =>
        setError(e.code === 'locked' ? 'Finish the previous material first.' : e.message),
      );
  }, [slug]);

  const onComplete = useCallback(() => {
    if (posted.current) return;
    posted.current = true;
    api
      .post<{ status: string; reward: RewardSummary | null }>(
        `/api/v1/learn/items/${slug}/complete`,
      )
      .then((res) => {
        setCompleted(true);
        showReward(res.reward);
      })
      .catch(() => {
        posted.current = false;
      });
  }, [slug]);

  if (error)
    return (
      <div>
        <p className="text-wrong">{error}</p>
        <Link className="mt-3 inline-block text-gold underline" to="/learn">
          ◂ Back to the path
        </Link>
      </div>
    );
  if (!item) return <p className="font-display italic text-muted">Setting up the board…</p>;

  if (item.kind === 'BOSS') return <BossChallenge item={item} />;

  return (
    <div>
      <header className="mb-6">
        <div className="mb-1 font-mono text-[11px] uppercase tracking-[0.14em] text-gold">
          {item.kind === 'LESSON' ? 'Lesson' : 'Drill'}
          {completed && ' · completed ✓'}
        </div>
        <h1 className="font-display text-3xl font-bold leading-tight">{item.title}</h1>
        {item.sub && <p className="mt-1 font-display italic text-muted">{item.sub}</p>}
      </header>

      {item.kind === 'LESSON' ? (
        <LessonPlayer content={item.content} onComplete={onComplete} />
      ) : (
        <DrillPlayer content={item.content} onComplete={onComplete} />
      )}

      <div className="mt-8">
        <Link
          to="/learn"
          className="rounded-xs border border-walnut-line px-4 py-2 text-sm text-muted hover:text-cream"
        >
          ◂ Back to the path
        </Link>
      </div>
    </div>
  );
}
