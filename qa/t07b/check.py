"""Behaviour checks for T07b: python qa/t07b/check.py. Writes qa/t07b/checks.json."""
import sys, json, time
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))
from lib import *
from playwright.sync_api import sync_playwright
out = {}

FIRST = """() => { const q = s => document.querySelector(s); const bb = e => { const b = e.getBoundingClientRect(); return {top: Math.round(b.top), bottom: Math.round(b.bottom)}; };
  const panel = q('#panel').getBoundingClientRect();
  const inside = e => { const b = e.getBoundingClientRect(); return b.top >= panel.top - 0.5 && b.bottom <= panel.bottom + 0.5; };
  const rows = [...document.querySelectorAll('#flist li.fnd')].filter(inside).length, groups = [...document.querySelectorAll('#flist li.grp')].filter(inside).length;
  return { viewport: [innerWidth, innerHeight], panel: bb(q('#panel')), panelScrollTop: q('#panel').scrollTop, headline: q('#fcount').innerText, headlineInside: inside(q('#fcount')),
    headlineFigureFont: getComputedStyle(q('.hl-n.settled')).fontFamily.slice(0, 40),
    values: [...document.querySelectorAll('.two-values .one')].map(e => ({text: e.innerText.replace(/\\n/g, ' '), inside: inside(e)})),
    tapeSums: [...document.querySelectorAll('#tape .sum.two')].map(e => ({heads: [...e.querySelectorAll('h4')].map(h => h.innerText), verdicts: [...e.querySelectorAll('.res')].map(r => r.innerText), inside: inside(e)})),
    card: {top: bb(q('#card')).top, bottom: bb(q('#card')).bottom, inside: inside(q('#card'))}, groupLines: groups, findingRowsFullyInside: rows,
    chipsOneLine: (() => { const c = [...document.querySelectorAll('.chip')]; return new Set(c.map(x => Math.round(x.getBoundingClientRect().top))).size === 1; })(),
    sheetSideways: document.documentElement.scrollWidth > innerWidth, replayLabel: q('#replay-hint').innerText, replayDisabled: q('#replay').disabled, speed: q('#speed').innerText,
    dockTop: Math.round(q('.dock').getBoundingClientRect().top), valuesBottom: Math.round(q('.two-values').getBoundingClientRect().bottom), ticks: document.querySelectorAll('.tick').length,
    tickShape: (() => { const t = q('.tick circle'); const s = getComputedStyle(t); return {tag: t.tagName, r: t.getAttribute('r'), strokeWidth: s.strokeWidth, fill: s.fill, stroke: s.stroke}; })() }; }"""

def wait_done(pg, secs=70):
    pg.wait_for_function("!document.body.classList.contains('replaying')", timeout=secs * 1000)

