// The stage: the scanned sheet in depth, its marks, and the two sums drawn across it.
const SVGNS = 'http://www.w3.org/2000/svg';
const TILT_X = 34, TILT_Z = -3, ZOOM = 1.2, LEAN_MAX = 3;
const TURN_MS = 600, LINE_MS = 350, RING_MS = 180, PAGE_MS = 400;

const svg = (tag, attrs = {}) => {
  const e = document.createElementNS(SVGNS, tag);
  for (const k in attrs) e.setAttribute(k, attrs[k]);
  return e;
};
const wait = ms => new Promise(r => setTimeout(r, ms));

export class Stage {
  constructor(els, { reduced, coarse, onPick, onError }) {
    Object.assign(this, els);
    this.reduced = reduced; this.coarse = coarse; this.onPick = onPick; this.onError = onError;
    this.flat = false; this.token = 0; this.sel = null; this.page = null;
    this.lean = { x: 0, y: 0, tx: 0, ty: 0, raf: 0 };
    new ResizeObserver(() => this.layout(true)).observe(this.viewport);
    if (!reduced && !coarse) this.watchPointer();
  }

  setStore(store) { this.store = store; this.page = null; this.sel = null; }
  get pg() { return this.store && this.store.pages.find(p => p.n === this.page); }
  setLabel(text) { this.paper.setAttribute('aria-label', text); }

  // ---- geometry
  layout(instant = false) {
    const pg = this.pg;
    if (!pg) return;
    const W = this.viewport.clientWidth, H = this.viewport.clientHeight;
    const sw = Math.min(W * 0.84, (H * 0.8 * pg.w) / pg.h * 1.2);
    this.k = sw / pg.w; this.sw = sw; this.sh = sw * pg.h / pg.w;
    const st = this.pose.style;
    st.setProperty('--w', `${this.sw}px`); st.setProperty('--h', `${this.sh}px`);
    const n = this.stackCount();
    st.setProperty('--depth', `${n * 2}px`);
    this.apply(instant);
  }
  stackCount() { return Math.min(5, this.store.pages.length - 1); }
  zoom() { return this.coarse && this.viewport.clientWidth < 900 ? 1.25 : ZOOM; }
  center(i) {
    const v = this.store.values[i];
    return v && v.x ? [(v.x[0] + v.x[2]) / 2 * this.k, (v.x[1] + v.x[3]) / 2 * this.k] : [this.sw / 2, this.sh / 2];
  }
  pose_(i) {
    const [cx, cy] = this.center(i);
    const s = this.zoom();
    const rx = this.flat ? 0 : TILT_X, rz = this.flat ? 0 : TILT_Z;
    return { s, text: `rotateX(${rx}deg) rotateZ(${rz}deg) scale(${s}) translate(${-cx}px, ${-cy}px)` };
  }
  apply(instant = false, fast = false) {
    const { s, text } = this.pose_(this.sel);
    this.u = 1 / (this.k * s);
    for (const e of [this.bands, this.marks]) e.style.setProperty('--u', this.u);
    this.pose.classList.toggle('flat-fast', fast);
    if (instant) this.pose.style.transition = 'none';
    this.pose.style.transform = text;
    if (instant) { void this.pose.offsetWidth; this.pose.style.transition = ''; }
  }

