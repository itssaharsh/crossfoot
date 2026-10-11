// The replay: the run's own recorded events, played on the sheet in order. Nothing is invented: every step is built from
// an event or a figure in the county's data (see buildTimeline), and a step whose data is missing is left out.
//
// buildTimeline(d) is a plain function of the county's JSON (site/data/<county>.json, keys in crossfoot/sitebuild.py):
// no page, no DOM. The Replay class plays what it returns.
import { fmt } from './data.js';

const SVGNS = 'http://www.w3.org/2000/svg';
export const SPEEDS = [1, 2, 4];
// milliseconds a step lasts at the default speed
const MS = { sample: 2400, read: 200, readTurn: 420, check: 3000, suspect: 2700, audit: 3800, end: 1800 };
const CANCELLED = Symbol('replay cancelled');

const cap = s => (s ? s[0].toUpperCase() + s.slice(1) : s);
const sentence = s => { const t = String(s || '').trim(); const m = /^(.+?[.!?])(\s|$)/.exec(t); return cap(m ? m[1] : t.replace(/[.\s]+$/, '')); };
const sumTotal = o => Object.values(o || {}).reduce((a, n) => a + (Number(n) || 0), 0);
// the run's sum keys use `grand_col` where the page's checks say `grand`
export const checkKey = key => {
  const [k, p, b, ...rest] = String(key).split(':');
  return `${k === 'grand_col' ? 'grand' : k}:${p}:${b}:${rest.join(':')}`;
};

