"""Panola with the same data, old code against new: python3 qa/t07c/compare_panola.py <scratch folder>
Exports site/ of the commit before T07c (git archive 1809cb8) to <scratch>/A, copies the current site/ to <scratch>/B with the old
data in it, opens both at 1440x900 and 390x844 and counts the pixels that differ. Writes the numbers to stdout."""
import sys, subprocess, shutil, http.server, socketserver, threading, functools, pathlib
from playwright.sync_api import sync_playwright
from PIL import Image, ImageChops
import numpy as np
ROOT = pathlib.Path(__file__).resolve().parents[2]
S = pathlib.Path(sys.argv[1]); shutil.rmtree(S / "A", ignore_errors=True); shutil.rmtree(S / "B", ignore_errors=True)
(S / "A").mkdir(parents=True); (S / "B").mkdir(parents=True)
subprocess.run(f"git archive 1809cb8 site | tar -x -C {S / 'A'}", shell=True, check=True, cwd=ROOT)
shutil.copytree(ROOT / "site", S / "B" / "site"); shutil.rmtree(S / "B" / "site" / "data"); shutil.copytree(S / "A" / "site" / "data", S / "B" / "site" / "data")
class Q(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a, **k): pass
def serve(d):
    srv = socketserver.TCPServer(("127.0.0.1", 0), functools.partial(Q, directory=str(d))); threading.Thread(target=srv.serve_forever, daemon=True).start()
    return f"http://127.0.0.1:{srv.server_address[1]}/"
urls = {"old": serve(S / "A" / "site"), "new": serve(S / "B" / "site")}
with sync_playwright() as p:
    b = p.chromium.launch()
    for w, h in ((1440, 900), (390, 844)):
        for tag, u in urls.items():
            ctx = b.new_context(viewport={"width": w, "height": h}); pg = ctx.new_page()
            pg.goto(u, wait_until="load"); pg.wait_for_timeout(3500); pg.screenshot(path=str(S / f"cmp-{tag}-{w}.png")); ctx.close()
        a, c = Image.open(S / f"cmp-old-{w}.png").convert("RGB"), Image.open(S / f"cmp-new-{w}.png").convert("RGB")
        d = np.asarray(ImageChops.difference(a, c)).sum(axis=2)
        print(f"{w}x{h}: pixels differing by more than 30 (of 765): {int((d > 30).sum())} of {d.size}; largest difference {int(d.max())}")
    b.close()
