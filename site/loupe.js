// The loupe: the scan itself around the selected value, from the block's own 300 dpi image.
import { loopPath, boxPath } from './ring.js';
import { COLS } from './data.js';
const SVGNS = 'http://www.w3.org/2000/svg';
const S0 = 1.25, CLEAR = 10, ROW_PAD = 8, FADE_MS = 150, AIR = 8, RING_PX = 2.5, RING_MS = 180;
const TAG_H = 22, TAG_GAP = 5, LOOP_BELOW = 10;   // the tag, its distance from the ring, and how far the loop reaches below the digits (block px)
// scale tiers tried in turn when the view is fitted to column edges: [smallest, largest, the row-label column must be whole]
const TIERS = [[1.0, 1.6, true], [0.8, 1.9, true], [1.0, 1.6, false], [0.8, 1.9, false]];
const NOTE = "This value has no position in this run's data", NOTE_REPORT = 'No crop was cut for this row: rows with a finding have one.';
const READ_PX = 17.5, S_MIN = 0.62, S_MAX = 1.15;   // the report layout: figures at least this tall on screen (px), and the scales allowed
const RIGHT_AIR = 44, LEFT_AIR = 14, COLUMN_AIR = 56, MIN_PX = 16.2;   // COLUMN_AIR: other rows' figures in a column may be wider than the ringed one   // the report layout: clear paper right of the last figure, so the column heading above it is whole
const EDGE_AIR = 14;   // the loop needs this much clear paper (block pixels) between the digits and the view's edge

const svg = (tag, attrs = {}) => {
  const e = document.createElementNS(SVGNS, tag);
  for (const k in attrs) e.setAttribute(k, attrs[k]);
  return e;
};
const fmt = n => (n === null || n === undefined ? 'none' : Number(n).toLocaleString('en-US'));

export class Loupe {
  constructor({ root, view, note, ctx = null }, { onPick, reduced = false }) {
    this.root = root; this.view = view; this.note = note; this.ctxEl = ctx; this.stemEl = null; this.tagEdge = 'top'; this.onPick = onPick; this.reduced = reduced;
    this.layer = null; this.last = null; this.ringEl = null; this.token = 0; this.tagEl = null; this.peekEl = null;
  }
  setTag(text) {   // the replay's tag: a text of its own on the ring that is drawn
    this.tagText = text;
    if (this.last) this.moveTag(this.layer, this.last.store.values[this.last.i], false);
    if (this.tagEl && text) this.tagEl.classList.add('on');
  }
  // the ring's colour: holds, fails, or warn (the document disagrees with itself, or nothing can decide)
  setRing(cls) {
    for (const r of this.view.querySelectorAll('.lp-ring')) r.setAttribute('class', `lp-ring ${cls}`);
    for (const l of this.view.querySelectorAll('.lp-svg line')) l.setAttribute('class', cls === 'holds' ? 'holds' : 'fails');
  }
  get W() { return this.view.clientWidth; }
  get H() { return this.view.clientHeight; }

  clear() {
    this.last = null; this.ringEl = null; this.peekEl = null;
    for (const e of [this.tagEl, this.stemEl]) if (e) e.remove();
    this.tagEl = this.stemEl = null; this.setCtx(null);
    for (const l of this.view.querySelectorAll('.lp-layer')) l.remove();
    this.layer = null; this.note.hidden = true; this.note.textContent = NOTE;
  }

  // the part of the block image a value takes: [x0, x1, y0, y1] in block-image pixels
  extent(store, blk, v, layer) {
    const mx = blk.bi.w / (blk.x[2] - blk.x[0]), my = blk.bi.h / (blk.x[3] - blk.x[1]);
    if (v.ix) return [v.ix[0], v.ix[2], v.ix[1], v.ix[3]];
    let b = v.x;
    if (!b) {
      const sib = store.values.find(o => o.p === v.p && o.b === v.b && o.c === v.c && o.x);
      if (sib) return [(sib.x[0] - blk.x[0]) * mx, (sib.x[2] - blk.x[0]) * mx, layer.top, layer.top];
      return [0, 0, layer.top, layer.top];
    }
    return [(b[0] - blk.x[0]) * mx, (b[2] - blk.x[0]) * mx, (b[1] - blk.x[1]) * my, (b[3] - blk.x[1]) * my];
  }

