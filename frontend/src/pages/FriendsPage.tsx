import { useCallback, useEffect, useState } from 'react';
import {
  api,
  del,
  type FriendsView,
  type FriendSummary,
  type UserSearchResult,
} from '../lib/api';
import { sendChallenge, useSocial } from '../features/social/socialStore';

const DOT: Record<string, string> = {
  online: 'bg-correct',
  in_game: 'bg-gold',
  in_duel: 'bg-gold',
  offline: 'bg-walnut-line',
};

const PRESENCE_LABEL: Record<string, string> = {
  online: 'online',
  in_game: 'in a game',
  in_duel: 'in a duel',
  offline: 'offline',
};

export default function FriendsPage() {
  const social = useSocial();
  const [view, setView] = useState<FriendsView | null>(null);
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<UserSearchResult[] | null>(null);
  const [challengeFor, setChallengeFor] = useState<FriendSummary | null>(null);

  const load = useCallback(() => {
    api.get<FriendsView>('/api/v1/friends').then(setView);
  }, []);

  useEffect(() => {
    load();
  }, [load, social.friendsVersion]);

  // live presence merges over the REST snapshot
  const presenceOf = (f: FriendSummary) => social.presence[f.user_id] ?? f.presence;

  const search = async (q: string) => {
    setQuery(q);
    if (q.length < 1) {
      setResults(null);
      return;
    }
    setResults(await api.get<UserSearchResult[]>(`/api/v1/friends/search?q=${encodeURIComponent(q)}`));
  };

  const sendRequest = async (username: string) => {
    await api.post('/api/v1/friends/requests', { username });
    await search(query);
    load();
  };

  const respond = async (id: number, accept: boolean) => {
    await api.post(`/api/v1/friends/requests/${id}/${accept ? 'accept' : 'decline'}`);
    load();
  };

  const unfriend = async (f: FriendSummary) => {
    await del(`/api/v1/friends/${f.user_id}`);
    load();
  };

  const block = async (f: FriendSummary) => {
    if (!confirm(`Block ${f.username}?`)) return;
    await api.post(`/api/v1/friends/${f.user_id}/block`);
    load();
  };

  if (!view) return <p className="font-display italic text-muted">Gathering your circle…</p>;

  return (
    <div className="max-w-2xl">
      <h1 className="font-display mb-1 text-3xl font-bold">Friends</h1>
      <p className="mb-6 font-display italic text-muted">
        Add rivals, see who's online, and challenge them across the board.
      </p>

      {social.toast && (
        <div className="mb-4 rounded-xs border border-gold/45 bg-gold/15 px-3 py-2 text-sm text-gold">
          {social.toast}
        </div>
      )}

      <div className="mb-6">
        <input
          value={query}
          onChange={(e) => search(e.target.value)}
          placeholder="Search players by username…"
          className="w-full rounded-xs border border-walnut-line bg-walnut-800 px-3 py-2 text-sm outline-none focus:border-gold"
        />
        {results && (
          <ul className="mt-2 space-y-1">
            {results.length === 0 && <li className="text-sm text-muted">No players found.</li>}
            {results.map((r) => (
              <li
                key={r.username}
                className="flex items-center gap-3 rounded-xs border border-walnut-line bg-walnut-800 px-3 py-2 text-sm"
              >
                <span className="flex-1">{r.username}</span>
                {r.relation === 'none' && (
                  <button
                    onClick={() => sendRequest(r.username)}
                    className="rounded-xs bg-gold px-3 py-1 text-xs font-bold text-walnut-950"
                  >
                    Add friend
                  </button>
                )}
                <span className="font-mono text-[10px] uppercase text-muted">
                  {r.relation !== 'none' ? r.relation : ''}
                </span>
              </li>
            ))}
          </ul>
        )}
      </div>

      {view.incoming.length > 0 && (
        <Section title="Requests">
          {view.incoming.map((f) => (
            <Row key={f.friendship_id} name={f.username} dot={presenceOf(f)}>
              <button
                onClick={() => respond(f.friendship_id, true)}
                className="rounded-xs bg-gold px-3 py-1 text-xs font-bold text-walnut-950"
              >
                Accept
              </button>
              <button
                onClick={() => respond(f.friendship_id, false)}
                className="rounded-xs border border-walnut-line px-3 py-1 text-xs text-muted"
              >
                Decline
              </button>
            </Row>
          ))}
        </Section>
      )}

      <Section title={`Friends (${view.friends.length})`}>
        {view.friends.length === 0 && (
          <p className="text-sm text-muted">No friends yet — search above to add some.</p>
        )}
        {view.friends.map((f) => {
          const p = presenceOf(f);
          return (
            <Row key={f.friendship_id} name={f.username} dot={p}>
              <span className="font-mono text-[10px] text-muted">{PRESENCE_LABEL[p] ?? p}</span>
              <button
                onClick={() => setChallengeFor(f)}
                disabled={p === 'offline'}
                className="rounded-xs border border-gold/50 px-3 py-1 text-xs text-gold hover:bg-gold/10 disabled:opacity-30"
              >
                Challenge
              </button>
              <button
                onClick={() => unfriend(f)}
                className="rounded-xs border border-walnut-line px-2 py-1 text-xs text-muted hover:text-cream"
              >
                Remove
              </button>
              <button
                onClick={() => block(f)}
                className="rounded-xs border border-wrong/40 px-2 py-1 text-xs text-wrong/80 hover:bg-wrong/10"
              >
                Block
              </button>
            </Row>
          );
        })}
      </Section>

      {view.outgoing.length > 0 && (
        <Section title="Pending (sent)">
          {view.outgoing.map((f) => (
            <Row key={f.friendship_id} name={f.username} dot={presenceOf(f)}>
              <span className="font-mono text-[10px] text-muted">awaiting reply</span>
            </Row>
          ))}
        </Section>
      )}

      {challengeFor && (
        <ChallengeModal friend={challengeFor} onClose={() => setChallengeFor(null)} />
      )}
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="mb-6">
      <h2 className="mb-2 font-mono text-[11px] uppercase tracking-widest text-muted">{title}</h2>
      <div className="space-y-1">{children}</div>
    </section>
  );
}

