// The adding-machine tape: prints a sum line by line, ending on the printed total.
import { fmt } from './data.js';

const MAX_TOTAL_MS = 900, STEP_MS = 60;
const termLabel = (c, t) => (c.k === 'col' ? t.r : c.k === 'grand_row' ? t.c : `Precinct ${t.c}`);
const heading = c => c.k === 'col' ? `Down the column · precinct ${c.y}` : c.k === 'row' ? `Across the row · ${c.y}`
  : c.k === 'grand_row' ? 'Down the row totals' : 'Across the small totals';
const kindLabel = (kind, v) => (kind === 'col' ? v.r : kind === 'row' ? `Precinct ${v.c}` : kind === 'grand_row' ? v.c : `Precinct ${v.c}`);
// a short heading for a deciding sum; its whole name is in the card under "Decided by"
const sumHeading = (s, f, store) => {
  const v = f.ref === undefined ? null : store.values[f.ref];
  return s.kind === 'col' ? `Down the column${v && !store.isTotal(v) ? ` · precinct ${v.c}` : f.precinct ? ` · precinct ${f.precinct}` : ''}`
    : s.kind === 'row' ? `Across the row${v && v.r ? ` · ${v.r}` : ''}`
    : s.kind === 'grand_row' ? 'Down the row totals' : 'Across the small totals';
};
const val = n => (n === undefined || n === null ? '—' : fmt(n));
const cap = s => (s ? s[0].toUpperCase() + s.slice(1) : s);

export function termLines(store, c) {
  const terms = store.termsOf(c);
  const row = t => ({ label: termLabel(c, t), fig: fmt(t.v), i: t.i });
  if (terms.length <= 5) return terms.map(row);
  return [...terms.slice(0, 3).map(row), { label: `… ${terms.length - 4} more`, fig: '', more: true }, row(terms[terms.length - 1])];
}

// a fine zigzag along the lower edge, 6 px deep
function tornEdge() {
  const pts = ['0 0', '100% 0', '100% calc(100% - 6px)'];
  const n = 50;
  for (let i = n - 1; i >= 0; i--) pts.push(`${(i * 100 / n).toFixed(2)}% ${i % 2 ? 'calc(100% - 6px)' : '100%'}`);
  return `polygon(${pts.join(', ')})`;
}

function el(tag, cls, text) {
  const e = document.createElement(tag);
  if (cls) e.className = cls;
  if (text !== undefined) e.textContent = text;
  return e;
}
function line(label, fig, cls, pick) {
  const d = el('div', 'ln' + (cls ? ' ' + cls : ''));
  d.append(el('span', '', label), el('span', '', fig));
  if (!pick) return d;
  // a term line is a button: it selects its value
  const b = el('button', 'ln pick' + (cls ? ' ' + cls : ''));
  b.type = 'button';
  b.append(...d.children);
  b.addEventListener('click', pick);
  return b;
}

// the lines of a finding's sum, both ways: [{label, file, scan, diff, ref, more}]. `own` is the value the finding sits on.
// Terms hold the scan's value (the ledger's); the file's column swaps in the file's value at the term that differs.
export function pairLines(store, f, s) {
  const own = f.ref;
  const rows = s.terms.map(([ref, val]) => {
    const v = ref === null || ref === undefined ? null : store.values[ref];
    const diff = own !== undefined && ref === own;
    return { label: v ? kindLabel(s.kind, v) : '…', scan: fmt(val), file: diff ? (f.file === undefined ? '—' : fmt(f.file)) : fmt(val), diff, ref: v ? ref : undefined };
  });
  if (!rows.some(r => r.diff) && f.kind === 'extra_row' && f.file !== undefined) {
    // a row only the file has: no term of the scan's sum is it
    rows.push({ label: 'file only', scan: '—', file: fmt(f.file), diff: true });
  }
  if (rows.length <= 6) return rows;
  const keep = new Set([0, 1, rows.length - 1]);
  rows.forEach((r, i) => { if (r.diff) keep.add(i); });
  const out = []; let gap = 0;
  rows.forEach((r, i) => {
    if (keep.has(i)) { if (gap) { out.push({ label: `… ${gap} more`, scan: '', file: '', more: true }); gap = 0; } out.push(r); } else gap++;
  });
  return out;
}