// The steps, in the order the run recorded them:
//   sample    the sample read that chose the reader                      (the sample figures)
//   read      one step per block_read event, in order                    (each event)
//   check     the sums that failed after the first read                  (the suspect events, the summary's count)
//   suspect   one step per suspect event with its re-reads and verdict   (the events of its item, the verdicts)
//   audit     the findings laid against the published file               (the findings' pages)
//   end       back to the opening finding
// Each step: {beat, ms, caption, ...what the step draws}. `ms` is its length at the default speed.
export function buildTimeline(d) {
  const ev = d.events || [];
  const steps = [];
  const items = d.fd ? d.fd.items : [];
  const nPages = (d.pages || []).length;
  if (!ev.length) return { steps, ms: 0, seconds: 0 };
  const chosen = ev.findIndex(e => e.k === 'choose_reader');
  const sample = (chosen >= 0 ? ev[chosen].p : null) || (d.fd && d.fd.run_info && d.fd.run_info.sample) || null;

  if (sample && sample.row_sums !== undefined && sample.failing !== undefined && sample.sampled_with && sample.reader) {
    steps.push({ beat: 'sample', ms: MS.sample, blocks: sample.blocks || [],
                 caption: `A sample read with ${sample.sampled_with} fails ${fmt(sample.failing)} of ${fmt(sample.row_sums)} row sums. The county is read with ${sample.reader}.` });
  }

  // the reads: two passes when the run chose a reader after a sample, else one
  const reads = ev.map((e, i) => ({ e, i })).filter(({ e }) => e.k === 'block_read' && e.p && e.p.page !== undefined && e.p.block);
  const passOf = i => (chosen >= 0 && i < chosen ? 0 : 1);
  const size = [0, 0];
  reads.forEach(({ i }) => size[passOf(i)]++);
  const seen = [0, 0];
  let page = null;
  for (const { e, i } of reads) {
    const pass = passOf(i), k = ++seen[pass], p = e.p;
    const turn = page !== null && p.page !== page;
    page = p.page;
    steps.push({ beat: 'read', ms: turn ? MS.readTurn : MS.read, page: p.page, block: p.block, k, all: size[pass], model: p.model,
                 first: k === 1 && !(pass === 0 && chosen >= 0), sample: pass === 0 && chosen >= 0,
                 caption: pass === 0 && chosen >= 0
                   ? `Sample read with ${p.model || 'the first reader'}, page ${p.page}: ${k} of ${size[pass]} blocks`
                   : `Reading page ${p.page} of ${nPages || p.page}: ${k} of ${size[pass]} blocks` });
  }

  // the suspects: each with the events of its item up to the next item
  const suspects = [];
  ev.forEach((e, i) => {
    if (e.k !== 'suspect' || !e.p || !e.p.sums) return;
    const item = e.p.item;
    let end = ev.findIndex((x, j) => j > i && x.k === 'item_start');
    if (end < 0) end = ev.length;
    const mine = ev.slice(i + 1, end).filter(x => x.p && x.p.item === item);
    const rereads = mine.filter(x => x.k === 'reread').length;
    const changes = mine.filter(x => x.k === 'reread').flatMap(x => x.p.changes || []);
    const changed = changes.find(c => c.old !== c.new && c.old !== undefined && c.new !== undefined);
    const checks = mine.filter(x => x.k === 'check');
    const last = checks[checks.length - 1];
    const ended = mine.find(x => x.k === 'item_end');
    const verdict = (d.vd || []).find(v => e.p.sums.includes(v.s));
    suspects.push({ beat: 'suspect', ms: MS.suspect, caption: '', item, sums: e.p.sums, entity: e.p.entity || null, read: e.p.read, wouldBe: e.p.would_be,
                    rereads, changed: changed ? { old: changed.old, new: changed.new } : null,
                    reread: changes.length ? changes[changes.length - 1].new : undefined,
                    computed: last ? last.p.computed : undefined, printed: last ? last.p.printed : undefined,
                    result: ended ? ended.p.result : null, verdict: verdict ? verdict.v : null, reason: verdict ? verdict.r : null,
                    page: e.p.entity ? e.p.entity[0] : (mine.find(x => x.p.page) || { p: {} }).p.page });
  });

  // the check: the sums that failed after the first read
  const failing = [...new Set(suspects.flatMap(s => s.sums))];
  const nFail = (d.sm && sumTotal(d.sm.sums_failing_before)) || failing.length;
  if (nFail > 0 && d.checks && d.checks.length) {
    steps.push({ beat: 'check', ms: MS.check, sums: failing, caption: `${fmt(nFail)} of ${fmt(d.checks.length)} printed sums do not hold.` });
  }
  for (const s of suspects) s.caption = suspectCaptions(s).first;
  steps.push(...suspects);

  // the audit: the findings by the page they are on
  if (items.length) {
    const pages = [...new Set(items.map(f => f.page).filter(x => x !== undefined))].sort((a, b) => a - b);
    steps.push({ beat: 'audit', ms: MS.audit, pages, caption: 'Laid against the published file' });
  }
  steps.push({ beat: 'end', ms: MS.end, caption: '' });
  const ms = steps.reduce((a, s) => a + s.ms, 0);
  return { steps, ms, seconds: ms / 1000 };
}

// what the suspect step says at each of its moments, from its own figures
export function suspectCaptions(s) {
  const first = s.read !== undefined && s.wouldBe !== undefined
    ? `Read ${fmt(s.read)}. The two printed sums that run through it need ${fmt(s.wouldBe)}.`
    : s.computed !== undefined && s.printed !== undefined
      ? `The cells add to ${fmt(s.computed)}. The printed total is ${fmt(s.printed)}.`
      : 'A printed sum does not hold here.';
  let then = null, ring = null;
  if (s.verdict === 'document_inconsistent') {
    const x = s.reread !== undefined ? s.reread : s.read;
    const times = s.rereads === 2 ? 'twice' : s.rereads > 2 ? `${s.rereads} times` : 'again';
    then = `Read ${fmt(x)} ${times}.${s.computed !== undefined ? ` The cells add to ${fmt(s.computed)}.` : ''} The document disagrees with itself. Listed for a person.`;
    ring = 'warn';
  } else if (s.verdict === 'cannot_verify') {
    then = `${sentence(s.reason)}. No printed total can decide this.`;
    ring = 'warn';
  } else if (s.changed) {
    then = `Read again: ${fmt(s.changed.new)}, not ${fmt(s.changed.old)}.${s.result === 'holds' ? ' Both sums now hold.' : ''}`;
    ring = s.result === 'holds' ? 'holds' : null;
  } else if (s.result === 'holds') {
    then = 'Read again: the same value. The sums now hold.';
    ring = 'holds';
  }
  return { first, then, ring };
}

