// The stage: the scanned sheet in depth, its marks, the two sums drawn across it, and the leader to the loupe.
const SVGNS = 'http://www.w3.org/2000/svg';
const TILT_X = 46, TILT_Z = -3, LEAN_MAX = 3, CLEAR = 24, SLACK_X = 18, SLACK_Y = 10, TURN_Z = 2, STACK_PX = 3;
const TURN_MS = 600, LINE_MS = 350, RING_MS = 180, PAGE_MS = 400, FLAT_MS = 400;

const svg = (tag, attrs = {}) => {
  const e = document.createElementNS(SVGNS, tag);
  for (const k in attrs) e.setAttribute(k, attrs[k]);
  return e;
};
const wait = ms => new Promise(r => setTimeout(r, ms));
const ease = t => (t < 0.5 ? 8 * t ** 4 : 1 - ((-2 * t + 2) ** 4) / 2);
const mix = (a, b, t) => a + (b - a) * t;

export class Stage {
  constructor(els, { reduced, coarse, onPick, onError }) {
    Object.assign(this, els);
    this.reduced = reduced; this.coarse = coarse; this.onPick = onPick; this.onError = onError;
    this.flat = false; this.token = 0; this.sel = null; this.page = null;
    this.P = { f: 1, tx: 0, ty: 0, rx: 0, rz: 0 }; this.base = this.P; this.anchor = null; this.loupe = null;
    this.lean = { x: 0, y: 0, tx: 0, ty: 0, raf: 0 };
    this.until = 0; this.pumping = false;
    new ResizeObserver(() => { this.layout(true); }).observe(this.viewport);
    if (!reduced && !coarse) this.watchPointer();
  }

  setStore(store) { this.store = store; this.page = null; this.sel = null; }
  setLoupe(loupe) { this.loupe = loupe; }
  get pg() { return this.store && this.store.pages.find(p => p.n === this.page); }
  setLabel(text) { this.paper.setAttribute('aria-label', text); }

  // ---- geometry
  // the part of the stage the sheet may use: below the loupe, above the controls, 24 px clear inside it
  area() {
    const W = this.viewport.clientWidth, H = this.viewport.clientHeight;
    const top = this.loupeEl ? this.loupeEl.offsetTop + this.loupeEl.offsetHeight + 12 : 0;
    const bottom = H - (this.controls ? this.controls.offsetHeight + 24 + 10 : 0);
    const a = { l: CLEAR, r: W - CLEAR, t: top + CLEAR, b: bottom - CLEAR };
    if (a.b - a.t < 60) a.b = a.t + 60;
    return a;
  }
  stackPx() { return this.store ? this.stackCount() * STACK_PX : 0; }
  layout(instant = true) {
    const pg = this.pg;
    if (!pg || !this.viewport.clientWidth) return;
    const A = this.area();
    this.sw = A.r - A.l; this.sh = this.sw * pg.h / pg.w; this.k = this.sw / pg.w;
    const st = this.pose.style;
    st.setProperty('--w', `${this.sw}px`); st.setProperty('--h', `${this.sh}px`);
    st.setProperty('--depth', `${this.stackCount() * 2}px`);
    this.viewport.style.perspectiveOrigin = `${this.viewport.clientWidth / 2}px ${(A.t + A.b) / 2}px`;
    this.base = this.fit();
    this.setP(this.target());
    if (this.loupe) this.loupe.relayout();
    this.updateLeader();
  }
  stackCount() { return Math.min(5, this.store.pages.length - 1); }

  // the sheet's projected box, relative to the stage, with the pointer lean taken out
  measure(P) {
    this.setP(P);
    const lean = this.leanEl.style.transform;
    this.leanEl.style.transform = 'none';
    const r = this.sheet.getBoundingClientRect(), v = this.viewport.getBoundingClientRect();
    this.leanEl.style.transform = lean;
    return { l: r.left - v.left, t: r.top - v.top, w: r.width, h: r.height, r: r.right - v.left, b: r.bottom - v.top };
  }
  fit() {
    const A = this.area(), sa = this.stackPx();
    const box = { l: A.l + SLACK_X, r: A.r - SLACK_X - sa, t: A.t + SLACK_Y, b: A.b - SLACK_Y - sa };
    const P = { f: 0.5, tx: (box.l + box.r) / 2, ty: (box.t + box.b) / 2, rx: this.flat ? 0 : TILT_X, rz: this.flat ? 0 : TILT_Z };
    for (let n = 0; n < 5; n++) {
      let m = this.measure(P);
      P.f *= Math.min((box.r - box.l) / m.w, (box.b - box.t) / m.h);
      m = this.measure(P);
      P.tx += (box.l + box.r) / 2 - (m.l + m.r) / 2;
      P.ty += (box.t + box.b) / 2 - (m.t + m.b) / 2;
    }
    return P;
  }
  // the pose for the current selection: a small turn toward the value, never out of the sheet zone
  target() {
    const keep = { ...this.P };
    const v = this.store && this.sel !== null ? this.store.values[this.sel] : null;
    if (!v || !v.x || v.p !== this.page || this.flat) return { ...this.base };
    const pg = this.pg;
    const nx = ((v.x[0] + v.x[2]) / 2 / pg.w - 0.5) * 2, ny = ((v.x[1] + v.x[3]) / 2 / pg.h - 0.5) * 2;
    const P = { ...this.base, rz: this.base.rz - TURN_Z * nx, tx: this.base.tx - nx * SLACK_X, ty: this.base.ty - ny * SLACK_Y };
    const A = this.area(), sa = this.stackPx();
    for (let n = 0; n < 2; n++) {
      const m = this.measure(P);
      P.tx += Math.max(0, A.l - m.l) - Math.max(0, m.r + sa - A.r);
      P.ty += Math.max(0, A.t - m.t) - Math.max(0, m.b + sa - A.b);
    }
    this.setP(keep);
    return P;
  }
  setP(P) {
    this.P = P;
    this.pose.style.transform = `translate(${P.tx}px, ${P.ty}px) rotateX(${P.rx}deg) rotateZ(${P.rz}deg) scale(${P.f})`;
    const st = this.pose.style;
    st.setProperty('--u', 1 / (this.k * P.f)); st.setProperty('--inv', 1 / P.f);
  }
  go(P, ms) {
    cancelAnimationFrame(this.tw);
    const A = { ...this.P };
    if (!ms || this.reduced) { this.setP(P); this.updateLeader(); return; }
    const t0 = performance.now();
    const step = now => {
      const t = Math.min(1, (now - t0) / ms), e = ease(t);
      this.setP({ f: mix(A.f, P.f, e), tx: mix(A.tx, P.tx, e), ty: mix(A.ty, P.ty, e), rx: mix(A.rx, P.rx, e), rz: mix(A.rz, P.rz, e) });
      this.updateLeader();
      if (t < 1) this.tw = requestAnimationFrame(step);
    };
    this.tw = requestAnimationFrame(step);
  }

