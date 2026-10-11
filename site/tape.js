// The adding-machine tape: prints a sum line by line, ending on the printed total.
import { fmt } from './data.js';

const MAX_TOTAL_MS = 900, STEP_MS = 60;
const termLabel = (c, t) => (c.k === 'col' ? t.r : `Precinct ${t.c}`);
const heading = c => c.k === 'col' ? `Down the column · precinct ${c.y}` : c.k === 'row' ? `Across the row · ${c.y}` : 'Across the small totals';

export function termLines(store, c) {
  const terms = store.termsOf(c);
  const row = t => ({ label: termLabel(c, t), fig: fmt(t.v) });
  if (terms.length <= 5) return terms.map(row);
  return [...terms.slice(0, 3).map(row), { label: `… ${terms.length - 4} more`, fig: '', more: true }, row(terms[terms.length - 1])];
}

function el(tag, cls, text) {
  const e = document.createElement(tag);
  if (cls) e.className = cls;
  if (text !== undefined) e.textContent = text;
  return e;
}
function line(label, fig, cls) {
  const d = el('div', 'ln' + (cls ? ' ' + cls : ''));
  d.append(el('span', '', label), el('span', '', fig));
  return d;
}

export class Tape {
  constructor(root, reduced) { this.root = root; this.reduced = reduced; this.timers = []; this.clear(); }
  stop() { this.timers.forEach(clearTimeout); this.timers = []; }
  clear() { this.stop(); this.root.replaceChildren(); }
  // sums: [{check, axis}]; the lines are built first, then shown one by one
  print(store, sums, animate = true) {
    this.stop();
    this.root.replaceChildren();
    const steps = [];
    if (!sums.length) { this.root.append(el('p', 'empty', 'No printed sum was recorded through this value.')); return; }
    for (const { check: c } of sums) {
      const box = el('div', 'sum');
      const h = el('h3', '', heading(c));
      box.append(h);
      const mk = (node) => { node.hidden = true; box.append(node); steps.push(node); };
      for (const l of termLines(store, c)) mk(line(l.label, l.fig, l.more ? 'more' : ''));
      mk(line('adds to', fmt(c.co), 'rule'));
      mk(line('printed total', fmt(c.pr)));
      const res = el('div', 'res ' + (c.ok ? 'holds' : 'fails'), c.ok ? '✓ matches' : '✗ does not match');
      mk(res);
      this.root.append(box);
    }
    if (!animate || this.reduced) { steps.forEach(s => (s.hidden = false)); return; }
    const step = Math.min(STEP_MS, MAX_TOTAL_MS / steps.length);
    steps.forEach((s, i) => this.timers.push(setTimeout(() => { s.hidden = false; }, i * step)));
  }
}
