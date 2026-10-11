// The loupe: the scan itself around the selected value, from the block's own 300 dpi image.
const SVGNS = 'http://www.w3.org/2000/svg';
const S = 1.25, PAD = 5, ROW_PAD = 8, SLIDE_MS = 350, FADE_MS = 150;

const svg = (tag, attrs = {}) => {
  const e = document.createElementNS(SVGNS, tag);
  for (const k in attrs) e.setAttribute(k, attrs[k]);
  return e;
};

export class Loupe {
  constructor({ root, view, note }, { onPick }) {
    this.root = root; this.view = view; this.note = note; this.onPick = onPick;
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
    let ty = PAD - layer.top * S;
    if (bi.h * S + ty < this.H && bi.h * S > this.H) ty = this.H - bi.h * S;
    return `translate(${tx}px, ${ty}px) scale(${S})`;
  }

  // draws: [{line (page-image pixels), ok}]; animate: slide and fade, else change at once
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
    this.paint(layer, store, blk, v, draws);
  }

  // the block-image x the pan is centred on: the value, or its column when the value has no box
  centerX(store, blk, v) {
    const m = blk.bi.w / (blk.x[2] - blk.x[0]);
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
    const top = rows.length ? (Math.min(...rows.map(o => o.x[1])) - blk.x[1]) * m - ROW_PAD : 0;
    return { key, blk, el, pan, img, svg: s, top: Math.max(0, top), cx: 0 };
  }

  paint(layer, store, blk, v, draws) {
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
    this.ringEl = null;
    if (v.x) {
      // an ellipse around the whole cell, so the printed figure (set low and right in its cell) is inside it
      const w = (v.x[2] - v.x[0]) * mx, h = (v.x[3] - v.x[1]) * my;
      const ring = svg('ellipse', { cx: X((v.x[0] + v.x[2]) / 2), cy: Y((v.x[1] + v.x[3]) / 2), rx: Math.min(w * 0.5, 95), ry: h * 0.5,
                                    class: 'lp-ring ' + (draws.every(d => d.ok) ? 'holds' : 'fails') });
      s.append(ring);
      this.ringEl = ring;
    }
  }

  // the window changed size: put the pan back where it belongs, at once
  relayout() {
    if (!this.layer || !this.last) return;
    const l = this.layer;
    l.pan.classList.remove('slide');
    l.pan.style.transform = this.place(l, l.cx);
  }
}
