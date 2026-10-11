import { getJSON, LoadError, loadMessage, Store, progress, fmt } from './data.js';
import { Tabs, renderRunLine, emptyLine } from './tabs.js';
import { Stage } from './stage.js';
import { Loupe } from './loupe.js';
import { Tape } from './tape.js';
import { renderCard, stageLabel, FailList } from './panel.js';
import { renderFindingCard, FindingList, Dialog, renderRun, contextLine, siblingOf, setHeadline, runSeconds, tagText } from './findings.js';
import { Replay } from './replay.js';

const $ = id => document.getElementById(id);
const q = new URLSearchParams(location.search);
const reduced = matchMedia('(prefers-reduced-motion: reduce)').matches;
const coarse = matchMedia('(pointer: coarse)').matches;
const FIRST_RUN = 'No run has been built into this page yet. Run crossfoot site build.';
const EMPTY = 'No disagreements in this county.';
const STATES = ['loading', 'error', 'empty', 'partial', 'first-run'];
const NOT_CHECKED = 'Nothing on this scan can be cross-checked; left as published.';

// ?reset=1 opens the page as if for the first time: no state, cell or flat parameter is read, and the address is cleaned
const reset = q.get('reset') === '1';
if (reset) { q.delete('reset'); for (const k of ['state', 'cell', 'flat']) q.delete(k); history.replaceState(null, '', location.pathname + (q.toString() ? '?' + q : '')); }
const forced = !reset && STATES.includes(q.get('state')) ? q.get('state') : null;
if (q.get('record') === '1') document.body.classList.add('record');   // recording mode: see the .judge-only rule in styles.css

const stage = new Stage({
  viewport: $('viewport'), leanEl: $('lean'), pose: $('pose'), paper: $('paper'), sheet: $('sheet'), stack: $('stack'), root: $('stage'),
  loupeEl: $('loupe'), leader: $('leader'), leaderLine: $('leader-line'), controls: $('controls'),
  scan: $('scan'), bands: $('bands'), marks: $('marks'), notice: $('notice'), flatEl: $('flatblock'), blankNote: $('blank-note'),
}, { reduced, coarse, onPick: i => select(i), onError: loadMessage, onFocusValue: i => peek(i) });
const loupe = new Loupe({ root: $('loupe'), view: $('lp-view'), note: $('lp-note'), ctx: $('ctx') }, { onPick: i => select(i), reduced });
stage.setLoupe(loupe);
const tape = new Tape($('tape'), reduced, i => select(i));
const dialog = new Dialog($('dlg'));
const state = { key: null, tabs: null, replay: null, opening: null, store: null, list: null, flist: null, sel: null, finding: null, index: null, counties: {}, first: true };
const sorted = c => c.t.slice().sort((a, b) => a - b).join(',');

