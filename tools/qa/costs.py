"""The run numbers and the replay label of each county as the page shows them, against the county files: python3 tools/qa/costs.py
Writes qa/final/costs.json and a 1440x900 screenshot of the run numbers (qa/final/<county>-run-numbers-1440.png)."""
import sys, json
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))
from lib import *
from playwright.sync_api import sync_playwright

R = {}
with sync_playwright() as p:
    b = p.chromium.launch()
    for county in ("panola", "jones"):
        ctx, pg, errs = open_page(b, 1440, 900, f"?county={county}", wait=3000)
        nums = pg.evaluate("Object.fromEntries([...document.querySelectorAll('.nums > div')].map(d => [d.children[0].textContent, d.children[1].textContent]))")
        label = pg.evaluate("document.getElementById('replay-hint') ? document.querySelector('.rp-bar, #replay-hint').parentElement.textContent.replace(/\\s+/g,' ').trim() : ''")
        loc = pg.locator(".nums")
        loc.scroll_into_view_if_needed()
        loc.screenshot(path=str(OUT / f"{county}-run-numbers-1440.png"))
        info = json.loads((ROOT / "site" / "data" / f"{county}.json").read_text())["fd"]["run_info"]
        R[county] = {"page": nums, "label": label, "file_cost": info["metered_cost_estimate"], "file_seconds": info["seconds"],
                     "file_minutes": round(info["seconds"] / 60, 1), "console_errors": errs}
        print(county, json.dumps(R[county]), flush=True)
        ctx.close()
    b.close()
(OUT / "costs.json").write_text(json.dumps(R, indent=1))
