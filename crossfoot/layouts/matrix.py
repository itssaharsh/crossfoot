"""Matrix layout (Panola): precincts as columns, three ruled rows per candidate, totals both ways.

First read only: one crop per block goes to the model, the answer goes into the ledger as `first_read`.
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path

from PIL import Image

from .. import checks, tracing
from ..model import BudgetExceeded
from ..render import crop, page_png
from .. import segment
from ..segment import find_blocks

ROWS = ("EARLY", "ABSENTEE", "PRECINCT")
TOTAL = "TOTAL"

HEADER_PROMPT = """This image is the top of a landscape election canvass sheet. It has a header row of precinct
numbers ending in TOTAL, then a registered-voters row, then a ballots-cast block with rows EARLY, ABSENTEE and
PRECINCT, then a row of small totals under the columns and a grand total under TOTAL.
Answer with strict JSON only, no prose:
{"precincts": [precinct labels left to right, as printed, excluding TOTAL],
 "registered": {"values": [one integer per precinct], "total": integer},
 "rows": {"EARLY": {"values": [...], "total": integer}, "ABSENTEE": {...}, "PRECINCT": {...}},
 "col_totals": [the small printed total under each precinct, integers],
 "grand": the grand total under the TOTAL column}
Read digits exactly as printed. Every list has one entry per precinct, in order."""

BLOCK_PROMPT = """This image is {part} of one block of a landscape election canvass sheet. {labels}Its rows, top to
bottom, are EARLY, ABSENTEE and PRECINCT, with one cell per precinct, then under them a row of small printed totals
for each column. {total}There are {n} precinct columns in this image, in this order: {precincts}. A solid black cell
means the candidate is not in that precinct: use null for it, not 0.
Answer with strict JSON only, no prose:
{{"contest": {contest},
 "candidate": {candidate},
 "rows": {{"EARLY": {{"values": [{n} integers or null], "total": {tot}}},
          "ABSENTEE": {{"values": [{n} integers or null], "total": {tot}}},
          "PRECINCT": {{"values": [{n} integers or null], "total": {tot}}}}},
 "col_totals": [{n} integers or null: the small printed total under each column],
 "grand": {grand}}}
Read digits exactly as printed; do not correct or add anything up. Keep every value in the column it is printed in."""

READ_DPI = 300      # a printed digit is about 16 px tall here, against about 10 px at 200 dpi
MAX_WIDTH = 1500    # widest image sent to the model, in pixels at READ_DPI; wider ones are shrunk by the provider


def block_prompt(g, precincts):
    return BLOCK_PROMPT.format(
        n=len(precincts), precincts=", ".join(precincts),
        part="the whole" if g.labels and g.total else "a column group",
        labels=("The candidate's name is at the left (a contest title may appear above or beside it). "
                if g.labels else "The candidate's name is not in this image. "),
        total=("The last printed number at the end of each row is that row's TOTAL, and a grand total is printed "
               "under the TOTAL column at the far right. " if g.total else
               "The row TOTAL column is not in this image. "),
        contest='"the contest title if one is printed in this image, else null"' if g.labels else "null",
        candidate='"the candidate\'s name as printed, with party in brackets if shown"' if g.labels else "null",
        tot="integer" if g.total else "null", grand="the grand total under the TOTAL column" if g.total else "null")


@dataclass
class Group:
    c0: int
    c1: int          # columns c0..c1-1
    labels: bool     # includes the row-label strip at the left
    total: bool      # includes the TOTAL strip at the right
    width: float     # pixels at the read dpi


def plan_groups(edges, label_x0, total_x1, *, scale, max_w) -> list[Group]:
    """Cut the columns (n+1 edges) into runs whose image, with labels in the first and TOTAL in the last, fits max_w."""
    n = len(edges) - 1
    label_w = (edges[0] - label_x0) * scale
    total_w = (total_x1 - edges[n]) * scale
    out, c = [], 0
    while c < n:
        first = c == 0
        w = label_w if first else 0.0
        c1 = c
        while c1 < n:
            nw = w + (edges[c1 + 1] - edges[c1]) * scale
            last_extra = total_w if c1 + 1 == n else 0.0
            if c1 > c and nw + last_extra > max_w:
                break
            w, c1 = nw, c1 + 1
        last = c1 == n
        out.append(Group(c, c1, first, last, w + (total_w if last else 0.0)))
        c = c1
    return out


def merge_groups(ds: list[dict]) -> dict:
    """Join group answers left to right: values and small totals concatenate; row totals and grand come from the last."""
    rows = {r: {"values": [v for d in ds for v in d["rows"][r]["values"]], "total": ds[-1]["rows"][r]["total"]}
            for r in ROWS}
    return {"contest": ds[0].get("contest"), "candidate": ds[0].get("candidate"), "rows": rows,
            "col_totals": [v for d in ds for v in d["col_totals"]], "grand": ds[-1]["grand"]}


def group_image(hi_png, b, edges, g, scale, dest: Path) -> Path:
    """Stitch the strips of one group side by side: labels | columns | TOTAL, all the block's full height."""
    y0, y1 = round(b.y0 * scale), round(b.y1 * scale)
    xs = [(b.x0, edges[0])] if g.labels else []
    xs.append((edges[g.c0], edges[g.c1]))
    if g.total:
        xs.append((edges[-1], b.x1))
    with Image.open(hi_png) as im:
        strips = [im.crop((round(a * scale), y0, round(z * scale), y1)) for a, z in xs]
    out = Image.new(strips[0].mode, (sum(s.width for s in strips), y1 - y0), 255)
    x = 0
    for s in strips:
        out.paste(s, (x, 0))
        x += s.width
    dest.parent.mkdir(parents=True, exist_ok=True)
    out.save(dest)
    return dest