const svg = (tag, attrs = {}) => {
  const e = document.createElementNS(SVGNS, tag);
  for (const k in attrs) e.setAttribute(k, attrs[k]);
  return e;
};

export class Replay {
  // o: {store, stage, loupe, els: {cap, btn, speedBtn, hint, headline, card, findings, loupeEl, leaderEl}, reduced, date, seconds,
  //     headline: {set(counts), full()}, restore(): Promise}
  constructor(o) {
    Object.assign(this, o);
    this.tl = buildTimeline(this.store.d);
    this.state = 'idle'; this.tok = 0; this.speed = 1; this.mem = new Map(); this.curPage = null;
    this.pos = 0;                 // how far the replay has got, in milliseconds of the default speed; it stands still while paused
    this.layer = svg('svg', { class: 'rp', 'aria-hidden': 'true' });
    this.stage.sheet.append(this.layer);
    this.setup();
  }
  get items() { return this.store.items; }
  get available() { return this.tl.steps.length > 0 && !this.disabled; }
  get animate() { return !this.reduced && this.speed === 1; }
  // the figure the label shows: the run's recorded seconds divided by the replay's seconds, so it is true
  get ratio() { return this.seconds ? Math.max(1, Math.round(this.seconds / (this.tl.seconds / this.speed))) : null; }

  setup() {
    const { btn, speedBtn, hint } = this.els;
    btn.disabled = !this.available;
    speedBtn.hidden = !this.available;
    btn.onclick = () => this.toggle();
    speedBtn.onclick = () => { this.speed = SPEEDS[(SPEEDS.indexOf(this.speed) + 1) % SPEEDS.length]; this.label(); };
    this.label();
    btn.textContent = 'Replay the audit';
    if (!this.available) hint.textContent = "Replay comes with the run's events";
  }
  label() {
    const { speedBtn, hint } = this.els;
    speedBtn.textContent = `Speed ${this.speed}x`;
    speedBtn.setAttribute('aria-label', `Replay speed ${this.speed}x. Change speed`);
    if (!this.available) return;
    const n = this.ratio;
    hint.textContent = `Replay · run of ${this.date}${n ? ` · ${fmt(n)}x` : ''}`;
  }
  button(text) { this.els.btn.textContent = text; }

  toggle() {
    if (!this.available) return;
    if (this.state === 'idle') this.start();
    else if (this.state === 'running') this.pause();
    else this.resume();
  }
  pause() {
    if (this.state !== 'running') return;
    this.state = 'paused';
    this.button('Resume replay');
    this.freeze(true);
  }
  resume() {
    if (this.state !== 'paused') return;
    this.state = 'running';
    this.button('Pause replay');
    this.freeze(false);
  }
  // running animations stop with the replay; anything started while it waits is stopped too
  freeze(on) {
    clearInterval(this.holdTimer);
    // the short entrances (a wash, a mark) jump to their end, so a paused sheet shows what has been read and found
    const hold = () => document.getAnimations().forEach(a => {
      if (a.playState !== 'running') return;
      const t = a.effect && a.effect.target;
      if (t && t.matches && t.matches('.wash, .tick, .frame, .paper, .marks, .rp *')) a.finish(); else a.pause();
    });
    if (on) { hold(); this.holdTimer = setInterval(hold, 100); }
    else document.getAnimations().forEach(a => { if (a.playState === 'paused') a.play(); });
  }