  // ---- pages
  async setPage(n, animate = true, dir = 1) {
    if (n === this.page) return;
    const first = this.page === null;
    const leaving = !first && animate && !this.reduced ? this.paper.cloneNode(true) : null;
    this.page = n;
    const pg = this.pg;
    this.stack.replaceChildren(...Array.from({ length: this.stackCount() }, (_, i) => {
      const e = document.createElement('i');
      e.style.transform = `translate3d(${(i + 1) * 2}px, ${(i + 1) * 2}px, ${-(i + 1) * 2}px)`;
      e.style.background = ['#c9c6b8', '#bfbcae', '#b5b2a4', '#abaa9b', '#a1a092'][i];
      return e;
    }));
    this.clearBands();
    this.layout(true);
    this.buildMarks();
    this.notice.hidden = true;
    await new Promise(res => {
      this.scan.onload = () => res();
      this.scan.onerror = () => { this.notice.textContent = this.onError(pg.img); this.notice.hidden = false; res(); };
      this.scan.src = pg.img;
    });
    if (leaving) {
      leaving.removeAttribute('id'); leaving.removeAttribute('role');
      leaving.querySelectorAll('[id]').forEach(e => e.removeAttribute('id'));
      leaving.style.pointerEvents = 'none';
      this.paper.before(leaving);
      leaving.animate([{ transform: 'translate3d(0,0,0)', opacity: 1 },
                       { transform: `translate3d(${-dir * this.sw * 0.7}px, ${this.sh * 0.08}px, 30px) rotateZ(${-dir * 5}deg)`, opacity: 0 }],
                      { duration: PAGE_MS, easing: 'cubic-bezier(.77,0,.175,1)' }).finished.then(() => leaving.remove(), () => leaving.remove());
      for (const e of [this.paper, this.marks])
        e.animate([{ transform: `translate3d(${dir * 6}px, 6px, -6px)` }, { transform: e === this.marks ? 'translateZ(.5px)' : 'none' }],
                  { duration: PAGE_MS, easing: 'cubic-bezier(.23,1,.32,1)' });
    }
  }

