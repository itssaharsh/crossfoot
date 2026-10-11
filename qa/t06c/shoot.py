"""Screenshots for T06c: python qa/t06c/shoot.py [name ...]. Serves site/ itself; never installs a browser."""
import http.server, socketserver, threading, sys, functools, pathlib
from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = ROOT / "qa" / "t06c"
class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a, **k): pass
srv = socketserver.TCPServer(("127.0.0.1", 0), functools.partial(Quiet, directory=str(ROOT / "site")))
threading.Thread(target=srv.serve_forever, daemon=True).start()
BASE = f"http://127.0.0.1:{srv.server_address[1]}/"
W, M = (1440, 900), (390, 844)

def run(b, size, query, name, wait=2200, act=None, full=False):
    ctx = b.new_context(viewport={"width": size[0], "height": size[1]}); pg = ctx.new_page()
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.on("console", lambda m: errs.append(m.text) if m.type == "error" else None)
    pg.goto(BASE + query, wait_until="load"); pg.wait_for_timeout(wait)
    if act: act(pg); pg.wait_for_timeout(900)
    pg.screenshot(path=str(OUT / name), full_page=full)
    ctx.close()
    print(name, errs)

def to_list(pg):
    pg.evaluate("document.getElementById('findings').scrollIntoView({block:'start'})")

def chip(label):
    def go(pg):
        pg.get_by_role("button", name=label, exact=True).first.click(); to_list(pg)
    return go

def dialog(name):
    def go(pg):
        pg.get_by_role("button", name=name, exact=True).click(); pg.wait_for_timeout(600)
    return go

def main(only):
    want = lambda n: not only or n in only
    with sync_playwright() as p:
        b = p.chromium.launch()
        for key, size in (("1440", W), ("390", M), ("1024", (1024, 768)), ("320", (320, 640))):
            if want("open"): run(b, size, "", f"open-{key}.png")
        for key, size in (("1440", W), ("390", M)):
            if want("number"): run(b, size, "?finding=f010", f"wrong-number-{key}.png")
            if want("precinct"): run(b, size, "?finding=f006", f"wrong-precinct-{key}.png")
            if want("cannot"): run(b, size, "?finding=f001", f"cannot-verify-{key}.png")
            if want("missing"): run(b, size, "?finding=f077", f"missing-row-{key}.png")
            if want("noplace"): run(b, size, "?finding=f080", f"no-place-{key}.png")
            if want("crop"): run(b, size, "", f"crop-dialog-{key}.png", act=dialog("Open crop"))
            if want("evidence"): run(b, size, "", f"evidence-dialog-{key}.png", act=dialog("Evidence file"))
            if want("filtered"): run(b, size, "", f"filtered-cannot-verify-{key}.png", act=chip("cannot verify"))
            if want("list"): run(b, size, "", f"list-{key}.png", act=to_list)
        for st in ("empty", "partial"):
            if want("states"):
                for key, size in (("1440", W), ("390", M)): run(b, size, f"?state={st}", f"state-{st}-{key}.png")
        b.close()
main(set(sys.argv[1:]))
