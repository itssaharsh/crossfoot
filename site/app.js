import { getJSON, LoadError, loadMessage, Store, progress } from './data.js';
import { Stage } from './stage.js';
import { Loupe } from './loupe.js';
import { Tape } from './tape.js';
import { renderCard, stageLabel, FailList } from './panel.js';

const $ = id => document.getElementById(id);
const q = new URLSearchParams(location.search);
const reduced = matchMedia('(prefers-reduced-motion: reduce)').matches;
const coarse = matchMedia('(pointer: coarse)').matches;
const FIRST_RUN = 'No run has been built into this page yet. Run crossfoot site build.';
const EMPTY = 'No disagreements in this county.';
const STATES = ['loading', 'error', 'empty', 'partial', 'first-run'];

// ?reset=1 opens the page as if for the first time: no state, cell or flat parameter is read, and the address is cleaned
const reset = q.get('reset') === '1';
if (reset) { q.delete('reset'); for (const k of ['state', 'cell', 'flat']) q.delete(k); history.replaceState(null, '', location.pathname + (q.toString() ? '?' + q : '')); }
const forced = !reset && STATES.includes(q.get('state')) ? q.get('state') : null;
if (q.get('record') === '1') document.body.classList.add('record');   // recording mode: see the .judge-only rule in styles.css

const stage = new Stage({
  viewport: $('viewport'), leanEl: $('lean'), pose: $('pose'), paper: $('paper'), sheet: $('sheet'), stack: $('stack'), root: $('stage'),
  loupeEl: $('loupe'), leader: $('leader'), leaderLine: $('leader-line'), controls: $('controls'),
  scan: $('scan'), bands: $('bands'), marks: $('marks'), notice: $('notice'), flatEl: $('flatblock'),
}, { reduced, coarse, onPick: i => select(i), onError: loadMessage, onFocusValue: i => peek(i) });
const loupe = new Loupe({ root: $('loupe'), view: $('lp-view'), note: $('lp-note') }, { onPick: i => select(i), reduced });
stage.setLoupe(loupe);
const tape = new Tape($('tape'), reduced, i => select(i));
const state = { store: null, list: null, sel: null, index: null, counties: {}, first: true };

// ---- the page's state: body[data-state] decides what shows (styles.css); the controls follow it
function setState(name) {
  document.body.dataset.state = name;
  const live = !['loading', 'error', 'first-run'].includes(name);
  for (const id of ['flat', 'prev', 'next']) $(id).disabled = !live;
  const sb = $('statebox');
  if (name === 'loading') sb.textContent = `Loading run… ${progress.n} ${progress.n === 1 ? 'file' : 'files'}`;
  else if (name === 'first-run') sb.textContent = FIRST_RUN;
  else sb.textContent = '';
  if (!live) $('pageno').replaceChildren();
}
progress.on = n => { if (document.body.dataset.state === 'loading') setState('loading'); };

function fail(file) {
  $('notice').textContent = loadMessage(file);
  $('notice').hidden = false;
  $('paper').setAttribute('aria-label', loadMessage(file));
  setState('error');
}

// ---- selection
async function select(i, { animate = true, entrance = false, settle = false } = {}) {
  const { store } = state;
  const v = store.values[i];
  if (!v) return;
  state.sel = i;
  const sums = store.sumsFor(v);
  renderCard($('card'), store, v);
  stage.setLabel(stageLabel(store, v, sums));
  state.list.follow(sums);
  tape.clear();
  if (v.p !== stage.page) await goPage(v.p, animate, v.p > stage.page ? 1 : -1, false);
  const done = await stage.select(i, sums, animate, { settle });
  if (done && state.sel === i) tape.print(store, sums, animate, entrance ? 260 : undefined);
  updatePager();
}

// the keyboard is on a value of the sheet: the loupe shows it too, and goes back to the selection when focus leaves
function peek(i) { if (state.store) loupe.peek(state.store, i); }

async function goPage(n, animate, dir, pick = true) {
  await stage.setPage(n, animate, dir);
  updatePager();
  if (pick) {
    const i = state.store.defaultOn(n);
    if (i !== null) await select(i, { animate });
  }
}

