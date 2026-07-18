/* app.js — UI: curriculum nav, lesson stepper, interactive drills, progress. */

const GLYPHS = { k: '♚', q: '♛', r: '♜', b: '♝', n: '♞', p: '♟' };
const LS_KEY = 'study-progress-v1';
const LS_LAST = 'study-last-item';

const els = {
  nav: document.getElementById('nav'),
  board: document.getElementById('board'),
  overlay: document.getElementById('overlay'),
  noteLabel: document.getElementById('note-label'),
  noteBody: document.getElementById('note-body'),
  controls: document.getElementById('controls'),
  movelist: document.getElementById('movelist'),
  movelistWrap: document.getElementById('movelist-wrap'),
  headEyebrow: document.getElementById('head-eyebrow'),
  headTitle: document.getElementById('head-title'),
  headSub: document.getElementById('head-sub'),
  turnChip: document.getElementById('turn-chip'),
  caption: document.getElementById('board-caption'),
  feedback: document.getElementById('feedback'),
  itemNav: document.getElementById('item-nav'),
  progressSummary: document.getElementById('progress-summary'),
  sidebar: document.getElementById('sidebar'),
};

const ALL_ITEMS = [];
CURRICULUM.forEach(mod => mod.items.forEach(it => { it.module = mod; ALL_ITEMS.push(it); }));

let progress = new Set(JSON.parse(localStorage.getItem(LS_KEY) || '[]'));
function saveProgress() { localStorage.setItem(LS_KEY, JSON.stringify([...progress])); }

const state = {
  item: null,
  flipped: false,
  // lesson
  stepIdx: -1,       // -1 = intro (start position)
  positions: [],     // positions[i] = position after steps[i]
  // puzzle
  pos: null,
  lineIdx: 0,
  selected: null,    // board index
  solved: false,
  hintUsed: 0,
};

/* ---------- curriculum nav ---------- */

function renderNav() {
  els.nav.innerHTML = '';
  CURRICULUM.forEach((mod, mi) => {
    const group = document.createElement('div');
    group.className = 'nav-group';
    const done = mod.items.filter(i => progress.has(i.id)).length;
    group.innerHTML = `
      <div class="nav-group-head">
        <span class="nav-group-num">${['I','II','III','IV'][mi]}</span>
        <div>
          <div class="nav-group-title">${mod.title}</div>
          <div class="nav-group-blurb">${mod.blurb}</div>
        </div>
        <span class="nav-group-count">${done}/${mod.items.length}</span>
      </div>`;
    mod.items.forEach(it => {
      const btn = document.createElement('button');
      btn.className = 'nav-item' +
        (state.item && state.item.id === it.id ? ' active' : '') +
        (progress.has(it.id) ? ' done' : '');
      btn.innerHTML = `
        <span class="nav-item-kind ${it.kind}">${it.kind === 'puzzle' ? '⚔' : '§'}</span>
        <span class="nav-item-title">${it.title}</span>
        <span class="nav-item-check">✓</span>`;
      btn.addEventListener('click', () => { loadItem(it.id); closeSidebarMobile(); });
      group.appendChild(btn);
    });
    els.nav.appendChild(group);
  });
  const total = ALL_ITEMS.length, done = ALL_ITEMS.filter(i => progress.has(i.id)).length;
  els.progressSummary.innerHTML =
    `<div class="prog-bar"><div class="prog-fill" style="width:${Math.round(done / total * 100)}%"></div></div>
     <div class="prog-text">${done} of ${total} complete</div>`;
}

/* ---------- board rendering ---------- */

function displayIndex(i) { return state.flipped ? 63 - i : i; }

function buildBoard() {
  els.board.innerHTML = '';
  for (let d = 0; d < 64; d++) {
    const i = state.flipped ? 63 - d : d;
    const f = i % 8, r = Math.floor(i / 8);
    const sq = document.createElement('div');
    sq.className = 'sq ' + ((f + r) % 2 === 0 ? 'light' : 'dark');
    sq.dataset.idx = i;
    const df = d % 8, dr = Math.floor(d / 8);
    if (dr === 7) sq.innerHTML += `<span class="coord coord-file">${FILES[state.flipped ? 7 - df : df]}</span>`;
    if (df === 0) sq.innerHTML += `<span class="coord coord-rank">${state.flipped ? dr + 1 : 8 - dr}</span>`;
    sq.addEventListener('click', () => onSquareClick(i));
    els.board.appendChild(sq);
  }
}