  // ---- running
  async start() {
    if (this.state !== 'idle' || !this.available) return;
    const tok = ++this.tok;
    this.state = 'running';
    this.began = performance.now();
    const { cap, card, findings, loupeEl } = this.els;
    document.body.classList.add('replaying');
    document.body.classList.remove('rp-ticks');
    this.loupe.tagEdge = 'bottom';
    for (const e of [card, findings]) e.setAttribute('aria-busy', 'true');
    loupeEl.classList.remove('rise');
    this.quietLoupe(true);
    this.stage.deselect();
    this.loupe.hideTag();
    this.button('Pause replay');
    this.headline.set({ all: 0, settled: 0, cannot: 0, doc: 0, confirmed: 0 });
    this.mem.clear(); this.layer.replaceChildren();
    for (const pg of this.store.pages) { const im = new Image(); im.src = pg.img; }   // the pages are fetched before they are needed
    try {
      this.pos = 0;
      this.clock(tok);
      let at = 0;
      for (const s of this.tl.steps) {
        if (tok !== this.tok) return;
        at += s.ms;
        await Promise.all([this.play(s, tok), this.until(at, tok)]);
      }
      this.seconds_played = (performance.now() - this.began) / 1000;
      this.finish();
    } catch (e) {
      if (e !== CANCELLED) { console.error(e); this.finish(); }
    }
  }
  // a selection by hand: the replay stops where it is and the page is left in its finished state
  stop() {
    if (this.state === 'idle' || this.restoring) return;
    this.tok++;
    this.finish();
  }
  finish() {
    this.freeze(false);
    this.state = 'idle';
    const { cap, card, findings } = this.els;
    document.body.classList.remove('replaying', 'rp-ticks');
    this.loupe.tagEdge = 'top';
    for (const e of [card, findings]) e.removeAttribute('aria-busy');
    cap.textContent = '';
    this.els.loupeEl.style.translate = '';
    this.layer.replaceChildren(); this.mem.clear(); this.curPage = null;
    this.quietLoupe(false);
    this.headline.full();
    this.button('Replay the audit');
  }
  quietLoupe(on) {
    this.els.loupeEl.classList.toggle('rp-off', on);
    this.els.leaderEl.classList.toggle('rp-off', on);
  }
  // the replay's own clock: it runs at the chosen speed and stands still while paused, so a step that ran long is made up
  // by the steps after it and the whole stays the length the label says
  clock(tok) {
    let last = performance.now();
    const tick = now => {
      if (tok !== this.tok || this.state === 'idle') return;
      if (this.state === 'running') this.pos += (now - last) * this.speed;
      last = now;
      requestAnimationFrame(tick);
    };
    requestAnimationFrame(tick);
  }
  // waits until the clock reads `target`
  until(target, tok) {
    return new Promise((res, rej) => {
      const tick = () => {
        if (tok !== this.tok) return rej(CANCELLED);
        if (this.pos >= target) res(); else requestAnimationFrame(tick);
      };
      tick();
    });
  }
  sleep(ms, tok) { return this.until(this.pos + ms, tok); }
  guard(tok) { if (tok !== this.tok) throw CANCELLED; }
  // the caption; a window so narrow that it runs to a second line (a page zoomed to 160 percent) pushes the loupe down
  // out of its way, by as much as it needs
  say(text) {
    const { cap, loupeEl } = this.els;
    cap.textContent = text;
    loupeEl.style.translate = '';
    const clash = cap.getBoundingClientRect().bottom + 4 - loupeEl.getBoundingClientRect().top;
    if (text && clash > 0) loupeEl.style.translate = `0 ${Math.ceil(clash)}px`;
  }

  async play(s, tok) {
    this.say(s.caption);
    switch (s.beat) {
      case 'sample': return this.sampleStep(s, tok);
      case 'read': return this.readStep(s, tok);
      case 'check': return this.checkStep(s, tok);
      case 'suspect': return this.suspectStep(s, tok);
      case 'audit': return this.auditStep(s, tok);
      case 'end': return this.endStep(tok);
    }
  }

