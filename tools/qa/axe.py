"""axe-core (tools/qa/axe.min.js, injected) at 1440x900 and 390x844 on the top of the page, the explorer with a finding, a county with
nothing found, the county that was not checked, and both dialogs. Writes qa/final/axe.json.   python3 tools/qa/axe.py"""
import sys, json
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))
from lib import *
from playwright.sync_api import sync_playwright
AXE = (ROOT / "tools" / "qa" / "axe.min.js").read_text()
TAGS = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"]

def explorer(pg): pg.evaluate("document.getElementById('counties').scrollIntoView()"); pg.wait_for_timeout(2200)
def crop_dialog(pg): explorer(pg); pg.get_by_role("button", name="Open the full crop").click(); pg.wait_for_timeout(600)
def evidence_dialog(pg): explorer(pg); pg.get_by_role("button", name="Evidence (JSON)").click(); pg.wait_for_timeout(1200)
def tape_open(pg): explorer(pg); pg.locator(".every summary").click(); pg.wait_for_timeout(400)

CASES = [("top of the page", "", None), ("how it works", "", lambda pg: pg.evaluate("document.getElementById('how').scrollIntoView()")),
         ("explorer, Panola finding", "", explorer), ("explorer, Panola, the tape open", "", tape_open),
         ("explorer, Jones (a row)", "?county=jones", explorer), ("explorer, San Saba (a row nothing can decide)", "?county=san_saba&finding=f003", explorer),
         ("explorer, Cottle (nothing found)", "?county=cottle", explorer), ("explorer, Limestone (not checked)", "?county=limestone", explorer),
         ("the run and the limits", "", lambda pg: pg.evaluate("document.getElementById('run').scrollIntoView()")),
         ("crop dialog", "", crop_dialog), ("evidence dialog", "", evidence_dialog)]
res, total = [], 0
with sync_playwright() as p:
    b = p.chromium.launch()
    for w, h in [(1440, 900), (390, 844)]:
        for name, q, act in CASES:
            ctx, pg, errs = open_page(b, w, h, q, wait=3000)
            if act: act(pg)
            pg.wait_for_timeout(500)
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
