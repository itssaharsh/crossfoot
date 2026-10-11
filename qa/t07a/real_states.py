"""The states reached for real (no ?state=): a page image that fails, a county file that fails, no index built.
python qa/t07a/real_states.py"""
import http.server, socketserver, threading, functools, pathlib, json
from playwright.sync_api import sync_playwright
ROOT = pathlib.Path(__file__).resolve().parents[2]
class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a, **k): pass
srv = socketserver.TCPServer(("127.0.0.1", 0), functools.partial(Quiet, directory=str(ROOT / "site")))
threading.Thread(target=srv.serve_forever, daemon=True).start()
BASE = f"http://127.0.0.1:{srv.server_address[1]}/"
out = {}
with sync_playwright() as p:
    b = p.chromium.launch()
    def run(name, route, js):
        pg = b.new_page(viewport={"width": 1440, "height": 900}); errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.route(route[0], route[1]); pg.goto(BASE); pg.wait_for_timeout(2500)
        out[name] = {"state": pg.evaluate("document.body.dataset.state"), "detail": pg.evaluate(js), "errors": errs}
        pg.close()
    run("page image fails", ("**/pages/*.webp", lambda r: r.abort()), "[document.getElementById('stage').className, document.getElementById('notice').hidden, !!document.querySelector('.fb-pan')]")
    run("county file fails", ("**/panola.json", lambda r: r.fulfill(status=500, body='x')), "document.getElementById('notice').textContent")
    run("no index built", ("**/index.json", lambda r: r.fulfill(status=404, body='')), "document.getElementById('statebox').textContent")
    b.close()
print(json.dumps(out, indent=1))
