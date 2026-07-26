import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api, type StageOut } from '../../lib/api';
import { CheckIcon, CrownIcon, DrillIcon, LessonIcon, LockIcon } from '../../components/icons';

const ROMAN = ['I', 'II', 'III', 'IV', 'V', 'VI', 'VII', 'VIII', 'IX', 'X', 'XI', 'XII'];

/** Stage medallion state derived from its items. */
function stageState(stage: StageOut): 'done' | 'current' | 'locked' {
  if (stage.items.length === 0) return 'locked';
  if (stage.items.every((i) => i.status === 'DONE')) return 'done';
  if (stage.items.some((i) => i.status !== 'LOCKED')) return 'current';
  return 'locked';
}

const MEDALLION: Record<string, string> = {
  done: 'bg-gradient-to-br from-gold-bright to-gold-deep text-walnut-950 border-gold/50 shadow-[0_3px_10px_rgba(0,0,0,.5)]',
  current: 'bg-[#241b10] text-gold-soft border-gold shadow-[0_0_16px_-4px_rgba(217,164,65,.8)]',
  locked: 'bg-[#241b10] text-[#6b5a41] border-walnut-edge',
};

export default function PathPage() {
  const [stages, setStages] = useState<StageOut[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .get<StageOut[]>('/api/v1/learn/path')
      .then(setStages)
      .catch((e) => setError(e.message));
  }, []);

  if (error) return <p className="text-wrong">{error}</p>;
  if (!stages) return <p className="page-sub">Opening the Study…</p>;

  const all = stages.flatMap((s) => s.items);
  const done = all.filter((i) => i.status === 'DONE').length;
  const pct = all.length ? Math.round((done / all.length) * 100) : 0;

  return (
    <div className="max-w-3xl">
      <div className="eyebrow-gold">The Path</div>
      <div className="flex items-baseline justify-between gap-5">
        <h1 className="page-title mt-1">Twelve stages to mastery</h1>
        <span className="whitespace-nowrap font-mono text-[13px] text-gold-soft">
          {done} / {all.length}
        </span>
      </div>
      <p className="page-sub mt-1">
        Finish each item to unlock the next; beat the boss to turn the page.
      </p>
      <div className="xp-track mb-9 mt-4 h-[7px] w-full">
        <div className="xp-fill" style={{ width: `${pct}%` }} />
      </div>

      {stages.map((stage, si) => {
        const state = stageState(stage);
        return (
          <div key={stage.slug} className="flex gap-5">
            {/* medallion + connecting rule */}
            <div className="flex w-11 flex-none flex-col items-center">
              <div
                className={`flex h-11 w-11 flex-none items-center justify-center rounded-full border-[1.5px] font-display text-[17px] font-semibold italic ${MEDALLION[state]}`}
              >
                {ROMAN[si]}
              </div>
              {si < stages.length - 1 && (
                <div className="my-2 w-px flex-1 bg-gradient-to-b from-walnut-line to-walnut-line/25" />
              )}
            </div>

            <div className="min-w-0 flex-1 pb-8">
              <div className="flex items-baseline gap-3">
                <h2
                  className={`font-display text-[22px] font-semibold ${
                    state === 'current' ? 'text-parchment' : state === 'done' ? 'text-cream-dim' : 'text-[#8f8065]'
                  }`}
                >
                  {stage.title}
                </h2>
                <span
                  className={`font-mono text-[10px] uppercase tracking-[.14em] ${
                    state === 'done' ? 'text-correct' : state === 'current' ? 'text-gold-soft' : 'text-[#6b5a41]'
                  }`}
                >
                  {state === 'done' ? 'complete' : state === 'current' ? 'in progress' : 'locked'}
                </span>
              </div>
              <p className="mb-3 mt-0.5 font-display text-[13.5px] italic text-muted">{stage.intro}</p>

              {stage.items.length === 0 ? (
                <p className="panel px-4 py-3 text-sm italic text-muted opacity-60">
                  Content arriving in a later phase.
                </p>
              ) : (
                <ul
                  className={`panel flex flex-col gap-0.5 p-1.5 ${
                    state === 'locked' ? 'opacity-55' : state === 'done' ? 'opacity-80' : ''
                  }`}
                >
                  {stage.items.map((item) => {
                    const inner = (
                      <>
                        {item.kind === 'BOSS' ? (
                          <span className="seal h-[26px] w-[26px]">
                            <CrownIcon size={13} strokeWidth={1.8} className="text-parchment" />
                          </span>
                        ) : item.kind === 'LESSON' ? (
                          <LessonIcon size={16} className="flex-none text-[#a8895a]" />
                        ) : (
                          <DrillIcon size={16} className="flex-none text-[#b06a4f]" />
                        )}
                        <span
                          className={`flex-1 text-sm ${
                            item.kind === 'BOSS' ? 'font-display font-semibold' : ''
                          } ${item.status === 'AVAILABLE' ? 'text-parchment' : 'text-[#c9bda6]'}`}
                        >
                          {item.title}
                        </span>
                        {item.status === 'DONE' && (
                          <CheckIcon size={15} strokeWidth={2} className="text-correct" />
                        )}
                        {item.status === 'AVAILABLE' && (
                          <span className="btn-primary rounded-[5px] px-3.5 py-1 text-[11.5px]">
                            {item.kind === 'BOSS' ? 'Face the boss' : 'Begin'}
                          </span>
                        )}
                        {item.status === 'LOCKED' && (
                          <LockIcon size={14} className="text-[#6b5a41]" />
                        )}
                      </>
                    );
                    const rowCls =
                      'flex min-h-10 items-center gap-3 rounded-[6px] px-3 py-0.5 transition-colors duration-150';
                    return (
                      <li key={item.slug}>
                        {item.status === 'LOCKED' ? (
                          <div className={`${rowCls} opacity-60`}>{inner}</div>
                        ) : (
                          <Link
                            to={`/learn/${item.slug}`}
                            className={`${rowCls} hover:bg-cream/[.04] ${
                              item.status === 'AVAILABLE'
                                ? 'border border-gold/45 bg-gradient-to-r from-gold/15 to-gold/[.02]'
                                : ''
                            }`}
                          >
                            {inner}
                          </Link>
                        )}
                      </li>
                    );
                  })}
                </ul>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}
