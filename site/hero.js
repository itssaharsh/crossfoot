// The explaining half of the page: the hero and its worked example, the three steps, and the run. Everything on it comes from
// data/index.json and the county files; nothing is typed in here except the words around the figures.
import { fmt, PART, COLS, COL_WORD, pcl, cap } from './data.js';
import { loopPath } from './ring.js';
import { decidingSum, termTokens, placeOf } from './findings.js';

const SVGNS = 'http://www.w3.org/2000/svg';
const el = (tag, cls, text) => { const e = document.createElement(tag); if (cls) e.className = cls; if (text !== undefined) e.textContent = text; return e; };
const svg = (tag, attrs = {}) => { const e = document.createElementNS(SVGNS, tag); for (const k in attrs) e.setAttribute(k, attrs[k]); return e; };
const GITHUB = 'https://github.com/itssaharsh/crossfoot';
const DIGIT_PX = 34, DIGIT_MIN = 28;   // the figure in the example crop is drawn this tall on screen (never less than the minimum)

// the opening finding of a county: the first wrong-column group the printed sums all settled, else the first settled finding
export function opening(store) {
  const settled = f => f.status === 'settled_against_file';
  const g = store.fd.groups.find(g => g.kind === 'wrong_column' && g.findings.length && g.findings.every(id => settled(store.itemById.get(id))));
  if (g) { const fs = g.findings.map(id => store.itemById.get(id)); return fs.find(f => f.ref !== undefined) || fs[0]; }
  return store.items.find(f => settled(f) && f.ref !== undefined) || store.items.find(settled) || store.items[0];
}
export const startFinding = store => (store.report ? store.items[0] : opening(store));

// ---- the example crop: the scan's own pixels round the value, from the loupe's image
export function cropSpec(store, f) {
  if (f.ref === undefined) return null;
  const v = store.values[f.ref];
  if (!v) return null;
  if (store.report) {
    const rc = store.rowCrop(v), fb = rc && rc.fb && rc.fb[v.c];
    return fb ? { src: rc.img, w: rc.w, h: rc.h, box: fb.slice(), digit: fb[3] - fb[1] } : null;
  }
  const blk = store.block(v);
  if (!blk || !blk.bi || !blk.x || (!v.ix && !v.x)) return null;
  const mx = blk.bi.w / (blk.x[2] - blk.x[0]), my = blk.bi.h / (blk.x[3] - blk.x[1]);
  const box = v.ix ? v.ix.slice() : [(v.x[0] - blk.x[0]) * mx, (v.x[1] - blk.x[1]) * my, (v.x[2] - blk.x[0]) * mx, (v.x[3] - blk.x[1]) * my];
  return { src: blk.bi.img, w: blk.bi.w, h: blk.bi.h, box, digit: (box[3] - box[1]) * (v.ix ? 1 : 0.6) };
}

// the finding the picture is made of: the page's opening finding when it can be drawn, else the first settled one that can
export function pickExample(store) {
  if (!store || !store.fd || !store.items.length) return null;
  const ok = f => f && f.status === 'settled_against_file' && f.ref !== undefined && f.scan !== undefined && f.file !== undefined && decidingSum(f) && cropSpec(store, f);
  const first = startFinding(store);
  return ok(first) ? first : store.items.find(ok) || null;
}

// ---- the hero's words and figures
export function renderHeroText(index) {
  const t = index.totals || {};
  document.getElementById('headline').textContent = `${fmt(t.findings)} numbers in a public election dataset don't match the scanned originals.`;
  const figs = document.getElementById('figs');
  figs.replaceChildren(...[[t.read, 'county files checked'], [t.findings, 'mismatches found'], [t.settled, "proven by the scans' own totals"]].map(([n, l]) => {
    const li = el('li');
    li.append(el('span', 'n', fmt(n)), el('span', 'l', l));
    return li;
  }));
  const note = document.getElementById('figs-note');
  note.textContent = t.cannot_verify !== undefined ? `${fmt(t.cannot_verify)} could not be proven and were left alone.` : '';
  note.hidden = t.cannot_verify === undefined;
}

