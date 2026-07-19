import { useState, type FormEvent } from 'react';
import { Link, Navigate, useNavigate } from 'react-router-dom';
import { api, ApiError, type User } from '../lib/api';
import { useAuth } from '../lib/auth';

function AuthShell({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <main className="flex min-h-screen items-center justify-center p-6">
      <div className="w-full max-w-sm">
        <div className="mb-6 text-center">
          <div className="text-4xl text-gold">♞</div>
          <h1 className="font-display mt-2 text-3xl font-bold">The Study</h1>
          <p className="font-display italic text-muted">{title}</p>
        </div>
        <div className="relative rounded-xs bg-parchment p-6 text-parchment-ink shadow-xl">
          <div className="absolute left-6 right-6 top-0 h-[3px] rounded-b-xs bg-gold" />
          {children}
        </div>
      </div>
    </main>
  );
}

const inputCls =
  'w-full rounded-xs border border-[#c9b78d] bg-[#fbf6e9] px-3 py-2 text-sm text-parchment-ink outline-none focus:border-gold';
const labelCls = 'mb-1 block font-mono text-[11px] uppercase tracking-wider text-parchment-muted';

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
    <AuthShell title="Welcome back">
      <form onSubmit={submit} className="space-y-4">
        <div>
          <label className={labelCls}>Email or username</label>
          <input
            className={inputCls}
            value={identifier}
            onChange={(e) => setIdentifier(e.target.value)}
            autoFocus
          />
        </div>
        <div>
          <label className={labelCls}>Password</label>
          <input
            className={inputCls}
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
        </div>
        {error && <p className="text-sm text-wrong">{error}</p>}
        <button
          disabled={busy}
          className="w-full rounded-xs bg-gold py-2 font-bold text-walnut-950 hover:bg-[#e5b458] disabled:opacity-50"
        >
          {busy ? 'Signing in…' : 'Sign in'}
        </button>
        <a
          href="/api/v1/auth/google"
          className="block w-full rounded-xs border border-[#c9b78d] py-2 text-center text-sm hover:border-gold"
        >
          Continue with Google
        </a>
        <p className="text-center text-sm text-parchment-muted">
          New here?{' '}
          <Link to="/register" className="text-[#8c5f22] underline">
            Create an account
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
          <label className={labelCls}>Email</label>
          <input
            className={inputCls}
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            autoFocus
          />
        </div>
        <div>
          <label className={labelCls}>Username</label>
          <input
            className={inputCls}
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            placeholder="3–20 letters, digits, _"
          />
        </div>
        <div>
          <label className={labelCls}>Password</label>
          <input
            className={inputCls}
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="8+ chars, letter + digit"
          />
        </div>
        {error && <p className="text-sm text-wrong">{error}</p>}
        <button
          disabled={busy}
          className="w-full rounded-xs bg-gold py-2 font-bold text-walnut-950 hover:bg-[#e5b458] disabled:opacity-50"
        >
          {busy ? 'Creating…' : 'Create account'}
        </button>
        <p className="text-center text-sm text-parchment-muted">
          Already studying?{' '}
          <Link to="/login" className="text-[#8c5f22] underline">
            Sign in
          </Link>
        </p>
      </form>
    </AuthShell>
  );
}