  // where the pan sits: the view starts and ends on column edges (no figure or label cut in half), shows the row-label
  // column whole whenever it shows any of it, and keeps the value, its loop and its tag in view
  place(layer, ext) {
    const { bi } = layer.blk, W = this.W, H = this.H, E = layer.edges, lr = layer.labelRight;
    const [a, b, ya, yb] = ext, cx = (a + b) / 2;
    let S = S0, tx = null;
    outer: for (const [smin, smax, whole] of TIERS) {
      let best = null;
      for (const i of E) {
        if (whole && i > 0 && i < lr - 2) continue;
        for (const j of E) {
          if (j <= i + 40) continue;
          const sc = W / (j - i);
          if (sc < smin || sc > smax || a < i + EDGE_AIR || b > j - EDGE_AIR) continue;
          const score = Math.abs((i + j) / 2 - cx) + Math.abs(sc - S0) * 160;
          if (!best || score < best.score) best = { sc, left: i, score };
        }
      }
      if (best) { S = best.sc; tx = -best.left * S; break outer; }
    }
    if (tx === null) {   // no fit: the value centred, never past the block's own ends
      tx = W / 2 - cx * S;
      tx = Math.max(Math.min(tx, 0), Math.min(0, W - bi.w * S));
    }
    let ty = CLEAR - layer.top * S;   // 10 px of clear paper above the block's first row
    if (bi.h * S + ty < H && bi.h * S > H) ty = H - bi.h * S;
    const need = (yb + LOOP_BELOW) * S + TAG_GAP + TAG_H + 2;   // the value's loop and the tag hanging under it
    if (ty + need > H) ty = H - need;
    if (ty + ya * S < 4) ty = 4 - ya * S;
    return { S, tx, ty };
  }
  apply(layer, p) {
    layer.S = p.S; layer.tx = p.tx; layer.ty = p.ty;
    layer.pan.style.transform = `translate(${p.tx}px, ${p.ty}px) scale(${p.S})`;
  }

  // draws: [{line (page-image pixels), ok}]; animate: slide and fade, else change at once; extra: {tag, other}
  // a ring that waits to be drawn on (reveal) when the selection is animated
  show(store, i, draws, animate = true, extra = {}) {
    const v = store.values[i];
    if (store.report) return this.showReport(store, i, v, draws, animate, extra);
    const blk = store.block(v);
    this.last = { store, i, draws, extra };
    if (!blk || !blk.bi || !blk.x) { this.clear(); this.last = { store, i, draws, extra }; this.note.hidden = !!v.x; return; }
    this.note.hidden = !!v.x;
    const key = `${blk.p}:${blk.id}`;
    const same = this.layer && this.layer.key === key;
    let layer = this.layer;
    if (!same) {
      const old = this.layer;
      layer = this.layer = this.build(store, blk, key);
      this.view.append(layer.el);
      this.fadeIn(layer, animate);
      if (old) this.fadeOut(old, animate);
    }
    const ext = this.extent(store, blk, v, layer);
    layer.pan.classList.toggle('slide', same && animate);
    layer.ext = ext;
    this.apply(layer, this.place(layer, ext));
    this.paint(layer, store, blk, v, draws, extra, animate && !this.reduced);
    this.moveTag(layer, v, same && animate);
  }

