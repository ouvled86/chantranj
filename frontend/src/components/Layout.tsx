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
import {
  ArchiveIcon,
  DuelIcon,
  FlameIcon,
  FriendsIcon,
  PathIcon,
  PlayIcon,
  ProfileIcon,
  QuillIcon,
  RanksIcon,
  RosetteIcon,
  SettingsIcon,
} from './icons';

const navItems = [
  { to: '/learn', label: 'The Path', Icon: PathIcon },
  { to: '/play', label: 'Play', Icon: PlayIcon },
  { to: '/duel', label: 'Puzzle Duel', Icon: DuelIcon },
  { to: '/friends', label: 'Friends', Icon: FriendsIcon },
  { to: '/leaderboards', label: 'Leaderboards', Icon: RanksIcon },
  { to: '/profile', label: 'Profile', Icon: ProfileIcon },
  { to: '/achievements', label: 'Achievements', Icon: RosetteIcon },
  { to: '/games', label: 'Archive', Icon: ArchiveIcon },
  { to: '/settings', label: 'Settings', Icon: SettingsIcon },
];

const adminNavItem = { to: '/admin', label: 'Content Studio', Icon: QuillIcon };

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
    <nav className="flex-1 space-y-[3px] px-3.5 py-4">
      {links.map((item) => (
        <NavLink
          key={item.to}
          to={item.to}
          onClick={() => setOpen(false)}
          className={({ isActive }) =>
            `flex h-[38px] items-center gap-3 rounded-[6px] px-3 text-sm transition-colors duration-150 ${
              isActive
                ? 'bg-gradient-to-r from-gold/[.18] to-gold/[.03] text-gold-soft shadow-[inset_2.5px_0_0_-0.5px_#d9a441,inset_0_0_0_1px_rgba(217,164,65,.15)]'
                : 'text-[#c9bda6] hover:bg-walnut-850/70 hover:text-parchment'
            }`
          }
        >
          {({ isActive }) => (
            <>
              <item.Icon className={isActive ? 'opacity-100' : 'opacity-80'} />
              {item.label}
            </>
          )}
        </NavLink>
      ))}
    </nav>
  );

  const lockup = (
    <div className="flex items-center gap-3.5 border-b border-walnut-line/70 px-5 py-6">
      <span className="flex h-[46px] w-[46px] flex-none items-center justify-center rounded-[3px] border border-gold/55 bg-gradient-to-br from-gold/[.14] to-gold/[.02] text-[27px] leading-none text-gold outline outline-1 outline-offset-[3px] outline-gold/[.18]">
        ♞
      </span>
      <div>
        <h1 className="font-display text-[21px] font-semibold leading-tight tracking-[.02em]">
          Shantranj
        </h1>
        <p className="font-display text-[11px] italic text-muted">Chess beyond the rules</p>
      </div>
    </div>
  );

  const footer = (
    <>
      {stats && (
        <div className="border-t border-walnut-line/70 px-5 py-3.5">
          <div className="flex items-center justify-between font-mono text-[10px] uppercase tracking-[.14em]">
            <span className="text-gold">Lv {stats.level}</span>
            <span className="flex items-center gap-1 text-muted">
              <FlameIcon size={12} strokeWidth={1.7} className="text-gold" />
              {stats.streak}
            </span>
          </div>
          <div className="xp-track mt-2 h-1.5 w-full">
            <div
              className="xp-fill"
              style={{
                width: `${stats.xp_for_next ? Math.round((stats.xp_into_level / stats.xp_for_next) * 100) : 0}%`,
              }}
            />
          </div>
          <div className="mt-1 font-mono text-[10px] text-parchment-muted">
            {stats.xp_into_level} / {stats.xp_for_next} XP
          </div>
        </div>
      )}
      <div className="flex items-center gap-3 border-t border-walnut-line/70 px-5 py-4">
        <span className="flex h-[34px] w-[34px] flex-none items-center justify-center rounded-full bg-gradient-to-br from-gold-bright to-gold-deep font-display text-base font-bold text-walnut-950">
          {user?.username?.[0]?.toUpperCase() ?? '?'}
        </span>
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm">{user?.username}</p>
          <p className="font-mono text-[9px] uppercase tracking-[.16em] text-parchment-muted">
            {user?.role === 'ADMIN' ? 'administrator' : 'student'}
          </p>
        </div>
        <button
          onClick={logout}
          className="border-b border-muted/40 text-xs text-muted transition-colors hover:text-cream"
        >
          Sign out
        </button>
      </div>
    </>
  );

  return (
    <div className="flex min-h-screen">
      <aside className="sticky top-0 hidden h-screen w-[264px] flex-col border-r border-walnut-line/80 bg-gradient-to-b from-[#1c150d] to-[#171008] shadow-[inset_-1px_0_0_rgba(0,0,0,.4)] md:flex">
        {lockup}
        {nav}
        {footer}
      </aside>

      {/* mobile: knight FAB → drawer */}
      <button
        onClick={() => setOpen(!open)}
        aria-label="Menu"
        className="fixed bottom-4 left-4 z-30 flex h-[54px] w-[54px] items-center justify-center rounded-full bg-gradient-to-br from-gold-bright to-gold-deep text-[26px] text-walnut-950 shadow-[0_14px_30px_-8px_rgba(0,0,0,.7),inset_0_1px_0_rgba(255,255,255,.35)] md:hidden"
      >
        ♞
      </button>
      {open && (
        <div className="fixed inset-0 z-20 bg-[#0a0704]/70 md:hidden" onClick={() => setOpen(false)}>
          <aside
            className="flex h-full w-[288px] flex-col bg-gradient-to-b from-[#1c150d] to-[#171008] shadow-[30px_0_60px_rgba(0,0,0,.6)]"
            onClick={(e) => e.stopPropagation()}
          >
            {lockup}
            {nav}
            {footer}
          </aside>
        </div>
      )}

      <main className="min-w-0 flex-1 px-5 py-8 md:px-10 md:py-10">
        <Outlet />
      </main>

      <RewardToasts />

      {social.incoming && (
        <div className="parchment-card card-rise fixed bottom-4 right-4 z-40 w-72 p-4">
          <div className="rule-gold" />
          <div className="font-mono text-[10px] uppercase tracking-[.18em] text-[#8c5f22]">
            Challenge
          </div>
          <p className="mt-1 text-sm">
            <b>{social.incoming.from_username}</b> challenges you —{' '}
            {social.incoming.time_control.base_min ?? '∞'}+{social.incoming.time_control.inc_sec}
            {social.incoming.rated ? ', rated' : ', casual'}
          </p>
          <div className="mt-3 flex gap-2">
            <button
              onClick={() => acceptChallenge(social.incoming!.challenge_id)}
              className="btn-primary rounded-[5px] px-3.5 py-1 text-xs"
            >
              Accept
            </button>
            <button
              onClick={() => declineChallenge(social.incoming!.challenge_id)}
              className="rounded-[5px] border border-[#c4ae7f] px-3.5 py-1 text-xs"
            >
              Decline
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
