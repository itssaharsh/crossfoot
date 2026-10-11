// The findings: the card, the list with its filters, the run numbers and the crop and evidence dialogs.
import { fmt, KIND, KINDS, STATUS, STATUSES, PART, UNCONFIRMED, COLS, COL_WORD, pcl } from './data.js';

const el = (tag, cls, text) => { const e = document.createElement(tag); if (cls) e.className = cls; if (text !== undefined) e.textContent = text; return e; };
const hid = e => { e.setAttribute('aria-hidden', 'true'); return e; };
const cap = s => (s ? s[0].toUpperCase() + s.slice(1) : s);
const val = n => (n === undefined || n === null ? '—' : fmt(n));
const valWords = n => (n === undefined || n === null ? 'none' : fmt(n));
export const VIRTUAL_ABOVE = 200;   // rows; more than this and only the rows near the viewport are in the page

// the other finding of the group that holds the value this one's scan has (a swap): where the file put it
export function siblingOf(store, f) {
  const g = store.groupById.get(f.group);
  if (!g || f.scan === undefined || f.file === undefined) return null;
  const sibs = g.findings.map(id => store.itemById.get(id)).filter(o => o && o.id !== f.id && (o.precinct !== f.precinct || o.part !== f.part));
  return sibs.find(o => o.file === f.scan && o.scan === f.file) || null;
}

// the one plain sentence for what kind of slip this is
export function sentence(store, f) {
  const sib = siblingOf(store, f);
  const v = f.ref === undefined ? null : store.values[f.ref];
  if (store.report) return reportSentence(store, f, sib);
  if (f.scan === undefined && (f.kind === 'wrong_column' || f.kind === 'wrong_precinct')) {
    return `The file has ${val(f.file)} under precinct ${f.precinct}${f.part && f.part !== 'votes' ? `, ${PART[f.part]}` : ''}. The scan has no value there.`;
  }
  switch (f.kind) {
    case 'wrong_column':
      return `On the scan this vote is under ${v ? v.r : PART[f.part] || 'one column'}. ` +
        (sib ? `The file has it under ${PART[sib.part] || 'another column'}.` : 'The file has it under another column.');
    case 'wrong_precinct':
      return `On the scan this value is under precinct ${f.precinct}. ` +
        (sib ? `The file has it under precinct ${sib.precinct}.` : 'The file has it under another precinct.');
    case 'missing_row': return 'The scan has this value. The file has no row for it.';
    case 'extra_row': return 'The file has a row here that is not on the scan.';
    case 'file_row_fails_own_total': return "The parts of this row in the file do not add to the row's own total in the file.";
    default: return 'The file and the scan give different numbers for this one value.';
  }
}

// the report layout: the figures of the row that differ between the file's row and the scan's row (indexes into COLS)
export const differs = f => (f.rv && f.rv.file && f.rv.scan ? COLS.map((_, k) => k).filter(k => f.rv.file[k] !== f.rv.scan[k]) : []);
function reportSentence(store, f, sib) {
  if (f.scan === undefined && f.kind !== 'extra_row') return `The file has ${val(f.file)} under ${pcl(f.precinct)}${f.part && f.part !== 'votes' ? `, ${PART[f.part]}` : ''}. The scan has no value there.`;
  switch (f.kind) {
    case 'wrong_column':
      return `On the scan this vote is under ${PART[f.part] || 'one column'}. ` + (sib ? `The file has it under ${PART[sib.part] || 'another column'}.` : 'The file has it under another column.');
    case 'extra_row': return 'The file has a row here that is not on the scan.';
    case 'missing_row': return 'The scan has this row. The file has no row for it.';
    case 'file_row_fails_own_total': return "The parts of this row in the file do not add to the row's own total in the file.";
    default: {
      const n = differs(f).length;
      return n > 1 ? `The file and the scan give different numbers for ${n} figures of this row.` : 'The file and the scan give different numbers for this one value.';
    }
  }
}
// the status in one plain line; in the report layout a row nothing can decide says why, from the finding's own sums
export function statusLine(store, f) {
  const st = STATUS[f.status] || { line: '' };
  if (!store.report || f.status !== 'cannot_verify') return st.line;
  const rows = f.sums.filter(s => s.kind === 'report_row');
  const both = rows.length > 0 && rows.every(s => s.holds_file && s.holds_scan);
  let t = both ? 'Both rows add up to their own total, and nothing else printed on this page can tell them apart. Left as published.' : st.line;
  if (f.reread_agrees) t += ' The scan was read twice and both readings agree.';
  return t;
}
// the tag on the loupe: the file's value, or the file's values of every figure of the row that differs
export function tagText(store, f) {
  if (f.file === undefined && !(f.rv && f.rv.file)) return 'public file: none';
  const d = store.report ? differs(f) : [];
  if (d.length > 1) return 'public file: ' + d.map(k => `${COL_WORD[COLS[k]]} ${f.rv.file[k] === null || f.rv.file[k] === undefined ? 'none' : fmt(f.rv.file[k])}`).join(' · ');
  return `public file: ${f.file === undefined ? 'none' : fmt(f.file)}`;
}

