// The loupe: the scan itself around the selected value, from the block's own 300 dpi image.
import { loopPath, boxPath } from './ring.js';
const SVGNS = 'http://www.w3.org/2000/svg';
const S = 1.25, CLEAR = 10, ROW_PAD = 8, SLIDE_MS = 350, FADE_MS = 150, AIR = 8, RING_PX = 2.5, RING_MS = 180;

const svg = (tag, attrs = {}) => {
  const e = document.createElementNS(SVGNS, tag);
  for (const k in attrs) e.setAttribute(k, attrs[k]);
  return e;
};

export class Loupe {
  constructor({ root, view, note }, { onPick, reduced = false }) {
    this.root = root; this.view = view; this.note = note; this.onPick = onPick; this.reduced = reduced;
    this.layer = null; this.last = null; this.ringEl = null; this.token = 0;
  }
  get W() { return this.view.clientWidth; }
  get H() { return this.view.clientHeight; }

  clear() {
    this.last = null; this.ringEl = null;
    for (const l of this.view.querySelectorAll('.lp-layer')) l.remove();
    this.layer = null; this.note.hidden = true;
  }

  // where the pan sits so the value is centred sideways and the block's rows start at the top
  place(layer, cx) {
    const { bi } = layer.blk;
    let tx = this.W / 2 - cx * S;
    tx = Math.max(Math.min(tx, 0), Math.min(0, this.W - bi.w * S));
    let ty = CLEAR - layer.top * S;   // 10 px of clear paper above the block's first row
    if (bi.h * S + ty < this.H && bi.h * S > this.H) ty = this.H - bi.h * S;
    return `translate(${tx}px, ${ty}px) scale(${S})`;
  }

  // draws: [{line (page-image pixels), ok}]; animate: slide and fade, else change at once
  // a ring that waits to be drawn on (reveal) when the selection is animated
  show(store, i, draws, animate = true) {
    const v = store.values[i];
    const blk = store.block(v);
    this.last = { store, i, draws };
    if (!blk || !blk.bi || !blk.x) { this.clear(); this.last = { store, i, draws }; this.note.hidden = !!v.x; return; }
    this.note.hidden = !!v.x;
    const key = `${blk.p}:${blk.id}`;
    const same = this.layer && this.layer.key === key;
    let layer = this.layer;
    if (!same) {
      const old = this.layer;
      layer = this.layer = this.build(store, blk, key);
      this.view.append(layer.el);
      const done = () => { layer.el.classList.add('in'); };
      if (!animate) { layer.el.classList.add('instant'); done(); }
      else if (layer.img.complete && layer.img.naturalWidth) requestAnimationFrame(() => requestAnimationFrame(done));
      else { layer.img.onload = done; layer.img.onerror = done; }
      if (old) {
        old.el.classList.remove('in');
        const gone = () => old.el.remove();
        if (animate) setTimeout(gone, FADE_MS + 60); else gone();
      }
    }
    const cx = this.centerX(store, blk, v);
    layer.pan.classList.toggle('slide', same && animate);
    layer.pan.style.transform = this.place(layer, cx);
    layer.cx = cx;
    this.paint(layer, store, blk, v, draws, animate && !this.reduced);
  }

  // the block-image x the pan is centred on: the value, or its column when the value has no box
  centerX(store, blk, v) {
    const m = blk.bi.w / (blk.x[2] - blk.x[0]);
    if (v.ix) return (v.ix[0] + v.ix[2]) / 2;
    let b = v.x;
    if (!b) {
      const sib = store.values.find(o => o.p === v.p && o.b === v.b && o.c === v.c && o.x);
      b = sib && sib.x;
    }
    return b ? ((b[0] + b[2]) / 2 - blk.x[0]) * m : 0;
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
    const rows = (store.byPage.get(blk.p) || []).map(j => store.values[j]).filter(o => o.b === blk.id && o.x && !store.isTotal(o));
    const m = bi.h / (blk.x[3] - blk.x[1]);
    // the ruled line above the first row when the build found it, else a little above the first cell
    const top = bi.rt != null ? bi.rt - 1 : rows.length ? (Math.min(...rows.map(o => o.x[1])) - blk.x[1]) * m - ROW_PAD : 0;
    return { key, blk, el, pan, img, svg: s, top: Math.max(0, top), cx: 0 };
  }

  paint(layer, store, blk, v, draws, pending = false) {
    const { svg: s } = layer, { bi } = blk;
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
  }

  // draws the ring on, from its top left, once the sums are drawn
  reveal(animate = true, ms = RING_MS) {
    const r = this.ringEl;
    if (!r || r.style.strokeDashoffset !== '1') return Promise.resolve();
    if (!animate || this.reduced) { r.style.strokeDashoffset = ''; r.style.strokeDasharray = ''; return Promise.resolve(); }
    const done = () => { r.style.strokeDashoffset = ''; r.style.strokeDasharray = ''; };
    return r.animate([{ strokeDashoffset: 1 }, { strokeDashoffset: 0 }], { duration: ms, easing: 'ease-out', fill: 'forwards' })
      .finished.then(done, done);
  }

  // the keyboard is on another value of the sheet: show it here too, without selecting it (i null: back to the selection)
  peek(store, i) {
    const l = this.layer;
    if (!l) return;
    if (this.peekEl) { this.peekEl.remove(); this.peekEl = null; }
    const sel = this.last && store.values[this.last.i];
    const v = i === null || i === undefined ? sel : store.values[i];
    if (!v || v.p !== l.blk.p || v.b !== l.blk.id) return;
    l.pan.classList.add('slide');
    l.cx = this.centerX(store, l.blk, v);
    l.pan.style.transform = this.place(l, l.cx);
    if (i === null || i === undefined || i === (this.last && this.last.i) || !v.x) return;
    const { blk } = l, { bi } = blk;
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
    if (!this.layer || !this.last) return;
    const l = this.layer;
    l.pan.classList.remove('slide');
    l.pan.style.transform = this.place(l, l.cx);
  }
}