  // ---- marks: one focusable rectangle per value that has a box
  buildMarks() {
    const pg = this.pg, m = this.marks;
    m.replaceChildren();
    m.setAttribute('viewBox', `0 0 ${pg.w} ${pg.h}`);
    this.bands.setAttribute('viewBox', `0 0 ${pg.w} ${pg.h}`);
    this.rects = [];
    for (const i of this.store.byPage.get(this.page) || []) {
      const v = this.store.values[i];
      if (!v.x) continue;
      const r = svg('rect', { x: v.x[0], y: v.x[1], width: v.x[2] - v.x[0], height: v.x[3] - v.x[1], tabindex: -1, role: 'button' });
      r.dataset.i = i;
      if (this.store.isTotal(v)) r.classList.add('total');
      r.setAttribute('aria-label', `${v.v}, ${this.store.rowLabel(v)} ${this.store.colLabel(v)}`.trim());
      r.addEventListener('click', () => this.onPick(i));
      r.addEventListener('keydown', e => this.keys(e, r));
      m.append(r);
      this.rects.push({ r, i, cx: (v.x[0] + v.x[2]) / 2, cy: (v.x[1] + v.x[3]) / 2 });
    }
    this.markSelected();
  }
  markSelected() {
    for (const o of this.rects || []) o.r.setAttribute('tabindex', o.i === this.sel ? 0 : -1);
    if (!this.rects.some(o => o.i === this.sel) && this.rects[0]) this.rects[0].r.setAttribute('tabindex', 0);
  }
  keys(e, r) {
    const i = +r.dataset.i;
    if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); this.onPick(i); return; }
    const dirs = { ArrowRight: [1, 0], ArrowLeft: [-1, 0], ArrowDown: [0, 1], ArrowUp: [0, -1] };
    const d = dirs[e.key];
    if (!d) return;
    e.preventDefault();
    const cur = this.rects.find(o => o.i === i);
    let best = null, bs = Infinity;
    for (const o of this.rects) {
      const dx = o.cx - cur.cx, dy = o.cy - cur.cy;
      const along = dx * d[0] + dy * d[1], across = Math.abs(dx * d[1] - dy * d[0]);
      if (along < 4) continue;
      const score = along + across * 4;
      if (score < bs) { bs = score; best = o; }
    }
    if (best) { r.setAttribute('tabindex', -1); best.r.setAttribute('tabindex', 0); best.r.focus(); }
  }

  // ---- the bands
  clearBands() { this.bands.replaceChildren(); }
  async select(i, sums, animate = true) {
    const tk = ++this.token;
    this.sel = i;
    this.clearBands();
    this.markSelected();
    const instant = !animate || this.reduced;
    const first = sums.slice().sort((a, b) => (a.axis === 'row' ? -1 : 1) - (b.axis === 'row' ? -1 : 1));
    const draws = first.map(s => ({ ...s, line: this.store.band(s.check) })).filter(s => s.line);
    const v = this.store.values[i];
    const ring = this.ringFor(v, draws);
    if (instant) {
      this.apply(true);
      draws.forEach(s => this.band(s, true));
      if (ring) this.svgRing(ring, true);
      return true;
    }
    this.apply(false);
    await wait(TURN_MS);
    for (const s of draws) {
      if (tk !== this.token) return false;
      await this.band(s, false);
    }
    if (tk !== this.token) return false;
    if (ring) await this.svgRing(ring, false);
    return tk === this.token;
  }
  ringFor(v, draws) {
    const w = v.x[2] - v.x[0], h = v.x[3] - v.x[1];
    return { x: (v.x[0] + v.x[2]) / 2, y: (v.x[1] + v.x[3]) / 2, r: Math.max(h * 0.9, 20), ok: draws.every(d => d.check.ok) };
  }
  band(s, instant) {
    const { x1, y1, x2, y2 } = s.line;
    const l = svg('line', { x1, y1, x2, y2, class: s.check.ok ? 'holds' : 'fails' });
    this.bands.append(l);
    const len = Math.hypot(x2 - x1, y2 - y1);
    l.setAttribute('stroke-dasharray', `${len} ${len}`);
    if (instant) return Promise.resolve();
    return l.animate([{ strokeDashoffset: len }, { strokeDashoffset: 0 }], { duration: LINE_MS, easing: 'cubic-bezier(.23,1,.32,1)', fill: 'backwards' }).finished.catch(() => {});
  }
  svgRing(r, instant) {
    const c = svg('circle', { cx: r.x, cy: r.y, r: r.r, class: r.ok ? 'holds' : 'fails' });
    c.style.opacity = 1;
    this.bands.append(c);
    const len = 2 * Math.PI * r.r;
    c.setAttribute('stroke-dasharray', `${len} ${len}`);
    c.setAttribute('transform', `rotate(-90 ${r.x} ${r.y})`);
    if (instant) return Promise.resolve();
    return c.animate([{ strokeDashoffset: len }, { strokeDashoffset: 0 }], { duration: RING_MS, easing: 'ease-out', fill: 'backwards' }).finished.catch(() => {});
  }

  // ---- flat and tilted
  setFlat(f, animate = true) {
    this.flat = f;
    if (this.sel !== null) this.apply(!animate || this.reduced, true);
  }

  // ---- the sheet leans toward the pointer, by at most 3 degrees
  watchPointer() {
    const t = this.lean;
    this.viewport.addEventListener('pointermove', e => {
      if (e.pointerType !== 'mouse') return;
      const b = this.viewport.getBoundingClientRect();
      const nx = ((e.clientX - b.left) / b.width) * 2 - 1, ny = ((e.clientY - b.top) / b.height) * 2 - 1;
      t.tx = -nx * LEAN_MAX; t.ty = ny * LEAN_MAX;
      this.tick();
    });
    this.viewport.addEventListener('pointerleave', () => { t.tx = 0; t.ty = 0; this.tick(); });
  }
  tick() {
    const t = this.lean;
    if (t.raf) return;
    const step = () => {
      t.x += (t.tx - t.x) * 0.12; t.y += (t.ty - t.y) * 0.12;
      const done = Math.abs(t.tx - t.x) < 0.01 && Math.abs(t.ty - t.y) < 0.01;
      if (done) { t.x = t.tx; t.y = t.ty; }
      this.leanEl.style.transform = `rotateX(${t.y}deg) rotateY(${t.x}deg)`;
      t.raf = done ? 0 : requestAnimationFrame(step);
    };
    t.raf = requestAnimationFrame(step);
  }
}