  // ---- the report layout: the row's clean crop, read at the size of its figures
  showReport(store, i, v, draws, animate, extra) {
    const rc = store.rowCrop(v);
    this.last = { store, i, draws, extra };
    if (!rc) { this.clear(); this.last = { store, i, draws, extra }; this.note.textContent = NOTE_REPORT; this.note.hidden = false; return; }
    this.note.hidden = true;
    const key = `rc:${rc.id}`;
    const same = this.layer && this.layer.key === key;
    let layer = this.layer;
    if (!same) {
      const old = this.layer;
      layer = this.layer = this.buildReport(rc, key);
      this.view.append(layer.el);
      this.fadeIn(layer, animate);
      if (old) this.fadeOut(old, animate);
    }
    const ext = this.reportExtent(layer, v);
    layer.pan.classList.toggle('slide', same && animate);
    layer.ext = ext;
    this.apply(layer, this.placeReport(layer, ext, v));
    this.paintReport(layer, store, v, draws, extra, animate && !this.reduced);
    this.moveTag(layer, v, same && animate);
  }
  buildReport(rc, key) {
    const el = document.createElement('div');
    el.className = 'lp-layer';
    const pan = document.createElement('div');
    pan.className = 'lp-pan';
    pan.style.width = `${rc.w}px`; pan.style.height = `${rc.h}px`;
    const img = document.createElement('img');
    img.alt = ''; img.decoding = 'async'; img.width = rc.w; img.height = rc.h; img.src = rc.img;
    const s = svg('svg', { viewBox: `0 0 ${rc.w} ${rc.h}`, width: rc.w, height: rc.h, class: 'lp-svg' });
    pan.append(img, s);
    el.append(pan);
    return { key, rc, report: true, blk: null, el, pan, img, svg: s, top: 0, S: S_MIN, tx: 0, ty: 0, ext: null };
  }
  // [x0, x1, y0, y1] in the crop's pixels: the figure, else the row's figures, else the right part of the row
  reportExtent(layer, v) {
    const { rc } = layer, fb = rc.fb || {};
    const one = fb[v.c];
    const all = COLS.map(c => fb[c]).filter(Boolean);
    if (one) return [one[0], one[2], one[1], one[3]];
    if (all.length) return [Math.min(...all.map(b => b[0])), Math.max(...all.map(b => b[2])), Math.min(...all.map(b => b[1])), Math.max(...all.map(b => b[3]))];
    return [rc.rb[2] * 0.55, rc.rb[2] - 8, rc.rb[1] + 4, rc.rb[3] - 4];
  }
  placeReport(layer, ext, v) {
    const { rc } = layer, W = this.W, H = this.H;
    const fh = (rc.fb && rc.fb[v.c] ? rc.fb[v.c][3] - rc.fb[v.c][1] : rc.fh) || 24;
    let S = Math.min(S_MAX, Math.max(S_MIN, READ_PX / fh));
    const Smin = Math.min(S, Math.max(0.3, MIN_PX / fh));
    const figs = COLS.map(c => rc.fb && rc.fb[c]);
    const known = figs.filter(Boolean);
    const left = Math.min(ext[0], ...known.map(b => b[0])), right = Math.max(ext[1], ...known.map(b => b[2]));
    let L;
    // the four figures and the clear paper round them, at the size of the figures: the window is as wide as it needs to be
    for (; S > Smin + 1e-6 && (right + RIGHT_AIR) - (left - LEFT_AIR - COLUMN_AIR) > W / S; S -= 0.02);
    S = Math.max(S, Smin);
    const win = W / S;
    if (rc.w <= win) L = 0;
    else if ((right + RIGHT_AIR) - (left - LEFT_AIR - COLUMN_AIR) <= win) L = Math.min(Math.max(0, right + RIGHT_AIR - win), rc.w - win);
    else {
      // not all four fit: as many of the figures as fit, the selected one among them, and no figure cut by the window's edge
      const idx = COLS.indexOf(v.c);
      let lo = idx < 0 || !figs[idx] ? 0 : idx, hi = lo;
      const ok = (l, h) => figs[l] && figs[h] && figs[h][2] - figs[l][0] + 20 <= win;
      for (let grew = true; grew;) {
        grew = false;
        if (hi + 1 < figs.length && ok(lo, hi + 1)) { hi++; grew = true; }
        else if (lo > 0 && ok(lo - 1, hi)) { lo--; grew = true; }
      }
      const a1 = lo > 0 && figs[lo - 1] ? figs[lo - 1][2] + 6 : 0, a2 = (figs[lo] ? figs[lo][0] : ext[0]) - 8 - COLUMN_AIR;
      const b1 = (figs[hi] ? figs[hi][2] : ext[1]) + 8, b2 = hi + 1 < figs.length && figs[hi + 1] ? figs[hi + 1][0] - 6 : rc.w;
      const lo_ = Math.max(a1, b1 - win), hi_ = Math.min(a2, b2 - win);
      L = lo_ <= hi_ ? (lo_ + hi_) / 2 : Math.min(Math.max(0, ((figs[lo] ? figs[lo][0] : ext[0]) + (figs[hi] ? figs[hi][2] : ext[1])) / 2 - win / 2), rc.w - win);
      L = Math.min(Math.max(0, L), rc.w - win);
    }
    const lb = rc.lb;
    if (lb && L > lb[0] && L < lb[1] && lb[1] + 8 <= ext[0] - 20) L = Math.min(lb[1] + 8, Math.max(0, rc.w - win));   // no label cut in half: the label is left out whole
    // the rows: the window opens on the contest's heading when the row is near it, else on the column headings (a crop of two
    // pieces) when they fit above the row, else on the row's neighbourhood with its top on a gap between two rows
    const winH = H / S, rowY = (rc.rb[1] + rc.rb[3]) / 2, pitch = Math.max(30, rc.rb[3] - rc.rb[1]), want = rc.rb[3] + pitch * 1.2;
    const has = rc.ch !== null && rc.ch !== undefined;
    const lattice = () => Math.round((rowY - winH / 2 - (rc.rb[1] - 4)) / pitch) * pitch + rc.rb[1] - 4;
    let t;
    if (has && want - rc.ch <= winH) t = rc.ch;                       // opens on the column headings; the window may run past the crop's end
    else if (rc.h <= winH) t = (rc.h - winH) / 2;
    else if (!has && want <= winH) t = 0;
    else if (rc.gp && rc.gp.length) {
      // the window opens and closes on the blank between two lines: of the gaps that keep the row whole, the one that
      // puts the row nearest the middle and lets the window end in blank paper
      const lo = Math.max(0, (rc.fr || 0) - 4), hi = rc.h - winH, ideal = rowY - winH / 2;
      let best = null;
      for (const g of [lo, ...rc.gp.filter(g => g > lo)]) {
        if (g > rc.rb[1] - 2 || g + winH < rc.rb[3] + 2 || g > hi + 0.5) continue;
        const end = g + winH, away = Math.min(...rc.gp.map(q => Math.abs(q - end)), end > rc.h ? 0 : 1e9);
        const score = Math.abs(g - ideal) * 0.4 + away;
        if (!best || score < best.score) best = { g, score };
      }
      t = best ? best.g : Math.min(Math.max(lo, lattice()), Math.max(0, hi));
    } else {
      t = Math.min(Math.max(0, lattice()), rc.h - winH);
      // a window that opens inside the headings would cut a line of them: it opens on the first row instead
      if (rc.fr !== undefined && rc.fr !== null && t > 0 && t < rc.fr - 4) t = Math.min(rc.fr - 4, rc.h - winH);
    }
    return { S, tx: -L * S, ty: -t * S };
  }
  paintReport(layer, store, v, draws, extra, pending = false) {
    const { svg: s, rc } = layer, S = layer.S;
    s.replaceChildren();
    const rowDraw = draws.find(d => d.axis === 'row') || draws[0];
    const mid = (rc.rb[1] + rc.rb[3]) / 2;
    s.append(svg('line', { x1: 0, y1: mid, x2: rc.w, y2: mid, 'stroke-width': rc.rb[3] - rc.rb[1], class: !rowDraw || rowDraw.ok ? 'holds' : 'fails' }));
    store.rowCells(v).forEach((j, k) => {
      const b = rc.fb && rc.fb[COLS[k]];
      if (j === undefined || !b) return;
      const r = svg('rect', { x: b[0] - 4, y: b[1] - 4, width: b[2] - b[0] + 8, height: b[3] - b[1] + 8, class: 'lp-hit' });
      r.dataset.i = j;
      r.addEventListener('click', () => this.onPick(j));
      s.append(r);
    });
    const other = extra.other !== undefined ? store.values[extra.other] : null;
    const ob = other && other.p === v.p && other.b === v.b && other.r === v.r && rc.fb ? rc.fb[other.c] : null;
    if (ob) {
      const o = svg('rect', { x: ob[0] - 5, y: ob[1] - 5, width: ob[2] - ob[0] + 10, height: ob[3] - ob[1] + 10, class: 'lp-ring2' });
      o.style.strokeWidth = 1.5 / S;
      s.append(o);
    }
    const ok = draws.every(d => d.ok), e = layer.ext, one = rc.fb && rc.fb[v.c];
    const box = [e[0], e[2], e[1], e[3]];
    const ring = svg('path', { d: one ? loopPath(box, AIR / S) : boxPath([box[0] - 4, box[1] - 4, box[2] + 4, box[3] + 4]), pathLength: 1, class: 'lp-ring ' + (ok ? 'holds' : 'fails') });
    ring.style.strokeWidth = RING_PX / S;
    if (pending) { ring.style.strokeDasharray = '1 1'; ring.style.strokeDashoffset = 1; }
    s.append(ring);
    this.ringEl = ring; this.peekEl = null;
    this.tagText = extra.tag === undefined ? null : extra.tag;
  }

