"""Behaviour checks for T07a (no pass/fail framework: prints what it measured). python qa/t07a/check.py"""
import http.server, socketserver, threading, functools, pathlib, json, sys
from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = ROOT / "qa" / "t07a"
class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a, **k): pass
srv = socketserver.TCPServer(("127.0.0.1", 0), functools.partial(Quiet, directory=str(ROOT / "site")))
threading.Thread(target=srv.serve_forever, daemon=True).start()
BASE = f"http://127.0.0.1:{srv.server_address[1]}/"
out = {}

with sync_playwright() as p:
    b = p.chromium.launch()
    # 1. no sideways scroll, no text under 12 px, touch targets
    for w, h in [(320, 640), (360, 740), (390, 844), (600, 800), (899, 700), (900, 700), (1024, 768), (1100, 800), (1440, 900)]:
        ctx = b.new_context(viewport={"width": w, "height": h}); pg = ctx.new_page(); errs = []
        pg.on("pageerror", lambda e: errs.append(str(e))); pg.on("console", lambda m: m.type == "error" and errs.append(m.text))
        pg.goto(BASE); pg.wait_for_timeout(1500)
        r = pg.evaluate("""() => {
          const sw = document.documentElement.scrollWidth, small = [];
          for (const e of document.querySelectorAll('body *')) {
            if (!e.offsetParent && getComputedStyle(e).position !== 'fixed') continue;
            if (e.closest('svg')) continue;
            const t = [...e.childNodes].some(n => n.nodeType === 3 && n.textContent.trim());
            if (t) { const fs = parseFloat(getComputedStyle(e).fontSize); if (fs < 12) small.push([e.className || e.tagName, fs]); }
          }
          const tt = [];
          for (const e of document.querySelectorAll('button, a, [role=option], .list li')) {
            if (!e.offsetParent && getComputedStyle(e).position !== 'fixed') continue;
            const b = e.getBoundingClientRect(); if (b.width && (b.height < 44 || b.width < 44)) tt.push([e.id || e.className || e.textContent.slice(0, 20), Math.round(b.width), Math.round(b.height)]);
          }
          return {sw, iw: innerWidth, small, tt};
        }""")
        out[f"{w}x{h}"] = {"scrollWidth": r["sw"], "innerWidth": r["iw"], "textUnder12": r["small"], "targetsUnder44": r["tt"], "errors": errs}
        ctx.close()
    # 2. keyboard
    ctx = b.new_context(viewport={"width": 1440, "height": 900}); pg = ctx.new_page(); errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto(BASE); pg.wait_for_timeout(1500)
    order = []
    for _ in range(14):
        pg.keyboard.press("Tab")
        order.append(pg.evaluate("() => { const e = document.activeElement; return (e.id || e.className.baseVal || e.className || e.tagName) + ' | ' + (e.getAttribute('aria-label') || e.textContent || '').trim().slice(0, 28); }"))
    out["tab_order"] = order
    # focus visible: outline on a button, focus ring on a sheet value
    pg.goto(BASE); pg.wait_for_timeout(1500)
    for _ in range(4): pg.keyboard.press("Tab")
    out["focus_style_after_4_tabs"] = pg.evaluate("() => { const e = document.activeElement; const c = getComputedStyle(e); return [e.tagName, e.id || e.getAttribute('role'), c.outlineWidth, c.outlineColor, c.outlineStyle]; }")
    # arrows in the sheet's values: find the rect with tabindex 0
    pg.focus("#marks rect[tabindex='0']"); pg.wait_for_timeout(300)
    before = pg.evaluate("() => document.activeElement.getAttribute('aria-label')")
    pg.keyboard.press("ArrowDown"); pg.wait_for_timeout(500)
    after = pg.evaluate("() => document.activeElement.getAttribute('aria-label')")
    peek = pg.evaluate("() => !!document.querySelector('.lp-peek')")
    ring_vis = pg.evaluate("() => { const g = document.querySelector('.focus-ring'); return g && g.getAttribute('display') }")
    pg.screenshot(path=str(OUT / "keyboard-arrow.png"))
    pg.keyboard.press("Enter"); pg.wait_for_timeout(2500)
    out["arrows"] = {"before": before, "after_ArrowDown": after, "loupe_peek_shown": peek, "focus_ring_display_attr": ring_vis,
                     "card_after_enter": pg.inner_text("#card h2")}
    pg.screenshot(path=str(OUT / "keyboard-enter.png"))
    # shortcuts
    pg.keyboard.press("Alt+Shift+KeyP"); pg.wait_for_timeout(200)
    out["alt_shift_p_errors"] = list(errs)
    pg.goto(BASE + "?state=empty"); pg.wait_for_timeout(1200)
    pg.keyboard.press("Alt+Shift+KeyR"); pg.wait_for_timeout(2500)
    out["alt_shift_r"] = {"url": pg.url.replace(BASE, "/"), "state": pg.evaluate("() => document.body.dataset.state")}
    pg.goto(BASE + "?state=empty&reset=1"); pg.wait_for_timeout(2500)
    out["reset_param"] = {"url": pg.url.replace(BASE, "/"), "state": pg.evaluate("() => document.body.dataset.state")}
    ctx.close()
    # 3. entrance length and reduced motion
    ctx = b.new_context(viewport={"width": 1440, "height": 900}); pg = ctx.new_page()
    pg.add_init_script("window.__t0 = performance.now();")
    pg.goto(BASE)
    pg.wait_for_function("document.body.dataset.state === 'ready'")
    t_ready = pg.evaluate("performance.now()")
    pg.wait_for_function("document.querySelectorAll('#tape .ln').length > 0 && [...document.querySelectorAll('#tape .ln, #tape .res')].every(e => e.style.visibility !== 'hidden')", timeout=5000)
    t_done = pg.evaluate("performance.now()")
    out["entrance_ms_from_ready_to_tape_complete"] = round(t_done - t_ready)
    ctx.close()
    ctx = b.new_context(viewport={"width": 1440, "height": 900}, reduced_motion="reduce"); pg = ctx.new_page()
    pg.goto(BASE); pg.wait_for_timeout(300)
    out["reduced"] = pg.evaluate("""() => ({flatLabel: document.getElementById('flat').textContent,
        anims: document.getAnimations().length, loupeAnim: getComputedStyle(document.getElementById('loupe')).animationName,
        tapeHidden: [...document.querySelectorAll('#tape .ln')].filter(e => e.style.visibility === 'hidden').length})""")
    ctx.close()
    # 4. record mode at 160 percent zoom (1440 px window -> 900 css px)
    for rec in ("", "?record=1"):
        ctx = b.new_context(viewport={"width": 900, "height": 563}, device_scale_factor=1.6); pg = ctx.new_page()
        pg.goto(BASE + rec); pg.wait_for_timeout(1800)
        pg.screenshot(path=str(OUT / f"zoom160{'-record' if rec else ''}.png"))
        out[f"zoom160{rec}"] = pg.evaluate("() => ({sw: document.documentElement.scrollWidth, iw: innerWidth, bar: document.querySelector('.bar').getBoundingClientRect().height, descr: getComputedStyle(document.querySelector('.descriptor')).fontSize})")
        ctx.close()
    b.close()
(OUT / "checks.json").write_text(json.dumps(out, indent=1))
print(json.dumps(out, indent=1))
