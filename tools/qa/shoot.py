"""Screenshots for T07c: python3 tools/qa/shoot.py [states|tabs|replay]. Serves site/ itself; never installs a browser.
Each state at 1440x900 and 390x844 (named <state>-1440.png and <state>-390.png)."""
import sys
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))
from lib import *
from playwright.sync_api import sync_playwright

W, M = ("1440", (1440, 900)), ("390", (390, 844))
STATES = [("panola-open", ""), ("san-saba-open", "?county=san_saba"), ("san-saba-cannot-verify", "?county=san_saba&finding=f003"),
          ("jones-settled", "?county=jones&finding=f009"), ("jones-cannot-verify", "?county=jones&finding=f001"),
          ("lynn-wrong-column", "?county=lynn&finding=f004"), ("cottle-empty", "?county=cottle"), ("limestone-not-checked", "?county=limestone"),
          ("scurry-open", "?county=scurry")]

def states(b):
    for name, q in STATES:
        for tag, size in (W, M):
            ctx, pg, errs = open_page(b, *size, q, wait=3000)
            pg.screenshot(path=str(OUT / f"{name}-{tag}.png")); print(name, tag, errs); ctx.close()

def tabs(b):
    for tag, size in (W, M):
        ctx, pg, errs = open_page(b, *size, "?county=jones", wait=2500)
        pg.locator("#tabs [aria-selected=true]").focus()
        pg.keyboard.press("ArrowRight"); pg.keyboard.press("ArrowRight"); pg.wait_for_timeout(300)
        pg.screenshot(path=str(OUT / f"tabs-focus-{tag}.png"), clip={"x": 0, "y": 0, "width": size[0], "height": 140})
        pg.screenshot(path=str(OUT / f"tabs-focus-full-{tag}.png"))
        print("tabs", tag, "focused:", pg.evaluate("document.activeElement.textContent"), "stops:", pg.evaluate("[...document.querySelectorAll('#tabs button')].filter(b => b.tabIndex === 0).length"), errs)
        ctx.close()

def replay(b):
    for tag, size in (W, M):
        ctx, pg, errs = open_page(b, *size, "?county=san_saba", wait=2500)
        pg.get_by_role("button", name="Replay the audit").click()
        pg.wait_for_function("document.getElementById('rp-cap').textContent.startsWith('Page 2: the printed sum')", timeout=60000)
        pg.wait_for_timeout(1500); pg.keyboard.press("Escape"); pg.wait_for_timeout(300)
        pg.screenshot(path=str(OUT / f"san-saba-replay-{tag}.png")); print("replay", tag, pg.evaluate("document.getElementById('rp-cap').textContent"), errs)
        ctx.close()

with sync_playwright() as p:
    b = p.chromium.launch()
    only = set(sys.argv[1:])
    for name, fn in (("states", states), ("tabs", tabs), ("replay", replay)):
        if not only or name in only: fn(b)
    b.close()