function updatePager() {
  const n = stage.page, total = state.store.pages.length;
  $('pageno').replaceChildren(Object.assign(document.createElement('span'), { className: 'pw', textContent: 'Page ' }), `${n} of ${total}`);
  $('prev').disabled = n <= 1; $('next').disabled = n >= total;
}

function setFlatLabel() { $('flat').textContent = stage.flat ? 'Tilt sheet' : 'Lay flat'; }

async function openCounty(key) {
  const entry = state.index.counties.find(c => c.key === key);
  let data = state.counties[key];
  if (!data) {
    try { data = state.counties[key] = await getJSON(entry.file); } catch (e) { fail(e.file || entry.file); return; }
  }
  const store = state.store = new Store(data);
  stage.setStore(store);
  stage.forcePartial = forced === 'partial';
  state.list = new FailList($('fails'), store, c => {
    const i = store.firstValue(c);
    if (i !== null) select(i);
  }, { none: forced === 'empty' });
  const none = !state.list.items.length;
  $('fails-h').textContent = none ? EMPTY : 'Sums that do not hold';
  $('fails').hidden = none;
  $('fails-sec').classList.toggle('none', none);
  let start = null;
  const want = q.get('cell');
  if (want && store.byId.has(want)) start = store.byId.get(want);
  if (start === null) start = store.defaultOn(1);
  if (start === null) { fail(entry.file); return; }
  const v = store.values[start];
  // the first load only: one short entrance (sheet settles, loupe rises, sums draw, tape prints), none under reduced motion
  const enter = state.first && !reduced;
  const settle = enter && !stage.flat;
  if (settle) stage.flat = true;
  setState(forced || 'ready');
  if (enter) $('loupe').classList.add('rise');
  await stage.setPage(v.p, false);
  stage.sel = start;
  stage.layout(true);
  updatePager();
  await select(start, { animate: enter, entrance: enter, settle });
  state.first = false;
  setFlatLabel();
  for (const b of document.querySelectorAll('#tabs button')) b.setAttribute('aria-pressed', String(b.dataset.key === key));
}

async function main() {
  stage.flat = q.get('flat') === '1' || reduced || innerWidth < 900;
  setFlatLabel();
  $('flat').onclick = () => { stage.setFlat(!stage.flat); setFlatLabel(); };
  $('prev').onclick = () => goPage(stage.page - 1, true, -1);
  $('next').onclick = () => goPage(stage.page + 1, true, 1);
  setState('loading');
  if (forced === 'loading') {                 // stays on the loading state, for looking at it; the count is real
    try { const ix = await getJSON('data/index.json'); await getJSON(ix.counties[0].file); } catch (e) { /* the count stays where it is */ }
    return;
  }
  if (forced === 'first-run') { setState('first-run'); return; }
  try { state.index = await getJSON('data/index.json'); }
  catch (e) {
    if (e instanceof LoadError && e.missing) setState('first-run');   // nothing built yet
    else fail(e.file || 'data/index.json');
    return;
  }
  const cs = state.index.counties;
  if (!cs || !cs.length) { setState('first-run'); return; }
  if (forced === 'error') { fail(cs[0].file); return; }
  if (cs.length > 1) {
    const nav = $('tabs');
    nav.hidden = false;
    cs.forEach(c => {
      const b = document.createElement('button');
      b.type = 'button'; b.textContent = c.name; b.dataset.key = c.key;
      b.onclick = () => openCounty(c.key);
      nav.append(b);
    });
  }
  await openCounty(cs[0].key);
}

// ---- shortcuts, matched on the key's position so a keyboard layout does not matter
addEventListener('keydown', e => {
  if (!e.altKey || !e.shiftKey || e.ctrlKey || e.metaKey) return;
  if (e.code === 'KeyR') {            // back to the opening state
    e.preventDefault();
    for (const k of ['state', 'cell', 'flat', 'reset']) q.delete(k);
    location.assign(location.pathname + (q.toString() ? '?' + q : ''));
  } else if (e.code === 'KeyP') {     // reserved for the replay: nothing to do yet, and no error
    e.preventDefault();
    document.dispatchEvent(new CustomEvent('crossfoot:replay'));
  }
});

main();