// the line above the loupe: page, contest, row label, precinct (report layout: page, precinct, contest, row label)
export const contextLine = (store, f) => (store.report
  ? [f.page ? `Page ${f.page}` : null, f.precinct ? pcl(f.precinct) : null, f.office, f.row].filter(Boolean).join(' · ')
  : [f.page ? `Page ${f.page}` : null, f.office, f.row, f.precinct ? pcl(f.precinct) : null].filter(Boolean).join(' · '));

export function renderFindingCard(root, store, f, { onCrop, onEvidence }) {
  root.replaceChildren();
  root.className = 'card finding';
  root.setAttribute('aria-label', 'Selected finding');
  const kind = KIND[f.kind] || { word: f.kind, glyph: '' };
  const st = STATUS[f.status] || { word: f.status, glyph: '', line: '' };
  const title = [f.row, f.precinct ? pcl(f.precinct) : null, PART[f.part]].filter(Boolean).join(' · ');
  const h = el('h2', '', title);
  h.title = [f.office, f.page ? `page ${f.page}` : null, title].filter(Boolean).join(' · ');   // the full label is in the loupe's caption
  root.append(h);
  if (store.report && f.rv) root.append(reportValues(f));
  const pair = el('div', 'two-values');
  for (const [label, n, cls] of store.report && f.rv ? [] : [['Public file', f.file, 'file'], ['Scan', f.scan, 'scan']]) {
    const d = el('div', 'one ' + cls);
    d.append(el('span', 'lab', label), el('span', 'fig', val(n)));
    if (n === undefined || n === null) d.firstChild.after(Object.assign(el('span', 'sr', ': none')));
    pair.append(d);
  }
  if (pair.children.length) root.append(pair);
  const k = el('p', 'kind');
  k.append(el('span', 'lab', 'Kind of slip'), el('span', 'kg', kind.glyph), el('span', 'kw', kind.word));
  k.querySelector('.kg').setAttribute('aria-hidden', 'true');
  root.append(k, el('p', 'sentence', sentence(store, f)));
  const status = el('p', 'status ' + (f.status === 'settled_against_file' ? 'ok' : 'open'));
  status.append(hid(el('span', 'sg', st.glyph)), statusLine(store, f));
  root.append(status);
  root.append(el('p', 'person', UNCONFIRMED));
  if (f.reread_disagrees) {
    root.append(el('p', 'how', `A closer look at this one value read ${val(f.reread_value)}. The printed sums decide.`));
  }
  const btns = el('div', 'btns');
  const crop = el('button', '', 'Open crop'), ev = el('button', '', 'Evidence file');
  crop.type = ev.type = 'button';
  crop.addEventListener('click', () => onCrop(f, crop));
  ev.addEventListener('click', () => onEvidence(f, ev));
  btns.append(crop, ev);
  root.append(btns);
}