  fadeIn(layer, animate) {
    const done = () => { layer.el.classList.add('in'); };
    const img = layer.img;
    if (!animate) { layer.el.classList.add('instant'); done(); }
    else if (img.complete && img.naturalWidth) requestAnimationFrame(() => requestAnimationFrame(done));
    else { img.onload = done; img.onerror = done; }
  }
  fadeOut(old, animate) {
    old.el.classList.remove('in');
    if (animate) setTimeout(() => old.el.remove(), FADE_MS + 60); else old.el.remove();
  }

  // a finding with no place on the sheet: the group's crop, flat, with no ring
  showCrop(src, alt, animate = true) {
    const old = this.layer;
    this.last = null; this.ringEl = null; this.peekEl = null;
    this.hideTag();
    this.note.hidden = true;
    const el = document.createElement('div');
    el.className = 'lp-layer lp-cropbox';
    const img = document.createElement('img');
    img.className = 'lp-crop'; img.alt = alt || ''; img.decoding = 'async'; img.src = src;
    el.append(img);
    const layer = this.layer = { key: `crop:${src}`, el, img, crop: true };
    this.view.append(el);
    this.fadeIn(layer, animate);
    if (old) this.fadeOut(old, animate);
  }

  build(store, blk, key) {
    const { bi } = blk;
    const el = document.createElement('div');
    el.className = 'lp-layer';
    const pan = document.createElement('div');
    pan.className = 'lp-pan';
    pan.style.width = `${bi.w}px`; pan.style.height = `${bi.h}px`;
    const img = document.createElement('img');
    img.alt = ''; img.decoding = 'async'; img.width = bi.w; img.height = bi.h;
    img.src = bi.img;
    const s = svg('svg', { viewBox: `0 0 ${bi.w} ${bi.h}`, width: bi.w, height: bi.h, class: 'lp-svg' });
    pan.append(img, s);
    el.append(pan);
    const all = (store.byPage.get(blk.p) || []).map(j => store.values[j]).filter(o => o.b === blk.id && o.x);
    const rows = all.filter(o => !store.isTotal(o));
    const mx = bi.w / (blk.x[2] - blk.x[0]), m = bi.h / (blk.x[3] - blk.x[1]);
    // the ruled line above the first row when the build found it, else a little above the first cell
    const top = bi.rt != null ? bi.rt - 1 : rows.length ? (Math.min(...rows.map(o => o.x[1])) - blk.x[1]) * m - ROW_PAD : 0;
    // column edges: where the cells and printed totals begin and end, in block-image pixels; the label column is what lies left of them
    const raw = [0, bi.w];
    for (const o of all) raw.push((o.x[0] - blk.x[0]) * mx, (o.x[2] - blk.x[0]) * mx);
    raw.sort((p, q) => p - q);
    const edges = [];
    for (const e of raw) { if (!edges.length || e - edges[edges.length - 1] > 6) edges.push(Math.max(0, Math.min(bi.w, e))); }
    const first = all.length ? Math.min(...all.map(o => (o.x[0] - blk.x[0]) * mx)) : 0;
    return { key, blk, el, pan, img, svg: s, top: Math.max(0, top), S: S0, tx: 0, ty: 0, edges, labelRight: first > 30 ? first : 0, ext: null };
  }

