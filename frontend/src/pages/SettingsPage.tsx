import { useState, type FormEvent } from 'react';
import { api, ApiError, type User } from '../lib/api';
import { useAuth } from '../lib/auth';

export default function SettingsPage() {
  const { user, setUser } = useAuth();
  const [username, setUsername] = useState(user?.username ?? '');
  const [avatarUrl, setAvatarUrl] = useState(user?.avatar_url ?? '');
  const [msg, setMsg] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setMsg(null);
    setError(null);
    try {
      const updated = await api.patch<User>('/api/v1/users/me', {
        username: username !== user?.username ? username : undefined,
        avatar_url: avatarUrl || undefined,
      });
      setUser(updated);
      setMsg('Saved.');
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Save failed');
    }
  };

  return (
    <div className="max-w-md">
      <h1 className="font-display mb-6 text-3xl font-bold">Settings</h1>
      <form onSubmit={submit} className="space-y-4">
        <div>
          <label className="mb-1 block font-mono text-[11px] uppercase tracking-wider text-muted">
            Username
          </label>
          <input
            className="w-full rounded-xs border border-walnut-line bg-walnut-800 px-3 py-2 text-sm outline-none focus:border-gold"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
          />
        </div>
        <div>
          <label className="mb-1 block font-mono text-[11px] uppercase tracking-wider text-muted">
            Avatar URL
          </label>
          <input
            className="w-full rounded-xs border border-walnut-line bg-walnut-800 px-3 py-2 text-sm outline-none focus:border-gold"
            value={avatarUrl}
            onChange={(e) => setAvatarUrl(e.target.value)}
          />
        </div>
        {msg && <p className="text-sm text-correct">{msg}</p>}
        {error && <p className="text-sm text-wrong">{error}</p>}
        <button className="rounded-xs bg-gold px-5 py-2 text-sm font-bold text-walnut-950 hover:bg-[#e5b458]">
          Save changes
        </button>
      </form>
      <p className="mt-8 font-mono text-xs text-muted">
        Signed in as {user?.email} · member since{' '}
        {user ? new Date(user.created_at).toLocaleDateString() : ''}
      </p>
    </div>
  );
}