// ---- the page's state: body[data-state] decides what shows (styles.css); the controls follow it
function setState(name) {
  document.body.dataset.state = name;
  const live = !['loading', 'error', 'first-run', 'unchecked'].includes(name);
  for (const id of ['flat', 'prev', 'next']) $(id).disabled = !live;
  const sb = $('statebox');
  if (name === 'loading') sb.textContent = `Loading run… ${progress.n} ${progress.n === 1 ? 'file' : 'files'}`;
  else if (name === 'first-run') sb.textContent = FIRST_RUN;
  else if (name === 'unchecked') sb.textContent = NOT_CHECKED;
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
// a value of the sheet; when a finding sits on it, the page shows the finding
async function select(i, { animate = true, entrance = false, settle = false } = {}) {
  if (state.replay) state.replay.stop();      // a selection by hand ends the replay
  const { store } = state;
  const v = store.values[i];
  if (!v) return;
  if (document.body.classList.contains('idle')) { document.body.classList.remove('idle'); stage.layout(true); }   // the loupe is back: the sheet makes room
  state.sel = i;
  const f = store.itemByRef.get(i) || null;
  state.finding = f;
  const sums = store.sumsFor(v);
  const card = $('card');
  card.className = 'card';
  if (f) renderFindingCard(card, store, f, { onCrop: (x, b) => dialog.crop(store, x, b), onEvidence: (x, b) => dialog.evidenceFile(store, x, b) });
  else renderCard(card, store, v);
  setContext(f ? contextLine(store, f) : [`Page ${v.p}`, store.block(v) && store.block(v).contest, store.printedLabel(v), store.isTotal(v) ? null : `precinct ${v.c}`].filter(Boolean).join(' · '));
  stage.setLabel(stageLabel(store, v, sums, f));
  state.list.follow(sums);
  state.flist.select(f ? f.id : null);
  tape.clear();
  if (v.p !== stage.page) await goPage(v.p, animate, v.p > stage.page ? 1 : -1, false);
  let extra = {};
  if (f) {
    extra = { tag: tagText(store, f), f };
    const sib = f.kind === 'wrong_column' ? siblingOf(store, f) : null;
    if (sib && sib.ref !== undefined) extra.other = sib.ref;
  }
  const done = await stage.select(i, sums, animate, { settle, extra });
  if (done && state.sel === i) {
    if (f) {
      const dec = new Set(f.sums.map(s => s.terms.map(t => t[0]).filter(x => x !== null && x !== undefined).sort((a, b) => a - b).join(',')));
      tape.printFinding(store, f, sums.filter(s => !dec.has(sorted(s.check))), animate, entrance ? 260 : undefined);
    } else tape.print(store, sums, animate, entrance ? 260 : undefined);
  }
  updatePager();
}

// a finding the sheet has no place for: the group's crop, flat, and no ring
async function selectPlaceless(f, { animate = true } = {}) {
  if (state.replay) state.replay.stop();
  const { store } = state;
  state.sel = null; state.finding = f;
  const card = $('card');
  renderFindingCard(card, store, f, { onCrop: (x, b) => dialog.crop(store, x, b), onEvidence: (x, b) => dialog.evidenceFile(store, x, b) });
  setContext(contextLine(store, f));
  stage.setLabel(`Page ${f.page} of the scan. Selected: ${contextLine(store, f)}. This value has no place on the sheet; the group's crop is shown.`);
  state.flist.select(f.id);
  tape.clear();
  if (f.page && f.page !== stage.page) await goPage(f.page, animate, f.page > stage.page ? 1 : -1, false);
  stage.deselect();
  const g = store.groupById.get(f.group);
  if (g && g.crop) loupe.showCrop(g.crop, `The scan around ${f.row || 'the row'}, as cropped by the audit`, animate);
  else { loupe.clear(); loupe.note.hidden = false; }
  tape.printFinding(store, f, [], animate);
  updatePager();
}
const selectFinding = (f, o) => (f.ref !== undefined ? select(f.ref, o) : selectPlaceless(f, o));
function setContext(text) { $('ctx').textContent = text; }

// the keyboard is on a value of the sheet: the loupe shows it too, and goes back to the selection when focus leaves
function peek(i) { if (state.store) loupe.peek(state.store, i); }

async function goPage(n, animate, dir, pick = true) {
  if (state.replay) state.replay.stop();
  await stage.setPage(n, animate, dir);
  updatePager();
  if (pick) {
    const f = state.store.items.find(x => x.page === n && x.ref !== undefined);
    const i = f ? f.ref : state.store.defaultOn(n);
    if (i !== null) await select(i, { animate });
  }
}

// the pages the run lists, in order (a page the run could not read has no entry: the pager skips it)
const pageNums = () => state.store.pages.map(p => p.n);
const pageStep = d => { const ns = pageNums(), i = ns.indexOf(stage.page); return ns[i + d]; };

function updatePager() {
  const n = stage.page, ns = pageNums(), last = ns[ns.length - 1];
  $('pageno').replaceChildren(Object.assign(document.createElement('span'), { className: 'pw', textContent: 'Page ' }), `${n} of ${last}`);
  $('prev').disabled = pageStep(-1) === undefined; $('next').disabled = pageStep(1) === undefined;
}

function setFlatLabel() { $('flat').textContent = stage.flat ? 'Tilt sheet' : 'Lay flat'; }

async function openCounty(key, { push = false } = {}) {
  if (state.replay) { state.replay.stop(); state.replay = null; }
  const entry = state.index.counties.find(c => c.key === key);
  if (state.tabs) state.tabs.select(key);
  state.key = key;
  if (push) { q.set('county', key); for (const k of ['cell', 'finding']) q.delete(k); history.replaceState(null, '', location.pathname + '?' + q); }
  document.body.classList.remove('unchecked-county');
  $('panel').scrollTop = 0;
  if (entry.status === 'unchecked') return openUnchecked(entry);
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
  if (state.flist) state.flist.destroy();
  const none = forced === 'empty';
  state.flist = new FindingList($('flist'), store, {
    onPick: f => selectFinding(f), none, countEl: $('fcount'), filterEl: $('filters'), statusEl: $('fshowing'),
  });
  const hasFindings = !!store.fd && store.items.length > 0 && !none;
  $('findings-h').textContent = !store.fd || hasFindings ? 'Disagreements' : EMPTY;
  $('flist').hidden = !hasFindings;
  $('findings').classList.toggle('none', !hasFindings);
  $('findings').hidden = !store.fd && !none;
  $('fails-sec').open = !store.fd;            // with no findings in the data, the failing sums are what there is to see
  $('fails-sec').hidden = none;
  renderRun($('run'), store.fd);
  if (store.report && store.fd && !store.items.length && !none) return openEmpty(store, entry);
  let start = null, startFinding = null;
  const want = q.get('cell'), wantF = q.get('finding');
  if (wantF && store.itemById.has(wantF)) startFinding = store.itemById.get(wantF);
  else if (want && store.byId.has(want)) start = store.byId.get(want);
  else if (hasFindings) startFinding = store.report ? store.items[0] : opening(store);
  state.opening = startFinding || null;
  if (startFinding) {
    if (startFinding.ref !== undefined) start = startFinding.ref;
    else { await openPlaceless(startFinding, entry, key); makeReplay(); return; }
  }
  if (start === null) start = store.defaultOn(1);
  if (start === null) { fail(entry.file); return; }
  const v = store.values[start];
  // the first load only: one short entrance (sheet settles, loupe rises, sums draw, tape prints), none under reduced motion
  const enter = state.first && !reduced;
  const settle = enter && !stage.flat;
  if (settle) stage.flat = true;
  setState(forced || 'ready');
  document.body.classList.remove('idle');
  if (enter) $('loupe').classList.add('rise');
  await stage.setPage(v.p, false);
  stage.sel = start;
  stage.layout(true);
  updatePager();
  await select(start, { animate: enter, entrance: enter, settle });
  state.first = false;
  setFlatLabel();
  makeReplay(start);
}

// a county with no disagreements: its first page with nothing marked, and what the data says about its printed sums
async function openEmpty(store, entry) {
  state.opening = null; state.sel = null; state.finding = null;
  setState(forced || 'ready');
  document.body.classList.add('idle');
  await stage.setPage(1, false);
  stage.deselect();
  stage.layout(true);
  updatePager();
  loupe.clear();
  tape.clear();
  const card = $('card');
  card.className = 'card empty-county';
  card.removeAttribute('aria-label');
  card.replaceChildren(Object.assign(document.createElement('p'), { className: 'ec-line', textContent: emptyLine(entry) }));
  $('ctx').textContent = `Page 1 · ${entry.name}`;
  stage.setLabel(`Page 1 of the scan of ${entry.name}. Nothing on it is marked: the run found no disagreement in this county.`);
  state.first = false;
  setFlatLabel();
  makeReplay(null);
}

// a county the run did not check: the run's own sentence, and nothing to point at
function openUnchecked(entry) {
  state.store = null; state.opening = null; state.sel = null; state.finding = null;
  const text = NOT_CHECKED;
  document.body.classList.add('unchecked-county');
  setState('unchecked');
  $('statebox').textContent = text;
  $('fcount').textContent = text;
  $('card').replaceChildren(); $('tape').replaceChildren();
  $('ctx').textContent = '';
  $('paper').setAttribute('aria-label', text);
  const btn = $('replay');
  btn.disabled = true; $('speed').hidden = true;
  $('replay-hint').textContent = text;
  state.first = false;
}

// the replay of the county's recorded run; its end puts the page back on the opening value, drawn as on load
function makeReplay(start = null) {
  const { store } = state;
  const info = (store.fd && store.fd.run_info) || {};
  const started = state.index.started ? new Date(state.index.started) : null;
  const date = started && !isNaN(started) ? started.toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' }) : state.index.run;
  const o = state.opening;
  state.replay = new Replay({
    store, stage, loupe, reduced, date, onPage: () => updatePager(), seconds: runSeconds(info), disabled: !!forced,
    els: { cap: $('rp-cap'), btn: $('replay'), speedBtn: $('speed'), hint: $('replay-hint'), card: $('card'), findings: $('findings'), loupeEl: $('loupe'), leaderEl: $('leader') },
    headline: { set: c => setHeadline($('fcount'), c), full: () => state.flist.counts() },
    restore: async animate => {
      if (o && o.ref === undefined) await selectPlaceless(o, { animate });
      else if (start !== null || o) await select(start !== null ? start : o.ref, { animate });
      else { await stage.setPage(1, animate); stage.deselect(); loupe.clear(); document.body.classList.add('idle'); updatePager(); }   // a county with nothing found: its first page, nothing marked
    },
  });
  stage.layout(true);   // the speed control and the replay label change how tall the controls are
}

// the opening finding: the first wrong-column group the printed sums all settled, else the first settled finding
function opening(store) {
  const settled = f => f.status === 'settled_against_file';
  const g = store.fd.groups.find(g => g.kind === 'wrong_column' && g.findings.length && g.findings.every(id => settled(store.itemById.get(id))));
  if (g) { const fs = g.findings.map(id => store.itemById.get(id)); return fs.find(f => f.ref !== undefined) || fs[0]; }
  return store.items.find(f => settled(f) && f.ref !== undefined) || store.items.find(settled) || store.items[0];
}

async function openPlaceless(f, entry, key) {
  setState(forced || 'ready');
  document.body.classList.remove('idle');
  await stage.setPage(f.page || 1, false);
  stage.layout(true);
  updatePager();
  await selectPlaceless(f, { animate: false });
  state.first = false;
  setFlatLabel();
}

async function main() {
  stage.flat = q.get('flat') === '1' || reduced || innerWidth < 900;
  setFlatLabel();
  $('flat').onclick = () => { stage.setFlat(!stage.flat); setFlatLabel(); };
  $('prev').onclick = () => { const n = pageStep(-1); if (n !== undefined) goPage(n, true, -1); };
  $('next').onclick = () => { const n = pageStep(1); if (n !== undefined) goPage(n, true, 1); };
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
  renderRunLine($('runline'), state.index);
  state.tabs = new Tabs($('tabs'), cs, key => { if (key !== state.key) openCounty(key, { push: true }); });
  const want = q.get('county');
  await openCounty(cs.some(c => c.key === want) ? want : cs[0].key);
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
