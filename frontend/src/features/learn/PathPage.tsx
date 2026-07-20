import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api, type StageOut } from '../../lib/api';

const ROMAN = ['I', 'II', 'III', 'IV', 'V', 'VI', 'VII', 'VIII', 'IX', 'X', 'XI', 'XII'];

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
  if (!stages) return <p className="text-muted italic font-display">Opening the Study…</p>;

  const all = stages.flatMap((s) => s.items);
  const done = all.filter((i) => i.status === 'DONE').length;

  return (
    <div className="max-w-3xl">
      <div className="mb-8">
        <div className="h-1.5 w-full overflow-hidden rounded-full bg-walnut-800">
          <div
            className="h-full rounded-full bg-gold transition-all"
            style={{ width: `${all.length ? Math.round((done / all.length) * 100) : 0}%` }}
          />
        </div>
        <p className="mt-2 font-mono text-xs text-muted">
          {done} of {all.length} complete — finish each item to unlock the next
        </p>
      </div>

      {stages.map((stage, si) => (
        <section key={stage.slug} className="mb-9">
          <div className="mb-3 flex items-baseline gap-3">
            <span className="font-display text-lg italic text-gold">{ROMAN[si]}</span>
            <div>
              <h2 className="font-display text-xl font-semibold">{stage.title}</h2>
              <p className="text-sm text-muted">{stage.intro}</p>
            </div>
          </div>
          {stage.items.length === 0 ? (
            <p className="ml-8 border-l-2 border-walnut-line pl-4 text-sm italic text-muted">
              Content arriving in a later phase.
            </p>
          ) : (
            <ul className="ml-2 space-y-1">
              {stage.items.map((item) => (
                <li key={item.slug}>
                  {item.status === 'LOCKED' ? (
                    <div className="flex items-center gap-3 border-l-2 border-walnut-line py-2 pl-4 opacity-45">
                      <span className="font-mono text-xs">🔒</span>
                      <span className="text-sm">{item.title}</span>
                    </div>
                  ) : (
                    <Link
                      to={`/learn/${item.slug}`}
                      className={`flex items-center gap-3 border-l-2 py-2 pl-4 transition hover:bg-walnut-800 ${
                        item.kind === 'BOSS'
                          ? item.status === 'AVAILABLE'
                            ? 'border-gold bg-gold/20'
                            : 'border-gold/40 bg-gold/5'
                          : item.status === 'AVAILABLE'
                            ? 'border-gold bg-gold/10'
                            : 'border-walnut-line'
                      }`}
                    >
                      <span
                        className={`font-mono text-xs ${
                          item.kind === 'LESSON'
                            ? 'text-muted'
                            : item.kind === 'BOSS'
                              ? ''
                              : 'text-wrong'
                        }`}
                      >
                        {item.kind === 'LESSON' ? '§' : item.kind === 'BOSS' ? '👑' : '⚔'}
                      </span>
                      <span
                        className={`flex-1 text-sm ${
                          item.kind === 'BOSS' ? 'font-display font-semibold' : ''
                        }`}
                      >
                        {item.title}
                      </span>
                      {item.status === 'DONE' && (
                        <span className="text-xs font-bold text-correct">✓</span>
                      )}
                      {item.status === 'AVAILABLE' && (
                        <span className="font-mono text-[10px] uppercase tracking-wider text-gold">
                          {item.kind === 'BOSS' ? 'boss' : 'next'}
                        </span>
                      )}
                    </Link>
                  )}
                </li>
              ))}
            </ul>
          )}
        </section>
      ))}
    </div>
  );
}