function Row({
  name,
  dot,
  children,
}: {
  name: string;
  dot: string;
  children: React.ReactNode;
}) {
  return (
    <div className="flex items-center gap-3 rounded-xs border border-walnut-line bg-walnut-800 px-3 py-2">
      <span className={`h-2 w-2 rounded-full ${DOT[dot] ?? DOT.offline}`} />
      <span className="flex-1 text-sm">{name}</span>
      {children}
    </div>
  );
}

const TCS = [
  { label: '3+2', base: 3, inc: 2 },
  { label: '5+0', base: 5, inc: 0 },
  { label: '10+5', base: 10, inc: 5 },
];

function ChallengeModal({ friend, onClose }: { friend: FriendSummary; onClose: () => void }) {
  const [tc, setTc] = useState(1);
  const [rated, setRated] = useState(false);
  return (
    <div className="fixed inset-0 z-40 flex items-center justify-center bg-black/60" onClick={onClose}>
      <div
        className="w-full max-w-sm rounded-xs bg-parchment p-6 text-parchment-ink shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <h3 className="font-display text-xl font-bold">Challenge {friend.username}</h3>
        <div className="mt-4 flex gap-2">
          {TCS.map((t, i) => (
            <button
              key={t.label}
              onClick={() => setTc(i)}
              className={`rounded-xs border px-3 py-2 font-mono text-sm ${
                i === tc ? 'border-[#8c5f22] bg-gold/20' : 'border-[#c9b78d]'
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>
        <label className="mt-4 flex items-center gap-2 text-sm">
          <input type="checkbox" checked={rated} onChange={(e) => setRated(e.target.checked)} />
          Rated
        </label>
        <div className="mt-5 flex gap-2">
          <button
            onClick={() => {
              sendChallenge(
                friend.user_id,
                { base_min: TCS[tc].base, inc_sec: TCS[tc].inc },
                rated,
              );
              onClose();
            }}
            className="rounded-xs bg-gold px-4 py-2 text-sm font-bold text-walnut-950"
          >
            Send challenge
          </button>
          <button onClick={onClose} className="rounded-xs border border-[#c9b78d] px-4 py-2 text-sm">
            Cancel
          </button>
        </div>
      </div>
    </div>
  );
}