def _int_or_none(v, what):
    if v is None or (isinstance(v, int) and not isinstance(v, bool)):
        return v
    raise ValueError(f"{what} must be an integer or null, got {v!r}")


def _check_list(vals, n, what):
    if not isinstance(vals, list) or len(vals) != n:
        raise ValueError(f"{what} must be a list of {n} entries, got "
                         f"{len(vals) if isinstance(vals, list) else type(vals).__name__}")
    for v in vals:
        _int_or_none(v, what)


def validator(n: int, rows=ROWS, extra=()):
    def check(d):
        if not isinstance(d, dict) or not isinstance(d.get("rows"), dict):
            raise ValueError("answer must be an object with a 'rows' object")
        for r in rows + tuple(extra):
            if r not in d["rows"]:
                raise ValueError(f"row {r} is missing")
            _check_list(d["rows"][r].get("values"), n, f"{r} values")
            _int_or_none(d["rows"][r].get("total"), f"{r} total")
        _check_list(d.get("col_totals"), n, "col_totals")
        _int_or_none(d.get("grand"), "grand")
    return check


def header_validator(d):
    p = d.get("precincts")
    if not isinstance(p, list) or not p:
        raise ValueError("precincts must be a non-empty list")
    d["precincts"] = [str(x).strip() for x in p]
    if len(set(d["precincts"])) != len(d["precincts"]):
        raise ValueError("precinct labels must be distinct")
    n = len(p)
    _check_list(d.get("registered", {}).get("values"), n, "registered values")
    validator(n)(d)


def _edges(blocks, n):
    """Column edges for a page: from the first block with n+2 lines: the left edge of the row-label box, then the n+1
    precinct edges (the last is TOTAL's left edge). Returns those n+1 edges."""
    for b in blocks:
        if len(b.lines) == n + 2:
            return b.lines[1:n + 2]
    return None


def _box(edges, b, row_i, col_i):
    if edges is None:
        return (None,) * 4
    h = (b.rule_y1 - b.rule_y0) / len(ROWS)
    return (edges[col_i], round(b.rule_y0 + row_i * h), edges[col_i + 1], round(b.rule_y0 + (row_i + 1) * h))