// the row's four figures, the file's and the scan's, each in a line; the figures that differ are the strong ones
function reportValues(f) {
  const box = el('div', 'two-values rep');
  const head = el('div', 'rv head');
  head.setAttribute('aria-hidden', 'true');
  head.append(el('span', 'lab', ''), ...COLS.map(c => el('span', 'colh', COL_WORD[c])));
  box.append(head);
  const d = new Set(differs(f));
  for (const [label, row, cls] of [['Public file', f.rv.file, 'file'], ['Scan', f.rv.scan, 'scan']]) {
    const line = el('div', `rv one ${cls}`);
    line.setAttribute('role', 'group'); line.setAttribute('aria-label', label);
    line.append(el('span', 'lab', label));
    COLS.forEach((c, k) => {
      const g = el('span', 'fg' + (d.has(k) ? ' d' : ''));
      g.append(el('span', 'sr', `${COL_WORD[c]} `), document.createTextNode(row ? val(row[k]) : '—'));
      if (d.has(k)) g.append(el('span', 'sr', ' (differs)'));
      line.append(g);
    });
    box.append(line);
  }
  return box;
}

// ---- the dialog: the group's crop with the sums in words, or the finding's evidence
export class Dialog {
  constructor(root) {
    this.root = root; this.title = root.querySelector('.dlg-title'); this.body = root.querySelector('.dlg-body');
    this.opener = null; this.evidence = null;
    root.querySelector('.dlg-close').addEventListener('click', () => root.close());
    root.addEventListener('close', () => { if (this.opener && this.opener.isConnected) this.opener.focus(); this.opener = null; });
    root.addEventListener('click', e => { if (e.target === root) root.close(); });   // a click on the backdrop
  }
  open(title, nodes, opener) {
    this.opener = opener || document.activeElement;
    this.title.textContent = title;
    this.body.replaceChildren(...nodes);
    if (!this.root.open) this.root.showModal();
    this.root.querySelector('.dlg-close').focus();
  }
  crop(store, f, opener) {
    const g = store.groupById.get(f.group);
    const nodes = [];
    if (g && g.crop) {
      const fig = el('figure', 'dlg-fig');
      const img = el('img');
      img.src = g.crop;
      img.alt = `The scan around ${f.row || 'the row'}, ${pcl(f.precinct)}, as cropped by the audit`;
      fig.append(img);
      nodes.push(fig);
    } else nodes.push(el('p', 'dlg-note', 'No crop was saved for this group.'));
    nodes.push(el('p', 'dlg-note', 'The scan is the source. Add the figures up yourself.'));
    for (const s of f.sums) {
      const d = el('div', 'dlg-sum');
      d.append(el('h3', '', cap(s.name)));
      const ul = el('ul');
      ul.append(el('li', '', `With the public file's value it adds to ${val(s.with_file)}, and ${s.holds_file ? 'matches' : 'does not match'}.`));
      ul.append(el('li', '', `With the scan's value it adds to ${val(s.with_scan)}, and ${s.holds_scan ? 'matches' : 'does not match'}.`));
      ul.append(el('li', '', `The printed total (${s.label || 'printed'}) is ${val(s.printed)}.`));
      d.append(ul);
      nodes.push(d);
    }
    this.open(`Crop · ${[f.row, f.precinct ? pcl(f.precinct) : null, PART[f.part]].filter(Boolean).join(' · ')}`, nodes, opener);
  }
  async evidenceFile(store, f, opener) {
    const fd = store.fd;
    const p = el('p', 'dlg-note', `Finding ${f.id} in ${fd.path || 'the run\'s findings.json'}`);
    const pre = el('pre', 'dlg-pre');
    pre.tabIndex = 0;
    pre.setAttribute('aria-label', `The evidence for finding ${f.id}, as recorded`);
    pre.textContent = 'Loading…';
    this.open('Evidence file', [p, pre], opener);
    try {
      if (!this.evidence || this.evidence.file !== fd.evidence) {
        const r = await fetch(fd.evidence);
        if (!r.ok) throw new Error(String(r.status));
        this.evidence = { file: fd.evidence, doc: await r.json() };
      }
      const rec = this.evidence.doc.findings.find(x => x.id === f.id);
      pre.textContent = rec ? JSON.stringify(rec, null, 2) : `No record of ${f.id} in ${fd.path}.`;
    } catch (e) {
      pre.textContent = `Couldn't load ${fd.evidence}. Open ${fd.path} in the repository instead.`;
    }
  }
}

