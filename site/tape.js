// The adding-machine tape: prints a sum line by line, ending on the printed total.
import { fmt } from './data.js';

const MAX_TOTAL_MS = 900, STEP_MS = 60;
const termLabel = (c, t) => (c.k === 'col' ? t.r : `Precinct ${t.c}`);
const heading = c => c.k === 'col' ? `Down the column · precinct ${c.y}` : c.k === 'row' ? `Across the row · ${c.y}` : 'Across the small totals';

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

export class Tape {
  constructor(root, reduced, onPick = () => {}) {
    this.onPick = onPick; this.root = root; this.reduced = reduced; this.timers = [];
    root.style.clipPath = tornEdge();
    this.clear();
  }
  stop() { this.timers.forEach(clearTimeout); this.timers = []; }
  // keeps its height while empty, so the panel under it does not jump
  clear() { this.stop(); this.root.style.minHeight = `${this.root.offsetHeight}px`; this.root.replaceChildren(); }
  // sums: [{check, axis}]; the lines are built first, then shown one by one
  print(store, sums, animate = true, totalMs = MAX_TOTAL_MS) {
    this.stop();
    this.root.replaceChildren();
    this.root.style.minHeight = '';
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
