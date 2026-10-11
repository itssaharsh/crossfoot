// The findings: the panel for one finding, the list with its filter, and the crop and evidence dialogs.
import { fmt, KIND, STATUS, PART, UNCONFIRMED, COLS, COL_WORD, pcl, cap } from './data.js';
import { pairRows } from './tape.js';

const el = (tag, cls, text) => { const e = document.createElement(tag); if (cls) e.className = cls; if (text !== undefined) e.textContent = text; return e; };
const hid = e => { e.setAttribute('aria-hidden', 'true'); return e; };
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

// the tag on the loupe: the file's value, or the file's values of every figure of the row that differs
export function tagText(store, f) {
  if (f.file === undefined && !(f.rv && f.rv.file)) return 'public file: none';
  const d = store.report ? differs(f) : [];
  if (d.length > 1) return 'public file: ' + d.map(k => `${COL_WORD[COLS[k]]} ${f.rv.file[k] === null || f.rv.file[k] === undefined ? 'none' : fmt(f.rv.file[k])}`).join(' · ');
  return `public file: ${f.file === undefined ? 'none' : fmt(f.file)}`;
}

// where the finding is, in plain words: "Precinct 18 · early voting", and the row as printed on the scan with its page
export const placeOf = f => cap([f.precinct ? pcl(f.precinct) : null, PART[f.part]].filter(Boolean).join(' · ') || f.row || 'This value');
export const printedOf = f => [f.office, f.row, f.page ? `page ${f.page}` : null].filter(Boolean).join(' · ');
export const stageLabel = (store, f) =>
  `Page ${f.page} of the scan. Selected: ${placeOf(f)}, ${printedOf(f)}. Public file ${valWords(f.file)}, scan ${valWords(f.scan)}.`;

// ---- the sum, said short: at most five terms, the changed one marked, the rest folded into "…"
const noun = kind => (kind === 'row' || kind === 'report_row' ? 'row' : kind === 'col' || kind === 'report_contest' || kind === 'grand_row' ? 'column' : 'set of totals');
// the sum that decides: the first one that holds with the scan's value and fails with the file's
export const decidingSum = f => f.sums.find(s => s.holds_scan && !s.holds_file) || null;
export function termTokens(store, f, s, side) {
  const rows = pairRows(store, f, s);
  const keep = new Set(rows.map((r, i) => (r.diff ? i : -1)).filter(i => i >= 0).slice(0, 3));
  if (rows.length <= 5) rows.forEach((_, i) => keep.add(i));
  else { keep.add(0); keep.add(rows.length - 1); }
  const out = []; let gap = false;
  rows.forEach((r, i) => {
    if (!keep.has(i)) { gap = true; return; }
    if (gap) { out.push({ t: '…' }); gap = false; }
    out.push({ t: side === 'file' ? r.file : r.scan, diff: r.diff });
  });
  if (gap) out.push({ t: '…' });
  return out;
}
// "4 + 4 + … + 1 + … = 10" as a span, the changed term strong
function sumSpan(tokens, total) {
  const s = el('span', 'terms');
  tokens.forEach((k, i) => {
    if (i) s.append(' + ');
    if (k.diff) s.append(el('strong', 'chg', k.t)); else s.append(k.t);
  });
  s.append(` = ${fmt(total)}`);
  return s;
}
// one plain sentence when nothing decides, from the finding's own sums (else its own reason, cut at the first clause)
export function whyNot(store, f) {
  const sums = f.sums || [];
  let t;
  if (f.status === 'document_inconsistent') t = 'The printed totals on this page disagree with each other, so they cannot say which number is right.';
  else if (sums.length && sums.every(s => s.holds_file && s.holds_scan)) t = 'Every printed sum through this number holds with either value, so the totals cannot tell them apart.';
  else if (sums.length && sums.every(s => !s.holds_file && !s.holds_scan)) t = 'The printed sums through this number fail with either value, so the totals cannot say which is right.';
  else if (sums.length) t = 'The printed sums through this number give the same answer with either value, so they cannot decide.';
  else {
    const r = String(f.reason || '').split(/;|\. /)[0].replace(/[.\s]+$/, '');
    t = r ? `${cap(r)}.` : 'No printed total can decide this one.';
  }
  if (f.reread_agrees) t += ' The scan was read twice and both readings agree.';
  return t;
}