  // ---- the layer on the sheet: what is drawn is kept per page, so a page that is turned back to shows it again
  async page(n, tok) {
    if (n === this.curPage || n === undefined) return;
    const dir = this.curPage !== null && n < this.curPage ? -1 : 1;
    this.curPage = n;
    await this.stage.setPage(n, this.animate, dir);
    this.guard(tok);
    if (this.onPage) this.onPage(n);
    const pg = this.store.pages.find(p => p.n === n);
    this.layer.setAttribute('viewBox', `0 0 ${pg.w} ${pg.h}`);
    this.layer.replaceChildren();
    for (const m of this.mem.get(n) || []) this.layer.append(this.node(m, false));
  }
  node(m, fresh) {
    if (m.type === 'rect') {
      const r = svg('rect', { x: m.x[0], y: m.x[1], width: m.x[2] - m.x[0], height: m.x[3] - m.x[1], class: m.cls });
      if (fresh && m.cls === 'wash') r.classList.add(this.animate ? 'sweep' : 'fade');
      else if (fresh) r.classList.add('fade');
      return r;
    }
    const l = svg('line', { x1: m.x1, y1: m.y1, x2: m.x2, y2: m.y2, class: m.cls });
    if (fresh && this.animate) {
      const len = Math.hypot(m.x2 - m.x1, m.y2 - m.y1);
      l.setAttribute('stroke-dasharray', `${len} ${len}`);
      l.animate([{ strokeDashoffset: len }, { strokeDashoffset: 0 }], { duration: 450, easing: 'cubic-bezier(.23,1,.32,1)', fill: 'backwards' });
    } else if (fresh) l.classList.add('fade');
    return l;
  }
  put(page, m) {
    if (!this.mem.has(page)) this.mem.set(page, []);
    this.mem.get(page).push(m);
    if (page === this.curPage) this.layer.append(this.node(m, true));
  }
  clearLayer() { this.mem.clear(); this.layer.replaceChildren(); }
  boxOf(page, block) { const b = this.store.blocks.get(`${page}:${block}`); return b && b.x ? b.x : null; }

