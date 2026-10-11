import { getJSON, LoadError, loadMessage, Store, progress, fmt, NOT_CHECKED, cap } from './data.js';
import { Cards, emptyLine } from './cards.js';
import { Stage } from './stage.js';
import { Loupe } from './loupe.js';
import { Tape } from './tape.js';
import { renderFindingPanel, FindingList, Dialog, siblingOf, tagText, stageLabel, runSeconds } from './findings.js';
import { Replay } from './replay.js';
import { renderHeroText, renderHeroPic, renderSteps, renderRun, pickExample, startFinding } from './hero.js';

const $ = id => document.getElementById(id);
const q = new URLSearchParams(location.search);
const reduced = matchMedia('(prefers-reduced-motion: reduce)').matches;
const coarse = matchMedia('(pointer: coarse)').matches;
const FIRST_RUN = 'No run has been built into this page yet. Run crossfoot site build.';
const STATES = ['loading', 'error', 'empty', 'partial', 'first-run'];
const sorted = c => c.t.slice().sort((a, b) => a - b).join(',');
const scrollTo = el => el.scrollIntoView({ behavior: reduced ? 'auto' : 'smooth', block: 'start' });

// ?reset=1 opens the page as if for the first time: no state, cell or flat parameter is read, and the address is cleaned
const reset = q.get('reset') === '1';
if (reset) { q.delete('reset'); for (const k of ['state', 'cell', 'flat']) q.delete(k); history.replaceState(null, '', location.pathname + (q.toString() ? '?' + q : '')); }
const forced = !reset && STATES.includes(q.get('state')) ? q.get('state') : null;
if (q.get('record') === '1') document.body.classList.add('record');   // recording mode: larger type for a screen capture, nothing hidden

const state = { key: null, cards: null, replay: null, opening: null, store: null, flist: null, sel: null, finding: null, index: null,
                stores: new Map(), first: true, hero: null, openTok: 0, everyOpen: false, enter: false };

const stage = new Stage({
  viewport: $('viewport'), leanEl: $('lean'), pose: $('pose'), paper: $('paper'), sheet: $('sheet'), stack: $('stack'), root: $('stage'),
  loupeEl: $('loupe'), leader: $('leader'), leaderLine: $('leader-line'),
  scan: $('scan'), bands: $('bands'), marks: $('marks'), notice: $('snotice'), flatEl: $('flatblock'),
}, { reduced, coarse, onPick: i => pickRef(i), onError: loadMessage, onStep: d => step(d) });
const loupe = new Loupe({ root: $('loupe'), view: $('lp-view') }, { onPick: i => pickRef(i), reduced });
stage.setLoupe(loupe);
const dialog = new Dialog($('dlg'));

// the tape sits in a disclosure inside the panel; one tape and one disclosure serve every finding
const every = document.createElement('details');
every.className = 'every';
const tapeHost = document.createElement('div');
tapeHost.className = 'tapewrap';
const tapeEl = document.createElement('section');
tapeEl.className = 'tape';
tapeEl.setAttribute('aria-label', 'The arithmetic');
tapeHost.append(tapeEl);
const tape = new Tape(tapeEl, reduced);

// ---- the page's state: body[data-state] decides what shows (styles.css); the controls follow it
function setState(name) {
  document.body.dataset.state = name;
  const live = !['loading', 'error', 'first-run'].includes(name);
  for (const id of ['flat', 'prev', 'next']) $(id).disabled = !live;
  const sb = $('statebox');
  if (name === 'loading') sb.textContent = `Loading run… ${progress.n} ${progress.n === 1 ? 'file' : 'files'}`;
  else if (name === 'first-run') sb.textContent = FIRST_RUN;
  else sb.textContent = '';
}
progress.on = () => { if (document.body.dataset.state === 'loading') setState('loading'); };

function fail(file) {
  $('notice').textContent = loadMessage(file);
  $('notice').hidden = false;
  setState('error');
}
// one county that cannot be loaded: the rest of the page stays
function localError(file) {
  const x = $('xpanel');
  x.dataset.kind = 'error';
  $('xnotice').textContent = loadMessage(file);
  $('xnotice').hidden = false;
  $('county-msg').hidden = true;
}

const getStore = async entry => {
  if (state.stores.has(entry.key)) return state.stores.get(entry.key);
  const s = new Store(await getJSON(entry.file));
  state.stores.set(entry.key, s);
  return s;
};

