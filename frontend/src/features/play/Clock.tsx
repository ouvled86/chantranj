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
      className={`rounded-[6px] border px-3.5 py-1 font-mono text-[21px] tabular-nums transition-colors duration-200 ${
        running
          ? low
            ? 'border-wrong/60 bg-wrong/20 text-[#e37a60] shadow-[0_0_18px_-6px_rgba(200,80,60,.6)]'
            : 'border-gold/50 bg-gradient-to-b from-gold/[.22] to-gold/[.08] text-gold-bright shadow-glow-gold'
          : 'border-walnut-edge bg-[#241b10] text-[#8f8065]'
      }`}
    >
      {mm}:{ss}
    </span>
  );
}