export function renderFindingPanel(root, store, f, { onCrop, onEvidence, details, tapeHost, open, onToggle }) {
  root.replaceChildren();
  const st = STATUS[f.status] || { word: f.status, glyph: '', line: '' };
  const place = el('h3', 'place', placeOf(f));
  place.id = 'place';
  place.tabIndex = -1;
  root.append(place, el('p', 'printed', printedOf(f)));
  if (store.report && f.rv) root.append(reportValues(f));
  else {
    const pair = el('div', 'two-values');
    for (const [label, n, cls] of [['Public file', f.file, 'file'], ['Scan', f.scan, 'scan']]) {
      const d = el('div', 'one ' + cls);
      d.append(el('span', 'lab', label), el('span', 'fig', val(n)));
      if (n === undefined || n === null) d.firstChild.after(el('span', 'sr', ': none'));
      pair.append(d);
    }
    root.append(pair);
  }
  root.append(el('p', 'sentence', sentence(store, f)));
  const status = el('p', 'status ' + (st.proven ? 'ok' : 'open'));
  status.append(hid(el('span', 'sg', st.glyph)), st.line);
  root.append(status);

  const why = el('div', 'why');
  why.append(el('h4', '', 'Why'));
  const ds = decidingSum(f);
  if (st.proven && ds) {
    const own = store.report ? ds.kind === 'report_row' && f.col === 'total' : f.ref !== undefined && store.isTotal(store.values[f.ref]) && !ds.terms.some(t => t[0] === f.ref);
    for (const [who, side, total, holds] of [["scan's", 'scan', ds.with_scan, ds.holds_scan], ["file's", 'file', ds.with_file, ds.holds_file]]) {
      const line = el('p', 'sumline ' + (holds ? 'holds' : 'fails'));
      line.append(el('span', 'who', `With the ${who} number:`), ' ', sumSpan(termTokens(store, f, ds, side), total), ' ');
      line.append(hid(el('span', 'tick', holds ? '✓' : '✗')), el('span', 'sr', holds ? ', matches the printed total' : ', does not match the printed total'));
      why.append(line);
    }
    why.append(el('p', 'printed-total', `printed total ${fmt(ds.printed)}${own && f.file !== undefined ? ` (the file has ${fmt(f.file)})` : ''}`));
  } else why.append(el('p', 'why-not', whyNot(store, f)));
  root.append(why);

  if (f.sums.length) {
    details.open = !!open;
    details.replaceChildren(el('summary', '', 'Show every number'), tapeHost);
    details.ontoggle = () => onToggle(details.open);
    root.append(details);
  }
  root.append(el('p', 'person', UNCONFIRMED));
  const btns = el('div', 'btns');
  const g = store.groupById.get(f.group);
  const ev = el('button', '', 'Evidence (JSON)');
  ev.type = 'button';
  ev.addEventListener('click', () => onEvidence(f, ev));
  if (g && g.crop) {
    const crop = el('button', '', 'Open the full crop');
    crop.type = 'button';
    crop.addEventListener('click', () => onCrop(f, crop));
    btns.append(crop);
  }
  btns.append(ev);
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
    }
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
    this.open('Evidence (JSON)', [p, pre], opener);
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

// ---- the list
const rowOf = f => (f.precinct ? pcl(f.precinct) : '');
export const FILTERS = [['all', 'All'], ['proven', 'Proven'], ['cant', "Can't be proven"]];
const passes = (mode, f) => mode === 'all' || (mode === 'proven') === !!(STATUS[f.status] && STATUS[f.status].proven);

export class FindingList {
  constructor(root, store, { onPick, none = false, filterEl, statusEl, onChange = () => {} }) {
    this.root = root; this.store = store; this.onPick = onPick; this.filterEl = filterEl; this.statusEl = statusEl; this.onChange = onChange;
    this.all = none ? [] : store.items;
    this.mode = 'all';
    this.cur = null; this.sel = null; this.rows = []; this.vis = [];
    root.onkeydown = e => this.keys(e);
    root.onfocus = () => this.mark(true);
    root.onclick = e => { const li = e.target.closest('li[data-id]'); if (li) { this.cur = li.dataset.id; this.mark(); this.pick(); } };
    this.onScroll = () => { if (this.virtual) this.paint(); };
    addEventListener('scroll', this.onScroll, true);
    addEventListener('resize', this.onScroll);
    this.seg(); this.build();
  }
  destroy() { removeEventListener('scroll', this.onScroll, true); removeEventListener('resize', this.onScroll); }

  // All · Proven · Can't be proven; with only one kind of status in the county there is nothing to choose, so no filter
  seg() {
    const box = this.filterEl;
    box.replaceChildren();
    const n = m => this.all.filter(f => passes(m, f)).length;
    const shown = n('proven') > 0 && n('cant') > 0;
    box.hidden = !shown;
    if (!shown) return;
    for (const [m, label] of FILTERS) {
      const b = el('button', 'segb', label);
      b.type = 'button'; b.dataset.mode = m;
      b.setAttribute('aria-pressed', String(m === this.mode));
      b.append(' ', el('span', 'segn', fmt(n(m))));
      b.addEventListener('click', () => {
        this.mode = m;
        for (const x of box.children) x.setAttribute('aria-pressed', String(x.dataset.mode === m));
        this.build();
        this.onChange();
      });
      box.append(b);
    }
  }

