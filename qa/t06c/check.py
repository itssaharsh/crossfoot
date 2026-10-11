"""Behaviour checks for T06c: python qa/t06c/check.py. Writes qa/t06c/checks.json."""
import http.server, socketserver, threading, functools, pathlib, json, copy
from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parents[2]
class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a, **k): pass
srv = socketserver.TCPServer(("127.0.0.1", 0), functools.partial(Quiet, directory=str(ROOT / "site")))
threading.Thread(target=srv.serve_forever, daemon=True).start()
BASE = f"http://127.0.0.1:{srv.server_address[1]}/"
out = {}

def page(b, w=1440, h=900, q="", route=None, **kw):
    ctx = b.new_context(viewport={"width": w, "height": h}, **kw); pg = ctx.new_page()
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.on("console", lambda m: errs.append(m.text) if m.type == "error" else None)
    if route: route(pg)
    pg.goto(BASE + q); pg.wait_for_timeout(2200)
    return ctx, pg, errs

with sync_playwright() as p:
    b = p.chromium.launch()
    # 1. opening state: 1440 and 390, no input
    for w, h in ((1440, 900), (390, 844)):
        ctx, pg, errs = page(b, w, h)
        r = pg.evaluate("""() => { const q = s => document.querySelector(s); const bb = e => { const r = q(e).getBoundingClientRect(); return [Math.round(r.top), Math.round(r.bottom)]; };
          return { card: q('#card').innerText.slice(0, 160), fileFig: q('.two-values .file .fig').innerText, scanFig: q('.two-values .scan .fig').innerText,
                   tag: q('.lp-tag').innerText, tagOn: q('.lp-tag').classList.contains('on'), ring: !!q('.lp-ring'), ring2: !!q('.lp-ring2'),
                   ctx: q('#ctx').innerText, pairs: document.querySelectorAll('#tape .sum.two').length, heads: [...document.querySelectorAll('#tape .heads h4')].slice(0,2).map(x => x.innerText),
                   valuesTop: bb('.two-values'), dockTop: Math.round(q('.dock').getBoundingClientRect().top), vh: innerHeight, ticks: document.querySelectorAll('.tick').length,
                   count: q('#fcount').innerText, selected: document.querySelectorAll('#flist [aria-selected=true]').length, scrollX: document.documentElement.scrollWidth > innerWidth,
                   judge: getComputedStyle(q('.judge')).display, replayDisabled: q('#replay').disabled }; }""")
        r["errors"] = errs
        out[f"open-{w}"] = r
        ctx.close()
    # 2. record mode hides the judge list
    ctx, pg, errs = page(b, q="?record=1")
    out["record"] = {"judge": pg.evaluate("getComputedStyle(document.querySelector('.judge')).display"), "errors": errs}; ctx.close()
    # 3. keyboard: one tab stop for the list, arrows move, Enter selects
    ctx, pg, errs = page(b)
    pg.evaluate("document.getElementById('flist').focus()")
    before = pg.evaluate("document.querySelector('#flist li[aria-selected=true]').dataset.id")
    for _ in range(3): pg.keyboard.press("ArrowDown")
    cur = pg.evaluate("document.querySelector('#flist li.cur').dataset.id")
    pg.keyboard.press("Enter"); pg.wait_for_timeout(1800)
    after = pg.evaluate("document.querySelector('#flist li[aria-selected=true]').dataset.id")
    out["keyboard"] = {"before": before, "cur_after_3_down": cur, "selected_after_enter": after,
                       "card_h2": pg.evaluate("document.querySelector('#card h2').innerText"),
                       "listbox_tabindex": pg.evaluate("document.getElementById('flist').tabIndex"),
                       "options_tabbable": pg.evaluate("[...document.querySelectorAll('#flist li')].filter(l => l.tabIndex >= 0).length"), "errors": errs}
    # dialog focus return
    pg.get_by_role("button", name="Open crop", exact=True).focus(); pg.keyboard.press("Enter"); pg.wait_for_timeout(500)
    open_ = pg.evaluate("document.getElementById('dlg').open")
    pg.keyboard.press("Escape"); pg.wait_for_timeout(300)
    out["dialog"] = {"opened": open_, "closed": not pg.evaluate("document.getElementById('dlg').open"),
                     "focus_back_on": pg.evaluate("document.activeElement.innerText")}
    ctx.close()
    # 4. filters
    ctx, pg, errs = page(b)
    pg.get_by_role("button", name="cannot verify", exact=True).click()
    out["filter"] = {"rows": pg.evaluate("document.querySelectorAll('#flist li.fnd').length"), "showing": pg.evaluate("document.getElementById('fshowing').innerText"),
                     "pressed": pg.evaluate("document.querySelector('.chip[aria-pressed=true]').innerText")}
    pg.get_by_role("button", name="wrong number", exact=True).click()
    out["filter"]["status_and_kind"] = pg.evaluate("document.querySelectorAll('#flist li.fnd').length"); ctx.close()
    # 5. a long list (more than 200 rows) renders only what is near the viewport
    def many(pg):
        def handle(route):
            r = route.fetch(); d = json.loads(r.text()); fd = d["fd"]; items = fd["items"]; groups = fd["groups"]
            n = len(items)
            for k in range(1, 4):
                for f in items[:n]:
                    g = copy.deepcopy(f); g["id"] = f"{f['id']}x{k}"; g["group"] = f"{f['group']}x{k}"; items.append(g)
                for gg in groups[:46]:
                    h = copy.deepcopy(gg); h["id"] = f"{gg['id']}x{k}"; h["findings"] = [f"{i}x{k}" for i in gg["findings"]]; groups.append(h)
            route.fulfill(response=r, body=json.dumps(d))
        pg.route("**/data/panola.json", handle)
    ctx, pg, errs = page(b, route=many)
    pg.evaluate("document.getElementById('findings').scrollIntoView()")
    pg.wait_for_timeout(400)
    v = pg.evaluate("({virtual: document.getElementById('flist').classList.contains('virtual'), rendered: document.querySelectorAll('#flist li').length, count: document.getElementById('fcount').innerText})")
    pg.evaluate("document.getElementById('panel').scrollTop = 6000"); pg.wait_for_timeout(400)
    v["rendered_after_scroll"] = pg.evaluate("document.querySelectorAll('#flist li').length")
    v["first_after_scroll"] = pg.evaluate("document.querySelector('#flist li.fnd') && document.querySelector('#flist li.fnd').dataset.id")
    v["errors"] = errs; out["virtual"] = v; ctx.close()
    # 6. county tabs when the build holds two counties; none with one
    def two(pg):
        def idx(route):
            r = route.fetch(); d = json.loads(r.text()); d["counties"].append({"key": "second", "name": "Second", "file": "data/second.json", "pages": 6})
            route.fulfill(response=r, body=json.dumps(d))
        def second(route):
            r = route.fetch(url=BASE + "data/panola.json"); route.fulfill(response=r)
        pg.route("**/data/index.json", idx); pg.route("**/data/second.json", second)
    ctx, pg, errs = page(b, route=two)
    out["tabs"] = {"buttons": pg.evaluate("[...document.querySelectorAll('#tabs button')].map(b => b.innerText + ':' + b.getAttribute('aria-pressed'))")}
    pg.get_by_role("button", name="Second").click(); pg.wait_for_timeout(2500)
    out["tabs"]["after_click"] = pg.evaluate("[...document.querySelectorAll('#tabs button')].map(b => b.innerText + ':' + b.getAttribute('aria-pressed'))")
    out["tabs"]["card"] = pg.evaluate("document.querySelector('#card h2').innerText"); out["tabs"]["errors"] = errs; ctx.close()
    ctx, pg, errs = page(b)
    out["tabs"]["one_county_hidden"] = pg.evaluate("document.getElementById('tabs').hidden"); ctx.close()
    # 7. ?cell= still works; ?finding= picks; a finding with no place shows the crop
    ctx, pg, errs = page(b, q="?cell=2:p2-b5:EARLY:1")
    out["cell_param"] = {"card": pg.evaluate("document.querySelector('#card h2').innerText"), "errors": errs}; ctx.close()
    ctx, pg, errs = page(b, q="?finding=f080")
    out["no_place"] = pg.evaluate("({crop: !!document.querySelector('.lp-crop'), ring: !!document.querySelector('.lp-ring'), tag: !!document.querySelector('.lp-tag.on')})"); out["no_place"]["errors"] = errs; ctx.close()
    # 8. widths: no sideways scroll, nothing under 12 px
    widths = {}
    for w, h in ((320, 640), (360, 740), (390, 844), (600, 800), (899, 900), (900, 800), (1024, 768), (1100, 800), (1440, 900)):
        ctx, pg, errs = page(b, w, h)
        widths[f"{w}x{h}"] = pg.evaluate("""() => { let small = []; for (const e of document.querySelectorAll('body *')) { if (!e.childNodes.length) continue; const t = [...e.childNodes].some(n => n.nodeType === 3 && n.textContent.trim()); if (!t) continue; const cs = getComputedStyle(e); if (cs.display === 'none' || cs.visibility === 'hidden') continue; const r = e.getBoundingClientRect(); if (!r.width || e.closest('.sr') || cs.position === 'absolute' && r.width <= 1) continue; if (parseFloat(cs.fontSize) < 12) small.push(e.className + ':' + cs.fontSize); }
              return { sideways: document.documentElement.scrollWidth > innerWidth, small: small.slice(0, 5) }; }""")
        ctx.close()
    out["widths"] = widths
    # 9. reduced motion: nothing running
    ctx, pg, errs = page(b, reduced_motion="reduce")
    out["reduced"] = pg.evaluate("({anims: document.getAnimations().filter(a => a.playState === 'running').length, tape: document.querySelectorAll('#tape [style*=hidden]').length})"); ctx.close()
    b.close()
(ROOT / "qa" / "t06c" / "checks.json").write_text(json.dumps(out, indent=1))
print(json.dumps(out, indent=1))