// ---- selection: a finding of the county; the sheet turns to its page, the loupe shows the scan, the panel says what is wrong
const pickRef = i => { const f = state.store && state.store.itemByRef.get(i); if (f) selectFinding(f); };
const selectFinding = (f, o) => { state.enter = false; return f.ref !== undefined ? selectValue(f, o) : selectPlaceless(f, o); };

function afterLoupe() { if (loupe.toggled) { loupe.toggled = false; stage.layout(true); } }

function renderPanel(f) {
  const { store } = state;
  renderFindingPanel($('panel'), store, f, {
    onCrop: (x, b) => dialog.crop(store, x, b), onEvidence: (x, b) => dialog.evidenceFile(store, x, b),
    details: every, tapeHost, open: state.everyOpen, onToggle: on => { state.everyOpen = on; },
  });
}

async function selectValue(f, { animate = true, entrance = false, settle = false } = {}) {
  if (state.replay) state.replay.stop();      // a selection by hand ends the replay
  const { store } = state;
  const i = f.ref, v = store.values[i];
  if (!v) return;
  document.body.classList.remove('idle');
  state.sel = i; state.finding = f;
  const sums = store.sumsFor(v);
  renderPanel(f);
  stage.setLabel(stageLabel(store, f));
  state.flist.select(f.id);
  updateCounter();
  const dec = new Set(f.sums.map(s => s.terms.map(t => t[0]).filter(x => x !== null && x !== undefined).sort((a, b) => a - b).join(',')));
  tape.printFinding(store, f, sums.filter(s => !dec.has(sorted(s.check))), false);
  if (v.p !== stage.page) await stage.setPage(v.p, animate, v.p > stage.page ? 1 : -1);
  const sib = f.kind === 'wrong_column' ? siblingOf(store, f) : null;
  const extra = { tag: tagText(store, f), f };
  if (sib && sib.ref !== undefined) extra.other = sib.ref;
  await stage.select(i, sums, animate, { settle, extra });
  afterLoupe();
}

// a finding the sheet has no place for: the group's crop, and no ring
async function selectPlaceless(f, { animate = true } = {}) {
  if (state.replay) state.replay.stop();
  const { store } = state;
  document.body.classList.remove('idle');
  state.sel = null; state.finding = f;
  renderPanel(f);
  stage.setLabel(`${stageLabel(store, f)} This value has no place on the sheet.`);
  state.flist.select(f.id);
  updateCounter();
  tape.printFinding(store, f, [], false);
  if (f.page && f.page !== stage.page) await stage.setPage(f.page, animate, f.page > stage.page ? 1 : -1);
  stage.deselect();
  const g = store.groupById.get(f.group);
  if (g && g.crop) loupe.showCrop(g.crop, `The scan around ${f.row || 'the row'}, as cropped by the audit`, animate);
  else loupe.clear();
  afterLoupe();
}

// Previous and Next: the county's findings in the order of the list, the page follows
function step(d) {
  const fl = state.flist;
  if (!fl || !fl.vis.length) return;
  const n = fl.vis.length, cur = state.finding ? fl.position(state.finding.id) : 0;
  const k = cur ? cur - 1 + d : d > 0 ? 0 : n - 1;
  if (k < 0 || k >= n || (cur && k === cur - 1)) return;
  selectFinding(fl.at(k));
}
function updateCounter() {
  const fl = state.flist, n = fl ? fl.vis.length : 0, cur = fl && state.finding ? fl.position(state.finding.id) : 0;
  $('counter').textContent = n ? `${cur ? fmt(cur) : '–'} of ${fmt(n)}` : '';
  $('prev').disabled = !n || cur === 1;
  $('next').disabled = !n || cur === n;
}
function setFlatLabel() { $('flat').textContent = stage.flat ? 'Tilt sheet' : 'Lay flat'; }

