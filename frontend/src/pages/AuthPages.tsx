import { useState, type FormEvent } from 'react';
import { Link, Navigate, useNavigate } from 'react-router-dom';
import { api, ApiError, type User } from '../lib/api';
import { useAuth } from '../lib/auth';

function AuthShell({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <main className="relative flex min-h-screen items-center justify-center overflow-hidden p-6 [background:radial-gradient(ellipse_90%_65%_at_50%_-12%,#3d2e1a,#1a140e_70%),#1a140e]">
      <div
        aria-hidden
        className="pointer-events-none absolute -bottom-28 -right-16 select-none text-[520px] leading-none text-gold/5"
      >
        ♞
      </div>
      <div aria-hidden className="pointer-events-none absolute inset-0 shadow-[inset_0_0_180px_rgba(0,0,0,.55)]" />
      <div className="relative w-full max-w-sm">
        <div className="mb-7 text-center">
          <span className="mx-auto flex h-14 w-14 items-center justify-center rounded-[4px] border border-gold/55 bg-gradient-to-br from-gold/[.14] to-gold/[.02] text-[33px] text-gold outline outline-1 outline-offset-4 outline-gold/20">
            ♞
          </span>
          <h1 className="mt-4 font-display text-[38px] font-semibold tracking-[.02em]">Shantranj</h1>
          <p className="font-display text-[15px] italic text-muted">{title}</p>
        </div>
        <div className="parchment-card card-rise p-6">
          <div className="rule-gold" />
          {children}
        </div>
      </div>
    </main>
  );
}

export function LoginPage() {
  const { user, setUser } = useAuth();
  const navigate = useNavigate();
  const [identifier, setIdentifier] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  if (user) return <Navigate to="/learn" replace />;

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const u = await api.post<User>('/api/v1/auth/login', { identifier, password });
      setUser(u);
      navigate('/learn');
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Login failed');
    } finally {
      setBusy(false);
    }
  };

  return (
    <AuthShell title="Chess beyond the rules">
      <form onSubmit={submit} className="space-y-4">
        <div>
          <label className="label-parchment">Email or username</label>
          <input
            className="input-parchment"
            value={identifier}
            onChange={(e) => setIdentifier(e.target.value)}
            autoFocus
          />
        </div>
        <div>
          <label className="label-parchment">Password</label>
          <input
            className="input-parchment"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
        </div>
        {error && <p className="text-sm text-wrong">{error}</p>}
        <button disabled={busy} className="btn-primary w-full py-2.5">
          {busy ? 'Signing in…' : 'Sign in'}
        </button>
        <div className="flex items-center gap-2.5 font-mono text-[9px] uppercase tracking-[.2em] text-[#a8946c]">
          <span className="h-px flex-1 bg-[#d3c096]" />
          or
          <span className="h-px flex-1 bg-[#d3c096]" />
        </div>
        <a
          href="/api/v1/auth/google"
          className="block w-full rounded-[6px] border border-[#c4ae7f] py-2 text-center text-sm transition-colors hover:border-gold"
        >
          Continue with Google
        </a>
        <p className="text-center text-[13.5px] text-parchment-muted">
          New here?{' '}
          <Link to="/register" className="text-[#8c5f22] underline">
            Begin your study
          </Link>
        </p>
      </form>
    </AuthShell>
  );
}

export function RegisterPage() {
  const { user, setUser } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState('');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  if (user) return <Navigate to="/learn" replace />;

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const u = await api.post<User>('/api/v1/auth/register', { email, username, password });
      setUser(u);
      navigate('/learn');
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Registration failed');
    } finally {
      setBusy(false);
    }
  };

  return (
    <AuthShell title="Begin your study">
      <form onSubmit={submit} className="space-y-4">
        <div>
          <label className="label-parchment">Email</label>
          <input
            className="input-parchment"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            autoFocus
          />
        </div>
        <div>
          <label className="label-parchment">Username</label>
          <input
            className="input-parchment"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            placeholder="3–20 letters, digits, _"
          />
        </div>
        <div>
          <label className="label-parchment">Password</label>
          <input
            className="input-parchment"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="8+ chars, letter + digit"
          />
        </div>
        {error && <p className="text-sm text-wrong">{error}</p>}
        <button disabled={busy} className="btn-primary w-full py-2.5">
          {busy ? 'Creating…' : 'Create account'}
        </button>
        <p className="text-center text-[13.5px] text-parchment-muted">
          Already studying?{' '}
          <Link to="/login" className="text-[#8c5f22] underline">
            Sign in
          </Link>
        </p>
      </form>
    </AuthShell>
  );
}