// ---- the headline strip: the count line, figures in the typewriter face, the settled figure the strongest
export const countsOf = items => ({
  all: items.length,
  settled: items.filter(f => f.status === 'settled_against_file').length,
  cannot: items.filter(f => f.status === 'cannot_verify').length,
  doc: items.filter(f => f.status === 'document_inconsistent').length,
  confirmed: items.filter(f => f.confirmed_by_person).length,
});
// the parts of the line; `doc` is left out when it is zero in the full count, so the line keeps its shape while counting up
export function renderHeadline(root, c, { withDoc = c.doc > 0 } = {}) {
  root.replaceChildren();
  root.dataset.doc = withDoc ? '1' : '0';
  const part = (key, n, words, cls = '') => {
    const s = el('span', 'hl-part');
    s.append(el('span', 'hl-n ' + (cls || key), fmt(n)), ` ${words}`);
    s.firstChild.dataset.key = key;
    return s;
  };
  const parts = [part('all', c.all, c.all === 1 ? 'disagreement' : 'disagreements'),
                 part('settled', c.settled, STATUS.settled_against_file.count, 'settled'),
                 part('cannot', c.cannot, STATUS.cannot_verify.count)];
  if (withDoc) parts.push(part('doc', c.doc, STATUS.document_inconsistent.count));
  parts.push(part('confirmed', c.confirmed, 'confirmed by a person'));
  parts.forEach((p, i) => { if (i) root.append(el('span', 'hl-dot', ' · ')); root.append(p); });
}
// sets the figures of a strip already drawn
export function setHeadline(root, c) {
  for (const n of root.querySelectorAll('.hl-n')) if (c[n.dataset.key] !== undefined) n.textContent = fmt(c[n.dataset.key]);
}

// ---- the list
const rowOf = f => (f.precinct ? pcl(f.precinct) : '');

export class FindingList {
  constructor(root, store, { onPick, none = false, countEl, filterEl, statusEl }) {
    this.root = root; this.store = store; this.onPick = onPick; this.countEl = countEl; this.filterEl = filterEl; this.statusEl = statusEl;
    this.all = none ? [] : store.items;
    this.fs = new Set(); this.fk = new Set();   // filters: statuses, kinds
    this.cur = null; this.sel = null; this.rows = []; this.vis = [];
    root.onkeydown = e => this.keys(e);
    root.onfocus = () => this.mark(true);
    root.onclick = e => { const li = e.target.closest('li[data-id]'); if (li) { this.cur = li.dataset.id; this.mark(); this.pick(); } };
    this.scroller = null;
    this.onScroll = () => { if (this.virtual) this.paint(); };
    addEventListener('scroll', this.onScroll, true);
    addEventListener('resize', this.onScroll);
    this.counts(); this.chips(); this.build();
  }
  destroy() { removeEventListener('scroll', this.onScroll, true); removeEventListener('resize', this.onScroll); }

  counts() {
    if (!this.store.fd) { this.countEl.textContent = ''; return; }
    renderHeadline(this.countEl, countsOf(this.all));
  }

  chips() {
    const box = this.filterEl;
    box.replaceChildren();
    const mk = (set, key, label, group) => {
      const b = el('button', 'chip', label);
      b.type = 'button'; b.setAttribute('aria-pressed', 'false'); b.dataset.key = key;
      b.addEventListener('click', () => {
        if (set.has(key)) set.delete(key); else set.add(key);
        b.setAttribute('aria-pressed', String(set.has(key)));
        this.build();
      });
      group.append(b);
    };
    const present = (list, f) => list.filter(x => this.all.some(i => f(i) === x));
    const sg = el('div', 'chips'), kg = el('div', 'chips');
    sg.setAttribute('role', 'group'); sg.setAttribute('aria-label', 'Filter by status');
    kg.setAttribute('role', 'group'); kg.setAttribute('aria-label', 'Filter by kind of slip');
    for (const s of present(STATUSES, i => i.status)) mk(this.fs, s, STATUS[s].word, sg);
    for (const k of present(KINDS, i => i.kind)) mk(this.fk, k, KIND[k].word, kg);
    box.append(...[sg, kg].filter(g => g.children.length));
  }