def _store(led, county, page, bid, d, cols, contest, candidate, model, edges, b):
    """Write one block's answer: cells (null = blacked out, no cell) and printed totals. Returns cells stored."""
    stored = 0
    for ri, r in enumerate(ROWS):
        for ci, col in enumerate(cols):
            v = d["rows"][r]["values"][ci]
            if v is None:
                continue
            led.put_cell(county, page, bid, r, col, v, contest=contest, candidate=candidate, model=model,
                         box=_box(edges, b, ri, ci) if edges else (None,) * 4)
            stored += 1
        if d["rows"][r]["total"] is not None:
            led.put_total(county, page, bid, "row", r, d["rows"][r]["total"])
    for ci, col in enumerate(cols):
        if d["col_totals"][ci] is not None:
            led.put_total(county, page, bid, "col", col, d["col_totals"][ci])
    if d["grand"] is not None:
        led.put_total(county, page, bid, "grand", "", d["grand"])
    return stored


def _store_header(led, county, page, d, cols, model):
    n = 0
    for ci, col in enumerate(cols):
        led.put_cell(county, page, "reg", "REGISTERED", col, d["registered"]["values"][ci], contest="Registered voters",
                     model=model)
        n += 1
    if d["registered"].get("total") is not None:
        led.put_total(county, page, "reg", "row", "REGISTERED", d["registered"]["total"])
    n += _store(led, county, page, "cast", d, cols, "Ballots cast", None, model, None, None)
    return n


def summarize(led, county):
    cells, totals = led.cells(county), led.totals(county)
    rows, cols, grand = (checks.row_checks(cells, totals), checks.column_checks(cells, totals),
                         checks.grand_checks(totals))
    ok = lambda cs: sum(c.ok for c in cs)
    return {"cells_read": len(cells), "failed_cells": sum(c["status"] == "failed" for c in cells),
            "row_sums_pass": ok(rows), "row_sums_fail": len(rows) - ok(rows),
            "col_sums_pass": ok(cols), "col_sums_fail": len(cols) - ok(cols),
            "grand_sums_pass": ok(grand), "grand_sums_fail": len(grand) - ok(grand),
            "printed_totals": len(totals)}


def _read_block(gw, county, page, bid, b, edges, cols, png, crop_path, run_id, root, dpi):
    """One answer for the block: one call on the whole crop when the page gives no column edges, else one per group."""
    if edges is None:
        g = Group(0, len(cols), True, True, b.x1 - b.x0)
        return gw.ask_json(block_prompt(g, cols), crop_path, validate=validator(len(cols)))
    scale = READ_DPI / dpi
    hi = page_png(county, page, READ_DPI, root)
    groups = plan_groups(edges, b.x0, b.x1, scale=scale, max_w=MAX_WIDTH)
    answers = []
    for k, g in enumerate(groups):
        path = group_image(hi, b, edges, g, scale,
                           Path("runs") / run_id / "crops" / f"{bid}-g{k}.png" if run_id else Path(f"/tmp/{bid}-g{k}.png"))
        with Image.open(path) as im:
            w, h = im.size
        before = gw.cost
        with tracing.trace("read_group", kind="TOOL", run=run_id, county=county, page=page, block=bid, group=k,
                           col_first=g.c0, col_last=g.c1 - 1, crop_width=w, crop_height=h, dpi=READ_DPI) as sp:
            answers.append(gw.ask_json(block_prompt(g, cols[g.c0:g.c1]), path, validate=validator(g.c1 - g.c0)))
            sp.set_attribute("estimated_cost_usd", round(gw.cost - before, 5))
    return merge_groups(answers)


def _rows_in(led, county):
    cells, totals = led.cells(county), led.totals(county)
    chs = checks.row_checks(cells, totals)
    return len(chs), sum(1 for c in chs if not c.ok)