  paint(layer, store, blk, v, draws, extra, pending = false) {
    const { svg: s } = layer, { bi } = blk, S = layer.S;
    const mx = bi.w / (blk.x[2] - blk.x[0]), my = bi.h / (blk.x[3] - blk.x[1]);
    const X = x => (x - blk.x[0]) * mx, Y = y => (y - blk.x[1]) * my;
    s.replaceChildren();
    for (const d of draws) {
      if (!d.line) continue;
      const { x1, y1, x2, y2 } = d.line;
      // a band is one cell thick: the printed figure sits low in its cell, so a thin line would miss it
      const thick = d.axis === 'row' ? (v.x ? (v.x[3] - v.x[1]) * my : 48) : (v.x ? (v.x[2] - v.x[0]) * mx : 150);
      s.append(svg('line', { x1: X(x1), y1: Y(y1), x2: X(x2), y2: Y(y2), 'stroke-width': thick, class: d.ok ? 'holds' : 'fails' }));
    }
    for (const j of store.byPage.get(blk.p) || []) {
      const o = store.values[j];
      if (o.b !== blk.id || !o.x) continue;
      const r = svg('rect', { x: X(o.x[0]), y: Y(o.x[1]), width: (o.x[2] - o.x[0]) * mx, height: (o.x[3] - o.x[1]) * my, class: 'lp-hit' });
      r.dataset.i = j;
      r.addEventListener('click', () => this.onPick(j));
      s.append(r);
    }
    // the cell where the file put the value (a wrong column): outline only
    const other = extra.other !== undefined ? store.values[extra.other] : null;
    if (other && other.x && other.b === blk.id && other.p === blk.p) {
      const o = svg('rect', { x: X(other.x[0]) + 2, y: Y(other.x[1]) + 2, width: (other.x[2] - other.x[0]) * mx - 4, height: (other.x[3] - other.x[1]) * my - 4, class: 'lp-ring2' });
      o.style.strokeWidth = 1.5 / S;
      s.append(o);
    }
    this.ringEl = null; this.peekEl = null;
    if (v.x) {
      // a pencil loop round the printed figure (its ink box) with 8 px of air; without one, round the cell's box
      const ok = draws.every(d => d.ok);
      const box = v.ix || [X(v.x[0]), Y(v.x[1]), X(v.x[2]), Y(v.x[3])];
      const ring = svg('path', { d: v.ix ? loopPath(box, AIR / S) : boxPath(box), pathLength: 1,
                                 class: 'lp-ring ' + (ok ? 'holds' : 'fails') });
      ring.style.strokeWidth = RING_PX / S;
      if (pending) { ring.style.strokeDasharray = '1 1'; ring.style.strokeDashoffset = 1; }
      s.append(ring);
      this.ringEl = ring;
    }
    this.tagText = extra.tag === undefined ? null : extra.tag;
  }