  // ---- the leader: loupe's bottom edge to the ring on the sheet, followed on every frame while anything moves
  pump(ms) {
    this.until = Math.max(this.until, performance.now() + ms);
    if (this.pumping) return;
    this.pumping = true;
    const step = () => {
      this.updateLeader();
      if (performance.now() < this.until) requestAnimationFrame(step); else this.pumping = false;
    };
    requestAnimationFrame(step);
  }
  updateLeader() {
    const line = this.leaderLine, ringEl = this.loupe && this.loupe.ringEl, a = this.anchor;
    if (!ringEl || !ringEl.isConnected || !a || !a.isConnected) { line.setAttribute('hidden', ''); return; }
    const o = this.leader.getBoundingClientRect(), lb = this.loupeEl.getBoundingClientRect();
    const rb = ringEl.getBoundingClientRect(), ab = a.getBoundingClientRect();
    if (!ab.width || !rb.width) { line.setAttribute('hidden', ''); return; }
    const sx = Math.min(Math.max(rb.left + rb.width / 2, lb.left + 12), lb.right - 12), sy = lb.bottom;
    const cx = ab.left + ab.width / 2, cy = ab.top + ab.height / 2, rx = ab.width / 2, ry = ab.height / 2;
    const dx = sx - cx, dy = sy - cy, t = 1 / Math.hypot(dx / rx, dy / ry);
    line.setAttribute('x1', sx - o.left); line.setAttribute('y1', sy - o.top);
    line.setAttribute('x2', cx + dx * t - o.left); line.setAttribute('y2', cy + dy * t - o.top);
    line.removeAttribute('hidden');
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
      const d = `calc(var(--inv, 1) * ${(i + 1) * STACK_PX}px)`;
      e.style.transform = `translate3d(${d}, ${d}, calc(var(--inv, 1) * ${-(i + 1) * 2}px))`;
      e.style.background = ['#c9c6b8', '#bfbcae', '#b5b2a4', '#abaa9b', '#a1a092'][i];
      return e;
    }));
    const depth = this.stackCount(), d = `calc(var(--inv, 1) * ${(depth + 1) * STACK_PX}px)`;
    const under = document.createElement('i');   // the contact shadow, lowest in the pile
    under.className = 'under';
    under.style.transform = `translate3d(${d}, ${d}, calc(var(--inv, 1) * ${-(depth + 1) * 2}px))`;
    this.stack.prepend(under);
    this.clearBands();
    this.anchor = null;
    this.layout(true);
    this.buildMarks();
    this.notice.hidden = true;
    await new Promise(res => {
      this.scan.onload = () => res();
      this.scan.onerror = () => { this.notice.textContent = this.onError(pg.img); this.notice.hidden = false; res(); };
      this.scan.src = pg.img;
    });
    if (leaving) {
      this.pump(PAGE_MS + 100);
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
    const ring = v.x ? this.ringFor(v, draws) : null;
    this.anchor = null;
    if (ring) {
      this.anchor = svg('circle', { cx: ring.x, cy: ring.y, r: ring.r, fill: 'none', stroke: 'none' });
      this.bands.append(this.anchor);
    }
    if (this.loupe) this.loupe.show(this.store, i, draws.map(d => ({ line: d.line, ok: d.check.ok, axis: d.axis })), !instant);
    if (v.x) this.go(this.target(), instant ? 0 : TURN_MS);
    this.updateLeader();
    if (instant) {
      draws.forEach(s => this.band(s, true));
      if (ring) this.svgRing(ring, true);
      return true;
    }
    this.pump(TURN_MS + 150);
    if (v.x) await wait(TURN_MS);
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
    if (!this.pg) return;
    const keep = { ...this.P };
    this.base = this.fit();
    const P = this.target();
    this.setP(keep);
    this.go(P, animate && !this.reduced ? FLAT_MS : 0);
    this.pump(FLAT_MS + 100);
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
      this.updateLeader();
      t.raf = done ? 0 : requestAnimationFrame(step);
    };
    t.raf = requestAnimationFrame(step);
  }
}