def read_county(county, gw, led, *, run_id="", pages=None, dpi=200, log=print, data_root=None, model="auto") -> dict:
    """Read every page of a matrix-layout county block by block into the ledger. Returns the summary dict.

    model="auto": a sample of page 1 is read with claude-haiku first and the reader is chosen by the share of its row
    sums that fail (layouts/profile.py); the sample always comes from page 1, whatever `pages` says. Any other name
    reads the county with that model and skips the sample."""
    from ..sources import DATA
    from . import profile
    root = data_root or DATA
    t0 = time.time()
    pages = list(pages or range(1, 7))
    st = {"cols": None, "contest": None, "failed": 0, "log": [], "done": set()}
    stopped, sample = None, None
    blocks_of: dict = {}

    def blocks_for(page):
        if page not in blocks_of:
            blocks_of[page] = find_blocks(page_png(county, page, dpi, root))
        return blocks_of[page]

    def read_blocks(page, stop_when=None):
        """Read the blocks of one page not read yet. Stops early when `stop_when()` is true after a block."""
        png = page_png(county, page, dpi, root)
        blocks = blocks_for(page)
        for i, b in enumerate(blocks):
            bid = f"p{page}-b{i}"
            is_header = page == 1 and i == 0
            if bid in st["done"] or (page not in pages and not is_header and not stop_when):
                continue
            crop_path = Path("runs") / run_id / "crops" / f"{bid}.png" if run_id else Path(f"/tmp/{bid}.png")
            crop(png, b.box, crop_path)
            st["done"].add(bid)
            try:
                with tracing.trace("read_block", kind="TOOL", run=run_id, county=county, page=page, block=bid):
                    if is_header:
                        d = gw.ask_json(HEADER_PROMPT, crop_path, validate=header_validator)
                        st["cols"] = d["precincts"]
                        n = _store_header(led, county, page, d, st["cols"], gw.model)
                        what = "header"
                    else:
                        edges = _edges(blocks, len(st["cols"]))
                        d = _read_block(gw, county, page, bid, b, edges, st["cols"], png, crop_path, run_id, root, dpi)
                        st["contest"] = d.get("contest") or st["contest"]
                        n = _store(led, county, page, bid, d, st["cols"], st["contest"], d.get("candidate"), gw.model,
                                   edges, b)
                        what = d.get("candidate")
                led.event(county, "block_read", {"page": page, "block": bid, "cells": n, "candidate": what,
                                                 "model": gw.model})
                st["log"].append({"block": bid, "page": page, "status": "read", "cells": n, "candidate": what,
                                  "box": list(b.box)})
            except BudgetExceeded:
                raise
            except Exception as e:  # bad JSON twice, wrong shape, or a model error: mark the block failed, go on
                st["failed"] += 1
                if st["cols"]:
                    for r in ROWS:
                        for col in st["cols"]:
                            led.put_cell(county, page, bid, r, col, None, model=gw.model)
                            led.set_status(county, page, bid, r, col, "failed")
                led.event(county, "block_failed", {"page": page, "block": bid, "error": str(e)[:300]})
                st["log"].append({"block": bid, "page": page, "status": "failed", "error": str(e)[:300]})
                log(f"  {bid}: failed ({str(e)[:100]})")
                if is_header:
                    raise RuntimeError("the page-1 header could not be read; later pages need its precinct order")
            if stop_when and stop_when():
                return

    try:
        with tracing.trace("read_county", kind="WORKFLOW", run=run_id, county=county):
            # the header row is printed on page 1 only (checked by eye); later pages reuse its precinct order
            if model == "auto":
                gw.model = profile.SAMPLE_MODEL
                read_blocks(1, stop_when=lambda: _rows_in(led, county)[0] >= profile.SAMPLE_ROW_SUMS)
                with tracing.trace("choose_reader", kind="TOOL", run=run_id, county=county) as sp:
                    total, failing = _rows_in(led, county)
                    sample = profile.decide(failing, total)
                    sample["blocks"] = sorted(st["done"])
                    for k in ("row_sums", "failing", "rate", "reader", "kept_sample"):
                        sp.set_attribute(f"sample_{k}" if k != "reader" else "choice", sample[k])
                led.event(county, "choose_reader", sample)
                log(profile.sentence(sample))
                gw.model = sample["reader"]
                if not sample["kept_sample"]:
                    led.clear_values(county)
                    st.update(cols=None, contest=None, failed=0, log=[], done=set())
            else:
                gw.model = model
                sample = {"reader": model, "skipped": True, "kept_sample": False}
                led.event(county, "choose_reader", sample)
                log(f"reader: {model} (set with --model; no sample was read)")
            for page in sorted(set(pages) | {1}):
                read_blocks(page)
    except BudgetExceeded as e:
        stopped = str(e)
        log(f"stopped: {e}")
    s = summarize(led, county)
    found = sum(len(blocks_for(p)) for p in pages)
    s.update(county=county, run_id=run_id, blocks_found=found, blocks_failed=st["failed"], reader=gw.model,
             sample=sample, precincts=st["cols"], model_calls=gw.calls, prompt_tokens=gw.prompt_tokens,
             completion_tokens=gw.completion_tokens, metered_cost_estimate=round(gw.cost, 4),
             seconds=round(time.time() - t0, 1), stopped=stopped, blocks=st["log"])
    return s