function renderPosition(pos, opts = {}) {
  const marks = new Set((opts.marks || []).map(sqToIdx));
  const dots = new Set(opts.dots || []);
  const lastMove = opts.lastMove || null;
  for (const sqEl of els.board.children) {
    const i = +sqEl.dataset.idx;
    sqEl.querySelectorAll('.piece,.dot').forEach(n => n.remove());
    sqEl.classList.remove('marked', 'selected', 'last-from', 'last-to');
    const p = pos.board[i];
    if (p) {
      const span = document.createElement('span');
      span.className = 'piece ' + (isWhitePiece(p) ? 'wp' : 'bp');
      span.textContent = GLYPHS[p.toLowerCase()];
      sqEl.appendChild(span);
    }
    if (dots.has(i)) {
      const dot = document.createElement('span');
      dot.className = 'dot' + (p ? ' dot-capture' : '');
      sqEl.appendChild(dot);
    }
    if (marks.has(i)) sqEl.classList.add('marked');
    if (state.selected === i) sqEl.classList.add('selected');
    if (lastMove) {
      if (i === sqToIdx(lastMove.slice(0, 2))) sqEl.classList.add('last-from');
      if (i === sqToIdx(lastMove.slice(2, 4))) sqEl.classList.add('last-to');
    }
  }
  drawArrows(opts.arrows || []);
}

function drawArrows(arrows) {
  const svg = els.overlay;
  svg.innerHTML = `<defs>
    <marker id="arrowhead" markerWidth="3.2" markerHeight="3.2" refX="2.05" refY="1.6" orient="auto">
      <path d="M0,0 L3.2,1.6 L0,3.2 z" fill="var(--arrow)"/>
    </marker></defs>`;
  arrows.forEach(([from, to]) => {
    const a = center(sqToIdx(from)), b = center(sqToIdx(to));
    const dx = b.x - a.x, dy = b.y - a.y, len = Math.hypot(dx, dy);
    const trim = 34; // pull arrow tip short of square center edge
    const bx = b.x - dx / len * trim, by = b.y - dy / len * trim;
    const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
    line.setAttribute('x1', a.x); line.setAttribute('y1', a.y);
    line.setAttribute('x2', bx); line.setAttribute('y2', by);
    line.setAttribute('class', 'arrow-line');
    line.setAttribute('marker-end', 'url(#arrowhead)');
    svg.appendChild(line);
  });
}

function center(i) {
  const d = state.flipped ? 63 - i : i;
  return { x: (d % 8) * 100 + 50, y: Math.floor(d / 8) * 100 + 50 };
}

/* ---------- item loading ---------- */

function loadItem(id) {
  const item = ALL_ITEMS.find(i => i.id === id) || ALL_ITEMS[0];
  state.item = item;
  state.flipped = item.orientation === 'black';
  state.selected = null;
  state.solved = progress.has(item.id);
  state.hintUsed = 0;
  localStorage.setItem(LS_LAST, item.id);
  buildBoard();

  els.headEyebrow.textContent = `${item.module.title} · ${item.kind === 'puzzle' ? 'Drill' : 'Lesson'}`;
  els.headTitle.textContent = item.title;
  els.headSub.textContent = item.sub || '';
  hideFeedback();

  if (item.kind === 'lesson') {
    // Precompute every position.
    const startFen = item.fen || item.start || START_FEN;
    let pos = parseFEN(startFen);
    state.positions = [];
    for (const step of item.steps) {
      if (step.fen) pos = parseFEN(step.fen);
      if (step.move) pos = applyMove(pos, step.move);
      state.positions.push(pos);
    }
    state.startPos = parseFEN(startFen);
    state.stepIdx = -1;
    renderLesson();
  } else {
    state.pos = parseFEN(item.fen);
    state.lineIdx = 0;
    renderPuzzle({ intro: true });
  }
  renderNav();
  renderItemNav();
  document.getElementById('main').scrollTop = 0;
}

/* ---------- lesson mode ---------- */