  // the paper tag: in the blank left part of the ringed value's own cell, level with the ring (figures are printed at the
  // right of their cells); when that part is too narrow, just outside the loupe's top edge with a short line down to the ring
  hideTag() {
    for (const e of [this.tagEl, this.stemEl]) if (e) e.classList.remove('on');
    this.setCtx(null);
  }
  // the caption above the loupe gives way to a tag that sits outside the loupe's top edge
  setCtx(gap) {
    const c = this.ctxEl;
    if (!c) return;
    if (!gap) { c.style.left = c.style.right = c.style.textAlign = c.style.visibility = ''; return; }
    const W = c.parentElement.clientWidth, [l, r] = gap, side = l - 24 >= W - r - 24;
    c.style.visibility = Math.max(l - 24 - 12, W - r - 24 - 12) < 60 ? 'hidden' : '';   // no room beside the tag: the caption gives way entirely
    if (side) { c.style.left = '24px'; c.style.right = `${W - l + 12}px`; c.style.textAlign = 'right'; }
    else { c.style.left = `${r + 12}px`; c.style.right = '24px'; c.style.textAlign = 'left'; }
  }
  moveTag(layer, v, slide) {
    if (!this.tagText || !v.x || !layer || layer.crop) { this.hideTag(); return; }
    if (!this.tagEl) {
      this.tagEl = document.createElement('div');
      this.tagEl.className = 'lp-tag';
      this.tagEl.setAttribute('aria-hidden', 'true');
      this.stemEl = document.createElement('div');
      this.stemEl.className = 'lp-stem';
      this.stemEl.setAttribute('aria-hidden', 'true');
    }
    const t = this.tagEl, stem = this.stemEl, blk = layer.blk;
    t.textContent = this.tagText;
    t.classList.toggle('rep', !!layer.report);   // the report layout's tag: it may name two figures, so it may be long
    if (t.parentNode !== this.view) this.view.append(t);   // measured where it will usually sit
    const w = t.offsetWidth, [a, b, ya, yb] = layer.ext, S = layer.S;
    // the blank part of the row starts where the label ends (report layout), or at the cell's left edge
    let cellL;
    if (layer.report) {   // the blank part ends at the label's end, or at the nearest figure to the left of the ringed one
      let edge = layer.rc.lb ? layer.rc.lb[1] : 0;
      for (const c of COLS) { const fb = layer.rc.fb && layer.rc.fb[c]; if (fb && fb[2] <= a + 1 && fb[2] > edge) edge = fb[2]; }
      cellL = layer.tx + (edge + 6) * S;
    } else cellL = layer.tx + (v.x[0] - blk.x[0]) * (blk.bi.w / (blk.x[2] - blk.x[0])) * S;
    const ringL = layer.tx + a * S - 12, ringR = layer.tx + b * S + 12;
    const midY = layer.ty + ((ya + yb) / 2) * S, ringTop = layer.ty + ya * S - 12;
    const left = ringL - TAG_GAP - w, need = Math.max(cellL + 3, 4);
    const inside = left >= need && midY - TAG_H / 2 >= 2 && midY + TAG_H / 2 <= this.H - 2;
    t.classList.toggle('in-cell', inside);
    t.classList.toggle('out', !inside);
    if (inside) {
      t.classList.toggle('slide', !!slide);
      t.style.transform = `translate(${left}px, ${midY - TAG_H / 2}px)`;
      stem.classList.remove('on');
      this.setCtx(null);
    } else {
      const stage = this.root.parentElement, sb = stage.getBoundingClientRect(), lb = this.root.getBoundingClientRect();
      if (t.parentNode !== stage) stage.append(t);
      t.classList.remove('slide');
      const cx = Math.max(10, Math.min(this.W - 10, (ringL + ringR) / 2));       // the ring's middle, in the view
      const x = Math.max(lb.left - sb.left, Math.min(lb.right - sb.left - w, lb.left - sb.left + cx - w / 2));
      const low = this.tagEdge === 'bottom', ringBottom = layer.ty + yb * S + 12;   // the replay hangs it under the loupe: its caption is above
      t.style.transform = `translate(${x}px, ${low ? lb.bottom - sb.top + 1 : lb.top - sb.top - TAG_H - 1}px)`;
      if (stem.parentNode !== this.view) this.view.append(stem);
      const len = low ? Math.max(0, this.H - ringBottom) : Math.max(0, ringTop);
      stem.style.cssText = `left:${cx}px;top:${low ? ringBottom : 0}px;height:${len}px`;
      stem.classList.toggle('on', len > 2 && (!this.ringEl || this.ringEl.style.strokeDashoffset !== '1'));
      this.setCtx(low ? null : [x, x + w]);
    }
    t.classList.toggle('on', !this.ringEl || this.ringEl.style.strokeDashoffset !== '1');
  }

