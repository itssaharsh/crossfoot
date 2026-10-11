// Loading site/data/ and the questions the page asks of it. Short keys are documented in crossfoot/sitebuild.py.
export const fmt = n => (n === null || n === undefined ? '' : Number(n).toLocaleString('en-US'));

// the files fetched so far, for the "Loading run…" line
export const progress = { n: 0, on: () => {} };
export const loaded = () => { progress.n++; progress.on(progress.n); };

export async function getJSON(file) {
  let r;
  try { r = await fetch(file); } catch (e) { throw new LoadError(file); }
  if (!r.ok) throw new LoadError(file, r.status === 404);
  let d;
  try { d = await r.json(); } catch (e) { throw new LoadError(file); }
  loaded();
  return d;
}
export class LoadError extends Error { constructor(file, missing = false) { super(file); this.file = file; this.missing = missing; } }
export const loadMessage = file => `Couldn't load ${file}. Reload, or open the repository's runs folder.`;

export const idOf = v => `${v.p}:${v.b}:${v.r}:${v.c}`;
const isTotal = v => v.r === 'col' || v.r === 'row' || v.r === 'grand';

export class Store {
  constructor(d) {
    this.d = d;
    this.values = d.values; this.checks = d.checks; this.pages = d.pages;
    this.blocks = new Map(d.blocks.map(b => [`${b.p}:${b.id}`, b]));
    this.byId = new Map(); this.byPage = new Map();
    d.values.forEach((v, i) => {
      v.i = i; this.byId.set(idOf(v), i);
      if (!this.byPage.has(v.p)) this.byPage.set(v.p, []);
      this.byPage.get(v.p).push(i);
    });
    this.chk = new Map();
    d.checks.forEach((c, i) => { c.i = i; this.chk.set(`${c.k}:${c.p}:${c.b}:${c.y}`, c); });
  }
  isTotal(v) { return isTotal(v); }
  block(v) { return this.blocks.get(`${v.p}:${v.b}`); }
  // the sums a value sits on: [{check, axis}], axis 'col' (down) or 'row' (across), column first
  sumsFor(v) {
    const g = k => this.chk.get(k);
    const out = [];
    const add = (c, axis) => { if (c) out.push({ check: c, axis }); };
    if (!isTotal(v)) { add(g(`col:${v.p}:${v.b}:${v.c}`), 'col'); add(g(`row:${v.p}:${v.b}:${v.r}`), 'row'); }
    else if (v.r === 'col') { add(g(`col:${v.p}:${v.b}:${v.c}`), 'col'); add(g(`grand:${v.p}:${v.b}:`), 'row'); }
    else if (v.r === 'row') add(g(`row:${v.p}:${v.b}:${v.c}`), 'row');
    else add(g(`grand:${v.p}:${v.b}:`), 'row');
    return out;
  }
  termsOf(c) { return c.t.map(i => this.values[i]); }
  // the printed total a sum is decided by
  totalOf(c) {
    const key = c.k === 'grand' ? `${c.p}:${c.b}:grand:` : `${c.p}:${c.b}:${c.k}:${c.y}`;
    const i = this.byId.get(key);
    return i === undefined ? null : this.values[i];
  }
  // where to draw a sum, in image pixels, or null when the scan gave no boxes for it
  band(c) {
    const terms = this.termsOf(c).filter(t => t.x), total = this.totalOf(c);
    const blk = this.block({ p: c.p, b: c.b });
    const tb = total && total.x;
    if (!tb && !terms.length) return null;
    const mid = (a, b) => (a + b) / 2;
    const labelX = blk && blk.x ? blk.x[0] : Math.min(...terms.map(t => t.x[0])) - 20;
    if (c.k === 'col') {
      const x = tb ? mid(tb[0], tb[2]) : mid(terms[0].x[0], terms[0].x[2]);
      const y1 = terms.length ? Math.min(...terms.map(t => t.x[1])) : (blk && blk.x ? blk.x[1] : tb[1]);
      return { x1: x, y1, x2: x, y2: tb ? mid(tb[1], tb[3]) : Math.max(...terms.map(t => t.x[3])) };
    }
    const ys = terms.length ? terms.map(t => mid(t.x[1], t.x[3])) : [mid(tb[1], tb[3])];
    const y = ys.reduce((a, b) => a + b, 0) / ys.length;
    const x2 = tb ? tb[2] : Math.max(...terms.map(t => t.x[2]));
    return { x1: labelX, y1: y, x2, y2: y };
  }
  // the printed figure's own box in page-image pixels, from the ink box of the block image; null without one
  inkPage(v) {
    const b = this.block(v);
    if (!v.ix || !b || !b.bi || !b.x) return null;
    const mx = b.bi.w / (b.x[2] - b.x[0]), my = b.bi.h / (b.x[3] - b.x[1]);
    return [b.x[0] + v.ix[0] / mx, b.x[1] + v.ix[1] / my, b.x[0] + v.ix[2] / mx, b.x[1] + v.ix[3] / my];
  }
  // the value to turn the sheet to for a sum: its first term with a box, else its printed total
  firstValue(c) {
    const t = this.termsOf(c).find(x => x.x);
    if (t) return t.i;
    const tot = this.totalOf(c);
    if (tot && tot.x) return tot.i;
    const any = this.termsOf(c)[0] || tot;   // nothing has a box: the loupe says so
    return any ? any.i : null;
  }
  // the opening value: page 1, both sums hold, read as accepted
  defaultOn(page) {
    const ok = v => !isTotal(v) && v.x && v.s === 'accepted' && this.sumsFor(v).length === 2 && this.sumsFor(v).every(s => s.check.ok);
    const list = this.byPage.get(page) || [];
    const i = list.find(i => ok(this.values[i])) ?? list.find(i => this.values[i].x);
    return i === undefined ? null : i;
  }
  rowLabel(v) { return v.r === 'col' ? 'Total' : v.r === 'row' ? 'Row total' : v.r === 'grand' ? 'Grand total' : v.r; }
  colLabel(v) { return v.r === 'grand' ? '' : v.r === 'row' ? '' : `precinct ${v.c}`; }
}
