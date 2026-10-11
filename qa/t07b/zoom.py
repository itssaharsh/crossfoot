"""?record=1 at 160 percent browser zoom: a 900x562 CSS-pixel window at 1.6 device pixels per CSS pixel.
Takes the opening state and the replay caption, and measures that the headline and the caption fit. python qa/t07b/zoom.py"""
import sys, json
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))
from lib import *
from playwright.sync_api import sync_playwright
M = """() => { const r = e => { const b = document.querySelector(e).getBoundingClientRect(); return {l: Math.round(b.left), t: Math.round(b.top), r: Math.round(b.right), b: Math.round(b.bottom)}; };
  const q = s => document.querySelector(s);
  return { vw: innerWidth, vh: innerHeight, sideways: document.documentElement.scrollWidth > innerWidth,
           headline: r('#fcount'), headlineClipped: q('#fcount').scrollWidth > q('#fcount').clientWidth + 1, headlineLines: Math.round(q('#fcount').getBoundingClientRect().height / parseFloat(getComputedStyle(q('#fcount')).lineHeight)),
           headlineFont: getComputedStyle(q('#fcount')).fontSize, panel: r('#panel'), stage: r('#stage'), caption: r('#rp-cap'), captionFont: getComputedStyle(q('#rp-cap')).fontSize,
           loupe: r('#loupe'), judge: getComputedStyle(q('.judge')).display } }"""
out = {}
with sync_playwright() as p:
    b = p.chromium.launch()
    ctx, pg, errs = open_page(b, 900, 562, "?record=1", device_scale_factor=1.6)
    out["open"] = pg.evaluate(M); out["errors"] = errs
    pg.screenshot(path=str(OUT / "zoom160-record-open.png"))
    pg.get_by_role("button", name="Replay the audit").click()
    pg.wait_for_function("document.getElementById('rp-cap').textContent.startsWith('Read 1,079 twice')", timeout=70000)
    pg.wait_for_timeout(700)
    pg.keyboard.press("Escape"); pg.wait_for_timeout(300)
    out["replay"] = pg.evaluate(M)
    pg.screenshot(path=str(OUT / "zoom160-record-replay.png"))
    b.close()
(OUT / "zoom160.json").write_text(json.dumps(out, indent=1))
print(json.dumps(out, indent=1))