  // the rows to show: a group line, then one line per finding of the group that passes the filters
  build() {
    const keep = f => (!this.fs.size || this.fs.has(f.status)) && (!this.fk.size || this.fk.has(f.kind));
    const byGroup = new Map();
    for (const f of this.all) { if (!keep(f)) continue; if (!byGroup.has(f.group)) byGroup.set(f.group, []); byGroup.get(f.group).push(f); }
    this.rows = []; this.vis = [];
    for (const [gid, fs] of byGroup) {
      const g = this.store.groupById.get(gid);
      this.rows.push({ g: g || { id: gid, kind: fs[0].kind, row: fs[0].row, precincts: [fs[0].precinct] }, fs, h: 40 });
      for (const f of fs) { this.rows.push({ f, h: 36 }); this.vis.push(f.id); }
    }
    let y = 0;
    for (const r of this.rows) { r.y = y; y += r.h; }
    this.total = y;
    this.virtual = this.rows.length > VIRTUAL_ABOVE;
    this.root.classList.toggle('virtual', this.virtual);
    this.root.style.height = this.virtual ? `${this.total}px` : '';
    if (!this.vis.includes(this.cur)) this.cur = this.vis.includes(this.sel) ? this.sel : this.vis[0] || null;
    this.paint();
    if (this.statusEl) {
      const filtered = this.fs.size || this.fk.size;
      this.statusEl.textContent = filtered ? `Showing ${fmt(this.vis.length)} of ${fmt(this.all.length)}` : '';
    }
  }

  // which rows are in the page: all of them, or (long lists) those within a screen of the viewport
  paint() {
    let list = this.rows;
    if (this.virtual) {
      const r = this.root.getBoundingClientRect();
      const panel = this.root.closest('.panel');
      const sc = panel && panel.scrollHeight > panel.clientHeight + 1 ? panel.getBoundingClientRect() : { top: 0, bottom: innerHeight };
      const y0 = Math.max(0, sc.top - r.top) - 400, y1 = sc.bottom - r.top + 400;
      const curRow = this.rows.find(x => x.f && x.f.id === this.cur);
      list = this.rows.filter(x => (x.y + x.h >= y0 && x.y <= y1) || x === curRow);
    }
    this.root.replaceChildren(...list.map(r => this.li(r)));
    this.mark();
    this.shown = list.length;
  }

  li(r) {
    const li = el('li');
    if (this.virtual) { li.style.position = 'absolute'; li.style.top = `${r.y}px`; li.style.height = `${r.h}px`; li.style.left = li.style.right = '0'; }
    if (r.g) {
      const g = r.g, k = KIND[g.kind] || { word: g.kind, glyph: '' };
      li.className = 'grp'; li.setAttribute('role', 'presentation');
      const pr = g.precincts && g.precincts.length ? (g.precincts.length === 1 ? pcl(g.precincts[0]) : `precincts ${g.precincts.join(', ')}`) : '';
      li.append(hid(el('span', 'kg', k.glyph)), el('span', 'kw', k.word), el('span', 'rl', g.row || ''), el('span', 'pc', pr));
      return li;
    }
    const f = r.f, st = STATUS[f.status] || { word: f.status, glyph: '' };
    li.id = `finding-${f.id}`; li.dataset.id = f.id; li.className = 'fnd';
    li.setAttribute('role', 'option');
    li.setAttribute('aria-selected', String(f.id === this.sel));
    li.setAttribute('aria-label', `${KIND[f.kind] ? KIND[f.kind].word : f.kind}, ${f.row || ''}, ${rowOf(f)}, ${PART[f.part] || ''}. Public file ${valWords(f.file)}, scan ${valWords(f.scan)}. ${st.word}.`);
    li.append(el('span', 'wh', [f.precinct ? pcl(f.precinct) : null, PART[f.part]].filter(Boolean).join(' · ')));
    const v = el('span', 'vs');
    v.append(el('span', 'fv', val(f.file)), el('span', 'ar', '→'), el('span', 'sv', val(f.scan)));
    li.append(v);
    const s = el('span', 'st ' + (f.status === 'settled_against_file' ? 'ok' : 'open'));
    s.append(hid(el('span', 'sg', st.glyph)), st.word);
    li.append(s);
    return li;
  }

