import { useEffect, useState } from 'react';
import { NavLink, Outlet, useNavigate } from 'react-router-dom';
import { attachGame } from '../features/play/gameStore';
import {
  acceptChallenge,
  clearPendingGameStart,
  connectSocial,
  declineChallenge,
  useSocial,
} from '../features/social/socialStore';
import { RewardToasts } from '../features/stats/rewardToast';
import { refreshStats, useStats } from '../features/stats/statsStore';
import { useAuth } from '../lib/auth';

const navItems = [
  { to: '/learn', label: 'The Path', icon: '§' },
  { to: '/play', label: 'Play', icon: '⚔' },
  { to: '/duel', label: 'Puzzle Duel', icon: '⚡' },
  { to: '/friends', label: 'Friends', icon: '☰' },
  { to: '/leaderboards', label: 'Leaderboards', icon: '↑' },
  { to: '/profile', label: 'Profile', icon: '☗' },
  { to: '/achievements', label: 'Achievements', icon: '◆' },
  { to: '/games', label: 'Archive', icon: '❦' },
  { to: '/settings', label: 'Settings', icon: '⚙' },
];

const adminNavItem = { to: '/admin', label: 'Content Studio', icon: '✎' };

export default function Layout() {
  const { user, logout } = useAuth();
  const [open, setOpen] = useState(false);
  const social = useSocial();
  const stats = useStats();
  const navigate = useNavigate();

  useEffect(() => {
    connectSocial();
    refreshStats();
  }, []);

  // An accepted challenge (either side) hands off into the live game screen.
  useEffect(() => {
    if (social.pendingGameStart) {
      const { game_id, color } = social.pendingGameStart;
      attachGame(game_id, color, 'Challenger');
      clearPendingGameStart();
      navigate('/play');
    }
  }, [social.pendingGameStart, navigate]);

  const links = user?.role === 'ADMIN' ? [...navItems, adminNavItem] : navItems;
  const nav = (
    <nav className="flex-1 space-y-1 px-3 py-4">
      {links.map((item) => (
        <NavLink
          key={item.to}
          to={item.to}
          onClick={() => setOpen(false)}
          className={({ isActive }) =>
            `flex items-center gap-3 rounded-xs px-3 py-2 text-sm transition ${
              isActive
                ? 'bg-gold/15 text-gold border-l-2 border-gold'
                : 'text-cream hover:bg-walnut-800 border-l-2 border-transparent'
            }`
          }
        >
          <span className="w-4 text-center font-mono text-xs">{item.icon}</span>
          {item.label}
        </NavLink>
      ))}
    </nav>
  );

  return (
    <div className="flex min-h-screen">
      <aside className="sticky top-0 hidden h-screen w-64 flex-col border-r border-walnut-line bg-walnut-950 md:flex">
        <div className="flex items-center gap-3 border-b border-walnut-line px-5 py-5">
          <span className="text-3xl text-gold">♞</span>
          <div>
            <h1 className="font-display text-lg font-bold leading-tight">The Study</h1>
            <p className="font-display text-[11px] italic text-muted">Chess beyond the rules</p>
          </div>
        </div>
        {nav}
        {stats && (
          <div className="border-t border-walnut-line px-5 py-3">
            <div className="flex items-center justify-between font-mono text-[10px] uppercase text-muted">
              <span className="text-gold">Lv {stats.level}</span>
              <span>🔥 {stats.streak}</span>
            </div>
            <div className="mt-1 h-1.5 w-full overflow-hidden rounded-full bg-walnut-800">
              <div
                className="h-full rounded-full bg-gold"
                style={{
                  width: `${stats.xp_for_next ? Math.round((stats.xp_into_level / stats.xp_for_next) * 100) : 0}%`,
                }}
              />
            </div>
          </div>
        )}
        <div className="border-t border-walnut-line px-5 py-4">
          <p className="truncate text-sm">{user?.username}</p>
          <p className="font-mono text-[10px] uppercase tracking-wider text-muted">
            {user?.role === 'ADMIN' ? 'administrator' : 'student'}
          </p>
          <button
            onClick={logout}
            className="mt-2 rounded-xs border border-walnut-line px-3 py-1 text-xs text-muted hover:text-cream"
          >
            Sign out
          </button>
        </div>
      </aside>

      {/* mobile */}
      <button
        onClick={() => setOpen(!open)}
        className="fixed bottom-4 left-4 z-30 rounded-full bg-gold px-4 py-2 text-sm font-bold text-walnut-950 shadow-lg md:hidden"
      >
        ☰ Menu
      </button>
      {open && (
        <div className="fixed inset-0 z-20 bg-black/60 md:hidden" onClick={() => setOpen(false)}>
          <aside
            className="flex h-full w-72 flex-col bg-walnut-950"
            onClick={(e) => e.stopPropagation()}
          >
            {nav}
            <button onClick={logout} className="border-t border-walnut-line px-5 py-4 text-left text-sm text-muted">
              Sign out ({user?.username})
            </button>
          </aside>
        </div>
      )}

      <main className="min-w-0 flex-1 px-5 py-8 md:px-10">
        <Outlet />
      </main>

      <RewardToasts />

      {social.incoming && (
        <div className="fixed bottom-4 right-4 z-40 w-72 rounded-xs bg-parchment p-4 text-parchment-ink shadow-2xl">
          <div className="font-mono text-[10px] uppercase tracking-widest text-[#8c5f22]">
            Challenge
          </div>
          <p className="mt-1 text-sm">
            <b>{social.incoming.from_username}</b> challenges you —{' '}
            {social.incoming.time_control.base_min ?? '∞'}+{social.incoming.time_control.inc_sec}
            {social.incoming.rated ? ' rated' : ' casual'}
          </p>
          <div className="mt-3 flex gap-2">
            <button
              onClick={() => acceptChallenge(social.incoming!.challenge_id)}
              className="rounded-xs bg-gold px-3 py-1 text-xs font-bold text-walnut-950"
            >
              Accept
            </button>
            <button
              onClick={() => declineChallenge(social.incoming!.challenge_id)}
              className="rounded-xs border border-[#c9b78d] px-3 py-1 text-xs"
            >
              Decline
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
