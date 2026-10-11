// The panel's card and the list of sums that do not hold.
import { fmt } from './data.js';

const STATUS = {
  accepted: 'Both printed sums hold.',
  cannot_verify: 'A printed sum through this value does not hold. Not verified.',
};
const el = (tag, cls, text) => { const e = document.createElement(tag); if (cls) e.className = cls; if (text !== undefined) e.textContent = text; return e; };

export function describe(store, v) {
  const b = store.block(v);
  const where = [b && b.contest, b && b.cand].filter(Boolean).join(' · ');
  const what = store.isTotal(v)
    ? (v.r === 'col' ? `Printed total, precinct ${v.c}` : v.r === 'row' ? `Printed row total, ${v.c}` : 'Printed grand total')
    : `${v.r} · precinct ${v.c}`;
  return { where, what };
}

export function renderCard(root, store, v) {
  root.replaceChildren();
  if (!v) return;
  const { where, what } = describe(store, v);
  const b = store.block(v);
  root.append(el('p', 'eyebrow', `${b ? b.contest : ''} · page ${v.p}`));
  root.append(el('h2', '', what));
  if (b && b.cand) root.append(el('p', 'sub', b.cand));
  root.append(el('p', 'big', fmt(v.v)));
  root.append(el('p', 'status', store.isTotal(v) ? 'Printed on the scan.' : STATUS[v.s] || ''));
  if (!store.isTotal(v) && v.m) root.append(el('p', 'how', `Read by ${v.m}. Re-read tries: ${v.n ?? 0}.`));
}

export function stageLabel(store, v, sums) {
  const { where, what } = describe(store, v);
  const s = sums.map(({ check: c }) => `${c.k === 'col' ? 'column' : c.k === 'row' ? 'row' : 'small totals'} sum ${fmt(c.co)}, printed ${fmt(c.pr)}, ${c.ok ? 'holds' : 'does not hold'}`);
  return `Page ${v.p} of the scan. Selected: ${where}, ${what}, value ${fmt(v.v)}. ${s.join('. ')}.`;
}

export class FailList {
  constructor(root, store, onPick, { none = false } = {}) {
    this.root = root; this.store = store; this.onPick = onPick; this.cur = 0; this.sel = null;
    this.items = none ? [] : store.checks.filter(c => !c.ok);
    root.replaceChildren(...this.items.map((c, n) => this.row(c, n)));
    root.onkeydown = e => this.keys(e);
    root.onfocus = () => this.mark();
  }
  row(c, n) {
    const b = this.store.blocks.get(`${c.p}:${c.b}`);
    const li = el('li');
    li.id = `fail-${n}`; li.setAttribute('role', 'option'); li.setAttribute('aria-selected', 'false');
    const lab = c.k === 'col' ? `Precinct ${c.y}` : c.k === 'row' ? `Row ${c.y}` : 'Small totals to grand total';
    li.append(el('span', 'a', lab), el('span', 'b', `printed ${fmt(c.pr)}`),
              el('span', 'c', `Page ${c.p} · ${[b && b.contest, b && b.cand].filter(Boolean).join(' · ')} · adds to ${fmt(c.co)}`));
    li.addEventListener('click', () => { this.cur = n; this.mark(); this.pick(); });
    return li;
  }
  keys(e) {
    const n = this.items.length;
    if (!n) return;
    if (e.key === 'ArrowDown') this.cur = Math.min(n - 1, this.cur + 1);
    else if (e.key === 'ArrowUp') this.cur = Math.max(0, this.cur - 1);
    else if (e.key === 'Home') this.cur = 0;
    else if (e.key === 'End') this.cur = n - 1;
    else if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); this.pick(); return; }
    else return;
    e.preventDefault();
    this.mark();
  }
  mark() {
    const li = this.root.children[this.cur];
    this.root.querySelectorAll('li.cur').forEach(x => x.classList.remove('cur'));
    if (!li) return;
    li.classList.add('cur');
    this.root.setAttribute('aria-activedescendant', li.id);
    li.scrollIntoView({ block: 'nearest' });
  }
  pick() { const c = this.items[this.cur]; if (c) this.onPick(c); }
  // show which sum, if any, the selected value sits on
  follow(sums) {
    const on = new Set(sums.map(s => s.check.i));
    this.items.forEach((c, n) => this.root.children[n].setAttribute('aria-selected', String(on.has(c.i))));
  }
}