// ---- the worked example: the page lying in depth on a pale desk, the crop of the scan lifted above it
export function renderHeroPic(fig, store, f, index, firstPage) {
  fig.replaceChildren();
  if (!store || !f) return plainPage(fig, firstPage);
  const spec = cropSpec(store, f), v = store.values[f.ref], pg = store.pages.find(p => p.n === f.page);
  const s = decidingSum(f);
  const county = (index.counties.find(c => c.key === store.d.county) || {}).name || cap(String(store.d.county));
  const labels = el('div', 'hp-labels');
  const lScan = el('p', 'lab scan', `The scan says ${fmt(f.scan)}`), lFile = el('p', 'lab file', `The public file says ${fmt(f.file)}`);
  labels.append(lScan, lFile);
  const view = el('div', 'hp-view');
  const card = el('div', 'hp-crop');
  card.append(view);
  const top = el('div', 'hp-top');
  const lead = svg('svg', { class: 'hp-lead', 'aria-hidden': 'true' });
  top.append(labels, card, lead);
  const noun = ['col', 'report_contest', 'grand_row'].includes(s.kind) ? 'column' : s.kind === 'grand' ? 'set of totals' : 'row';
  const proof = el('p', 'hp-proof');
  proof.append(el('strong', '', 'Proof: '), `with the file's number this ${noun} adds up to ${fmt(s.with_file)}. The scan prints a total of ${fmt(s.printed)}.`);
  const cap_ = el('figcaption', 'hp-cap', `${county} County, page ${f.page} of the scan. A real example from this run.`);
  fig.append(top, proof, cap_);
  const sheet = pg && pg.img ? sheetScene(pg, v) : null;
  if (sheet) fig.append(sheet.wrap);

  // the crop: the figure at reading size, the pencil loop on it
  const img = el('img');
  img.alt = `A close crop of the scan. The ringed figure reads ${fmt(f.scan)}.`;
  img.src = spec.src; img.width = spec.w; img.height = spec.h;
  const pan = el('div', 'hp-pan');
  pan.style.width = `${spec.w}px`; pan.style.height = `${spec.h}px`;
  const ov = svg('svg', { viewBox: `0 0 ${spec.w} ${spec.h}`, width: spec.w, height: spec.h, class: 'hp-ov', 'aria-hidden': 'true' });
  const ring = svg('path', { d: loopPath(spec.box, 9), class: 'hp-ring' });
  ov.append(ring);
  pan.append(img, ov);
  view.append(pan);

  const place = () => {
    const W = view.clientWidth, H = view.clientHeight;
    if (!W || !H) return;
    const S = Math.max(DIGIT_MIN / spec.digit, Math.min(DIGIT_PX / spec.digit, 2.4));
    const cx = (spec.box[0] + spec.box[2]) / 2, cy = (spec.box[1] + spec.box[3]) / 2;
    let tx = W / 2 - cx * S, ty = H / 2 - cy * S;
    tx = spec.w * S <= W ? (W - spec.w * S) / 2 : Math.min(0, Math.max(W - spec.w * S, tx));
    ty = spec.h * S <= H ? (H - spec.h * S) / 2 : Math.min(0, Math.max(H - spec.h * S, ty));
    pan.style.transform = `translate(${tx}px, ${ty}px) scale(${S})`;
    ring.style.strokeWidth = `${3 / S}px`;
    if (sheet) sheet.fit(fig.clientWidth);
    // the two short leaders: from each label down into the crop, to the loop on the figure
    const o = top.getBoundingClientRect(), r = ring.getBoundingClientRect();
    lead.replaceChildren();
    for (const [lab, cls, fx] of [[lScan, 'scan', 0.3], [lFile, 'file', 0.7]]) {
      const b = lab.getBoundingClientRect();
      const x1 = b.left + b.width / 2 - o.left, y1 = b.bottom - o.top + 2;
      const x2 = r.left + r.width * fx - o.left, y2 = r.top + 6 - o.top;
      lead.append(svg('line', { x1, y1, x2, y2, class: cls }), svg('circle', { cx: x2, cy: y2, r: 3.5, class: cls }));
    }
  };
  requestAnimationFrame(place);
  new ResizeObserver(place).observe(fig);
  if (!img.complete) img.addEventListener('load', place);
}