# ---- where things are on the page (for re-reads and for the results page); boxes are in 200 dpi pixels ----

HEADER_ROWS = ("REGISTERED",) + ROWS + ("SMALL",)   # page 1's first block: one more row, and its small
# totals sit inside the ruled box, as its last row
GEO_DPI = 200
PAD = 8             # pixels of page around a crop, at 200 dpi
SMALL_ROW = 30      # height of the row of small printed totals under the ruled rows, at 200 dpi
MIN_DIGIT_PX = 40   # a re-read crop is enlarged until its digits are at least this tall
# printed digit height at 200 dpi, measured by eye on the Panola scan: cells and large totals about 10 px, the small
# totals about 6 px
DIGIT_200 = {"cell": 10, "row_total": 10, "grand": 10, "col_total": 6, "column": 6}


def digit_px(dpi: int, kind: str) -> float:
    return DIGIT_200[kind] * dpi / GEO_DPI


def scale_for(dpi: int, kind: str) -> float:
    return max(1.0, round(MIN_DIGIT_PX / digit_px(dpi, kind) + 0.01, 2))


class GeometryError(Exception):
    pass


class Geometry:
    """Boxes of cells, printed totals and blocks of one matrix-layout county, and crops of them from the scan."""

    def __init__(self, county, cols, root=None):
        from ..sources import DATA
        self.county, self.cols, self.root = county, list(cols), root or DATA
        self._pages: dict = {}
        self._rule_cache: dict = {}
        self._cur_page = None

    def _page(self, page):
        if page not in self._pages:
            blocks = find_blocks(page_png(self.county, page, GEO_DPI, self.root))
            self._pages[page] = (blocks, _edges(blocks, len(self.cols)))
        return self._pages[page]

    def _block(self, page, bid):
        blocks, edges = self._page(page)
        i = 0 if bid in ("reg", "cast") else int(bid.rsplit("-b", 1)[1])
        if i >= len(blocks) or edges is None:
            raise GeometryError(f"no column lines found for {bid} on page {page}")
        rows = HEADER_ROWS if bid in ("reg", "cast") else ROWS
        self._cur_page = page
        self._rules(blocks[i], edges)
        return blocks[i], edges, rows

    def _rules(self, b, edges):
        """y of each horizontal rule across the precinct columns inside the block's ruled height, found in the image."""
        key = (b.y0, b.x0)
        if key not in self._rule_cache:
            import numpy as np
            png = page_png(self.county, self._cur_page, GEO_DPI, self.root)
            with Image.open(png) as im:
                g = np.asarray(im.convert("L"))[b.rule_y0 - 3:b.rule_y1 + 4, edges[0]:edges[-2]]
            cover = (g < 110).mean(axis=1) >= 0.6
            ys = []
            for s_, e_ in segment._runs(cover):
                ys.append(b.rule_y0 - 3 + (s_ + e_) // 2)
            self._rule_cache[key] = ys
        return self._rule_cache[key]

    def _row(self, b, rows, kind):
        i = rows.index(kind)
        ys = self._rule_cache.get((b.y0, b.x0)) or []
        h = (b.rule_y1 - b.rule_y0) / len(rows)

        def edge(j):    # an even split, moved onto a drawn rule when one lies within 5 px
            y = b.rule_y0 + j * h
            near = min(ys, key=lambda r: abs(r - y), default=None)
            return round(near if near is not None and abs(near - y) <= 5 else y)
        return edge(i), edge(i + 1)

    def block_box(self, page, bid):
        try:
            return self._block(page, bid)[0].box
        except GeometryError:
            return None

    def cell_box(self, page, bid, row, col):
        b, edges, rows = self._block(page, bid)
        y0, y1 = self._row(b, rows, row)
        ci = self.cols.index(col)
        return (edges[ci], y0, edges[ci + 1], y1)

    def total_box(self, page, bid, direction, key):
        try:
            b, edges, rows = self._block(page, bid)
            n = len(self.cols)
            if direction == "row":
                y0, y1 = self._row(b, rows, key)
                return (edges[n], y0, b.x1, y1)
            if bid == "reg":
                return None
            if direction == "col":
                ci = self.cols.index(key)
                if bid == "cast":
                    y0, y1 = self._row(b, rows, "SMALL")
                    return (edges[ci], y0, edges[ci + 1], y1)
                return (edges[ci], b.rule_y1, edges[ci + 1], min(b.y1, b.rule_y1 + SMALL_ROW))
            if bid == "cast":
                y0, y1 = self._row(b, rows, "SMALL")
                return (edges[n], y0, b.x1, b.y1)
            return (edges[n], b.rule_y1, b.x1, b.y1)
        except (GeometryError, ValueError):
            return None

    def target_box(self, page, bid, t):
        """The box of a re-read target, without padding."""
        b, edges, rows = self._block(page, bid)
        kind = t["kind"]
        if kind == "cell":
            return self.cell_box(page, bid, t["row"], t["column"])
        if kind == "column":
            ci = self.cols.index(t["column"])
            y0 = self._row(b, rows, "EARLY")[0]
            if bid == "cast":
                return (edges[ci], y0, edges[ci + 1], self._row(b, rows, "SMALL")[1])
            return (edges[ci], y0, edges[ci + 1], min(b.y1, b.rule_y1 + SMALL_ROW))
        if kind == "row_total":
            return self.total_box(page, bid, "row", t["row"])
        if kind == "col_total":
            return self.total_box(page, bid, "col", t["column"])
        if kind == "grand":
            return self.total_box(page, bid, "grand", "")
        raise GeometryError(f"unknown target kind {kind!r}")

    def crop(self, page, bid, t, dpi, dest: Path):
        """Cut the target out of the page at `dpi`, with padding, enlarged so its digits are at least 40 px tall.
        Returns (path, box at 200 dpi)."""
        try:
            box = self.target_box(page, bid, t)
        except ValueError:
            box = None
        if box is None:
            raise GeometryError(f"cannot place {t} in {bid} on page {page}")
        return self._cut(page, box, t["kind"], dpi, dest), box

    def _cut(self, page, box, kind, dpi, dest: Path) -> Path:
        k = dpi / GEO_DPI
        x0, y0, x1, y1 = box
        with Image.open(page_png(self.county, page, dpi, self.root)) as im:
            win = (max(0, round((x0 - PAD) * k)), max(0, round((y0 - PAD) * k)),
                   min(im.width, round((x1 + PAD) * k)), min(im.height, round((y1 + PAD) * k)))
            c = im.crop(win)
        s = scale_for(dpi, kind)
        if s > 1:
            c = c.resize((round(c.width * s), round(c.height * s)), Image.LANCZOS)
        dest.parent.mkdir(parents=True, exist_ok=True)
        c.save(dest)
        return dest

    def strip_crops(self, page, bid, row, dpi, dest: Path, per: int = 7):
        """One row of one block cut into pieces of at most `per` cells. Returns [(path, [precincts], box at 200 dpi)]."""
        try:
            b, edges, rows = self._block(page, bid)
            if row not in rows:
                raise GeometryError(f"no row {row} in {bid}")
            y0, y1 = self._row(b, rows, row)
            out = []
            for i in range(0, len(self.cols), per):
                cols = self.cols[i:i + per]
                box = (edges[i], y0, edges[i + len(cols)], y1)
                out.append((self._cut(page, box, "cell", dpi, dest.with_name(f"{dest.stem}-s{i // per}{dest.suffix}")),
                            cols, box))
            return out
        except (ValueError, IndexError):
            raise GeometryError(f"cannot place row {row} in {bid} on page {page}") from None


def precinct_order(led, county) -> list[str]:
    """The precinct columns left to right, as the header block's registered-voters row was read."""
    seen = []
    for c in led.cells(county):
        if c["block_id"] == "reg" and c["column"] not in seen:
            seen.append(c["column"])
    return seen
