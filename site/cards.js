// The county cards: one per county, in the run's order, built from data/index.json only.
import { fmt, plural } from './data.js';

const el = (tag, cls, text) => { const e = document.createElement(tag); if (cls) e.className = cls; if (text !== undefined) e.textContent = text; return e; };

// what a county's card says under its name, from the run's own count
export function cardWords(c) {
  if (c.status === 'unchecked') return "Can't be checked";
  if (c.disagreements === undefined || c.disagreements === null) return null;
  return c.disagreements === 0 ? 'No mismatches' : plural(c.disagreements, 'mismatch', 'mismatches');
}

// one tab stop: the selected card; the arrow keys, Home and End move between the cards, Enter or Space opens the one in focus
export class Cards {
  constructor(box, counties, onPick) {
    this.box = box; this.onPick = onPick; this.tabs = [];
    box.setAttribute('role', 'tablist');
    box.replaceChildren();
    for (const c of counties) {
      const b = el('button', 'ccard');
      b.type = 'button'; b.setAttribute('role', 'tab'); b.dataset.key = c.key; b.tabIndex = -1; b.id = `tab-${c.key}`; b.setAttribute('aria-controls', 'xpanel');
      b.append(el('span', 'cn', c.name));
      const words = cardWords(c);
      if (words) b.append(el('span', 'cw', words));
      const st = c.by_status || {}, n = c.disagreements || 0;
      if (c.status !== 'unchecked' && n > 0) {
        const proven = st.settled_against_file || 0;
        const bar = el('span', 'cbar');
        bar.setAttribute('aria-hidden', 'true');
        const a = el('i', 'proven'); a.style.flexGrow = proven;
        const o = el('i', 'open'); o.style.flexGrow = n - proven;
        bar.append(a, o);
        b.append(bar, el('span', 'sr', `, ${proven} proven by the printed totals, ${n - proven} not proven`));
      }
      b.addEventListener('click', () => this.onPick(c.key));
      b.addEventListener('keydown', e => this.keys(e, b));
      box.append(b);
      this.tabs.push(b);
    }
  }
  keys(e, b) {
    const i = this.tabs.indexOf(b), n = this.tabs.length;
    const to = { ArrowRight: (i + 1) % n, ArrowLeft: (i - 1 + n) % n, Home: 0, End: n - 1 }[e.key];
    if (to === undefined) return;
    e.preventDefault();
    this.tabs[to].focus({ preventScroll: true });
    this.reveal(this.tabs[to]);
  }
  // scrolls the row of cards sideways, never the page
  reveal(b) {
    const box = this.box;
    if (box.scrollWidth <= box.clientWidth) return;
    const a = b.getBoundingClientRect(), c = box.getBoundingClientRect();
    if (a.left < c.left) box.scrollLeft -= c.left - a.left; else if (a.right > c.right) box.scrollLeft += a.right - c.right;
  }
  select(key) {
    for (const b of this.tabs) {
      const on = b.dataset.key === key;
      b.setAttribute('aria-selected', String(on));
      b.tabIndex = on ? 0 : -1;
    }
    const cur = this.tabs.find(b => b.dataset.key === key);
    if (cur) this.reveal(cur);
  }
}

// the empty county: what the data says about its printed sums
export function emptyLine(entry) {
  const sc = entry && entry.sums_check;
  if (!sc || sc.in_all === undefined || sc.holding_with_published === undefined) return 'No mismatches found.';
  if (sc.holding_with_published !== sc.in_all) return `No mismatches found. ${fmt(sc.holding_with_published)} of ${fmt(sc.in_all)} printed sums agree with the published file.`;
  const pages = entry.pages ? ` on this county's ${plural(entry.pages, 'page', 'pages')}` : '';
  return `No mismatches found. All ${plural(sc.in_all, 'printed sum', 'printed sums')}${pages} agree with the published file.`;
}
