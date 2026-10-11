// The loupe: the scan itself around the selected value, from the block's own 300 dpi image.
import { loopPath, boxPath } from './ring.js';
const SVGNS = 'http://www.w3.org/2000/svg';
const S0 = 1.25, CLEAR = 10, ROW_PAD = 8, FADE_MS = 150, AIR = 8, RING_PX = 2.5, RING_MS = 180;
const TAG_H = 22, TAG_GAP = 5, LOOP_BELOW = 10;   // the tag, its distance from the ring, and how far the loop reaches below the digits (block px)
// scale tiers tried in turn when the view is fitted to column edges: [smallest, largest, the row-label column must be whole]
const TIERS = [[1.0, 1.6, true], [0.8, 1.9, true], [1.0, 1.6, false], [0.8, 1.9, false]];
const EDGE_AIR = 14;   // the loop needs this much clear paper (block pixels) between the digits and the view's edge

const svg = (tag, attrs = {}) => {
  const e = document.createElementNS(SVGNS, tag);
  for (const k in attrs) e.setAttribute(k, attrs[k]);
  return e;
};
const fmt = n => (n === null || n === undefined ? 'none' : Number(n).toLocaleString('en-US'));

export class Loupe {
  constructor({ root, view, note }, { onPick, reduced = false }) {
    this.root = root; this.view = view; this.note = note; this.onPick = onPick; this.reduced = reduced;
    this.layer = null; this.last = null; this.ringEl = null; this.token = 0; this.tagEl = null; this.peekEl = null;
  }
  get W() { return this.view.clientWidth; }
  get H() { return this.view.clientHeight; }

  clear() {
    this.last = null; this.ringEl = null; this.peekEl = null; this.tagEl = null;
    for (const l of this.view.querySelectorAll('.lp-layer')) l.remove();
    this.layer = null; this.note.hidden = true;
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
    if (this.tagEl) this.tagEl.classList.remove('on');
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

  // the paper tag that hangs from the ring: under it, never over the digits
  moveTag(layer, v, slide) {
    if (!this.tagText || !v.x) { if (this.tagEl) this.tagEl.classList.remove('on'); return; }
    if (!this.tagEl) {
      this.tagEl = document.createElement('div');
      this.tagEl.className = 'lp-tag';
      this.tagEl.setAttribute('aria-hidden', 'true');
    }
    const t = this.tagEl;
    if (!t.isConnected) this.view.append(t);
    t.textContent = this.tagText;
    t.classList.toggle('slide', !!slide);
    const [a, b, , yb] = layer.ext, S = layer.S;
    const w = t.offsetWidth;
    // hangs from the loop's lower left, wholly to the left of the digits: figures sit at the right of their cells, so the
    // paper under and left of the loop is clear, and the figure of the row below is not covered
    const left = Math.max(4, Math.min(this.W - w - 4, layer.tx + a * S - 2 - w));
    const topPx = layer.ty + (yb + LOOP_BELOW) * S + TAG_GAP;
    t.style.transform = `translate(${left}px, ${topPx}px)`;
    t.classList.toggle('on', !this.ringEl || this.ringEl.style.strokeDashoffset !== '1');
  }

  // draws the ring on, from its top left, once the sums are drawn
  reveal(animate = true, ms = RING_MS) {
    const r = this.ringEl;
    const tag = () => { if (this.tagEl && this.tagText) this.tagEl.classList.add('on'); };
    if (!r || r.style.strokeDashoffset !== '1') { tag(); return Promise.resolve(); }
    if (!animate || this.reduced) { r.style.strokeDashoffset = ''; r.style.strokeDasharray = ''; tag(); return Promise.resolve(); }
    const done = () => { r.style.strokeDashoffset = ''; r.style.strokeDasharray = ''; tag(); };
    return r.animate([{ strokeDashoffset: 1 }, { strokeDashoffset: 0 }], { duration: ms, easing: 'ease-out', fill: 'forwards' })
      .finished.then(done, done);
  }

  // the keyboard is on another value of the sheet: show it here too, without selecting it (i null: back to the selection)
  peek(store, i) {
    const l = this.layer;
    if (!l || l.crop) return;
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
      this.tagEl.classList.toggle('slide', true);
      if (away) this.tagEl.classList.remove('on'); else { this.moveTag(l, v, true); this.tagEl.classList.add('on'); }
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
    const ext = this.extent(store, l.blk, v, l);
    l.ext = ext;
    this.apply(l, this.place(l, ext));
    this.paint(l, store, l.blk, v, this.last.draws, this.last.extra, false);
    this.moveTag(l, v, false);
  }
}