with sync_playwright() as p:
    b = p.chromium.launch()
    # 1. the first screen with no input
    for w, h in ((1440, 900), (1024, 768), (390, 844), (320, 640)):
        ctx, pg, errs = open_page(b, w, h)
        r = pg.evaluate(FIRST); r["errors"] = errs; out[f"first-{w}x{h}"] = r; ctx.close()
    # 2. the replay at 1x: its measured length, its label, pause / resume, and the finished state it returns to
    ctx, pg, errs = open_page(b, 1440, 900)
    label = pg.evaluate("document.getElementById('replay-hint').innerText")
    before = pg.evaluate("({sel: document.querySelector('#flist li[aria-selected=true]').dataset.id, h2: document.querySelector('#card h2').innerText, tag: document.querySelector('.lp-tag').innerText, count: document.getElementById('fcount').innerText, page: document.getElementById('pageno').innerText})")
    pg.get_by_role("button", name="Replay the audit").click()
    t0 = time.time()
    pg.wait_for_timeout(1500)
    run = {"label": label, "buttonWhileRunning": pg.evaluate("document.getElementById('replay').textContent"),
           "busy": pg.evaluate("[document.getElementById('card').getAttribute('aria-busy'), document.getElementById('findings').getAttribute('aria-busy')]"),
           "captionLive": pg.evaluate("document.getElementById('rp-cap').getAttribute('aria-live')"), "captionFont": pg.evaluate("getComputedStyle(document.getElementById('rp-cap')).fontSize")}
    pg.keyboard.press("Escape"); pg.wait_for_timeout(300)
    run["afterEscape"] = pg.evaluate("document.getElementById('replay').textContent")
    c1 = pg.evaluate("document.getElementById('rp-cap').textContent"); pg.wait_for_timeout(1500)
    run["captionHeldWhilePaused"] = c1 == pg.evaluate("document.getElementById('rp-cap').textContent")
    pg.keyboard.press("Alt+Shift+P"); pg.wait_for_timeout(300)
    run["afterAltShiftP"] = pg.evaluate("document.getElementById('replay').textContent")
    pg.get_by_role("button", name="Pause replay").click(); pg.wait_for_timeout(200)
    run["afterButton"] = pg.evaluate("document.getElementById('replay').textContent")
    pg.get_by_role("button", name="Resume replay").click()
    paused_s = 1.5 + 0.3 + 0.0
    wait_done(pg)
    total = time.time() - t0
    run["wallSecondsIncludingPause"] = round(total, 1)
    pg.wait_for_timeout(1200)
    run["after"] = pg.evaluate("({sel: document.querySelector('#flist li[aria-selected=true]').dataset.id, h2: document.querySelector('#card h2').innerText, tag: document.querySelector('.lp-tag').innerText, count: document.getElementById('fcount').innerText, page: document.getElementById('pageno').innerText, button: document.getElementById('replay').textContent, busy: document.getElementById('card').getAttribute('aria-busy'), cap: document.getElementById('rp-cap').textContent})")
    run["before"] = before; run["sameFinishedState"] = {k: before[k] == run["after"][k] for k in before}
    run["errors"] = errs; out["replay-1x"] = run; ctx.close()
    # 3. a length with no pause at all, and what the label says
    ctx, pg, errs = open_page(b, 1440, 900)
    pg.get_by_role("button", name="Replay the audit").click(); t0 = time.time(); pg.wait_for_timeout(500)
    wait_done(pg); out["replay-length"] = {"seconds": round(time.time() - t0, 1), "label": label, "errors": errs}; ctx.close()
    # 4. speed cycles 1x, 2x, 4x and the label follows
    ctx, pg, errs = open_page(b, 1440, 900)
    seen = []
    for _ in range(4):
        seen.append([pg.evaluate("document.getElementById('speed').innerText"), pg.evaluate("document.getElementById('replay-hint').innerText")])
        pg.get_by_role("button", name="Speed", exact=False).click()
    out["speed"] = {"cycle": seen}
    for name in ("2x", "4x"):                                    # the four clicks left it at 2x
        if name == "4x": pg.get_by_role("button", name="Speed", exact=False).click()
        label_now = pg.evaluate("document.getElementById('replay-hint').innerText")
        pg.get_by_role("button", name="Replay the audit").click(); t0 = time.time(); pg.wait_for_timeout(500)
        wait_done(pg); out["speed"][f"secondsAt{name}"] = round(time.time() - t0, 1); out["speed"][f"labelAt{name}"] = label_now
    out["speed"]["errors"] = errs; ctx.close()
    # 5. a selection by hand stops the replay and leaves the finished state
    ctx, pg, errs = open_page(b, 1440, 900)
    pg.get_by_role("button", name="Replay the audit").click(); pg.wait_for_timeout(3500)
    pg.evaluate("document.querySelectorAll('#flist li.fnd')[3].click()"); pg.wait_for_timeout(2200)
    out["hand-select"] = pg.evaluate("({replaying: document.body.classList.contains('replaying'), button: document.getElementById('replay').textContent, cap: document.getElementById('rp-cap').textContent, busy: document.getElementById('card').getAttribute('aria-busy'), count: document.getElementById('fcount').innerText, sel: document.querySelector('#flist li[aria-selected=true]').dataset.id, loupeHidden: document.getElementById('loupe').classList.contains('rp-off')})"); out["hand-select"]["errors"] = errs
    ctx.close()
    # 6. reduced motion: the same steps, no wash or draw-on animation
    ctx, pg, errs = open_page(b, 1440, 900, reduced_motion="reduce")
    pg.get_by_role("button", name="Replay the audit").click(); t0 = time.time()
    seen = {"maxRunning": 0, "captions": set()}
    while pg.evaluate("document.body.classList.contains('replaying')") or time.time() - t0 < 2:
        n = pg.evaluate("document.getAnimations().filter(a => a.playState === 'running' && !['opacity', 'fade'].includes(a.animationName || a.transitionProperty)).map(a => a.animationName || a.transitionProperty || a.constructor.name).join(',')")
        seen["maxRunning"] = max(seen["maxRunning"], len([x for x in n.split(',') if x]))
        seen["captions"].add(pg.evaluate("document.getElementById('rp-cap').textContent")[:30])
        pg.wait_for_timeout(250)
        if time.time() - t0 > 70: break
    out["reduced"] = {"seconds": round(time.time() - t0, 1), "otherAnimationsRunning": seen["maxRunning"], "captionsSeen": len(seen["captions"]), "washAnimation": pg.evaluate("getComputedStyle(document.body).animationName"), "errors": errs}; ctx.close()
    # 7. no events: the button is disabled with the reason beside it
    ctx = b.new_context(viewport={"width": 1440, "height": 900}); pg = ctx.new_page()
    def strip(route):
        r = route.fetch(); d = r.json(); d["events"] = []
        route.fulfill(response=r, body=json.dumps(d))
    pg.route("**/data/panola.json", strip)
    pg.goto(BASE); pg.wait_for_timeout(2500)
    out["no-events"] = pg.evaluate("({disabled: document.getElementById('replay').disabled, hint: document.getElementById('replay-hint').innerText, speedHidden: document.getElementById('speed').hidden, describedby: document.getElementById('replay').getAttribute('aria-describedby')})"); ctx.close()
    b.close()
(OUT / "checks.json").write_text(json.dumps(out, indent=1))
print(json.dumps(out, indent=1))
