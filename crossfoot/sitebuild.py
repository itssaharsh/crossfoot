"""Builds the results page's data: `python -m crossfoot.sitebuild --run <run_id>`.

Reads runs/<run_id>/<county>/county.json (fields: see outputs.py) and writes, under site/data/:
  index.json           run, started, ended, counties [{key, name, file, pages}], summary {county: figures the run
                       recorded}, run {model_calls, prompt_tokens, completion_tokens, metered_cost_estimate}
  <county>.json        the county, with short keys (below), no indentation
  pages/<county>-pN.webp   each scan page at most 1600 px wide
  blocks/<county>-<block id>.webp   each block cut from its page at 300 dpi, grey (for the loupe)

Short keys in <county>.json
  pages   [{n, img, w, h, sc}]   n page number, img path relative to site/, w and h image pixels,
                                 sc = image pixels per pixel of the run's 200 dpi boxes
  blocks  [{id, p, contest, cand, x, bi}]        x = box in page-image pixels, or null;
            bi = {img, w, h, rt} the block's own 300 dpi image (the pixels of the box x), or null with x;
            rt = y in that image of the ruled line above the block's first row, or null if none is found
  values  [{p, b, r, c, v, s, x, ix, m, n}]      cells and printed totals alike, in this order
            p page, b block, r row kind (cell) or 'col' / 'row' / 'grand' (printed total), c column (cell) or key
            (printed total), v value, s status (cells only), x box in image pixels or null (never a zero box),
            ix = the ink box: the box of the printed figure itself, in the pixels of the block's 300 dpi image,
            or null when no ink is found in the value's box (a zero is ink), m model and n tries (cells only)
  checks  [{k, p, b, y, ok, pr, co, t}]          k row | col | grand, y key, pr printed, co computed,
            t = indexes into values, in the order the sum is added
  events  [{t, k, p}]                            ts, kind, payload, as recorded
  layout, run, county                            as recorded
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

MAX_WIDTH = 1600
RENDER_DPI = 200
BLOCK_DPI = 300
INK_SHRINK = 3      # pixels cut off each side of a value's box, so ruled lines are left out
INK_BELOW = 160     # a pixel darker than this (0 black, 255 white) is ink
RULE_FRACTION = 0.9  # a row or column of the box this dark is a ruled line, not a figure
RULE_FRINGE = 2      # pixels cleared beside a ruled line, for its soft edge


def ink_box(im, box, shrink=INK_SHRINK, below=INK_BELOW):
    """The bounding box [x0, y0, x1, y1] of the ink inside `box` of the grey image `im`, the box shrunk by `shrink`
    pixels on every side; None when there is no ink."""
    x0, y0 = max(0, int(box[0] + shrink)), max(0, int(box[1] + shrink))
    x1, y1 = min(im.width, int(box[2] - shrink)), min(im.height, int(box[3] - shrink))
    if x1 <= x0 or y1 <= y0:
        return None
    from PIL import Image, ImageDraw
    dark = im.crop((x0, y0, x1, y1)).point(lambda v: 255 if v < below else 0)
    # ruled lines run the whole way across the box; a figure's own strokes do not: take those lines out first
    cols = dark.resize((dark.width, 1), Image.BOX).tobytes()
    rows = dark.resize((1, dark.height), Image.BOX).tobytes()
    pen = ImageDraw.Draw(dark)
    for x, v in enumerate(cols):
        if v >= RULE_FRACTION * 255:
            pen.rectangle([x - RULE_FRINGE, 0, x + RULE_FRINGE, dark.height], fill=0)
    for y, v in enumerate(rows):
        if v >= RULE_FRACTION * 255:
            pen.rectangle([0, y - RULE_FRINGE, dark.width, y + RULE_FRINGE], fill=0)
    ink = dark.getbbox()
    if not ink:
        return None
    return [x0 + ink[0], y0 + ink[1], x0 + ink[2], y0 + ink[3]]


def block_geometry(box, frame_w, rw):
    """The cut of one block from the 300 dpi render: (left, top, width, height) in 300 dpi pixels.
    `box` is in the frame of width `frame_w`; `rw` is the width of the 200 dpi render of the same page."""
    k = rw * BLOCK_DPI / RENDER_DPI / frame_w
    return round(box[0] * k), round(box[1] * k), max(1, round((box[2] - box[0]) * k)), max(1, round((box[3] - box[1]) * k))


def cut_block(im, geom):
    """Cuts `geom` out of a page image; a cut that would run past the edge is moved back inside it."""
    left, top, w, h = geom
    left = max(0, min(left, im.width - w))
    top = max(0, min(top, im.height - h))
    return im.crop((left, top, left + w, top + h))


def _scale_box(box, sc):
    """A box in 200 dpi pixels -> image pixels; None stays None, and so does anything that is not four numbers."""
    if not box or len(box) != 4 or any(v is None for v in box):
        return None
    return [round(v * sc, 1) for v in box]


def rule_top(im, box, reach=24, dark=0.6, below=110):
    """The first row of pixels, from `reach` pixels above the top of `box` to a few below it, that is a ruled line
    (more than `dark` of the box's width darker than `below`); None when there is none."""
    x0, x1 = max(0, int(box[0])), min(im.width, int(box[2]))
    y0, y1 = max(0, int(box[1] - reach)), min(im.height, int(box[1] + 8))
    if x1 <= x0 or y1 <= y0:
        return None
    strip = im.crop((x0, y0, x1, y1)).point(lambda v: 255 if v < below else 0)
    for y in range(strip.height):
        if strip.crop((0, y, strip.width, y + 1)).histogram()[255] > dark * strip.width:
            return y0 + y
    return None


def build_county(raw: dict, sizes: dict, img_path=lambda county, n: f"data/pages/{county}-p{n}.webp",
                 block_path=lambda county, bid: f"data/blocks/{county}-{bid}.webp", ink=None, rules=None) -> dict:
    """The county's JSON for the page. `sizes` maps page number -> (render_w, render_h, img_w, img_h);
    `ink` maps (page, block, row, column) -> ink box in block-image pixels, `rules` maps (page, block) -> the y of
    the ruled line above the block's first row (see render_blocks)."""
    ink, rules = ink or {}, rules or {}
    county = raw["county"]
    pages, sc_of, frame_of = [], {}, {}
    for pg in raw["pages"]:
        n = pg["number"]
        if n not in sizes:
            raise ValueError(f"page {n} of {county} has no rendered size")
        rw, rh, iw, ih = sizes[n]
        # the boxes live in the frame of the recorded size when there is one, else of the render
        frame_w = pg.get("width") or rw
        sc = iw / frame_w
        sc_of[n] = sc
        frame_of[n] = (frame_w, rw)
        pages.append({"n": n, "img": img_path(county, n), "w": iw, "h": ih, "sc": round(sc, 6)})

    values, index = [], {}

    def add(p, b, r, c, v, box, **extra):
        if (p, b, r, c) in index:
            raise ValueError(f"value {p}:{b}:{r}:{c} appears twice in {county}")
        index[(p, b, r, c)] = len(values)
        d = {"p": p, "b": b, "r": r, "c": c, "v": v, "x": _scale_box(box, sc_of.get(p, 1.0)),
             "ix": ink.get((p, b, r, c))}
        d.update(extra)
        values.append(d)

    for c in raw["cells"]:
        add(c["page"], c["block"], c["row_kind"], str(c["column"]), c["value"], c.get("box"),
            s=c["status"], m=c.get("model"), n=c.get("tries"))
    for t in raw["totals"]:
        add(t["page"], t["block"], t["direction"], str(t["key"]), t["value"], t.get("box"))

    checks = []
    for ch in raw["checks"]:
        refs = []
        for key, _ in ch["terms"]:
            p, b, r, c = key
            k = (p, b, r, str(c))
            if k not in index:
                raise ValueError(f"check {ch['kind']} {ch['page']}:{ch['block']}:{ch['key']} names a term "
                                 f"{p}:{b}:{r}:{c} that is not a value")
            refs.append(index[k])
        checks.append({"k": ch["kind"], "p": ch["page"], "b": ch["block"], "y": str(ch["key"]), "ok": bool(ch["ok"]),
                       "pr": ch["printed"], "co": ch["computed"], "t": refs})

    blocks = []
    for b in raw["blocks"]:
        box = b.get("box")
        ok = _scale_box(box, 1.0) is not None and b["page"] in frame_of
        bi = None
        if ok:
            _, _, w, h = block_geometry(box, *frame_of[b["page"]])
            bi = {"img": block_path(county, b["id"]), "w": w, "h": h, "rt": rules.get((b["page"], b["id"]))}
        blocks.append({"id": b["id"], "p": b["page"], "contest": b["contest"], "cand": b.get("candidate"),
                       "x": _scale_box(box, sc_of.get(b["page"], 1.0)), "bi": bi})
    return {"county": county, "run": raw["run_id"], "layout": raw["layout"], "pages": pages, "blocks": blocks,
            "values": values, "checks": checks,
            "events": [{"t": e["ts"], "k": e["kind"], "p": e["payload"]} for e in raw["events"]]}


def render_pages(county: str, page_numbers, out_dir: Path, data_root=None, max_width=MAX_WIDTH) -> dict:
    """Renders each page at 200 dpi (cached by crossfoot.render), saves a WebP at most max_width wide."""
    from PIL import Image
    from .render import page_png
    from .sources import DATA
    out_dir.mkdir(parents=True, exist_ok=True)
    sizes = {}
    for n in page_numbers:
        with Image.open(page_png(county, n, RENDER_DPI, data_root or DATA)) as im:
            rw, rh = im.size
            iw = min(max_width, rw)
            ih = round(rh * iw / rw)
            im.convert("L").resize((iw, ih), Image.LANCZOS).save(out_dir / f"{county}-p{n}.webp", quality=88, method=6)
        sizes[n] = (rw, rh, iw, ih)
    return sizes


def render_blocks(raw: dict, sizes: dict, out_dir: Path, data_root=None) -> dict:
    """Cuts every block that has a box out of its page at 300 dpi and saves it as a grey WebP.
    Returns (inks, rules): the ink box of every value that has one, {(page, block, row, column): [x0, y0, x1, y1]},
    and the y of the ruled line above each block's first row, {(page, block): y}, both in the pixels of the
    block's image."""
    from PIL import Image
    from .render import page_png
    from .sources import DATA
    out_dir.mkdir(parents=True, exist_ok=True)
    county, inks, rules = raw["county"], {}, {}
    frames = {pg["number"]: (pg.get("width") or sizes[pg["number"]][0], sizes[pg["number"]][0]) for pg in raw["pages"]}
    for n in sorted({b["page"] for b in raw["blocks"] if b.get("box")}):
        with Image.open(page_png(county, n, BLOCK_DPI, data_root or DATA)) as im:
            im = im.convert("L")
            for b in raw["blocks"]:
                if b["page"] != n or not _scale_box(b.get("box"), 1.0):
                    continue
                geom = block_geometry(b["box"], *frames[n])
                cut = cut_block(im, geom)
                cut.save(out_dir / f"{county}-{b['id']}.webp", quality=82, method=6)
                k = frames[n][1] * BLOCK_DPI / RENDER_DPI / frames[n][0]
                left = max(0, min(geom[0], im.width - geom[2]))
                top = max(0, min(geom[1], im.height - geom[3]))
                first = None
                for rows, rk, ck in ((raw["cells"], "row_kind", "column"), (raw["totals"], "direction", "key")):
                    for o in rows:
                        if o["page"] != n or o["block"] != b["id"] or not _scale_box(o.get("box"), 1.0):
                            continue
                        cb = [o["box"][0] * k - left, o["box"][1] * k - top, o["box"][2] * k - left, o["box"][3] * k - top]
                        if rk == "row_kind" and (first is None or cb[1] < first[1]):
                            first = cb
                        ib = ink_box(cut, cb)
                        if ib:
                            inks[(n, b["id"], o[rk], str(o[ck]))] = ib
                rt = rule_top(cut, first) if first else None
                if rt is not None:
                    rules[(n, b["id"])] = rt
    return inks, rules


def build(run_id: str, runs_dir="runs", out="site/data", counties=None, data_root=None) -> list[str]:
    run_dir = Path(runs_dir) / run_id
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    meta = json.loads((run_dir / "run.json").read_text()) if (run_dir / "run.json").exists() else {}
    keys = counties or sorted(p.parent.name for p in run_dir.glob("*/county.json"))
    if not keys:
        raise SystemExit(f"no county.json under {run_dir}")
    index = {"run": run_id, "started": meta.get("started"), "ended": meta.get("ended"), "counties": [], "summary": {},
             "run_totals": {k: meta[k] for k in ("model_calls", "prompt_tokens", "completion_tokens",
                                                 "metered_cost_estimate") if k in meta}}
    for key in keys:
        raw = json.loads((run_dir / key / "county.json").read_text())
        sizes = render_pages(key, [p["number"] for p in raw["pages"]], out / "pages", data_root)
        inks, rules = render_blocks(raw, sizes, out / "blocks", data_root)
        d = build_county(raw, sizes, ink=inks, rules=rules)
        (out / f"{key}.json").write_text(json.dumps(d, separators=(",", ":")))
        index["counties"].append({"key": key, "name": key.replace("_", " ").title(), "file": f"data/{key}.json",
                                  "pages": len(d["pages"])})
        index["summary"][key] = raw.get("summary", {})
    (out / "index.json").write_text(json.dumps(index, separators=(",", ":")))
    return keys


def main(argv=None):
    ap = argparse.ArgumentParser(prog="python -m crossfoot.sitebuild")
    ap.add_argument("--run", required=True)
    ap.add_argument("--runs-dir", default="runs")
    ap.add_argument("--out", default="site/data")
    ap.add_argument("--county", action="append")
    a = ap.parse_args(argv)
    keys = build(a.run, a.runs_dir, a.out, a.county)
    print(f"wrote {a.out}/index.json and {len(keys)} county file(s): {', '.join(keys)}")


if __name__ == "__main__":
    main()
