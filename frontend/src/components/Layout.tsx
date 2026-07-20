import { useState } from 'react';
import { NavLink, Outlet } from 'react-router-dom';
import { useAuth } from '../lib/auth';

const navItems = [
  { to: '/learn', label: 'The Path', icon: '§' },
  { to: '/play', label: 'Play', icon: '⚔' },
  { to: '/games', label: 'Archive', icon: '❦' },
  { to: '/settings', label: 'Settings', icon: '⚙' },
];

const adminNavItem = { to: '/admin', label: 'Content Studio', icon: '✎' };

export default function Layout() {
  const { user, logout } = useAuth();
  const [open, setOpen] = useState(false);

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
    </div>
  );
}
