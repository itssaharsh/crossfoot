"""Screenshots for T07a: python qa/t07a/shoot.py [name ...]. Serves site/ itself; never installs a browser."""
import http.server, socketserver, threading, sys, functools, pathlib
from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = ROOT / "qa" / "t07a"
class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a, **k): pass
H = functools.partial(Quiet, directory=str(ROOT / "site"))
srv = socketserver.TCPServer(("127.0.0.1", 0), H)
threading.Thread(target=srv.serve_forever, daemon=True).start()
BASE = f"http://127.0.0.1:{srv.server_address[1]}/"
SIZES = {"320": (320, 640), "390": (390, 844), "1024": (1024, 768), "1440": (1440, 900)}
STATES = ["loading", "error", "empty", "partial", "first-run"]

def shot(page, name, query="", wait=1800):
    errs = []
    page.on("pageerror", lambda e: errs.append(str(e)))
    page.goto(BASE + query, wait_until="load")
    page.wait_for_timeout(wait)
    page.screenshot(path=str(OUT / name))
    return errs

def main(only):
    with sync_playwright() as p:
        b = p.chromium.launch()
        for key, (w, h) in SIZES.items():
            ctx = b.new_context(viewport={"width": w, "height": h})
            pg = ctx.new_page()
            if not only or "open" in only:
                print(key, shot(pg, f"open-{key}.png"))
            ctx.close()
        for key in ("390", "1440"):
            w, h = SIZES[key]
            if not only or "failing" in only:
                ctx = b.new_context(viewport={"width": w, "height": h}); pg = ctx.new_page()
                print("failing", key, shot(pg, f"failing-selected-{key}.png", "?cell=2:p2-b5:EARLY:1", 2500))
                ctx.close()
            for st in STATES:
                if only and st not in only: continue
                ctx = b.new_context(viewport={"width": w, "height": h}); pg = ctx.new_page()
                print(st, key, shot(pg, f"state-{st}-{key}.png", f"?state={st}"))
                ctx.close()
        b.close()

main(set(sys.argv[1:]))