function plainPage(fig, page) {
  if (!page) return;
  const wrap = el('div', 'hp-plain');
  const im = el('img');
  im.alt = `The first page of the scan of ${page.county}`; im.src = page.img;
  wrap.append(im);
  fig.append(wrap, el('figcaption', 'hp-cap', `${page.county} County, page ${page.n} of the scan.`));
}

// the scan page in depth: its page stack, a soft shadow, and a ring where the value is
function sheetScene(pg, v) {
  const wrap = el('div', 'hp-desk');
  const sheet = el('div', 'hp-sheet');
  const under = el('i', 'under');
  const pile = Array.from({ length: 4 }, (_, i) => {
    const e = el('i', 'leaf');
    e.style.transform = `translate3d(${(i + 1) * 3}px, ${(i + 1) * 3}px, ${-(i + 1) * 2}px)`;
    e.style.background = ['#e4e1d6', '#dad7cb', '#d0cdc0', '#c6c3b5'][i];
    return e;
  });
  under.style.transform = 'translate3d(15px, 15px, -10px)';
  const page = el('div', 'face');
  const im = el('img');
  im.alt = 'The whole scanned page, lying on a desk'; im.src = pg.img;
  const ov = svg('svg', { viewBox: `0 0 ${pg.w} ${pg.h}`, class: 'face-ov', 'aria-hidden': 'true' });
  const dot = v && v.x ? svg('circle', { cx: (v.x[0] + v.x[2]) / 2, cy: (v.x[1] + v.x[3]) / 2, r: Math.max((v.x[3] - v.x[1]) * 1.2, 22), class: 'face-ring' }) : null;
  if (dot) ov.append(dot);
  page.append(im, ov);
  sheet.append(under, ...pile, page);
  wrap.append(sheet);
  return {
    wrap,
    fit(w) {   // the sheet's width follows the picture; the box under it is as tall as the tilted sheet
      const sw = Math.min(w * 0.76, 520), sh = sw * pg.h / pg.w;
      sheet.style.width = `${sw}px`; sheet.style.height = `${sh}px`;
      wrap.style.height = `${Math.round(sh * 0.8 + 34)}px`;
    },
  };
}

// ---- how it works: three cards, each with a small real picture
const FILE_COLS = [['early_voting', 'Early'], ['absentee', 'Absentee'], ['election_day', 'Election day'], ['votes', 'Total']];
// three rows of the published file round the example: [{label, cells: [{v, bad}]}], with the header words
export function neighbourRows(store, f) {
  const v = store.values[f.ref];
  const cell = (p, b, r, c) => { const i = store.byId.get(`${p}:${b}:${r}:${c}`); return i === undefined ? null : i; };
  const cellOf = (i) => { const o = store.fileAt.has(i) ? { v: store.fileAt.get(i), bad: true } : { v: store.values[i].v, bad: false }; return o; };
  if (store.report) {
    const rows = [];
    for (const i of store.byPage.get(v.p) || []) { const o = store.values[i]; if (o.b === v.b && !rows.includes(o.r)) rows.push(o.r); }
    const k = rows.indexOf(v.r), pick = rows.slice(Math.max(0, k - 1), k + 2);
    const out = pick.map(r => ({ label: r, cells: COLS.map(c => { const i = cell(v.p, v.b, r, c); return i === null ? null : cellOf(i); }) })).filter(r => r.cells.every(Boolean));
    return { head: COLS.map(c => cap(COL_WORD[c])), rows: out, title: [f.precinct ? cap(pcl(f.precinct)) : null, f.office].filter(Boolean).join(' · ') };
  }
  const blk = store.block(v);
  const peers = [...store.blocks.values()].filter(b => b.p === v.p && b.cand && blk && b.contest === blk.contest);
  const k = peers.findIndex(b => b.id === v.b), pick = peers.slice(Math.max(0, k - 1), k + 2);
  const KIND_ROWS = ['EARLY', 'ABSENTEE', 'PRECINCT', 'col'];
  const out = pick.map(b => ({ label: b.cand, cells: KIND_ROWS.map(r => { const i = cell(v.p, b.id, r, v.c); return i === null ? null : cellOf(i); }) })).filter(r => r.cells.every(Boolean));
  return { head: FILE_COLS.map(c => c[1]), rows: out, title: [f.precinct ? cap(pcl(f.precinct)) : null, blk && blk.contest].filter(Boolean).join(' · ') };
}

