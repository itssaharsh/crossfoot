"""Screenshots for T07b: python qa/t07b/shoot.py [open|replay|findings]. Serves site/ itself; never installs a browser.
Replay stills: the replay is run at 1x; at each beat the script waits a set time after the caption appears, pauses with
Escape, takes the still, and resumes with Alt+Shift+P."""
import sys
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))
from lib import *
from playwright.sync_api import sync_playwright

W, M = (1440, 900), (390, 844)
# (file name, start of the caption, wait after it appears in ms)
BEATS = [("01-sample", "A sample read", 1500), ("02-sample-read", "Sample read with", 900), ("03-read-page-3", "Reading page 3 of 6", 150),
         ("04-read-page-6", "Reading page 6 of 6: 40", 100), ("05-check", "7 of 984", 2300),
         ("06-suspect-first-read", "Read 78.", 1750), ("07-suspect-read-again", "Read again: 79", 500),
         ("08-document-disagrees", "Read 1,079 twice", 600), ("09-audit-page-1", "Laid against", 900), ("10-audit-page-4", "Laid against", 2500)]

def replay(b, size, tag, reduced=False):
    kw = {"reduced_motion": "reduce"} if reduced else {}
    ctx, pg, errs = open_page(b, *size, **kw)
    pg.get_by_role("button", name="Replay the audit").click()
    seen = set()
    for _ in range(900):                                    # 90 seconds at most
        cap = pg.evaluate("document.getElementById('rp-cap').textContent")
        for name, start, wait in BEATS:
            if name in seen or not cap.startswith(start): continue
            if name == "10-audit-page-4" and "09-audit-page-1" not in seen: continue
            seen.add(name)
            pg.wait_for_timeout(wait)
            pg.keyboard.press("Escape"); pg.wait_for_timeout(250)
            pg.screenshot(path=str(OUT / f"replay-{name}-{tag}.png"))
            if name == "05-check":
                pg.screenshot(path=str(OUT / f"replay-paused-{tag}.png"))
                print("paused button:", pg.evaluate("document.getElementById('replay').textContent"))
            pg.keyboard.press("Alt+Shift+P"); pg.wait_for_timeout(100)
        if not pg.evaluate("document.body.classList.contains('replaying')") and "09-audit-page-1" in seen: break
        pg.wait_for_timeout(100)
    pg.wait_for_timeout(1200)
    pg.screenshot(path=str(OUT / f"replay-11-end-{tag}.png"))
    print(tag, sorted(seen), errs)
    ctx.close()

def still(b, size, q, name, wait=2600):
    ctx, pg, errs = open_page(b, *size, q, wait=wait)
    pg.screenshot(path=str(OUT / name)); print(name, errs); ctx.close()

def main(only):
    want = lambda n: not only or n in only
    with sync_playwright() as p:
        b = p.chromium.launch()
        if want("open"):
            for key, size in (("1440", W), ("1024", (1024, 768)), ("390", M), ("320", (320, 640))): still(b, size, "", f"open-{key}.png")
        if want("findings"):
            for key, size in (("1440", W), ("390", M)):
                still(b, size, "?finding=f001", f"cannot-verify-{key}.png")
                still(b, size, "?finding=f010", f"wrong-number-{key}.png")
        if want("replay"):
            replay(b, W, "1440"); replay(b, M, "390")
        if want("reduced"):
            replay(b, W, "1440-reduced", True)
        b.close()
main(set(sys.argv[1:]))
