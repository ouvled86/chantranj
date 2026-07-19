import { useEffect, useState } from 'react';

/** Cosmetic countdown — the server clock is the truth, synced on every move. */
export default function Clock({
  ms,
  running,
  syncedAt,
}: {
  ms: number | null;
  running: boolean;
  syncedAt: number;
}) {
  const [now, setNow] = useState(syncedAt);

  useEffect(() => {
    if (ms === null || !running) return;
    const id = setInterval(() => setNow(Date.now()), 200);
    return () => clearInterval(id);
  }, [running, ms, syncedAt]);

  if (ms === null) return <span className="font-mono text-lg text-muted">∞</span>;

  const remaining = running ? Math.max(0, Math.min(ms, ms - (now - syncedAt))) : ms;

  const totalSec = Math.floor(remaining / 1000);
  const mm = Math.floor(totalSec / 60);
  const ss = String(totalSec % 60).padStart(2, '0');
  const low = remaining < 20_000;

  return (
    <span
      className={`rounded-xs px-3 py-1 font-mono text-xl tabular-nums ${
        running
          ? low
            ? 'bg-wrong/25 text-wrong'
            : 'bg-gold/20 text-gold'
          : 'bg-walnut-800 text-muted'
      }`}
    >
      {mm}:{ss}
    </span>
  );
}