export function renderSteps(box, store, f, firstPage) {
  box.replaceChildren();
  const card = (n, title, text, pic) => {
    const li = el('li', 'step');
    li.append(el('p', 'pic', ''), el('h3', '', `${n} · ${title}`), el('p', '', text));
    li.firstChild.replaceWith(pic);
    box.append(li);
  };
  // 1: a thumbnail of a real scanned page
  const pg1 = (store && f && store.pages.find(p => p.n === f.page && p.img)) || null;
  const src = pg1 ? { img: pg1.img, county: (store.d.county || '') } : firstPage;
  const p1 = el('div', 'pic thumb');
  if (src) { const im = el('img'); im.src = src.img; im.alt = 'A scanned page of county results: a printed table, as a picture'; p1.append(im); }
  card(1, 'A county publishes a scan', 'A picture of a printed table. There is no text in it to copy.', p1);
  // 2: three rows of the published file, the wrong cell marked red
  const p2 = el('div', 'pic minitable');
  const nb = store && f ? neighbourRows(store, f) : null;
  if (nb && nb.rows.length) {
    const cap_ = el('p', 'mt-title', `The published file · ${nb.title}`);
    const t = el('table');
    t.setAttribute('aria-label', `Three rows of the published file round the example. ${nb.title}`);
    const head = el('tr');
    head.append(el('th', '', ''), ...nb.head.map(h => Object.assign(el('th', 'num', h), { scope: 'col' })));
    head.firstChild.scope = 'col'; head.firstChild.append(el('span', 'sr', 'Row'));
    t.append(Object.assign(el('thead'), {}));
    t.firstChild.append(head);
    const tb = el('tbody');
    for (const r of nb.rows) {
      const tr = el('tr');
      const th = el('th', 'rowh', r.label); th.scope = 'row'; th.title = r.label;
      tr.append(th, ...r.cells.map(c => { const td = el('td', 'num' + (c.bad ? ' bad' : ''), fmt(c.v)); if (c.bad) td.append(el('span', 'sr', ' (wrong in the file)')); return td; }));
      tb.append(tr);
    }
    t.append(tb);
    p2.append(cap_, t);
  } else if (nb || !store) p2.append(el('p', 'mt-title', 'The published file is a spreadsheet of typed numbers.'));
  card(2, 'Volunteers type it into a spreadsheet', 'With thousands of numbers, slips get through, and nobody re-reads every page.', p2);
  // 3: the example's sum, two short lines
  const p3 = el('div', 'pic sums');
  const s = f ? decidingSum(f) : null;
  if (s) {
    for (const [who, side, total, holds] of [['Scan', 'scan', s.with_scan, s.holds_scan], ['File', 'file', s.with_file, s.holds_file]]) {
      const line = el('p', 'sumline ' + (holds ? 'holds' : 'fails'));
      const terms = el('span', 'terms');
      termTokens(store, f, s, side).forEach((k, i) => { if (i) terms.append(' + '); if (k.diff) terms.append(el('strong', 'chg', k.t)); else terms.append(k.t); });
      terms.append(` = ${fmt(total)}`);
      line.append(el('span', 'who', who), terms, ' ', Object.assign(el('span', 'tick', holds ? '✓' : '✗'), { ariaHidden: 'true' }), el('span', 'sr', holds ? ', matches the printed total' : ', does not match the printed total'));
      p3.append(line);
    }
    p3.append(el('p', 'mt-title', `printed total ${fmt(s.printed)}`));
  } else p3.append(el('p', 'mt-title', 'Every printed table adds up to its own totals.'));
  card(3, 'Crossfoot reads the scan again and adds it up', "Every table prints its own totals. A number is called wrong only when those totals prove it.", p3);
}