export class Tape {
  constructor(root, reduced, onPick = () => {}) {
    this.onPick = onPick; this.root = root; this.reduced = reduced; this.timers = [];
    root.style.clipPath = tornEdge();
    this.clear();
  }
  stop() { this.timers.forEach(clearTimeout); this.timers = []; }
  // keeps its height while empty, so the panel under it does not jump
  clear() { this.stop(); this.root.style.minHeight = `${this.root.offsetHeight}px`; this.root.replaceChildren(); }
  // a finding: each deciding sum printed twice side by side (the public file's value, the scan's value), then the other
  // sums through the value, quieter. Steps are rows of the pair, 60 ms each, as for a single sum.
  printFinding(store, f, others, animate = true, totalMs = MAX_TOTAL_MS) {
    this.stop();
    this.root.replaceChildren();
    this.root.style.minHeight = '';
    this.root.classList.add('two');
    const steps = [];
    const mk = (box, node) => { node.style.visibility = 'hidden'; box.append(node); steps.push(node); };
    const pair = (cls, a, b, pick) => {
      const row = el('div', 'pair' + (cls ? ' ' + cls : ''));
      for (const side of [a, b]) {
        const cell = el('div', 'ln' + (side.diff ? ' diff' : '') + (side.cls ? ' ' + side.cls : ''));
        const lab = el('span', '', side.label);
        if (side.diff) lab.append(el('span', 'sr', ' (differs)'));
        cell.append(lab, el('span', '', side.fig));
        if (pick && side.ref !== undefined) {
          const bt = el('button', 'ln pick' + (side.diff ? ' diff' : ''));
          bt.type = 'button'; bt.append(...cell.children);
          bt.addEventListener('click', () => this.onPick(side.ref));
          row.append(bt);
        } else row.append(cell);
      }
      return row;
    };
    if (!f.sums.length) this.root.append(el('p', 'empty', 'No printed sum was recorded through this value.'));
    for (const s of f.sums) {
      const box = el('div', 'sum two');
      box.append(el('h3', '', sumHeading(s, f, store)));
      const heads = el('div', 'pair heads');
      heads.append(el('h4', '', "With the public file's value"), el('h4', '', "With the scan's value"));
      box.append(heads);
      for (const l of pairLines(store, f, s)) {
        const cls = l.more ? 'more' : '';
        mk(box, pair(cls, { label: l.label, fig: l.file, diff: l.diff, ref: l.ref, cls }, { label: l.label, fig: l.scan, diff: l.diff, ref: l.ref, cls }, true));
      }
      mk(box, pair('rule', { label: 'adds to', fig: fmt(s.with_file) }, { label: 'adds to', fig: fmt(s.with_scan) }));
      // when the value the finding sits on is this sum's printed total, the file's column carries the file's value there
      const ownIsPrinted = f.ref !== undefined && store.isTotal(store.values[f.ref]) && !s.terms.some(t => t[0] === f.ref);
      mk(box, pair('', { label: 'printed total', fig: ownIsPrinted ? val(f.file) : fmt(s.printed), diff: ownIsPrinted },
                       { label: 'printed total', fig: fmt(s.printed), diff: ownIsPrinted }));
      const res = el('div', 'pair res2');
      for (const holds of [s.holds_file, s.holds_scan]) res.append(el('div', 'res ' + (holds ? 'holds' : 'fails'), holds ? '✓ matches' : '✗ does not match'));
      mk(box, res);
      this.root.append(box);
    }
    if (others.length) {
      const more = el('div', 'others');
      more.append(el('h3', '', 'Other printed sums through this value'));
      this.root.append(more);
      for (const { check: c } of others) {
        const box = el('div', 'sum quiet');
        box.append(el('h3', '', heading(c)));
        const sub = el('div', 'one');
        for (const l of termLines(store, c)) sub.append(line(l.label, l.fig, l.more ? 'more' : '', null));
        sub.append(line('adds to', fmt(c.co), 'rule'), line('printed total', fmt(c.pr)),
                   el('div', 'res ' + (c.ok ? 'holds' : 'fails'), c.ok ? '✓ matches' : '✗ does not match'));
        box.append(sub);
        mk(more, box);
      }
    }
    if (!animate || this.reduced) { steps.forEach(s => (s.style.visibility = '')); return; }
    const step = Math.min(STEP_MS, totalMs / steps.length);
    steps.forEach((s, i) => this.timers.push(setTimeout(() => { s.style.visibility = ''; }, i * step)));
  }

  // sums: [{check, axis}]; the lines are built first, then shown one by one
  print(store, sums, animate = true, totalMs = MAX_TOTAL_MS) {
    this.stop();
    this.root.replaceChildren();
    this.root.style.minHeight = '';
    this.root.classList.remove('two');
    const steps = [];
    if (!sums.length) { this.root.append(el('p', 'empty', 'No printed sum was recorded through this value.')); return; }
    for (const { check: c } of sums) {
      const box = el('div', 'sum');
      const h = el('h3', '', heading(c));
      box.append(h);
      const mk = (node) => { node.style.visibility = 'hidden'; box.append(node); steps.push(node); };
      for (const l of termLines(store, c)) mk(line(l.label, l.fig, l.more ? 'more' : '', l.i === undefined ? null : () => this.onPick(l.i)));
      mk(line('adds to', fmt(c.co), 'rule'));
      mk(line('printed total', fmt(c.pr)));
      mk(el('div', 'res ' + (c.ok ? 'holds' : 'fails'), c.ok ? '✓ matches' : '✗ does not match'));
      this.root.append(box);
    }
    if (!animate || this.reduced) { steps.forEach(s => (s.style.visibility = '')); return; }
    const step = Math.min(STEP_MS, totalMs / steps.length);
    steps.forEach((s, i) => this.timers.push(setTimeout(() => { s.style.visibility = ''; }, i * step)));
  }
}
