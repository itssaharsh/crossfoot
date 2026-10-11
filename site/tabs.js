// The county tabs in the top bar and the line for the whole run. Both are built from data/index.json only.
import { fmt } from './data.js';

const el = (tag, cls, text) => { const e = document.createElement(tag); if (cls) e.className = cls; if (text !== undefined) e.textContent = text; return e; };
const NOT_CHECKED_WORD = 'not checked';

// one tab per county, in the run's order: the name and its number of disagreements (a dash when the run did not check it).
// One tab stop: the selected tab; the arrow keys, Home and End move between the tabs, Enter or Space opens the one in focus.
export class Tabs {
  constructor(nav, counties, onPick) {
    this.nav = nav; this.onPick = onPick; this.tabs = [];
    nav.setAttribute('role', 'tablist');
    nav.replaceChildren();
    for (const c of counties) {
      const b = el('button', 'tab');
      b.type = 'button'; b.setAttribute('role', 'tab'); b.dataset.key = c.key; b.tabIndex = -1;
      const checked = c.status !== 'unchecked' && c.disagreements !== undefined && c.disagreements !== null;
      b.append(el('span', 'tw', c.name), ' ');
      if (checked) b.append(el('span', 'tn', fmt(c.disagreements)));
      else { b.append(el('span', 'tn dash', '–')); b.append(el('span', 'sr', ` ${NOT_CHECKED_WORD}`)); }
      b.addEventListener('click', () => this.onPick(c.key));
      b.addEventListener('keydown', e => this.keys(e, b));
      nav.append(b);
      this.tabs.push(b);
    }
    nav.hidden = counties.length < 2;
  }
  keys(e, b) {
    const i = this.tabs.indexOf(b), n = this.tabs.length;
    const to = { ArrowRight: (i + 1) % n, ArrowLeft: (i - 1 + n) % n, Home: 0, End: n - 1 }[e.key];
    if (to === undefined) return;
    e.preventDefault();
    this.tabs[to].focus();
    this.tabs[to].scrollIntoView({ block: 'nearest', inline: 'nearest' });
  }
  // the county on show: the one tab stop
  select(key) {
    for (const b of this.tabs) {
      const on = b.dataset.key === key;
      b.setAttribute('aria-selected', String(on));
      b.tabIndex = on ? 0 : -1;
    }
    const cur = this.tabs.find(b => b.dataset.key === key);
    if (cur && this.nav.scrollWidth > this.nav.clientWidth) cur.scrollIntoView({ block: 'nearest', inline: 'nearest' });
  }
}

// "8 counties · 7 read · 228 disagreements · ..." from index.json's totals; nothing for a build of one county
export function renderRunLine(root, index) {
  root.replaceChildren();
  const t = index.totals, cs = index.counties || [];
  if (!t || cs.length < 2) { root.hidden = true; return; }
  const parts = [];
  const part = (n, words, tail = '') => {
    if (n === undefined || n === null) return;
    const s = el('span', 'rl-part');
    s.append(el('span', 'rl-n', fmt(n)), ` ${words}`);
    if (tail) s.append(tail);
    parts.push(s);
  };
  part(t.counties, t.counties === 1 ? 'county' : 'counties');
  part(t.read, 'read');
  part(t.findings, t.findings === 1 ? 'disagreement' : 'disagreements');
  part(t.settled, 'settled by the printed totals');
  part(t.confirmed, 'confirmed by a person');
  if (t.sums_in_all !== undefined) {
    const s = el('span', 'rl-part');
    s.append(el('span', 'rl-n', fmt(t.sums_in_all)), ' printed sums');
    const holds = [];
    if (t.holding_published !== undefined) { const h = el('span', 'rl-sub'); h.append(el('span', 'rl-n', fmt(t.holding_published)), ' hold with the published files'); holds.push(h); }
    if (t.holding_corrected !== undefined) { const h = el('span', 'rl-sub'); h.append(el('span', 'rl-n', fmt(t.holding_corrected)), ' with the corrected'); holds.push(h); }
    if (holds.length) { s.append(': '); holds.forEach((h, i) => { if (i) s.append(', '); s.append(h); }); }
    parts.push(s);
  }
  parts.forEach((p, i) => { if (i) root.append(el('span', 'rl-dot', ' · ')); root.append(p); });
  root.hidden = !parts.length;
}

// the empty county: what the data says about its printed sums
export function emptyLine(entry) {
  const sc = entry && entry.sums_check;
  if (!sc || sc.in_all === undefined || sc.holding_with_published === undefined) return '';
  return `${fmt(sc.holding_with_published)} of ${fmt(sc.in_all)} printed sums hold with the published file.`;
}