// ---- the run
const EVIDENCE = `${GITHUB}/blob/main/docs/evidence/`;
const LINKS = [['Before and after', 'before-after.md'], ['The one-prompt baseline', 'baseline.md'], ['Recoveries', 'recovery.md'], ['Traces', 'traces.md']];
const listWords = names => (names.length <= 1 ? names.join('') : `${names.slice(0, -1).join(', ')} and ${names[names.length - 1]}`);

// the counties whose first sample failed more than the line, so the stronger reader was used: from the sample figures the run kept
export function switchedCounties(index, samples) {
  return index.counties.filter(c => {
    const s = samples.get(c.key);
    return s && s.row_sums && s.failing / s.row_sums > s.line && s.reader !== s.sampled_with;
  }).map(c => c.name);
}

export function renderRun(box, index, samples) {
  box.querySelectorAll('.run-body').forEach(n => n.remove());
  const t = index.totals || {};
  const body = el('div', 'run-body');
  const mins = t.seconds !== undefined ? (t.seconds / 60).toFixed(1) : null;
  const bits = [];
  if (t.counties !== undefined) bits.push(`audited all ${fmt(t.counties)} files`);
  if (mins) bits.push(`in ${mins} minutes`);
  const cost = t.metered_cost !== undefined ? ` for $${Number(t.metered_cost).toFixed(2)} of model calls${t.model_calls !== undefined ? ` (${fmt(t.model_calls)} calls)` : ''}` : '';
  if (bits.length) body.append(el('p', 'run-line', `One command ${bits.join(' ')}${cost}.`));
  if (t.sums_in_all) {
    const g = el('div', 'bars');
    g.append(el('h3', '', 'Printed sums that hold'));
    for (const [label, n, cls] of [['In the published files', t.holding_published, 'pub'], ['In the corrected files', t.holding_corrected, 'cor']]) {
      if (n === undefined) continue;
      const row = el('div', 'bar-row ' + cls);
      const track = el('div', 'track');
      track.setAttribute('role', 'img');
      track.setAttribute('aria-label', `${label}: ${fmt(n)} of ${fmt(t.sums_in_all)} printed sums hold`);
      const fill = el('i'); fill.style.width = `${(n / t.sums_in_all * 100).toFixed(2)}%`;
      track.append(fill);
      const val = el('p', 'bv');
      val.append(el('strong', '', fmt(n)), ` of ${fmt(t.sums_in_all)}`);
      row.append(el('p', 'bl', label), track, val);
      g.append(row);
    }
    body.append(g);
  }
  const sw = switchedCounties(index, samples);
  body.append(el('p', 'reader', `The agent read a sample of each county with a cheap model first and switched to a stronger one only where more than a tenth of the sample's sums failed: ${sw.length ? listWords(sw) : 'no county needed that'}.`));
  const ul = el('ul', 'evid');
  for (const [label, file] of LINKS) { const li = el('li'); const a = el('a', '', label); a.href = EVIDENCE + file; li.append(a); ul.append(li); }
  body.append(el('h3', 'evid-h', 'The evidence, on GitHub'), ul);
  box.append(body);
}