  // the rows to show: a group line, then one line per finding of the group that passes the filter
  build() {
    const byGroup = new Map();
    for (const f of this.all) { if (!passes(this.mode, f)) continue; if (!byGroup.has(f.group)) byGroup.set(f.group, []); byGroup.get(f.group).push(f); }
    this.rows = []; this.vis = [];
    for (const [gid, fs] of byGroup) {
      const g = this.store.groupById.get(gid);
      this.rows.push({ g: g || { id: gid, kind: fs[0].kind, row: fs[0].row, precincts: [fs[0].precinct] }, fs, h: 40 });
      for (const f of fs) { this.rows.push({ f, h: 40 }); this.vis.push(f.id); }
    }
    let y = 0;
    for (const r of this.rows) { r.y = y; y += r.h; }
    this.total = y;
    this.virtual = this.rows.length > VIRTUAL_ABOVE;
    this.root.classList.toggle('virtual', this.virtual);
    this.root.style.height = this.virtual ? `${this.total}px` : '';
    if (!this.vis.includes(this.cur)) this.cur = this.vis.includes(this.sel) ? this.sel : this.vis[0] || null;
    this.paint();
    if (this.statusEl) this.statusEl.textContent = this.mode !== 'all' ? `Showing ${fmt(this.vis.length)} of ${fmt(this.all.length)}` : '';
  }

  // which rows are in the page: all of them, or (long lists) those within a screen of the viewport
  paint() {
    let list = this.rows;
    if (this.virtual) {
      const r = this.root.getBoundingClientRect();
      const wrap = this.root.parentElement;
      const sc = wrap && wrap.scrollHeight > wrap.clientHeight + 1 ? wrap.getBoundingClientRect() : { top: 0, bottom: innerHeight };
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
      li.append(hid(el('span', 'kg', k.glyph)), el('span', 'kw', cap(k.word)), el('span', 'rl', g.row || ''), el('span', 'pc', pr));
      return li;
    }
    const f = r.f, st = STATUS[f.status] || { word: f.status, glyph: '' };
    li.id = `finding-${f.id}`; li.dataset.id = f.id; li.className = 'fnd';
    li.setAttribute('role', 'option');
    li.setAttribute('aria-selected', String(f.id === this.sel));
    li.setAttribute('aria-label', `${KIND[f.kind] ? KIND[f.kind].word : f.kind}, ${f.row || ''}, ${rowOf(f)}, ${PART[f.part] || ''}. Public file ${valWords(f.file)}, scan ${valWords(f.scan)}. ${st.word}.`);
    li.append(el('span', 'wh', [f.precinct ? cap(pcl(f.precinct)) : null, PART[f.part]].filter(Boolean).join(' · ')));
    const v = el('span', 'vs');
    v.append(el('span', 'fv', val(f.file)), el('span', 'ar', '→'), el('span', 'sv', val(f.scan)));
    li.append(v);
    const s = el('span', 'st ' + (st.proven ? 'ok' : 'open'));
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
    if (scroll || document.activeElement === this.root) this.reveal(li);
  }
  // scrolls the list's own box, never the page
  reveal(li) {
    const w = this.root.parentElement;
    if (!w || w.scrollHeight <= w.clientHeight) return;
    const a = li.getBoundingClientRect(), b = w.getBoundingClientRect();
    if (a.top < b.top) w.scrollTop -= b.top - a.top; else if (a.bottom > b.bottom) w.scrollTop += a.bottom - b.bottom;
  }
  pick() { const f = this.store.itemById.get(this.cur); if (f) this.onPick(f); }
  // the finding that is selected
  select(id) {
    this.sel = id;
    if (id && this.vis.includes(id)) this.cur = id;
    for (const li of this.root.querySelectorAll('li[data-id]')) li.setAttribute('aria-selected', String(li.dataset.id === id));
    this.mark();
    const li = this.root.querySelector(`li[data-id="${id}"]`);
    if (li) this.reveal(li);
  }
  // the position of a finding among those shown, from 1; 0 when it is not shown
  position(id) { return this.vis.indexOf(id) + 1; }
  at(n) { return this.store.itemById.get(this.vis[n]) || null; }
}

// the seconds the run took: a run that was resumed counts the runs it resumed too, and when one of them did not record its
// seconds there is no honest figure (undefined)
export const runSeconds = info => (info.resumed_from ? info.seconds_total : info.seconds);
