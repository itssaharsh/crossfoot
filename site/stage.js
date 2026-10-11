// The stage: the scanned sheet in depth, its marks, the two sums drawn across it, and the leader to the loupe.
import { loopPath, boxPath } from './ring.js';
import { loaded } from './data.js';
const SVGNS = 'http://www.w3.org/2000/svg';
const TILT_X = 46, TILT_Z = -3, LEAN_MAX = 3, CLEAR = 24, CLEAR_NARROW = 8, NARROW = 899, SLACK_X = 18, SLACK_Y = 10, TURN_Z = 2, STACK_PX = 3;
const ENTER_MS = 400, TURN_MS = 600, LINE_MS = 350, RING_MS = 180, PAGE_MS = 400, FLAT_MS = 400;

const svg = (tag, attrs = {}) => {
  const e = document.createElementNS(SVGNS, tag);
  for (const k in attrs) e.setAttribute(k, attrs[k]);
  return e;
};
const wait = ms => new Promise(r => setTimeout(r, ms));
const ease = t => (t < 0.5 ? 8 * t ** 4 : 1 - ((-2 * t + 2) ** 4) / 2);
const mix = (a, b, t) => a + (b - a) * t;

export class Stage {
  constructor(els, { reduced, coarse, onPick, onError, onFocusValue = () => {} }) {
    Object.assign(this, els);
    this.reduced = reduced; this.coarse = coarse; this.onPick = onPick; this.onError = onError; this.onFocusValue = onFocusValue;
    this.partial = false; this.forcePartial = false; this.focusRing = null;
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
    const bottom = this.controls && this.controls.offsetHeight ? this.controls.offsetTop - 10 : H;
    const c = innerWidth <= NARROW || innerHeight <= 720 ? CLEAR_NARROW : CLEAR;
    const a = { l: c, r: W - c, t: top + c, b: bottom - c };
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
    if (this.partial) this.updateFlat();
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
    const sx = this.flat ? 0 : SLACK_X, sy = this.flat ? 0 : SLACK_Y;   // room for the turn toward a value, tilted only
    const box = { l: A.l + sx, r: A.r - sx - sa, t: A.t + sy, b: A.b - sy - sa };
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
    const u = 1 / (this.k * P.f);
    for (const p of this.tickPaths || []) p.setAttribute('transform', `scale(${u.toFixed(4)})`);
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
    if (this.partial || !ringEl || !ringEl.isConnected || !a || !a.isConnected) { line.setAttribute('hidden', ''); return; }
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
    this.setPartial(this.forcePartial);
    if (!this.forcePartial) await new Promise(res => {
      this.scan.onload = () => { loaded(); res(); };
      this.scan.onerror = () => {
        // no page image: the block's own image is shown flat instead, and only when there is none is it an error
        if (this.hasBlockImage()) this.setPartial(true);
        else { this.notice.textContent = this.onError(pg.img); this.notice.hidden = false; }
        res();
      };
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
      r.dataset.i = i; r.dataset.b = v.b;
      r.addEventListener('focus', () => { this.showFocus(v.x); this.onFocusValue(i); });
      r.addEventListener('blur', () => { this.showFocus(null); setTimeout(() => { if (!this.marks.contains(document.activeElement)) this.onFocusValue(null); }); });
      if (this.store.isTotal(v)) r.classList.add('total');
      r.setAttribute('aria-label', `${v.v}, ${this.store.rowLabel(v)} ${this.store.colLabel(v)}`.trim());
      r.addEventListener('click', () => this.onPick(i));
      r.addEventListener('keydown', e => this.keys(e, r));
      m.append(r);
      this.rects.push({ r, i, cx: (v.x[0] + v.x[2]) / 2, cy: (v.x[1] + v.x[3]) / 2 });
    }
    this.ticks = new Map(); this.tickPaths = [];   // a pencil tick at every finding's value on this page (the selected one has its ring instead)
    const tg = svg('g', { class: 'ticks', 'aria-hidden': 'true' });
    for (const f of this.store.items) {
      const v = f.ref === undefined ? null : this.store.values[f.ref];
      if (!v || !v.x || v.p !== this.page) continue;
      const g = svg('g', { transform: `translate(${v.x[0]} ${(v.x[1] + v.x[3]) / 2})`, class: 'tick ' + (f.status === 'settled_against_file' ? 'settled' : 'open') });
      const path = svg('path', { d: 'M3 0L7 5L15 -7' });
      g.append(path);
      this.tickPaths.push(path);
      tg.append(g);
      this.ticks.set(f.ref, g);
    }
    m.prepend(tg);
    this.focusRing = svg('g', { class: 'focus-ring', 'aria-hidden': 'true' });
    for (const cls of ['dark', 'light']) this.focusRing.append(svg('rect', { class: cls }));
    this.focusRing.setAttribute('display', 'none');
    m.append(this.focusRing);
    this.markSelected();
  }
  // two strokes round the focused value, so it shows on white paper: ink outside, --focus inside, 2 px
  showFocus(b) {
    const g = this.focusRing;
    if (!g) return;
    if (!b) { g.setAttribute('display', 'none'); return; }
    for (const r of g.children) {
      r.setAttribute('x', b[0] - 1); r.setAttribute('y', b[1] - 1);
      r.setAttribute('width', b[2] - b[0] + 2); r.setAttribute('height', b[3] - b[1] + 2);
    }
    g.removeAttribute('display');
  }
  markSelected() {
    for (const [r, g] of this.ticks || []) { if (r === this.sel) g.setAttribute('display', 'none'); else g.removeAttribute('display'); }
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
    const inBlock = this.rects.filter(o => o.r.dataset.b === r.dataset.b);
    for (const o of this.rects.length && inBlock.some(o => o !== cur && (o.cx - cur.cx) * d[0] + (o.cy - cur.cy) * d[1] >= 4) ? inBlock : this.rects) {
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
  async select(i, sums, animate = true, opts = {}) {
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
    const loupeDraws = draws.map(d => ({ line: d.line, ok: d.check.ok, axis: d.axis }));
    if (this.loupe) this.loupe.show(this.store, i, loupeDraws, !instant, opts.extra || {});
    this.flatArgs = { v, draws: loupeDraws };
    if (this.partial) this.updateFlat();
    if (opts.settle) {   // the first load: the sheet settles from flat into its tilt
      const keep = { ...this.P };
      this.flat = false; this.base = this.fit();
      this.setP(keep);
    }
    if (v.x) this.go(this.target(), instant ? 0 : opts.settle ? ENTER_MS : TURN_MS);
    this.updateLeader();
    if (instant) {
      draws.forEach(s => this.band(s, true));
      if (ring) this.svgRing(ring, true);
      if (this.loupe) this.loupe.reveal(false);
      return true;
    }
    if (opts.settle) {   // the entrance: the sheet settles while the bands draw together, then the ring closes
      this.pump(ENTER_MS + 150);
      await wait(60);
      await Promise.all(draws.map(s => this.band(s, false, 260)));
      if (tk !== this.token) return false;
      await Promise.all([ring ? this.svgRing(ring, false, 120) : null, this.loupe ? this.loupe.reveal(true, 120) : null]);
      return tk === this.token;
    }
    this.pump(TURN_MS + 150);
    if (v.x) await wait(TURN_MS);
    for (const s of draws) {
      if (tk !== this.token) return false;
      await this.band(s, false);
    }
    if (tk !== this.token) return false;
    await Promise.all([ring ? this.svgRing(ring, false) : null, this.loupe ? this.loupe.reveal(true) : null]);
    return tk === this.token;
  }
  // a finding with no place on the sheet: nothing is ringed, no sum is drawn; the sheet stays where it is
  deselect() {
    this.token++;
    this.sel = null;
    this.clearBands();
    this.anchor = null;
    this.flatArgs = null;
    this.markSelected();
    this.go(this.target(), 0);
    this.updateLeader();
  }
  ringFor(v, draws) {
    const h = v.x[3] - v.x[1], ink = this.store.inkPage(v) || v.x;
    return { x: (ink[0] + ink[2]) / 2, y: (ink[1] + ink[3]) / 2, r: Math.max(h * 0.9, 20), ok: draws.every(d => d.check.ok) };
  }
  band(s, instant, ms = LINE_MS) {
    const { x1, y1, x2, y2 } = s.line;
    const l = svg('line', { x1, y1, x2, y2, class: s.check.ok ? 'holds' : 'fails' });
    this.bands.append(l);
    const len = Math.hypot(x2 - x1, y2 - y1);
    l.setAttribute('stroke-dasharray', `${len} ${len}`);
    if (instant) return Promise.resolve();
    return l.animate([{ strokeDashoffset: len }, { strokeDashoffset: 0 }], { duration: ms, easing: 'cubic-bezier(.23,1,.32,1)', fill: 'backwards' }).finished.catch(() => {});
  }
  svgRing(r, instant, ms = RING_MS) {
    const c = svg('circle', { cx: r.x, cy: r.y, r: r.r, class: r.ok ? 'holds' : 'fails' });
    c.style.opacity = 1;
    this.bands.append(c);
    const len = 2 * Math.PI * r.r;
    c.setAttribute('stroke-dasharray', `${len} ${len}`);
    c.setAttribute('transform', `rotate(-90 ${r.x} ${r.y})`);
    if (instant) return Promise.resolve();
    return c.animate([{ strokeDashoffset: len }, { strokeDashoffset: 0 }], { duration: ms, easing: 'ease-out', fill: 'backwards' }).finished.catch(() => {});
  }

  // ---- partial: no page image, so the block's own image is shown flat where the sheet would be
  hasBlockImage() { return this.store.blocks.size && [...this.store.blocks.values()].some(b => b.p === this.page && b.bi); }
  setPartial(on) {
    this.partial = on;
    this.root.classList.toggle('partial', on);
    const bs = document.body.dataset;
    if (on) bs.state = 'partial'; else if (bs.state === 'partial' && !this.forcePartial) bs.state = 'ready';
    this.flatEl.hidden = !on;
    if (on) { this.setLabel('The page image is not available. The block of the scan is shown flat.'); this.updateFlat(); }
    else this.flatEl.replaceChildren();
  }
  updateFlat() {
    const el = this.flatEl, a = this.flatArgs;
    el.replaceChildren();
    if (!a || !el.clientWidth) return;
    const { v, draws } = a, blk = this.store.block(v);
    if (!blk || !blk.bi || !blk.x) { const p = document.createElement('p'); p.textContent = 'No image of this block is available.'; el.append(p); return; }
    const { bi } = blk, W = el.clientWidth, H = el.clientHeight;
    const k = Math.min(0.75, H / bi.h);
    const mx = bi.w / (blk.x[2] - blk.x[0]), my = bi.h / (blk.x[3] - blk.x[1]);
    const X = x => (x - blk.x[0]) * mx, Y = y => (y - blk.x[1]) * my;
    const cx = v.ix ? (v.ix[0] + v.ix[2]) / 2 : v.x ? X((v.x[0] + v.x[2]) / 2) : 0;
    const tx = bi.w * k <= W ? (W - bi.w * k) / 2 : Math.min(0, Math.max(W - bi.w * k, W / 2 - cx * k));
    const pan = document.createElement('div');
    pan.className = 'fb-pan';
    pan.style.cssText = `width:${bi.w}px;height:${bi.h}px;transform:translate(${tx}px,${(H - bi.h * k) / 2}px) scale(${k})`;
    const img = document.createElement('img');
    img.alt = ''; img.src = bi.img; img.width = bi.w; img.height = bi.h;
    const o = svg('svg', { viewBox: `0 0 ${bi.w} ${bi.h}`, width: bi.w, height: bi.h, class: 'fb-svg', 'aria-hidden': 'true' });
    for (const d of draws) {
      if (!d.line) continue;
      const thick = d.axis === 'row' ? (v.x ? (v.x[3] - v.x[1]) * my : 48) : (v.x ? (v.x[2] - v.x[0]) * mx : 150);
      const l = svg('line', { x1: X(d.line.x1), y1: Y(d.line.y1), x2: X(d.line.x2), y2: Y(d.line.y2), class: d.ok ? 'holds' : 'fails' });
      l.style.strokeWidth = thick;
      o.append(l);
    }
    for (const j of this.store.byPage.get(blk.p) || []) {
      const q = this.store.values[j];
      if (q.b !== blk.id || !q.x) continue;
      const r = svg('rect', { x: X(q.x[0]), y: Y(q.x[1]), width: (q.x[2] - q.x[0]) * mx, height: (q.x[3] - q.x[1]) * my, class: 'fb-hit' });
      r.addEventListener('click', () => this.onPick(j));
      o.append(r);
    }
    if (v.x) {
      const box = v.ix || [X(v.x[0]), Y(v.x[1]), X(v.x[2]), Y(v.x[3])];
      const ring = svg('path', { d: v.ix ? loopPath(box, 8 / k) : boxPath(box, 4 / k), class: 'fb-ring ' + (draws.every(d => d.ok) ? 'holds' : 'fails') });
      ring.style.strokeWidth = 2.5 / k;
      o.append(ring);
    }
    pan.append(img, o);
    el.append(pan);
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
