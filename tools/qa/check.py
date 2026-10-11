"""Behaviour checks for the results page, results in qa/final/checks.json:  python3 tools/qa/check.py
The first screen at both sizes (what it says, the example is on it), the county cards (one tab stop, arrows, ?county=), Previous and
Next, no empty frame or placeholder in any county, the loupe's figure size, the page's width, and a whole replay."""
import sys, json
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))
from lib import *
from playwright.sync_api import sync_playwright

R = {}
def note(k, v): R[k] = v; print(k, json.dumps(v)[:300], flush=True)
BAD = ["No image of this page", "No crop was cut", "has no position", "Replay comes with", "No image of this block"]
COUNTIES = ["panola", "san_saba", "cottle", "jones", "lynn", "scurry", "foard", "limestone"]

with sync_playwright() as p:
    b = p.chromium.launch()
    for w, h in ((1440, 900), (390, 844)):
        ctx, pg, errs = open_page(b, w, h, "", wait=3500)
        note(f"first_screen_{w}", pg.evaluate("""(() => { const r = e => document.querySelector(e).getBoundingClientRect(); const H = innerHeight;
            return {headline: document.getElementById('headline').textContent, figures: [...document.querySelectorAll('#figs li')].map(l => l.textContent),
                    crop_bottom: Math.round(r('.hp-crop').bottom), labels_inside: [...document.querySelectorAll('.hp-labels .lab')].map(l => l.textContent),
                    proof: document.querySelector('.hp-proof').textContent, screen: H, crop_digit_px_min: 28}; })()"""))
        note(f"errors_{w}", errs); ctx.close()
    ctx, pg, errs = open_page(b, 1440, 900, "?county=lynn", wait=3000)
    tabs = pg.evaluate("[...document.querySelectorAll('#counties button')].map(b => ({text: b.textContent.replace(/\\s+/g, ' ').trim(), stop: b.tabIndex === 0, sel: b.getAttribute('aria-selected')}))")
    note("cards", tabs); note("card_tab_stops", sum(t["stop"] for t in tabs)); note("selected_by_query", [t["text"] for t in tabs if t["sel"] == "true"])
    pg.locator("#counties [aria-selected=true]").focus()
    g = lambda: pg.evaluate("document.activeElement.textContent.replace(/\\s+/g,' ').trim()")
    pg.keyboard.press("ArrowRight"); a = g(); pg.keyboard.press("End"); e = g(); pg.keyboard.press("ArrowRight"); wr = g(); pg.keyboard.press("Home"); hm = g()
    note("arrow_keys", {"ArrowRight": a, "End": e, "ArrowRight_wraps": wr, "Home": hm})
    pg.keyboard.press("Enter"); pg.wait_for_timeout(2500)
    note("enter_opens", {"url": pg.evaluate("location.search"), "selected": pg.evaluate("document.querySelector('#counties [aria-selected=true]').textContent.replace(/\\s+/g,' ').trim()")})
    # previous and next, and the arrow keys on the stage
    ctx.close()
    ctx, pg, errs = open_page(b, 1440, 900, "", wait=3000)
    c0 = pg.evaluate("document.getElementById('counter').textContent"); t0 = pg.evaluate("document.getElementById('place').textContent")
    pg.click("#next"); pg.wait_for_timeout(1500)
    c1 = pg.evaluate("document.getElementById('counter').textContent"); t1 = pg.evaluate("document.getElementById('place').textContent")
    pg.focus("#viewport"); pg.keyboard.press("ArrowLeft"); pg.wait_for_timeout(1500)
    c2 = pg.evaluate("document.getElementById('counter').textContent")
    pg.click("#filters [data-mode=cant]"); pg.wait_for_timeout(1500)
    c3 = pg.evaluate("document.getElementById('counter').textContent")
    note("prev_next", {"start": [c0, t0], "after_next": [c1, t1], "after_left_arrow": c2, "after_filter_cant": c3, "errors": errs}); ctx.close()
    # no empty frame, no placeholder, in any county, at both sizes
    for w, h in ((1440, 900), (390, 844)):
        for k in COUNTIES:
            ctx, pg, errs = open_page(b, w, h, f"?county={k}", wait=2800)
            r = pg.evaluate("""bad => { const t = document.body.innerText; const vis = e => { const r = e.getBoundingClientRect(); return r.width > 0 && r.height > 0 && getComputedStyle(e).visibility !== 'hidden'; };
                const imgs = [...document.querySelectorAll('img')].filter(vis).filter(i => !i.complete || i.naturalWidth === 0);
                return {placeholder_text: bad.filter(s => t.includes(s)), broken_images: imgs.length, overflow_x: document.documentElement.scrollWidth > innerWidth,
                        loupe_visible: vis(document.getElementById('loupe')), loupe_has_picture: !!document.querySelector('#loupe .lp-layer img, #loupe .lp-crop'),
                        stage_visible: vis(document.getElementById('stage')), kind: document.getElementById('xpanel').dataset.kind}; }""", BAD)
            note(f"county_{k}_{w}", {**r, "errors": errs}); ctx.close()
    # the loupe at reading size: the scale of the pan
    for w, h in ((1440, 900), (390, 844)):
        for q in ("?county=san_saba", "?county=jones", "?county=lynn"):
            ctx, pg, errs = open_page(b, w, h, q, wait=2600)
            note(f"loupe_{w}_{q}", pg.evaluate("(() => { const l = document.querySelector('.lp-layer .lp-pan'); if (!l) return null; return {scale: +new DOMMatrix(getComputedStyle(l).transform).a.toFixed(3)}; })()")); ctx.close()
    # a whole replay: San Saba (rows read again), Cottle (nothing found), Jones
    for q in ("?county=san_saba", "?county=cottle", "?county=jones"):
        ctx, pg, errs = open_page(b, 1440, 900, q, wait=2500)
        pg.keyboard.press("Alt+Shift+P"); pg.wait_for_timeout(500)
        caps, blank = set(), 0
        for _ in range(900):
            caps.add(pg.evaluate("document.getElementById('rp-cap').textContent"))
            blank += pg.evaluate("(() => { const s = document.getElementById('stage'); return document.body.innerText.includes('No image of this page') || (s.querySelector('.viewport').offsetParent !== null && !document.getElementById('scan').getAttribute('src')) ? 1 : 0; })()")
            if not pg.evaluate("document.body.classList.contains('replaying')"): break
            pg.wait_for_timeout(100)
        pg.wait_for_timeout(1500)
        note(f"replay_{q}", {"captions_seen": len(caps), "blank_sheet_frames": blank, "finished": not pg.evaluate("document.body.classList.contains('replaying')"), "errors": errs,
                           "button": pg.evaluate("document.getElementById('replay').textContent")})
        ctx.close()
    # a one-county build still works
    for w, h in ((1440, 900), (1024, 768), (390, 844), (320, 640)):
        ctx, pg, errs = open_page(b, w, h, "", wait=2000)
        note(f"overflow_{w}", pg.evaluate("document.documentElement.scrollWidth > innerWidth")); ctx.close()
    b.close()
(OUT / "checks.json").write_text(json.dumps(R, indent=1))