function renderLesson() {
  const item = state.item;
  const i = state.stepIdx;
  const step = i >= 0 ? item.steps[i] : null;
  const pos = i >= 0 ? state.positions[i] : state.startPos;
  const atEnd = i === item.steps.length - 1;

  renderPosition(pos, {
    marks: step ? step.marks : [],
    arrows: step ? step.arrows : [],
    lastMove: step && step.move ? step.move : null,
  });

  els.turnChip.textContent = '';
  els.turnChip.classList.remove('white-turn', 'black-turn');
  els.caption.textContent = state.flipped ? 'Playing as Black — board flipped' : '';

  if (i < 0) {
    els.noteLabel.textContent = 'Introduction';
    els.noteBody.innerHTML = `<p>${item.intro}</p><p class="note-cue">Use <b>Next ▸</b> (or the → key) to step through.</p>`;
  } else if (atEnd && item.outro) {
    els.noteLabel.textContent = step.san || `Step ${i + 1}`;
    els.noteBody.innerHTML = `${step.note ? `<p>${step.note}</p>` : ''}<div class="outro"><div class="outro-label">Takeaway</div><p>${item.outro}</p></div>`;
  } else {
    els.noteLabel.textContent = step.san || `Step ${i + 1}`;
    els.noteBody.innerHTML = step.note ? `<p>${step.note}</p>` : `<p class="quiet">…</p>`;
  }

  // controls
  els.controls.innerHTML = '';
  const restart = btn('↺', 'Restart', () => { state.stepIdx = -1; renderLesson(); }, 'icon');
  const prev = btn('◂ Back', null, () => { if (state.stepIdx > -1) { state.stepIdx--; renderLesson(); } });
  const next = btn('Next ▸', null, () => {
    if (state.stepIdx < item.steps.length - 1) { state.stepIdx++; renderLesson(); }
  }, 'primary');
  prev.disabled = i <= -1;
  next.disabled = atEnd;
  els.controls.append(restart, prev, next);
  if (atEnd) markComplete();

  renderMovelist(item.steps, i, (idx) => { state.stepIdx = idx; renderLesson(); });
}

/* ---------- puzzle mode ---------- */

function puzzlePos() { return state.pos; }
function userToPlay() { return state.lineIdx % 2 === 0 && state.lineIdx < state.item.line.length; }

function renderPuzzle(opts = {}) {
  const item = state.item;
  const finished = state.lineIdx >= item.line.length;
  const lastPlayed = state.lineIdx > 0 ? item.line[state.lineIdx - 1] : null;

  const dots = state.selected != null ? pseudoMoves(state.pos, state.selected) : [];
  renderPosition(state.pos, {
    dots,
    lastMove: lastPlayed ? lastPlayed.move : null,
    arrows: opts.arrows || [],
  });

  const turn = state.pos.turn;
  els.turnChip.textContent = finished ? 'Solved' : (turn === 'w' ? 'White to move' : 'Black to move');
  els.turnChip.className = 'turn-chip ' + (finished ? 'solved-chip' : (turn === 'w' ? 'white-turn' : 'black-turn'));
  els.caption.textContent = item.goal ? `Goal: ${item.goal}` : '';

  if (finished) {
    els.noteLabel.textContent = 'Solved ✦';
    els.noteBody.innerHTML =
      `${lastPlayed && lastPlayed.note ? `<p>${lastPlayed.note}</p>` : ''}
       <div class="outro"><div class="outro-label">Takeaway</div><p>${item.outro}</p></div>`;
    markComplete();
  } else if (opts.intro) {
    els.noteLabel.textContent = 'Your move';
    els.noteBody.innerHTML = `<p>${item.intro}</p><p class="note-cue">Click a piece, then its destination.</p>`;
  } else if (lastPlayed) {
    els.noteLabel.textContent = lastPlayed.san;
    els.noteBody.innerHTML = lastPlayed.note ? `<p>${lastPlayed.note}</p>` : `<p class="quiet">Keep going — find the next move.</p>`;
  }

  els.controls.innerHTML = '';
  const restart = btn('↺', 'Restart drill', resetPuzzle, 'icon');
  els.controls.appendChild(restart);
  if (!finished) {
    const hint = btn(state.hintUsed === 0 ? 'Hint' : 'Show the move', null, useHint);
    els.controls.appendChild(hint);
  }
  renderMovelist(item.line.slice(0, state.lineIdx), state.lineIdx - 1, null);
}

function resetPuzzle() {
  state.pos = parseFEN(state.item.fen);
  state.lineIdx = 0;
  state.selected = null;
  state.hintUsed = 0;
  hideFeedback();
  renderPuzzle({ intro: true });
}

function useHint() {
  const expected = state.item.line[state.lineIdx];
  if (state.hintUsed === 0) {
    state.hintUsed = 1;
    showFeedback('hint', state.item.hint || 'Look for the most forcing move — checks first.');
    renderPuzzle({});
  } else {
    showFeedback('hint', `The move is highlighted on the board.`);
    renderPuzzle({ arrows: [[expected.move.slice(0, 2), expected.move.slice(2, 4)]] });
  }
}

