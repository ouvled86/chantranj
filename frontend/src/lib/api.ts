/** Tiny API client: cookie auth, CSRF header, one silent refresh-retry on 401. */

export class ApiError extends Error {
  constructor(
    public status: number,
    public code: string,
    message: string,
    public details?: unknown,
  ) {
    super(message);
  }
}

function getCookie(name: string): string | null {
  const match = document.cookie.match(new RegExp(`(?:^|; )${name}=([^;]*)`));
  return match ? decodeURIComponent(match[1]) : null;
}

async function raw(method: string, path: string, body?: unknown): Promise<Response> {
  const headers: Record<string, string> = {};
  if (body !== undefined) headers['Content-Type'] = 'application/json';
  const csrf = getCookie('csrf_token');
  if (csrf) headers['X-CSRF-Token'] = csrf;
  return fetch(path, {
    method,
    headers,
    credentials: 'include',
    body: body === undefined ? undefined : JSON.stringify(body),
  });
}

async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
  let res = await raw(method, path, body);
  if (res.status === 401 && !path.startsWith('/api/v1/auth/')) {
    const refreshed = await raw('POST', '/api/v1/auth/refresh');
    if (refreshed.ok) res = await raw(method, path, body);
  }
  if (!res.ok) {
    let code = 'unknown';
    let message = res.statusText;
    let details: unknown;
    try {
      const data = await res.json();
      code = data?.error?.code ?? code;
      message = data?.error?.message ?? message;
      details = data?.error?.details;
    } catch {
      /* non-JSON error body */
    }
    throw new ApiError(res.status, code, message, details);
  }
  return (await res.json()) as T;
}

export const api = {
  get: <T>(path: string) => request<T>('GET', path),
  post: <T>(path: string, body?: unknown) => request<T>('POST', path, body),
  patch: <T>(path: string, body?: unknown) => request<T>('PATCH', path, body),
};

export interface User {
  id: number;
  email: string;
  username: string;
  avatar_url: string | null;
  role: 'USER' | 'ADMIN';
  created_at: string;
}

export interface ItemSummary {
  slug: string;
  kind: 'LESSON' | 'DRILL' | 'BOSS';
  title: string;
  sub: string;
  order_idx: number;
  status: 'DONE' | 'AVAILABLE' | 'LOCKED';
}

export interface StageOut {
  slug: string;
  title: string;
  intro: string;
  order_idx: number;
  items: ItemSummary[];
}

export interface BossConfig {
  bot_level: number;
  player_color: 'white' | 'black';
  objective: 'win' | 'checkmate' | 'draw' | 'convert';
  move_limit: number | null;
  start_fen: string | null;
  time_control: { base_min: number | null; inc_sec: number };
}

export interface ItemDetail {
  slug: string;
  kind: 'LESSON' | 'DRILL' | 'BOSS';
  title: string;
  sub: string;
  status: string;
  content: ItemContent;
  boss: BossConfig | null;
}

export interface ContentStep {
  move?: string;
  fen?: string;
  san?: string;
  note?: string;
  arrows?: [string, string][];
  marks?: string[];
  isBad?: boolean;
}

export interface LineEntry {
  move: string;
  san: string;
  note?: string;
}

export interface ItemContent {
  id: string;
  kind: 'lesson' | 'puzzle';
  title: string;
  sub: string;
  orientation: 'white' | 'black';
  fen: string | null;
  intro: string;
  outro: string;
  goal: string | null;
  hint: string | null;
  steps: ContentStep[] | null;
  line: LineEntry[] | null;
}

// ---- admin CMS ----
export interface AdminStage {
  id: number;
  slug: string;
  title: string;
  intro: string;
  order_idx: number;
  published: boolean;
  item_count: number;
}

export interface AdminItem {
  id: number;
  stage_id: number;
  slug: string;
  kind: 'LESSON' | 'DRILL' | 'BOSS';
  title: string;
  sub: string;
  order_idx: number;
  published: boolean;
  version: number;
}

export interface AdminItemFull extends AdminItem {
  content_json: Record<string, unknown>;
  boss_config: Record<string, unknown> | null;
}

export interface ValidationResult {
  valid: boolean;
  errors: string[];
}

export const del = (path: string) => request<void>('DELETE', path);

// ---- social ----
export interface FriendSummary {
  friendship_id: number;
  user_id: number;
  username: string;
  avatar_url: string | null;
  presence: string;
}

export interface FriendsView {
  friends: FriendSummary[];
  incoming: FriendSummary[];
  outgoing: FriendSummary[];
}

export interface UserSearchResult {
  username: string;
  avatar_url: string | null;
  relation: string;
}

export interface LeaderRow {
  rank: number;
  username: string;
  value: number;
  games: number;
  is_me: boolean;
}

// ---- gamification ----
export interface UnlockedAchievement {
  slug: string;
  title: string;
  icon: string;
  xp: number;
}

export interface RewardSummary {
  xp_gained: number;
  total_xp: number;
  level: number;
  leveled_up: boolean;
  streak: number;
  unlocked: UnlockedAchievement[];
}

export interface AchievementView {
  slug: string;
  title: string;
  description: string;
  icon: string;
  category: string;
  xp: number;
  unlocked: boolean;
  unlocked_at: string | null;
}