  // ---- the steps
  async sampleStep(s, tok) {
    const first = (s.blocks[0] || '').match(/^p(\d+)-/);
    await this.page(first ? +first[1] : 1, tok);
    for (const id of s.blocks) {
      const m = /^p(\d+)-/.exec(id), x = m ? this.boxOf(+m[1], id) : null;
      if (x && +m[1] === this.curPage) this.put(this.curPage, { type: 'rect', cls: 'frame', x });
    }
  }
  async readStep(s, tok) {
    if (s.first) this.clearLayer();
    await this.page(s.page, tok);
    const x = this.boxOf(s.page, s.block);
    if (x) this.put(s.page, { type: 'rect', cls: 'wash', x });
  }
  async checkStep(s, tok) {
    this.clearLayer();
    const checks = s.sums.map(k => this.store.chk.get(checkKey(k))).filter(Boolean);
    const pages = [...new Set(checks.map(c => c.p))].sort((a, b) => a - b);
    const each = (s.ms - 400) / Math.max(1, pages.length);
    for (const n of pages) {
      await this.page(n, tok);
      for (const c of checks.filter(c => c.p === n)) {
        const line = this.store.band(c);
        if (line) this.put(n, { type: 'line', cls: 'sum fails', ...line });
      }
      await this.sleep(Math.max(0, each - (this.animate ? 420 : 0)), tok);
    }
  }
  valueOf(s) {
    const { store } = this;
    if (s.entity) { const i = store.byId.get(s.entity.join(':')); if (i !== undefined) return i; }
    const c = s.sums.map(k => store.chk.get(checkKey(k))).find(Boolean);
    if (!c) return null;
    const t = store.totalOf(c);
    return t && t.x ? t.i : store.firstValue(c);
  }
  async suspectStep(s, tok) {
    const { store, stage, loupe } = this;
    const i = this.valueOf(s);
    this.clearLayer();
    if (i === null) return;                          // nothing on the sheet to point at: the step is left out
    const v = store.values[i], said = suspectCaptions(s);
    await this.page(v.p, tok);
    this.say(said.first);
    // the sums that run through the value, drawn as failing: that is what the run saw on the first read
    const mine = new Set(s.sums.map(checkKey));
    let sums = store.sumsFor(v);
    if (sums.some(x => mine.has(`${x.check.k}:${x.check.p}:${x.check.b}:${x.check.y}`))) sums = sums.filter(x => mine.has(`${x.check.k}:${x.check.p}:${x.check.b}:${x.check.y}`));
    sums = sums.map(x => ({ ...x, check: { ...x.check, ok: false } }));
    this.quietLoupe(false);
    const done = await stage.select(i, sums, this.animate, {});
    this.guard(tok);
    if (!done) return;
    await this.sleep(s.ms * 0.1, tok);
    if (said.then) {
      if (s.changed) loupe.setTag(`first read ${fmt(s.changed.old)} · read again ${fmt(s.changed.new)}`);
      if (said.ring) this.recolor(said.ring);
      this.say(said.then);
    }
  }
  // the lines and the ring of the value being looked at: holds (both sums hold now), or warn (the ring only: nothing decides it)
  recolor(cls) {
    for (const e of this.stage.bands.querySelectorAll('line')) e.setAttribute('class', cls === 'holds' ? 'holds' : 'fails');
    for (const e of this.stage.bands.querySelectorAll('circle[class]')) e.setAttribute('class', cls);
    this.loupe.setRing(cls);
  }
  async auditStep(s, tok) {
    const { store, stage } = this;
    this.clearLayer();
    stage.deselect();
    this.quietLoupe(true);
    this.loupe.hideTag();
    const all = this.items, per = (s.ms - 300) / Math.max(1, s.pages.length);
    document.body.classList.add('rp-ticks');
    let from = { all: 0, settled: 0, cannot: 0, doc: 0, confirmed: 0 };
    for (const n of s.pages) {
      await this.page(n, tok);
      stage.marks.querySelectorAll('.tick').forEach((t, k) => { t.classList.add('pop'); t.style.animationDelay = this.animate ? `${Math.min(k * 14, 400)}ms` : '0ms'; });
      const to = this.countsTo(all, n);
      await this.countUp(from, to, Math.min(per, 600), tok);
      from = to;
      await this.sleep(Math.max(0, per - 600), tok);
    }
    this.headline.full();
  }
  countsTo(items, page) {
    const got = items.filter(f => f.page !== undefined && f.page <= page);
    return { all: got.length, settled: got.filter(f => f.status === 'settled_against_file').length, cannot: got.filter(f => f.status === 'cannot_verify').length,
             doc: got.filter(f => f.status === 'document_inconsistent').length, confirmed: got.filter(f => f.confirmed_by_person).length };
  }
  countUp(a, b, ms, tok) {
    return new Promise((res, rej) => {
      const t0 = this.pos;
      const step = () => {
        if (tok !== this.tok) return rej(CANCELLED);
        const t = this.animate ? Math.min(1, (this.pos - t0) / ms) : 1;
        const at = {};
        for (const k in b) at[k] = Math.round(a[k] + (b[k] - a[k]) * t);
        this.headline.set(at);
        if (t < 1) requestAnimationFrame(step); else res();
      };
      requestAnimationFrame(step);
    });
  }
  async endStep(tok) {
    // the page goes back to its opening finding, drawn as on load; the page's own select must not stop this replay
    this.restoring = true;
    this.layer.replaceChildren(); this.mem.clear();
    this.headline.full();
    this.quietLoupe(false);
    try { await this.restore(this.animate); } finally { this.restoring = false; }
  }
}
