"""Behaviour checks for T07c, results in qa/final/checks.json:  python3 tools/qa/check.py
tabs (one tab stop, arrow keys, ?county=, sideways scroll inside the bar on a small screen), the run line, the states, a whole
replay of San Saba and of Cottle, the loupe's figure size, and the page's width at four window sizes."""
import sys, json
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))
from lib import *
from playwright.sync_api import sync_playwright

R = {}
def note(k, v): R[k] = v; print(k, json.dumps(v)[:300], flush=True)

with sync_playwright() as p:
    b = p.chromium.launch()
    # tabs
    ctx, pg, errs = open_page(b, 1440, 900, "?county=lynn", wait=2500)
    tabs = pg.evaluate("[...document.querySelectorAll('#tabs button')].map(b => ({text: b.textContent.replace(/\\s+/g, ' ').trim(), stop: b.tabIndex === 0, sel: b.getAttribute('aria-selected')}))")
    note("tabs", tabs)
    note("tab_stops", sum(t["stop"] for t in tabs))
    note("selected_by_query", [t["text"] for t in tabs if t["sel"] == "true"])
    pg.locator("#tabs [aria-selected=true]").focus()
    pg.keyboard.press("ArrowRight"); a = pg.evaluate("document.activeElement.textContent.replace(/\\s+/g,' ').trim()")
    pg.keyboard.press("End"); e = pg.evaluate("document.activeElement.textContent.replace(/\\s+/g,' ').trim()")
    pg.keyboard.press("ArrowRight"); w = pg.evaluate("document.activeElement.textContent.replace(/\\s+/g,' ').trim()")
    pg.keyboard.press("Home"); h = pg.evaluate("document.activeElement.textContent.replace(/\\s+/g,' ').trim()")
    note("arrow_keys", {"ArrowRight": a, "End": e, "ArrowRight_wraps": w, "Home": h})
    pg.keyboard.press("Enter"); pg.wait_for_timeout(2500)
    note("enter_opens", {"url": pg.evaluate("location.search"), "selected": pg.evaluate("document.querySelector('#tabs [aria-selected=true]').textContent.replace(/\\s+/g,' ').trim()"),
                         "card": pg.evaluate("document.querySelector('#card h2') ? document.querySelector('#card h2').textContent : null")})
    note("run_line", pg.evaluate("document.getElementById('runline').textContent"))
    note("errors_tabs", errs); ctx.close()
    # small screen: the tabs scroll inside the bar, the page does not move
    ctx, pg, errs = open_page(b, 390, 844, "?county=foard", wait=2500)
    note("tabs_390", pg.evaluate("(() => { const n = document.getElementById('tabs'); return {scrolls_inside: n.scrollWidth > n.clientWidth, bar_h: document.querySelector('.bar').offsetHeight, page_overflow: document.documentElement.scrollWidth > innerWidth, tab_h: document.querySelector('#tabs button').offsetHeight}; })()"))
    note("run_line_above_stage_390", pg.evaluate("(() => { const r = document.getElementById('runline').getBoundingClientRect(), s = document.getElementById('stage').getBoundingClientRect(); return {runline_bottom: Math.round(r.bottom), stage_top: Math.round(s.top)}; })()"))
    ctx.close()
    # no sideways scroll
    for w, h in ((1440, 900), (1024, 768), (390, 844), (320, 640)):
        for q in ("", "?county=jones&finding=f009", "?county=cottle", "?county=limestone"):
            ctx, pg, errs = open_page(b, w, h, q, wait=1800)
            note(f"overflow_{w}_{q or 'panola'}", pg.evaluate("document.documentElement.scrollWidth > innerWidth || document.body.scrollWidth > innerWidth"))
            ctx.close()
    # a one-county build shows no tabs and no run line
    ctx = b.new_context(viewport={"width": 1440, "height": 900}); pg = ctx.new_page()
    def one(route):
        r = route.fetch(); d = r.json(); d["counties"] = d["counties"][:1]; route.fulfill(response=r, json=d)
    pg.route("**/data/index.json", one); pg.goto(BASE, wait_until="load"); pg.wait_for_timeout(2500)
    note("one_county", pg.evaluate("({tabs_hidden: document.getElementById('tabs').hidden, runline_hidden: document.getElementById('runline').hidden})")); ctx.close()
    # the loupe at reading size: the ringed figure's height on screen
    for w, h in ((1440, 900), (390, 844), (1440, 650)):
        for q in ("?county=san_saba", "?county=jones&finding=f009", "?county=lynn&finding=f004"):
            ctx, pg, errs = open_page(b, w, h, q, wait=2600)
            hh = pg.evaluate("""(() => { const l = document.querySelector('.lp-layer'); const ring = document.querySelector('.lp-ring'); if (!l || !ring) return null;
                const m = new DOMMatrix(getComputedStyle(l.querySelector('.lp-pan')).transform); const s = m.a;
                const img = l.querySelector('img'); return {scale: +s.toFixed(3), loupe: [document.getElementById('loupe').offsetWidth, document.getElementById('loupe').offsetHeight]}; })()""")
            note(f"loupe_{w}x{h}_{q}", hh); ctx.close()
    # a whole replay: San Saba (rows read again) and Cottle (nothing found)
    for q in ("?county=san_saba", "?county=cottle", "?county=jones"):
        ctx, pg, errs = open_page(b, 1440, 900, q, wait=2500)
        pg.keyboard.press("Alt+Shift+P"); pg.wait_for_timeout(500)
        caps = set()
        for _ in range(900):
            caps.add(pg.evaluate("document.getElementById('rp-cap').textContent"))
            if not pg.evaluate("document.body.classList.contains('replaying')"): break
            pg.wait_for_timeout(100)
        pg.wait_for_timeout(1500)
        note(f"replay_{q}", {"captions_seen": len(caps), "finished": not pg.evaluate("document.body.classList.contains('replaying')"), "errors": errs,
                           "button": pg.evaluate("document.getElementById('replay').textContent"), "headline": pg.evaluate("document.getElementById('fcount').textContent")})
        ctx.close()
    # limestone: replay disabled with the reason
    ctx, pg, errs = open_page(b, 1440, 900, "?county=limestone", wait=2000)
    note("limestone", pg.evaluate("({disabled: document.getElementById('replay').disabled, hint: document.getElementById('replay-hint').textContent, headline: document.getElementById('fcount').textContent, stage: document.getElementById('statebox').textContent})"))
    ctx.close(); b.close()
(OUT / "checks.json").write_text(json.dumps(R, indent=1))
