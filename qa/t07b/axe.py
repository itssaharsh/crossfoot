"""axe-core (qa/axe.min.js, injected) at 1440x900 and 390x844 on /, on a paused replay (three beats) and on ?record=1.
Writes qa/t07b/axe.json. python qa/t07b/axe.py"""
import sys, json
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))
from lib import *
from playwright.sync_api import sync_playwright
AXE = (ROOT / "qa" / "axe.min.js").read_text()
TAGS = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"]

def paused_at(start, wait=600):
    def go(pg):
        pg.get_by_role("button", name="Replay the audit").click()
        pg.wait_for_function("t => document.getElementById('rp-cap').textContent.startsWith(t)", arg=start, timeout=70000)
        pg.wait_for_timeout(wait); pg.keyboard.press("Escape"); pg.wait_for_timeout(300)
    return go
CASES = [("/", "", None), ("/ replay paused (reading)", "", paused_at("Reading page 3")), ("/ replay paused (a suspect re-read)", "", paused_at("Read again: 79", 500)),
         ("/ replay paused (the document disagrees)", "", paused_at("Read 1,079 twice", 400)), ("/ replay paused (the audit)", "", paused_at("Laid against", 1500)),
         ("/?record=1", "?record=1", None), ("/?record=1 replay paused", "?record=1", paused_at("Read again: 79", 500))]
res, total = [], 0
with sync_playwright() as p:
    b = p.chromium.launch()
    for w, h in [(1440, 900), (390, 844)]:
        for name, q, act in CASES:
            ctx, pg, errs = open_page(b, w, h, q, wait=2500)
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