function onSquareClick(i) {
  const item = state.item;
  if (!item || item.kind !== 'puzzle' || !userToPlay()) return;
  const p = state.pos.board[i];
  const whiteToMove = state.pos.turn === 'w';

  if (state.selected == null) {
    if (p && isWhitePiece(p) === whiteToMove) { state.selected = i; renderPuzzle({}); }
    return;
  }
  if (i === state.selected) { state.selected = null; renderPuzzle({}); return; }
  if (p && isWhitePiece(p) === whiteToMove) { state.selected = i; renderPuzzle({}); return; }

  const attempt = idxToSq(state.selected) + idxToSq(i);
  const expected = item.line[state.lineIdx];
  state.selected = null;

  if (attempt === expected.move.slice(0, 4)) {
    hideFeedback();
    state.pos = applyMove(state.pos, expected.move);
    state.lineIdx++;
    renderPuzzle({});
    // auto-play the reply
    if (!userToPlay() && state.lineIdx < item.line.length) {
      setTimeout(() => {
        const reply = item.line[state.lineIdx];
        state.pos = applyMove(state.pos, reply.move);
        state.lineIdx++;
        renderPuzzle({});
      }, 650);
    }
  } else {
    showFeedback('wrong', 'Not this one. Run the scan again: checks, captures, threats.');
    els.board.classList.remove('shake');
    void els.board.offsetWidth;
    els.board.classList.add('shake');
    renderPuzzle({});
  }
}

/* ---------- shared bits ---------- */

function renderMovelist(steps, currentIdx, onJump) {
  els.movelist.innerHTML = '';
  const shown = steps.filter(s => s.san);
  els.movelistWrap.style.display = shown.length ? '' : 'none';
  steps.forEach((s, idx) => {
    if (!s.san) return;
    const chip = document.createElement(onJump ? 'button' : 'span');
    chip.className = 'mv' + (idx === currentIdx ? ' current' : '') + (s.isBad ? ' bad' : '') + (s.fen && !s.move ? ' meta' : '');
    chip.textContent = s.san;
    if (onJump) chip.addEventListener('click', () => onJump(idx));
    els.movelist.appendChild(chip);
  });
}

function renderItemNav() {
  const idx = ALL_ITEMS.indexOf(state.item);
  els.itemNav.innerHTML = '';
  if (idx > 0) {
    const b = btn('◂ ' + ALL_ITEMS[idx - 1].title, null, () => loadItem(ALL_ITEMS[idx - 1].id), 'nav-prev');
    els.itemNav.appendChild(b);
  }
  if (idx < ALL_ITEMS.length - 1) {
    const b = btn(ALL_ITEMS[idx + 1].title + ' ▸', null, () => loadItem(ALL_ITEMS[idx + 1].id), 'nav-next');
    els.itemNav.appendChild(b);
  }
}

function markComplete() {
  if (!progress.has(state.item.id)) {
    progress.add(state.item.id);
    saveProgress();
    renderNav();
  }
}

function btn(label, title, fn, cls = '') {
  const b = document.createElement('button');
  b.className = 'btn ' + cls;
  b.textContent = label;
  if (title) b.title = title;
  b.addEventListener('click', fn);
  return b;
}

function showFeedback(type, text) {
  els.feedback.className = 'feedback ' + type;
  els.feedback.textContent = text;
}
function hideFeedback() { els.feedback.className = 'feedback hidden'; els.feedback.textContent = ''; }

function closeSidebarMobile() { els.sidebar.classList.remove('open'); }

/* ---------- boot ---------- */

document.getElementById('sidebar-toggle').addEventListener('click', () => {
  els.sidebar.classList.toggle('open');
});
document.getElementById('reset-progress').addEventListener('click', () => {
  if (confirm('Clear all lesson progress?')) {
    progress = new Set();
    saveProgress();
    renderNav();
  }
});
document.addEventListener('keydown', (e) => {
  if (!state.item || state.item.kind !== 'lesson') return;
  if (e.key === 'ArrowRight' && state.stepIdx < state.item.steps.length - 1) { state.stepIdx++; renderLesson(); }
  if (e.key === 'ArrowLeft' && state.stepIdx > -1) { state.stepIdx--; renderLesson(); }
});

loadItem(localStorage.getItem(LS_LAST) || ALL_ITEMS[0].id);
