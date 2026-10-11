"""axe-core (qa/axe.min.js, injected) at 1440x900 and 390x844 on /, a filtered list, the crop dialog and the evidence dialog.
Writes qa/t06c/axe.json. python3 qa/t06c/axe.py"""
import http.server, socketserver, threading, functools, pathlib, json
from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parents[2]
class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a, **k): pass
srv = socketserver.TCPServer(("127.0.0.1", 0), functools.partial(Quiet, directory=str(ROOT / "site")))
threading.Thread(target=srv.serve_forever, daemon=True).start()
BASE = f"http://127.0.0.1:{srv.server_address[1]}/"
AXE = (ROOT / "qa" / "axe.min.js").read_text()
TAGS = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"]

def filtered(pg): pg.get_by_role("button", name="cannot verify", exact=True).click()
def crop(pg): pg.get_by_role("button", name="Open crop", exact=True).click()
def evidence(pg): pg.get_by_role("button", name="Evidence file", exact=True).click()
CASES = [("/", "", None), ("/ filtered list (cannot verify)", "", filtered), ("/ crop dialog", "", crop), ("/ evidence dialog", "", evidence),
         ("/?finding=f080 (no place on the sheet)", "?finding=f080", None), ("/?record=1", "?record=1", None)] + [(f"/?state={x}", f"?state={x}", None) for x in ("loading", "error", "empty", "partial", "first-run")]
res, total = [], 0
with sync_playwright() as p:
    b = p.chromium.launch()
    for w, h in [(1440, 900), (390, 844)]:
        for name, q, act in CASES:
            ctx = b.new_context(viewport={"width": w, "height": h}); pg = ctx.new_page()
            pg.goto(BASE + q); pg.wait_for_timeout(2500)
            if act: act(pg); pg.wait_for_timeout(900)
            pg.evaluate(AXE)
            r = pg.evaluate("tags => axe.run(document, {runOnly: {type: 'tag', values: tags}})", TAGS)
            v = [{"id": x["id"], "impact": x["impact"], "help": x["help"], "nodes": [{"target": n["target"], "summary": n.get("failureSummary", "")[:300]} for n in x["nodes"]]} for x in r["violations"]]
            total += len(v)
            res.append({"case": name, "viewport": f"{w}x{h}", "violations": v, "passes": len(r["passes"]), "incomplete": [x["id"] for x in r["incomplete"]]})
            print(w, name, len(v), [x["id"] for x in v])
            ctx.close()
    b.close()
(ROOT / "qa" / "t06c" / "axe.json").write_text(json.dumps({"axe": "4.12.1", "tags": TAGS, "violations_total": total, "runs": res}, indent=1))
print("total violations", total)
