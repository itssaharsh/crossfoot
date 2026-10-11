"""Screenshots of the results page: python3 tools/qa/shoot.py. Serves site/ itself; never installs a browser.
Writes qa/final/*.png: the top of the page, the three steps, the explorer on each county and kind of finding, a replay still,
the tape opened, and the whole page. Each at 1440x900 and 390x844 except the long page (1440 only)."""
import sys
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))
from lib import *
from playwright.sync_api import sync_playwright

W, M = ("1440", (1440, 900)), ("390", (390, 844))
EXPLORER = [("panola-opening", ""), ("panola-wrong-number", "?finding=f004"), ("panola-cannot-prove", "?finding=f001"),
            ("jones", "?county=jones"), ("san-saba", "?county=san_saba"), ("cottle", "?county=cottle"), ("scurry", "?county=scurry"),
            ("foard", "?county=foard"), ("limestone", "?county=limestone")]

def to(pg, sel, pad=64):
    pg.evaluate(f"window.scrollTo(0, document.querySelector('{sel}').getBoundingClientRect().top + scrollY - {pad})"); pg.wait_for_timeout(2600)

def run(b):
    for tag, size in (W, M):
        ctx, pg, errs = open_page(b, *size, "", wait=3500)
        pg.screenshot(path=str(OUT / f"top-{tag}.png"))
        to(pg, "#how"); pg.screenshot(path=str(OUT / f"steps-{tag}.png"))
        if tag == "1440":
            pg.evaluate("window.scrollTo(0,0)"); pg.screenshot(path=str(OUT / "page-1440-whole.png"), full_page=True)
        print("top", tag, errs); ctx.close()
        for name, q in EXPLORER:
            ctx, pg, errs = open_page(b, *size, q, wait=3000)
            to(pg, "#counties", 70); pg.screenshot(path=str(OUT / f"explorer-{name}-{tag}.png")); print(name, tag, errs); ctx.close()
        ctx, pg, errs = open_page(b, *size, "", wait=3000)
        to(pg, "#counties", 70); pg.locator(".every summary").click(); pg.wait_for_timeout(400)
        pg.locator(".every").scroll_into_view_if_needed(); pg.screenshot(path=str(OUT / f"tape-open-{tag}.png")); ctx.close()
        ctx, pg, errs = open_page(b, *size, "?county=san_saba", wait=2500)
        pg.evaluate("document.getElementById('counties').scrollIntoView()"); pg.click("#replay")
        pg.wait_for_function("document.getElementById('rp-cap').textContent.startsWith('Page 2: the printed sum')", timeout=60000)
        pg.wait_for_timeout(1500); pg.keyboard.press("Escape"); pg.wait_for_timeout(400)
        pg.screenshot(path=str(OUT / f"replay-{tag}.png")); print("replay", tag, pg.evaluate("document.getElementById('rp-cap').textContent"), errs); ctx.close()

with sync_playwright() as p:
    b = p.chromium.launch(); run(b); b.close()
