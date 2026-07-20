import { useEffect, useMemo, useState } from 'react';
import { Navigate } from 'react-router-dom';
import Board from '../components/Board';
import {
  api,
  ApiError,
  type AdminItem,
  type AdminItemFull,
  type AdminStage,
  type ValidationResult,
} from '../lib/api';
import { applyMove, parseFEN, START_FEN, type Pos } from '../lib/chess';
import { useAuth } from '../lib/auth';

export default function AdminPage() {
  const { user } = useAuth();
  const [stages, setStages] = useState<AdminStage[]>([]);
  const [stageId, setStageId] = useState<number | null>(null);
  const [items, setItems] = useState<AdminItem[]>([]);
  const [editingId, setEditingId] = useState<number | null>(null);

  useEffect(() => {
    api.get<AdminStage[]>('/api/v1/admin/stages').then((s) => {
      setStages(s);
      if (s.length && stageId === null) setStageId(s[0].id);
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (stageId === null) return;
    api.get<AdminItem[]>(`/api/v1/admin/items?stage_id=${stageId}`).then(setItems);
  }, [stageId]);

  const selectStage = (id: number) => {
    setEditingId(null);
    setStageId(id);
  };

  if (user && user.role !== 'ADMIN') return <Navigate to="/learn" replace />;

  const refreshItems = () => {
    if (stageId !== null)
      api.get<AdminItem[]>(`/api/v1/admin/items?stage_id=${stageId}`).then(setItems);
    api.get<AdminStage[]>('/api/v1/admin/stages').then(setStages);
  };

  return (
    <div>
      <h1 className="font-display mb-1 text-3xl font-bold">Content Studio</h1>
      <p className="mb-6 font-display italic text-muted">
        Author, validate and publish curriculum. Nothing invalid reaches learners.
      </p>

      <div className="grid gap-6 lg:grid-cols-[200px_240px_1fr]">
        <div>
          <div className="mb-2 font-mono text-[10px] uppercase tracking-widest text-muted">
            Stages
          </div>
          <ul className="space-y-1">
            {stages.map((s) => (
              <li key={s.id}>
                <button
                  onClick={() => selectStage(s.id)}
                  className={`w-full rounded-xs px-3 py-2 text-left text-sm ${
                    s.id === stageId ? 'bg-gold/15 text-gold' : 'text-cream hover:bg-walnut-800'
                  }`}
                >
                  {s.title}
                  <span className="ml-1 font-mono text-[10px] text-muted">{s.item_count}</span>
                  {!s.published && <span className="ml-1 text-[10px] text-wrong">draft</span>}
                </button>
              </li>
            ))}
          </ul>
        </div>

        <div>
          <div className="mb-2 flex items-center justify-between">
            <span className="font-mono text-[10px] uppercase tracking-widest text-muted">
              Items
            </span>
            {stageId !== null && (
              <NewItemButton stageId={stageId} onCreated={refreshItems} setEditingId={setEditingId} />
            )}
          </div>
          <ul className="space-y-1">
            {items.map((it) => (
              <li key={it.id}>
                <button
                  onClick={() => setEditingId(it.id)}
                  className={`flex w-full items-center gap-2 rounded-xs px-3 py-2 text-left text-sm ${
                    it.id === editingId ? 'bg-gold/15 text-gold' : 'text-cream hover:bg-walnut-800'
                  }`}
                >
                  <span className="font-mono text-[10px] text-muted">
                    {it.kind === 'LESSON' ? '§' : it.kind === 'BOSS' ? '👑' : '⚔'}
                  </span>
                  <span className="flex-1 truncate">{it.title}</span>
                  <span
                    className={`font-mono text-[9px] uppercase ${
                      it.published ? 'text-correct' : 'text-wrong'
                    }`}
                  >
                    {it.published ? 'live' : 'draft'}
                  </span>
                </button>
              </li>
            ))}
          </ul>
        </div>

        <div>
          {editingId === null ? (
            <p className="font-display italic text-muted">Select an item to edit.</p>
          ) : (
            <ItemEditor key={editingId} itemId={editingId} onChanged={refreshItems} />
          )}
        </div>
      </div>
    </div>
  );
}

function NewItemButton({
  stageId,
  onCreated,
  setEditingId,
}: {
  stageId: number;
  onCreated: () => void;
  setEditingId: (id: number) => void;
}) {
  const create = async () => {
    const slug = `new-item-${Date.now().toString(36)}`;
    try {
      const item = await api.post<AdminItemFull>('/api/v1/admin/items', {
        stage_id: stageId,
        slug,
        kind: 'DRILL',
        title: 'Untitled drill',
        order_idx: 50,
        content_json: {
          id: slug,
          kind: 'puzzle',
          orientation: 'white',
          fen: START_FEN,
          intro: '',
          outro: '',
          hint: '',
          goal: '',
          line: [],
        },
      });
      onCreated();
      setEditingId(item.id);
    } catch (e) {
      alert(e instanceof ApiError ? e.message : 'Create failed');
    }
  };
  return (
    <button onClick={create} className="font-mono text-[10px] uppercase text-gold hover:underline">
      + new
    </button>
  );
}

function ItemEditor({ itemId, onChanged }: { itemId: number; onChanged: () => void }) {
  const [item, setItem] = useState<AdminItemFull | null>(null);
  const [title, setTitle] = useState('');
  const [sub, setSub] = useState('');
  const [json, setJson] = useState('');
  const [jsonError, setJsonError] = useState<string | null>(null);
  const [validation, setValidation] = useState<ValidationResult | null>(null);
  const [msg, setMsg] = useState<string | null>(null);

  useEffect(() => {
    api.get<AdminItemFull>(`/api/v1/admin/items/${itemId}`).then((it) => {
      setItem(it);
      setTitle(it.title);
      setSub(it.sub);
      setJson(JSON.stringify(it.kind === 'BOSS' ? it.boss_config : it.content_json, null, 2));
    });
  }, [itemId]);

  const parsed = useMemo(() => {
    try {
      return JSON.parse(json) as Record<string, unknown>;
    } catch {
      return null;
    }
  }, [json]);

  if (!item) return <p className="font-display italic text-muted">Loading…</p>;
  const isBoss = item.kind === 'BOSS';

  const save = async () => {
    if (parsed === null) {
      setJsonError('Invalid JSON — fix before saving.');
      return;
    }
    setJsonError(null);
    const body: Record<string, unknown> = { title, sub };
    if (isBoss) body.boss_config = parsed;
    else body.content_json = parsed;
    await api.patch(`/api/v1/admin/items/${itemId}`, body);
    setMsg('Saved.');
    onChanged();
    setTimeout(() => setMsg(null), 2000);
  };

  const validate = async () => {
    await save();
    const v = await api.post<ValidationResult>(`/api/v1/admin/items/${itemId}/validate`);
    setValidation(v);
  };

  const publish = async () => {
    await save();
    try {
      await api.post(`/api/v1/admin/items/${itemId}/publish`);
      setMsg('Published ✓');
      setValidation({ valid: true, errors: [] });
      onChanged();
      const fresh = await api.get<AdminItemFull>(`/api/v1/admin/items/${itemId}`);
      setItem(fresh);
    } catch (e) {
      if (e instanceof ApiError && e.details) {
        setValidation({ valid: false, errors: e.details as string[] });
      }
      setMsg('Publish blocked — content invalid.');
    }
  };

  const unpublish = async () => {
    const fresh = await api.post<AdminItemFull>(`/api/v1/admin/items/${itemId}/unpublish`);
    setItem(fresh);
    onChanged();
  };

  return (
    <div className="grid gap-4 xl:grid-cols-[1fr_320px]">
      <div>
        <div className="mb-3 flex items-center gap-2">
          <span className="font-mono text-[10px] uppercase text-muted">{item.kind}</span>
          <span className="font-mono text-[10px] text-muted">v{item.version}</span>
          <span
            className={`font-mono text-[10px] uppercase ${
              item.published ? 'text-correct' : 'text-wrong'
            }`}
          >
            {item.published ? 'live' : 'draft'}
          </span>
        </div>
        <input
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="Title"
          className="mb-2 w-full rounded-xs border border-walnut-line bg-walnut-800 px-3 py-2 text-sm outline-none focus:border-gold"
        />
        <input
          value={sub}
          onChange={(e) => setSub(e.target.value)}
          placeholder="Subtitle"
          className="mb-3 w-full rounded-xs border border-walnut-line bg-walnut-800 px-3 py-2 text-sm outline-none focus:border-gold"
        />
        <div className="mb-1 font-mono text-[10px] uppercase tracking-widest text-muted">
          {isBoss ? 'boss_config' : 'content_json'}
        </div>
        <textarea
          value={json}
          onChange={(e) => setJson(e.target.value)}
          spellCheck={false}
          className={`h-80 w-full rounded-xs border bg-walnut-950 px-3 py-2 font-mono text-xs outline-none ${
            parsed === null ? 'border-wrong' : 'border-walnut-line focus:border-gold'
          }`}
        />
        {parsed === null && <p className="mt-1 text-xs text-wrong">Invalid JSON</p>}
        {jsonError && <p className="mt-1 text-xs text-wrong">{jsonError}</p>}

        <div className="mt-3 flex flex-wrap gap-2">
          <button onClick={save} className="rounded-xs border border-walnut-line px-4 py-2 text-sm hover:border-gold">
            Save
          </button>
          <button onClick={validate} className="rounded-xs border border-walnut-line px-4 py-2 text-sm hover:border-gold">
            Validate
          </button>
          {item.published ? (
            <button onClick={unpublish} className="rounded-xs border border-wrong/50 px-4 py-2 text-sm text-wrong hover:bg-wrong/10">
              Unpublish
            </button>
          ) : (
            <button onClick={publish} className="rounded-xs bg-gold px-4 py-2 text-sm font-bold text-walnut-950 hover:bg-[#e5b458]">
              Validate &amp; Publish
            </button>
          )}
          {msg && <span className="self-center text-sm text-correct">{msg}</span>}
        </div>

        {validation && (
          <div
            className={`mt-3 rounded-xs border p-3 text-sm ${
              validation.valid
                ? 'border-correct/50 bg-correct/10 text-correct'
                : 'border-wrong/50 bg-wrong/10 text-[#eba38f]'
            }`}
          >
            {validation.valid ? (
              '✓ Content is legal — every position and move checks out.'
            ) : (
              <ul className="list-inside list-disc font-mono text-xs">
                {validation.errors.map((e, i) => (
                  <li key={i}>{e}</li>
                ))}
              </ul>
            )}
          </div>
        )}
      </div>

      {!isBoss && parsed && <PreviewBoard content={parsed} />}
    </div>
  );
}

function PreviewBoard({ content }: { content: Record<string, unknown> }) {
  const [idx, setIdx] = useState(-1);
  const startFen = (content.fen as string) || START_FEN;

  const positions = useMemo(() => {
    const steps = (content.steps ?? content.line ?? []) as { move?: string; fen?: string }[];
    const list: Pos[] = [];
    let pos: Pos;
    try {
      pos = parseFEN(startFen);
    } catch {
      return [];
    }
    for (const step of steps) {
      try {
        if (step.fen) pos = parseFEN(step.fen);
        if (step.move) pos = applyMove(pos, step.move);
      } catch {
        break;
      }
      list.push(pos);
    }
    return list;
  }, [startFen, content]);

  let pos: Pos;
  try {
    pos = idx < 0 || !positions[idx] ? parseFEN(startFen) : positions[idx];
  } catch {
    return <p className="text-xs text-wrong">Unparseable FEN — fix the JSON.</p>;
  }

  return (
    <div>
      <div className="mb-2 font-mono text-[10px] uppercase tracking-widest text-muted">Preview</div>
      <Board pos={pos} orientation={content.orientation === 'black' ? 'black' : 'white'} />
      <div className="mt-2 flex items-center gap-2">
        <button
          onClick={() => setIdx((i) => Math.max(-1, i - 1))}
          className="rounded-xs border border-walnut-line px-3 py-1 text-xs"
        >
          ◂
        </button>
        <span className="font-mono text-xs text-muted">
          {idx + 1}/{positions.length}
        </span>
        <button
          onClick={() => setIdx((i) => Math.min(positions.length - 1, i + 1))}
          className="rounded-xs border border-walnut-line px-3 py-1 text-xs"
        >
          ▸
        </button>
      </div>
    </div>
  );
}