// ---- a county
async function openCounty(key, { push = false, wantFinding = null } = {}) {
  const tok = ++state.openTok;
  if (state.replay) { state.replay.stop(); state.replay = null; }
  const entry = state.index.counties.find(c => c.key === key);
  state.cards.select(key);
  state.key = key; state.enter = false;
  if (push) { q.set('county', key); for (const k of ['cell', 'finding']) q.delete(k); history.replaceState(null, '', location.pathname + '?' + q); }
  const x = $('xpanel');
  x.setAttribute('aria-labelledby', `tab-${key}`);
  $('xnotice').hidden = true;
  if (entry.status === 'unchecked') return openUnchecked(entry);
  let store;
  try { store = await getStore(entry); } catch (e) { localError(e.file || entry.file); return; }
  if (tok !== state.openTok) return;
  state.store = store;
  stage.setStore(store);
  stage.forcePartial = forced === 'partial';
  if (state.flist) state.flist.destroy();
  const none = forced === 'empty';
  state.flist = new FindingList($('flist'), store, { onPick: f => selectFinding(f), none, filterEl: $('filters'), statusEl: $('fshowing'), onChange: filterChanged });
  const hasFindings = !!store.fd && store.items.length > 0 && !none;
  if (!hasFindings) return openEmpty(store, entry, none);
  $('findings-h').textContent = `All ${store.items.length === 1 ? 'mismatch' : `${fmt(store.items.length)} mismatches`} in ${entry.name}`;
  x.dataset.kind = 'finding';
  $('county-msg').hidden = true;
  let start = null;
  const wantF = wantFinding || q.get('finding'), cell = q.get('cell');
  if (wantF && store.itemById.has(wantF)) start = store.itemById.get(wantF);
  else if (cell && store.byId.has(cell) && store.itemByRef.has(store.byId.get(cell))) start = store.itemByRef.get(store.byId.get(cell));
  else start = startFinding(store);
  state.opening = start;
  setState(forced || 'ready');
  document.body.classList.remove('idle');
  const first = start.ref !== undefined ? store.values[start.ref].p : start.page || 1;
  await stage.setPage(first, false);
  if (tok !== state.openTok) return;
  stage.layout(true);
  await selectFinding(start, { animate: false });
  state.first = false;
  state.enter = !reduced && !forced;      // the first look at the sheet gets one short entrance, when it comes into view
  setFlatLabel();
  makeReplay();
  updateCounter();
}

function filterChanged() {
  const fl = state.flist;
  if (state.finding && !fl.position(state.finding.id) && fl.vis.length) selectFinding(fl.at(0));
  else updateCounter();
}

// a county with no mismatches: what the data says, and its first page lying with nothing marked
async function openEmpty(store, entry, forcedNone) {
  state.opening = null; state.sel = null; state.finding = null;
  const x = $('xpanel');
  x.dataset.kind = 'empty';
  const msg = $('county-msg');
  msg.textContent = forcedNone ? 'No mismatches found.' : emptyLine(entry);
  msg.hidden = false;
  setState(forced || 'ready');
  document.body.classList.add('idle');
  const page = store.pages.find(p => p.n === 1 && p.img) || store.pages.find(p => p.img);
  $('panel').replaceChildren(); tape.clear();
  loupe.clear();
  if (page) {
    await stage.setPage(page.n, false);
    stage.deselect();
    stage.layout(true);
    stage.setLabel(`Page ${page.n} of the scan of ${entry.name}. Nothing on it is marked: the run found no mismatch in this county.`);
  } else stage.root.classList.add('no-sheet');
  state.first = false; state.enter = false;
  setFlatLabel();
  makeReplay();
  updateCounter();
}

// a county the run did not check: the run's own sentence, and nothing to point at
function openUnchecked(entry) {
  state.store = null; state.opening = null; state.sel = null; state.finding = null; state.enter = false;
  if (state.flist) { state.flist.destroy(); state.flist = null; }
  const x = $('xpanel');
  x.dataset.kind = 'unchecked';
  const note = entry.note ? cap(entry.note) : NOT_CHECKED;
  const msg = $('county-msg');
  msg.textContent = /[.!?]$/.test(note) ? note : `${note}.`;
  msg.hidden = false;
  setState(forced || 'ready');
  state.first = false;
}

// the replay of the county's recorded run; its end puts the page back on the opening finding, drawn as on load
function makeReplay() {
  const { store } = state;
  const info = (store.fd && store.fd.run_info) || {};
  const started = state.index.started ? new Date(state.index.started) : null;
  const date = started && !isNaN(started) ? started.toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' }) : state.index.run;
  const o = state.opening;
  state.replay = new Replay({
    store, stage, loupe, reduced, date, onPage: () => {}, seconds: runSeconds(info), disabled: !!forced,
    els: { cap: $('rp-cap'), btn: $('replay'), speedBtn: $('speed'), hint: $('replay-hint'), card: $('panel'), findings: $('findings'), loupeEl: $('loupe'), leaderEl: $('leader') },
    headline: { set: () => {}, full: () => {} },
    restore: async animate => {
      if (o) await selectFinding(o, { animate });
      else { const pg = store.pages.find(p => p.n === 1 && p.img) || store.pages.find(p => p.img); if (pg) { await stage.setPage(pg.n, animate); stage.deselect(); } loupe.clear(); afterLoupe(); document.body.classList.add('idle'); }
    },
  });
  stage.layout(true);
}

