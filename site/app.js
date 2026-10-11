import { getJSON, LoadError, loadMessage, Store, idOf } from './data.js';
import { Stage } from './stage.js';
import { Loupe } from './loupe.js';
import { Tape } from './tape.js';
import { renderCard, stageLabel, FailList } from './panel.js';

const $ = id => document.getElementById(id);
const q = new URLSearchParams(location.search);
const reduced = matchMedia('(prefers-reduced-motion: reduce)').matches;
const coarse = matchMedia('(pointer: coarse)').matches;

const stage = new Stage({
  viewport: $('viewport'), leanEl: $('lean'), pose: $('pose'), paper: $('paper'), sheet: $('sheet'), stack: $('stack'), root: $('stage'),
  loupeEl: $('loupe'), leader: $('leader'), leaderLine: $('leader-line'), controls: $('controls'),
  scan: $('scan'), bands: $('bands'), marks: $('marks'), notice: $('notice'),
}, { reduced, coarse, onPick: i => select(i), onError: loadMessage });
stage.setLoupe(new Loupe({ root: $('loupe'), view: $('lp-view'), note: $('lp-note') }, { onPick: i => select(i) }));
const tape = new Tape($('tape'), reduced, i => select(i));
const state = { store: null, list: null, sel: null, index: null, counties: {} };

function fail(file) {
  $('notice').textContent = loadMessage(file);
  $('notice').hidden = false;
  $('paper').setAttribute('aria-label', loadMessage(file));
}

async function select(i, { animate = true } = {}) {
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
  const done = await stage.select(i, sums, animate);
  if (done && state.sel === i) tape.print(store, sums, animate);
  updatePager();
}

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
  $('pageno').textContent = `Page ${n} of ${total}`;
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
  state.list = new FailList($('fails'), store, c => {
    const i = store.firstValue(c);
    if (i !== null) select(i);
  });
  let start = null;
  const want = q.get('cell');
  if (want && store.byId.has(want)) start = store.byId.get(want);
  if (start === null) start = store.defaultOn(1);
  if (start === null) { fail(entry.file); return; }
  const v = store.values[start];
  await stage.setPage(v.p, false);
  stage.sel = start;
  stage.layout(true);
  await select(start, { animate: false });
  for (const b of document.querySelectorAll('#tabs button')) b.setAttribute('aria-pressed', String(b.dataset.key === key));
}

async function main() {
  stage.flat = q.get('flat') === '1' || reduced || innerWidth < 900;
  setFlatLabel();
  $('flat').onclick = () => { stage.setFlat(!stage.flat); setFlatLabel(); };
  $('prev').onclick = () => goPage(stage.page - 1, true, -1);
  $('next').onclick = () => goPage(stage.page + 1, true, 1);
  try { state.index = await getJSON('data/index.json'); }
  catch (e) { fail(e.file); return; }
  const cs = state.index.counties;
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
main();
