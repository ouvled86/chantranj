/** Phase 0 placeholder shell — the full v1 design port happens in Phase 3. */
export default function App() {
  return (
    <main className="flex min-h-screen items-center justify-center p-6">
      <div className="max-w-lg text-center">
        <div className="text-5xl text-gold" aria-hidden>
          ♞
        </div>
        <h1 className="font-display mt-3 text-4xl font-bold">The Study</h1>
        <p className="font-display mt-1 italic text-muted">Chess beyond the rules</p>

        <div className="mt-8 rounded-sm bg-parchment p-5 text-left text-parchment-ink shadow-xl">
          <p className="font-mono text-xs uppercase tracking-widest text-parchment-muted">
            Scaffold check
          </p>
          <p className="mt-2 text-sm leading-relaxed">
            Full-stack rebuild in progress (Phase 0). Backend: FastAPI + TimescaleDB · Realtime:
            WebSockets + Redis · Engine: Stockfish · Observability: Prometheus + Grafana.
          </p>
        </div>

        <p className="mt-6 font-mono text-xs text-muted">
          v1 lessons still available in <code>legacy-v1/</code>
        </p>
      </div>
    </main>
  );
}