  // draws the ring on, from its top left, once the sums are drawn
  reveal(animate = true, ms = RING_MS) {
    const r = this.ringEl;
    const tag = () => { if (this.tagEl && this.tagText) { this.tagEl.classList.add('on'); if (this.stemEl && this.tagEl.classList.contains('out')) this.stemEl.classList.add('on'); } };
    if (!r || r.style.strokeDashoffset !== '1') { tag(); return Promise.resolve(); }
    if (!animate || this.reduced) { r.style.strokeDashoffset = ''; r.style.strokeDasharray = ''; tag(); return Promise.resolve(); }
    const done = () => { r.style.strokeDashoffset = ''; r.style.strokeDasharray = ''; tag(); };
    return r.animate([{ strokeDashoffset: 1 }, { strokeDashoffset: 0 }], { duration: ms, easing: 'ease-out', fill: 'forwards' })
      .finished.then(done, done);
  }

  // the keyboard is on another value of the sheet: show it here too, without selecting it (i null: back to the selection)
  peek(store, i) {
    const l = this.layer;
    if (!l || l.crop || l.report) return;
    if (this.peekEl) { this.peekEl.remove(); this.peekEl = null; }
    const sel = this.last && store.values[this.last.i];
    const v = i === null || i === undefined ? sel : store.values[i];
    if (!v || v.p !== l.blk.p || v.b !== l.blk.id) return;
    l.pan.classList.add('slide');
    const away = !(i === null || i === undefined || i === (this.last && this.last.i));
    const ext = this.extent(store, l.blk, v, l);
    l.ext = ext;
    this.apply(l, this.place(l, ext));
    if (this.tagEl) {
      if (away) this.hideTag(); else this.moveTag(l, v, true);
    }
    if (!away || !v.x) return;
    const { blk } = l, { bi } = blk, S = l.S;
    const mx = bi.w / (blk.x[2] - blk.x[0]), my = bi.h / (blk.x[3] - blk.x[1]);
    const b = v.ix ? [v.ix[0] - 3, v.ix[1] - 3, v.ix[2] + 3, v.ix[3] + 3]
                   : [(v.x[0] - blk.x[0]) * mx, (v.x[1] - blk.x[1]) * my, (v.x[2] - blk.x[0]) * mx, (v.x[3] - blk.x[1]) * my];
    const g = svg('g', { class: 'lp-peek' });
    for (const [cls, w] of [['dark', 4], ['light', 2]]) {
      const r = svg('rect', { x: b[0], y: b[1], width: b[2] - b[0], height: b[3] - b[1], class: cls });
      r.style.strokeWidth = w / S;
      g.append(r);
    }
    l.svg.append(g);
    this.peekEl = g;
  }

  // the window changed size: put the pan back where it belongs, at once
  relayout() {
    const l = this.layer;
    if (!l || l.crop || !this.last) return;
    l.pan.classList.remove('slide');
    if (this.tagEl) this.tagEl.classList.remove('slide');
    const { store, i } = this.last, v = store.values[i];
    if (l.report) {
      l.ext = this.reportExtent(l, v);
      this.apply(l, this.placeReport(l, l.ext, v));
      this.paintReport(l, store, v, this.last.draws, this.last.extra, false);
      this.moveTag(l, v, false);
      return;
    }
    const ext = this.extent(store, l.blk, v, l);
    l.ext = ext;
    this.apply(l, this.place(l, ext));
    this.paint(l, store, l.blk, v, this.last.draws, this.last.extra, false);
    this.moveTag(l, v, false);
  }
}
