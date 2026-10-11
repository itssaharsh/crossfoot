"""axe-core (qa/axe.min.js, injected) at 1440x900 and 390x844 on each state T07c adds. Writes qa/t07c/axe.json.
python3 qa/t07c/axe.py"""
import sys, json
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))
from lib import *
from playwright.sync_api import sync_playwright
AXE = (ROOT / "qa" / "axe.min.js").read_text()
TAGS = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"]

def tab_focus(pg):
    pg.locator("#tabs [aria-selected=true]").focus(); pg.keyboard.press("ArrowRight"); pg.wait_for_timeout(200)

def replay_paused(pg):
    pg.get_by_role("button", name="Replay the audit").click()
    pg.wait_for_function("document.getElementById('rp-cap').textContent.startsWith('Page 2: the printed sum')", timeout=60000)
    pg.wait_for_timeout(1200); pg.keyboard.press("Escape"); pg.wait_for_timeout(300)

CASES = [("Panola (opening)", "", None), ("San Saba (opening)", "?county=san_saba", None),
         ("San Saba (a row nothing can decide)", "?county=san_saba&finding=f003", None), ("Jones (a settled row)", "?county=jones&finding=f009", None),
         ("Jones (a column sum in the finding)", "?county=jones&finding=f001", None), ("Lynn (wrong column)", "?county=lynn&finding=f004", None),
         ("Scurry (rows only the file has)", "?county=scurry", None), ("Cottle (nothing found)", "?county=cottle", None),
         ("Limestone (not checked)", "?county=limestone", None), ("tabs with keyboard focus", "?county=jones", tab_focus),
         ("San Saba replay paused (a row read again)", "?county=san_saba", replay_paused)]
res, total = [], 0
with sync_playwright() as p:
    b = p.chromium.launch()
    for w, h in [(1440, 900), (390, 844)]:
        for name, q, act in CASES:
            ctx, pg, errs = open_page(b, w, h, q, wait=2800)
            if act: act(pg)
            pg.evaluate(AXE)
            r = pg.evaluate("tags => axe.run(document, {runOnly: {type: 'tag', values: tags}})", TAGS)
            v = [{"id": x["id"], "impact": x["impact"], "help": x["help"], "nodes": [{"target": n["target"], "summary": n.get("failureSummary", "")[:300]} for n in x["nodes"]]} for x in r["violations"]]
            total += len(v)
            res.append({"case": name, "viewport": f"{w}x{h}", "violations": v, "passes": len(r["passes"]), "incomplete": [x["id"] for x in r["incomplete"]], "pageErrors": errs})
            print(w, name, len(v), [x["id"] for x in v], flush=True)
            ctx.close()
    b.close()
(OUT / "axe.json").write_text(json.dumps({"axe": "4.12.1", "tags": TAGS, "violations_total": total, "runs": res}, indent=1))
print("total violations", total)
