"""Shared bits for the T07c scripts: a static server over site/, and a page opener that collects errors."""
import http.server, socketserver, threading, functools, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = ROOT / "qa" / "final"
class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a, **k): pass
srv = socketserver.TCPServer(("127.0.0.1", 0), functools.partial(Quiet, directory=str(ROOT / "site")))
threading.Thread(target=srv.serve_forever, daemon=True).start()
BASE = f"http://127.0.0.1:{srv.server_address[1]}/"

def open_page(b, w, h, q="", wait=2600, **kw):
    ctx = b.new_context(viewport={"width": w, "height": h}, **kw); pg = ctx.new_page()
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.on("console", lambda m: errs.append(m.text) if m.type == "error" else None)
    pg.goto(BASE + q, wait_until="load"); pg.wait_for_timeout(wait)
    return ctx, pg, errs