  keys(e) {
    const n = this.vis.length;
    if (!n) return;
    let i = Math.max(0, this.vis.indexOf(this.cur));
    if (e.key === 'ArrowDown') i = Math.min(n - 1, i + 1);
    else if (e.key === 'ArrowUp') i = Math.max(0, i - 1);
    else if (e.key === 'Home') i = 0;
    else if (e.key === 'End') i = n - 1;
    else if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); this.pick(); return; }
    else return;
    e.preventDefault();
    this.cur = this.vis[i];
    this.mark();
  }
  mark(scroll = false) {
    this.root.querySelectorAll('li.cur').forEach(x => x.classList.remove('cur'));
    const li = this.root.querySelector(`li[data-id="${this.cur}"]`);
    if (!li) { this.root.removeAttribute('aria-activedescendant'); return; }
    li.classList.add('cur');
    this.root.setAttribute('aria-activedescendant', li.id);
    if (scroll || document.activeElement === this.root) li.scrollIntoView({ block: 'nearest' });
  }
  pick() { const f = this.store.itemById.get(this.cur); if (f) this.onPick(f); }
  // the finding that is selected (null: none, a value of the sheet that is not a finding)
  select(id) {
    this.sel = id;
    if (id && this.vis.includes(id)) this.cur = id;
    for (const li of this.root.querySelectorAll('li[data-id]')) li.setAttribute('aria-selected', String(li.dataset.id === id));
    this.mark();
  }
}

// the seconds the run took: a run that was resumed counts the runs it resumed too, and when one of them did not record its
// seconds there is no honest figure (undefined)
export const runSeconds = info => (info.resumed_from ? info.seconds_total : info.seconds);

// ---- the run's numbers, and the sentence about the reader
export function runFigures(fd) {
  const f = fd.figures || {}, info = fd.run_info || {};
  const out = [];
  const add = (label, n, unit) => { if (n !== undefined && n !== null) out.push([label, n, unit]); };
  add('cells audited', f.cells, 'cells');
  add('right on first read', f.right_first, 'cells');
  add('right after re-reads', f.right_after, f.right_after === 1 ? 'cell' : 'cells');
  add('re-read', f.reread, f.reread === 1 ? 'cell' : 'cells');
  add('disagreements', f.disagreements, 'values');
  add('settled', f.settled, 'values');
  if (info.metered_cost_estimate !== undefined) out.push(['model cost', `$${Number(info.metered_cost_estimate).toFixed(2)}`, 'US dollars']);
  const secs = runSeconds(info);
  if (secs !== undefined) out.push(['minutes', (secs / 60).toFixed(1), 'min']);
  return out.map(([label, n, unit]) => [label, typeof n === 'number' ? fmt(n) : n, unit]);
}

export function readerSentence(fd) {
  const info = fd.run_info || {}, s = info.sample;
  if (!s || !info.reader || s.row_sums === undefined || s.failing === undefined || !s.sampled_with) return '';
  const pages = [...new Set((s.blocks || []).map(b => (/^p(\d+)-/.exec(b) || [])[1]).filter(Boolean))];
  const what = !s.blocks ? 'A sample' : pages.length === 1 && pages[0] === '1' ? 'A sample of the first page' : 'A sample of a few pages';   // the run may not say which pages
  return `${what} read with ${s.sampled_with} failed ${fmt(s.failing)} of ${fmt(s.row_sums)} row sums, so this county was read with ${info.reader}.`;
}

export function renderRun(root, fd) {
  root.replaceChildren();
  if (!fd) return;
  const rows = runFigures(fd);
  if (rows.length) {
    const dl = el('dl', 'nums');
    for (const [label, n, unit] of rows) {
      const d = el('div');
      d.append(el('dt', '', label), el('dd', '', n), el('dd', 'unit', unit));
      dl.append(d);
    }
    root.append(el('h2', '', 'Run numbers'), dl);
  }
  const s = readerSentence(fd);
  if (s) root.append(el('p', 'reader', s));
}