// the first time the stage comes into view the sheet settles from flat into its tilt, the loupe rises, the sums draw
function watchReveal() {
  if (reduced || !('IntersectionObserver' in window)) return;
  const io = new IntersectionObserver(async es => {
    if (!es.some(e => e.isIntersecting) || !state.enter || !state.finding || state.finding.ref === undefined) return;
    io.disconnect();
    state.enter = false;
    const f = state.finding, settle = !stage.flat;
    if (settle) { stage.flat = true; stage.layout(true); }
    $('loupe').classList.add('rise');
    await selectValue(f, { animate: true, entrance: true, settle });
    setFlatLabel();
  }, { threshold: 0.4 });
  io.observe($('stage'));
}

// ---- the hero's two buttons
async function toExplorer() {
  const h = state.hero;
  if (h && state.key !== h.key) await openCounty(h.key, { push: true, wantFinding: h.f.id });
  scrollTo($('explore'));
  return h;
}

async function main() {
  stage.flat = q.get('flat') === '1' || reduced || innerWidth < 900;
  setFlatLabel();
  $('flat').onclick = () => { stage.setFlat(!stage.flat); setFlatLabel(); };
  $('prev').onclick = () => step(-1);
  $('next').onclick = () => step(1);
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

  // the explaining half: from the run's totals, and one real finding from the first county that has one
  renderHeroText(state.index);
  let example = null, firstPage = null;
  try {
    for (const c of cs) {
      if (c.status === 'unchecked') continue;
      const s = await getStore(c);
      if (!firstPage) { const p = s.pages.find(p => p.img); if (p) firstPage = { img: p.img, county: c.name, n: p.n }; }
      const f = c.disagreements ? pickExample(s) : null;
      if (f) { example = { key: c.key, store: s, f }; break; }
    }
  } catch (e) { fail(e.file || cs[0].file); return; }
  state.cards = new Cards($('counties'), cs, key => { if (key !== state.key) openCounty(key, { push: true }); });
  state.hero = example ? { key: example.key, f: example.f } : null;
  setState('ready');                       // the sections take their size; the picture below measures itself
  renderHeroPic($('hero-pic'), example && example.store, example && example.f, state.index, firstPage);
  renderSteps($('steps'), example && example.store, example && example.f, firstPage);
  // the reader's sample of each county: the run's summary, else the county's own run information
  const samples = new Map();
  for (const c of cs) {
    if (c.status === 'unchecked') continue;
    let s = state.index.summary && state.index.summary[c.key] && state.index.summary[c.key].sample;
    if (!s) { try { const st = await getStore(c); s = st.fd && st.fd.run_info && st.fd.run_info.sample; } catch (e) { s = null; } }
    if (s) samples.set(c.key, s);
  }
  renderRun($('run-box'), state.index, samples);

  $('see-proof').onclick = async () => { await toExplorer(); const p = $('place'); if (p) p.focus({ preventScroll: true }); };
  $('watch').onclick = async () => {
    await toExplorer();
    const r = state.replay;
    if (r && r.available && r.state === 'idle') r.start();
  };

  const want = q.get('county');
  await openCounty(cs.some(c => c.key === want) ? want : cs[0].key);
  watchReveal();
  // a link to a county or a finding opens on the explorer
  if (q.get('county') || q.get('finding') || q.get('cell')) { state.enter = false; $('explore').scrollIntoView({ block: 'start' }); }
}

// ---- shortcuts, matched on the key's position so a keyboard layout does not matter
addEventListener('keydown', e => {
  if (!e.altKey || !e.shiftKey || e.ctrlKey || e.metaKey) return;
  if (e.code === 'KeyR') {            // back to the opening state
    e.preventDefault();
    for (const k of ['state', 'cell', 'flat', 'reset']) q.delete(k);
    location.assign(location.pathname + (q.toString() ? '?' + q : ''));
  } else if (e.code === 'KeyP') {     // the replay: start, pause, resume
    e.preventDefault();
    if (state.replay) state.replay.toggle();
  }
});
// Escape pauses a running replay (a dialog that is open takes the key for itself)
addEventListener('keydown', e => {
  if (e.key !== 'Escape' || e.altKey || e.ctrlKey || e.metaKey || $('dlg').open) return;
  if (state.replay && state.replay.state === 'running') { e.preventDefault(); state.replay.pause(); }
});

main();
