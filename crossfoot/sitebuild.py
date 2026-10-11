"""Builds the results page's data: `python -m crossfoot.sitebuild --run <run_id>`.

Reads runs/<run_id>/<county>/county.json (fields: see outputs.py) and writes, under site/data/:
  index.json           run, started, ended, counties [{key, name, file, pages, status, layout, disagreements, by_status,
                       confirmed, sums_check, second_sum, note}] in the run's order (file and the county's figures are left
                       out for a county the run did not check; note = the run's reason), summary {county: figures the run
                       recorded}, run_totals {model_calls, prompt_tokens, completion_tokens, metered_cost_estimate},
                       totals {counties, read, findings, settled, cannot_verify, confirmed, sums_in_all, holding_published,
                       holding_corrected, model_calls, metered_cost, seconds}
  <county>.json        the county, with short keys (below), no indentation; none for a county the run did not check
  pages/<county>-pN.webp   each scan page at most 1600 px wide (report layout: only the pages that carry a finding, and page 1)
  rows/<county>-rN.webp    report layout: the clean crop of each row that carries a finding (or was read again), 300 dpi
  blocks/<county>-<block id>.webp   each block cut from its page at 300 dpi, grey (for the loupe)

Short keys in <county>.json
  pages   [{n, img, w, h, sc}]   n page number, img path relative to site/ (null: no image written for the page), w and h
                                 image pixels, sc = image pixels per pixel of the run's 200 dpi boxes
  blocks  [{id, p, contest, cand, x, bi}]        x = box in page-image pixels, or null;
            bi = {img, w, h, rt} the block's own 300 dpi image (the pixels of the box x), or null with x;
            rt = y in that image of the ruled line above the block's first row, or null if none is found
  values  [{p, b, r, c, v, s, x, ix, m, n}]      cells and printed totals alike, in this order
            p page, b block, r row kind (cell) or 'col' / 'row' / 'grand' (printed total), c column (cell) or key
            (printed total), v value, s status (cells only), x box in image pixels or null (never a zero box),
            ix = the ink box: the box of the printed figure itself, in the pixels of the block's 300 dpi image,
            or null when no ink is found in the value's box (a zero is ink), m model and n tries (cells only)
  checks  [{k, p, b, y, ok, pr, co, t}]          k row | col | grand (the small totals add to the grand total) |
            grand_row (the row totals add to it), y key, pr printed, co computed,
            t = indexes into values, in the order the sum is added
  rc      [{id, p, b, r, img, w, h, parts, pb, rb, fb, lb, fh}]   report layout: the row crops. img the crop (300 dpi,
            w x h), parts [[src_y0, src_y1, dst_y0]] the pieces of the page it is cut from (300 dpi pixels; the contest's
            heading and the row with its context, so a piece or two), pb the crop's place on the page in page-image pixels
            [x0, y0, x1, y1], rb the row's box inside the crop, fb {total, absentee, early, election_day} the box of each
            figure inside the crop or null where the ink does not give it, lb the ink of the row's label [x0, x1] or null,
            fh the height of the figures in the crop's pixels or null, ch where the column headings start in the crop or
            null, fr where the rows begin in the crop, gp the middles of the blank bands between its lines.
            A value of such a row carries fx = its figure's box in page-image pixels (null when not found).
  events  [{t, k, p}]                            ts, kind, payload, as recorded
  vd      [{s, v, r, e}]                         the run's verdicts as recorded: sum key, verdict, reason, entity
  sm      {sums_failing_before, sums_failing_after, items_worked, cells_reread}   the summary's figures the replay reads
  layout, run, county                            as recorded
  fd      the audit's findings, when the run has a findings.json (a field the run lacks is left out, never zero-filled):
            path       the findings file's path in the repository; evidence = its copy, data/<county>-findings.json
            run        the run id
            counts     {findings, groups, by_kind, by_status, confirmed}   confirmed = findings a person confirmed
            sums_check the file's own sums check, when the findings file has one
            groups     [{id, kind, office, row, precincts, page, block, findings [ids], crop}]
            items      [{id, group, kind, status, office, row, precinct, part, file, scan, reason, page, block, ref,
                         reread_disagrees, reread_value, sums}]
                       report layout adds: col (the figure's column), rc (index into rc), rv {file, scan} (the row's four
                       figures, total / absentee / early voting / election day), tot (index of the contest total's value in
                       the figure's column), reread_agrees
                       row = the row label as printed on the scan (the block's candidate, else its contest);
                       ref = index into values of the value on the sheet, absent when it has no place there;
                       file / scan = the values, absent for a row the file or the scan lacks;
                       sums = [{kind, name, label, printed, with_file, with_scan, holds_file, holds_scan,
                                terms [[ref or null, value]]}]
            figures    {cells, right_first, right_after, reread, disagreements, settled}   what the run recorded
            run_info   {reader, sample, seconds, phases_seconds, model_calls_by_model, metered_cost_estimate,
                        resumed_from, seconds_total}   seconds_total = this run's seconds plus those of the runs it
                       resumed, present only when every one of them recorded its seconds
"""
from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

MAX_WIDTH = 1600
RENDER_DPI = 200
BLOCK_DPI = 300
INK_SHRINK = 3      # pixels cut off each side of a value's box, so ruled lines are left out
INK_BELOW = 160     # a pixel darker than this (0 black, 255 white) is ink
RULE_FRACTION = 0.9  # a row or column of the box this dark is a ruled line, not a figure
RULE_FRINGE = 2      # pixels cleared beside a ruled line, for its soft edge
SCAN_ROW = {"absentee": "ABSENTEE", "early_voting": "EARLY", "election_day": "PRECINCT"}   # as in crossfoot.audit


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


def _same_box(a, b):
    return bool(a) and bool(b) and len(a) == len(b) == 4 and all(abs(x - y) < 1.5 for x, y in zip(a, b))


# ---- report layout: the clean crop of a row, and its figures found from the ink --------------------------------------------
COLS = ("total", "absentee", "early", "election_day")         # the county's column order, as the audit keeps it
PART_COL = {"votes": "total", "absentee": "absentee", "early_voting": "early", "election_day": "election_day"}
CROP_DPI = 300
HEAD_GAP = 54        # blank pixels (300 dpi) that end a contest's heading, going up from its first row
HEAD_LIMIT = 330     # the heading never starts further than this above the first row
HEAD_FALLBACK = 170  # ... and where no gap is found it starts this far above it
CTX_ROWS = 2         # rows of context above and below the row
SPACER = 18          # white between the heading and the row's piece, when the two are not next to each other
EDGE_REACH = 10      # an edge of a piece moves at most this far to land on blank paper
FIG_GAP = 14         # blank columns (300 dpi) between two figures
FIG_DARK = 4         # dark pixels a column of a figure holds at least (a dotted rule holds one or two)


def _dark(im, box, below=INK_BELOW):
    import numpy as np
    x0, y0, x1, y1 = (int(v) for v in box)
    x0, y0, x1, y1 = max(0, x0), max(0, y0), min(im.width, x1), min(im.height, y1)
    if x1 <= x0 or y1 <= y0:
        return np.zeros((0, 0), dtype=bool), (x0, y0)
    return np.asarray(im.crop((x0, y0, x1, y1))) < below, (x0, y0)


def heading_top(inkrow, y_first, gap=HEAD_GAP, limit=HEAD_LIMIT, fallback=HEAD_FALLBACK):
    """The y where a contest's heading (title, "Vote For", column headings) starts: going up from the first row's top,
    the first blank band of `gap` rows ends it. `inkrow[y]` is True for a row of the page that holds ink."""
    seen, blank = False, 0
    for y in range(min(y_first, len(inkrow)) - 1, max(-1, y_first - limit - 1), -1):
        if inkrow[y]:
            seen, blank = True, 0
        elif seen:
            blank += 1
            if blank >= gap:
                return y + blank
    return max(0, y_first - fallback)


def snap(inkrow, y, reach=EDGE_REACH):
    """The y nearest to `y`, within `reach`, whose row of the page is blank: a piece cut there goes through no text."""
    n = len(inkrow)
    for d in range(reach + 1):
        for yy in (y - d, y + d):
            if 0 <= yy < n and not inkrow[yy]:
                return yy
    return max(0, min(y, n))


def figure_boxes(im, strip, cols=COLS, values=None):
    """The box of each of the row's figures, from the ink: the clusters of ink at the right end of the row's strip
    ([x0, y0, x1, y1] in the pixels of `im`), taken right to left and mapped through the column order. Returns
    ({column: box or None}, label_extent or None, figure height or None). A figure the ink does not give is None, and
    so is every figure when the row's clusters do not look like the row's figures (fewer than the columns, or widths that
    do not fit the number of digits in `values` {column: value})."""
    import numpy as np
    none = ({c: None for c in cols}, None, None)
    y0, y1 = int(strip[1]) + 6, int(strip[3]) - 6
    dark, (ox, oy) = _dark(im, [strip[0], y0, strip[2], y1])
    if dark.size == 0:
        return none
    colhit = dark.sum(axis=0) >= FIG_DARK
    runs, start, last = [], None, None
    for x, hit in enumerate(colhit):
        if hit:
            if start is None:
                start = x
            last = x
        elif start is not None and x - last > FIG_GAP:
            runs.append((start, last + 1)); start = None
    if start is not None:
        runs.append((start, last + 1))
    if len(runs) < len(cols):
        return none
    figs = runs[-len(cols):]
    boxes = {}
    for c, (a, b) in zip(cols, figs):
        prof = dark[:, a:b].sum(axis=1)
        rows = np.nonzero(prof >= 1)[0]
        # the figure is the heaviest run of ink rows: a dotted rule just under it is a run of its own
        runs_y, st = [], rows[0]
        for u, v in zip(rows, rows[1:]):
            if v - u > 1:
                runs_y.append((st, u)); st = v
        runs_y.append((st, rows[-1]))
        y0_, y1_ = max(runs_y, key=lambda r: prof[r[0]:r[1] + 1].sum())
        boxes[c] = [ox + a, oy + int(y0_), ox + b, oy + int(y1_) + 1]
    if values:
        # a figure is about as wide as its characters: the widths per character agree, within a factor of two of their median
        per = [(boxes[c][2] - boxes[c][0]) / max(1, len(f"{values[c]:,}")) for c in cols if c in values and boxes[c]]
        if per:
            med = sorted(per)[len(per) // 2]
            if any(p > 2 * med or p < med / 2 for p in per):
                return none
    hs = sorted(b[3] - b[1] for b in boxes.values())
    label = runs[:-len(cols)]
    lb = [ox + label[0][0], ox + label[-1][1]] if label else None
    return boxes, lb, hs[len(hs) // 2]


def row_pieces(strips, i, inkrow, ctx=CTX_ROWS):
    """The pieces of the page a row's crop is cut from, as [(y0, y1)] (300 dpi pixels), top to bottom. `strips` are the
    boxes' y ranges of the rows of the row's contest on this page, sorted; `i` the row. The first piece is the contest's
    heading and column headings (and, where the row is near the top, runs on to the row's context below); a second piece
    is the row with `ctx` rows of context above and below, when it is not next to the first."""
    first = strips[0][0]
    top = heading_top(inkrow, first)
    lo, hi = max(0, i - ctx), min(len(strips) - 1, i + ctx)
    c0, c1 = strips[lo][0], strips[hi][1]
    n = len(inkrow)
    c1 = snap(inkrow, min(n - 1, c1 + 4))
    if lo <= 1 or c0 <= first + 2:
        return [(snap(inkrow, top), c1 + 1)]
    return [(snap(inkrow, top), snap(inkrow, first)), (snap(inkrow, max(0, c0 - 4)), c1 + 1)]


def cut_pieces(im, pieces, x1):
    """The crop: the pieces one above the other, a spacer between two that are not neighbours. Returns (image, parts)
    with parts [[src_y0, src_y1, dst_y0]]."""
    from PIL import Image
    x1 = min(im.width, int(x1))
    h = sum(b - a for a, b in pieces) + SPACER * (len(pieces) - 1)
    out = Image.new("L", (x1, h), 255)
    parts, y = [], 0
    for a, b in pieces:
        out.paste(im.crop((0, a, x1, b)), (0, y))
        parts.append([a, b, y])
        y += b - a + SPACER
    return out, parts


def to_crop(parts, x, y):
    """A point of the page (300 dpi) -> the crop, or None when it is in none of the pieces."""
    for a, b, d in parts:
        if a <= y <= b:
            return x, d + (y - a)
    return None


def to_page(parts, x, y):
    for a, b, d in parts:
        if d <= y <= d + (b - a):
            return x, a + (y - d)
    return None


def row_strips(raw: dict) -> dict:
    """{(page, block): [(row, y0, y1, x1)]} sorted top to bottom, the row strips of the report layout in the pixels of the
    run's frame (the boxes the four values of a row share)."""
    seen, out = set(), {}
    for c in raw["cells"]:
        k = (c["page"], c["block"], c["row_kind"])
        if k in seen or not c.get("box"):
            continue
        seen.add(k)
        out.setdefault((c["page"], c["block"]), []).append((c["row_kind"], *c["box"][1::2], c["box"][2]))
    for v in out.values():
        v.sort(key=lambda r: (r[1], r[2]))
    return out


def wanted_rows(raw: dict, findings=None) -> tuple[list, list]:
    """The rows of a report county that need a clean crop: (crops, figures_only). The rows that carry a finding, and the
    first row each item read again; and the contest total row of each of their blocks, which only need their figures."""
    have = {(c["page"], c["block"], c["row_kind"]) for c in raw["cells"] if c.get("box")}
    crops, order = [], set()

    def add(p, b, r):
        if (p, b, r) in have and (p, b, r) not in order:
            order.add((p, b, r)); crops.append((p, b, r))
    for f in (findings or {}).get("findings", []):
        if f.get("page") is not None and f.get("row"):
            add(f["page"], f["block"], f["row"])
    items = set()
    for e in raw.get("events") or []:
        p = e.get("payload") or {}
        if e.get("kind") == "reread" and p.get("item") not in items and p.get("row"):
            items.add(p["item"])
            add(p["page"], p["block"], p["row"])
    from .checks import row_label_kind
    blocks = {b for _, b, _ in crops}
    tot = []
    for (p, b, r) in sorted(have):
        if b in blocks and row_label_kind(r) == "total" and (p, b, r) not in order:
            tot.append((p, b, r))
    return crops, tot


def build_rows(raw: dict, crops, totals, im_of, frame_w_of, sc_of, out_dir: Path, img_path) -> tuple[list, dict, dict]:
    """The row crops of a report county. im_of(page) is the page at 300 dpi (grey), frame_w_of(page) the width of the run's
    frame, sc_of(page) the image pixels per pixel of that frame. Writes rows/<county>-rN.webp and returns
    (rc, fx, index): the rc list (see the module's docstring), fx {(page, block, row, column): figure box in page-image
    pixels or None} and index {(page, block, row): position in rc}."""
    county = raw["county"]
    strips = row_strips(raw)
    import numpy as np
    cell = {(c["page"], c["block"], c["row_kind"], c["column"]): c["value"] for c in raw["cells"]}
    rc, fx, index, pages = [], {}, {}, {}

    def page_state(n):
        if n not in pages:
            pages.clear()          # one page at a time: a 300 dpi page is big
            im = im_of(n)
            K = im.width / frame_w_of(n)
            xr = max([r[3] for (pg, _), v in strips.items() if pg == n for r in v] or [im.width / K])
            dark, _ = _dark(im, [0, 0, min(im.width, xr * K + 8), im.height])
            pages[n] = (im, K, dark.sum(axis=1) >= 3)
        return pages[n]

    def place(p, b, r):
        im, K, inkrow = page_state(p)
        rows = [(s[0], round(s[1] * K), round(s[2] * K), round(s[3] * K)) for s in strips[(p, b)]]
        i = next(j for j, s in enumerate(rows) if s[0] == r)
        vals = {c: cell[(p, b, r, c)] for c in COLS if (p, b, r, c) in cell}
        return im, K, inkrow, rows, i, vals

    def keep_fx(p, b, r, boxes, f):
        for c, bx in boxes.items():
            fx[(p, b, r, c)] = [round(v * f, 1) for v in bx] if bx else None

    top = lambda k: (k[0], strips[(k[0], k[1])][[s[0] for s in strips[(k[0], k[1])]].index(k[2])][1])
    crops, totals = sorted(crops, key=top), sorted(totals, key=top)
    for (p, b, r) in totals:
        im, K, inkrow, rows, i, vals = place(p, b, r)
        boxes, _, _ = figure_boxes(im, [0, rows[i][1], rows[i][3], rows[i][2]], values=vals)
        keep_fx(p, b, r, boxes, sc_of(p) / K)
    out_dir.mkdir(parents=True, exist_ok=True)
    for (p, b, r) in crops:
        im, K, inkrow, rows, i, vals = place(p, b, r)
        f = sc_of(p) / K
        x1 = rows[i][3]
        pieces = row_pieces([(a, c) for _, a, c, _ in rows], i, inkrow)
        crop, parts = cut_pieces(im, pieces, x1 + 8)
        n = len(rc)
        crop.save(out_dir / f"{county}-r{n}.webp", quality=84, method=6)
        boxes, lb, fh = figure_boxes(im, [0, rows[i][1], x1, rows[i][2]], values=vals)
        keep_fx(p, b, r, boxes, f)
        mid = (rows[i][1] + rows[i][2]) / 2
        piece = next(pt for pt in parts if pt[0] <= mid <= pt[1])
        ry0 = piece[2] + max(0, rows[i][1] - piece[0]) if rows[i][1] >= piece[0] else piece[2]
        ry1 = piece[2] + min(piece[1], rows[i][2]) - piece[0]
        fb = {}
        for c, bx in boxes.items():
            u, w = (to_crop(parts, bx[0], bx[1]), to_crop(parts, bx[2], bx[3])) if bx else (None, None)
            fb[c] = [u[0], u[1], w[0], w[1]] if u and w else None
        lbc = lb if lb else None
        # where the rows begin in the crop: the second piece, or the first row of a crop in one piece
        fr = parts[1][2] if len(parts) == 2 else max(0, rows[0][1] - parts[0][0])
        ch = None      # where the column headings start: the loupe can open on them
        h0, h1 = parts[0][0], (parts[0][1] if len(parts) == 2 else rows[0][1])
        fl = min((bx[0] for bx in boxes.values() if bx), default=None)
        # the headings of the figures' columns: ink right of the label's side only, so the title and "Vote For" are left out
        seg = (_dark(im, [fl - 30, h0, x1, h1])[0].sum(axis=1) >= 3) if fl is not None and h1 > h0 else (inkrow[h0:h1] if h1 > h0 else [])
        y = len(seg) - 1
        while y >= 0 and not seg[y]:
            y -= 1
        if y >= 0:
            ytop, blank = y, 0
            for yy in range(y, -1, -1):
                if seg[yy]:
                    ytop, blank = yy, 0
                else:
                    blank += 1
                    if blank >= 24:      # more than the gap between the two lines of "Early Voting"
                        break
            ch = max(0, ytop - 8)
        # the blank bands between the lines of the crop (their middles): a window of the loupe opens and closes on them
        cd = np.asarray(crop) < INK_BELOW
        inked = cd.sum(axis=1) >= 3
        gp, run = [], 0
        for yy, hit in enumerate(list(inked) + [True]):
            if hit:
                if run >= 4:
                    gp.append(yy - run // 2 - 1)
                run = 0
            else:
                run += 1
        rc.append({"id": n, "p": p, "b": b, "r": r, "img": img_path(county, n), "w": crop.width, "h": crop.height,
                   "parts": parts, "pb": [0, round(min(a for a, _, _ in parts) * f, 1), round(crop.width * f, 1),
                                          round(max(c for _, c, _ in parts) * f, 1)],
                   "rb": [0, ry0, crop.width, ry1], "fb": fb, "lb": lbc, "fh": fh, "ch": ch, "fr": fr, "gp": gp})
        index[(p, b, r)] = n
    return rc, fx, index


def report_item(it: dict, f: dict, scan_fig: dict, rcix: dict, index: dict) -> None:
    """What the report layout adds to an item: the figure's column, the row's crop, the reread's agreement and where the
    contest's total row stands in the figure's column."""
    col = PART_COL.get(f.get("part"))
    if col:
        it["col"] = col
    p, b, r = f.get("page"), f.get("block"), f.get("row")
    if (p, b, r) in rcix:
        it["rc"] = rcix[(p, b, r)]
    rr = f.get("reread") or {}
    if rr.get("agrees_with_ledger") and not rr.get("error") and not f.get("reread_disagrees"):
        it["reread_agrees"] = True
    if any(s["kind"] == "report_contest" for s in f.get("sums") or []) and col:
        from .checks import row_label_kind
        for (kp, kb, kr, kc), i in index.items():
            if kb == b and kc == col and row_label_kind(kr) == "total":
                it["tot"] = i
                break


def report_rows(items: list, findings: list, scan_fig: dict) -> None:
    """`rv` of each item of a report county: {file, scan}, the row's four figures (total, absentee, early voting, election
    day; null for a figure the file or the scan does not have). The scan's are the ledger's; the file's are the scan's with
    the file's value at each place a finding of the same row names one. A row only the file has takes the file's own."""
    by_row = {}
    for it, f in zip(items, findings):
        if f.get("page") is not None and f.get("row"):
            by_row.setdefault((f["page"], f["block"], f["row"]), []).append(f)
    for it, f in zip(items, findings):
        rows = (f.get("row_values") or {})
        if rows.get("file") or rows.get("scan"):
            order = {"votes": 0, "absentee": 1, "early_voting": 2, "election_day": 3}
            pick = lambda d: [d.get(k) for k in order] if d else None
            it["rv"] = {"file": pick(rows.get("file")), "scan": pick(rows.get("scan"))}
            continue
        key = (f.get("page"), f.get("block"), f.get("row"))
        if key not in by_row:
            continue
        scan = [scan_fig.get((*key, c)) for c in COLS]
        file = list(scan)
        for g in by_row[key]:
            c = PART_COL.get(g.get("part"))
            if c in COLS and g.get("file_value") is not None:
                file[COLS.index(c)] = g["file_value"]
            elif c in COLS:
                file[COLS.index(c)] = None
        it["rv"] = {"file": file, "scan": scan}


def build_findings(raw: dict, index: dict, doc: dict, run: dict | None = None, path=None, evidence=None,
                   crop_path=lambda county, gid, src: None, rcix=None) -> dict:
    """The `fd` part of the county's JSON from a findings.json (`doc`), the run's run.json (`run`) and the county's
    values (`index`: (page, block, row, column) -> index into values). See the module's docstring."""
    county = raw["county"]
    report = raw.get("layout") == "report"
    rcix = rcix or {}
    blocks = {b["id"]: b for b in raw["blocks"]}
    scan_fig = {(c["page"], c["block"], c["row_kind"], c["column"]): c["value"] for c in raw["cells"]} if report else {}
    boxed = [(c["page"], c["block"], c["row_kind"], str(c["column"]), c.get("box")) for c in raw["cells"]] + \
            [(t["page"], t["block"], t["direction"], str(t["key"]), t.get("box")) for t in raw["totals"]]

    def label(bid, f=None):
        if report:   # a block is a whole contest: the row is the label the finding names, as printed on the scan
            return (f or {}).get("row") or (f or {}).get("candidate") or (f or {}).get("office") or None
        b = blocks.get(bid)
        if b and (b.get("candidate") or b.get("contest")):
            return b.get("candidate") or b["contest"]
        return (f or {}).get("candidate") or (f or {}).get("office") or None

    def ref_of(f):
        """The finding's value on the sheet: the cell the audit compares (as crossfoot.audit.entity_key), else the
        value whose box is the finding's box."""
        p, b, part, pr = f.get("page"), f.get("block"), f.get("part"), str(f.get("precinct"))
        if report:
            k = (p, b, f.get("row"), PART_COL.get(part))
            return index.get(k)
        if part == "votes":
            keys = [(p, b, "REGISTERED", pr)] if b == "reg" else [(p, b, "col", pr)]
        else:
            keys = [(p, b, SCAN_ROW.get(part), pr)]
        for k in keys:
            if k in index:
                return index[k]
        for (bp, bb, r, c, box) in boxed:
            if (bp, bb) == (p, b) and _same_box(box, f.get("box")) and (bp, bb, r, c) in index:
                return index[(bp, bb, r, c)]
        return None

    items = []
    for f in doc["findings"]:
        it = {"id": f["id"], "group": f.get("group"), "kind": f["kind"], "status": f["status"]}
        for k, v in (("office", f.get("office")), ("row", label(f.get("block"), f)), ("precinct", f.get("precinct")),
                     ("part", f.get("part")), ("file", f.get("file_value")), ("scan", f.get("scan_value")),
                     ("reason", f.get("reason")), ("page", f.get("page")), ("block", f.get("block"))):
            if v is not None and v != "":
                it[k] = v
        r = ref_of(f)
        if r is not None:
            it["ref"] = r
        if f.get("reread_disagrees"):
            it["reread_disagrees"] = True
            rv = (f.get("reread") or {}).get("value")
            if rv is not None:
                it["reread_value"] = rv
        it["sums"] = []
        for s in f.get("sums") or []:
            d = {"kind": s["kind"], "name": s["name"]}
            for k, v in (("label", s.get("printed_label")), ("printed", s.get("printed")),
                         ("with_file", s.get("computed_with_file")), ("with_scan", s.get("computed_with_scan")),
                         ("holds_file", s.get("holds_with_file")), ("holds_scan", s.get("holds_with_scan"))):
                if v is not None:
                    d[k] = v
            d["terms"] = [[index.get((t["cell"][0], t["cell"][1], t["cell"][2], str(t["cell"][3]))), t["value"]]
                          for t in s.get("terms") or []]
            it["sums"].append(d)
        if f.get("confirmed_by_person"):
            it["confirmed_by_person"] = True
        if report:
            report_item(it, f, scan_fig, rcix, index)
        items.append(it)
    if report:
        report_rows(items, doc["findings"], scan_fig)

    groups = []
    for g in doc.get("groups") or []:
        d = {"id": g["id"], "kind": g["kind"], "findings": list(g.get("findings") or [])}
        first = next((f for f in doc["findings"] if f["id"] in d["findings"]), None) if report else None
        for k, v in (("office", g.get("office")), ("row", label(g.get("block"), first or g)), ("precincts", g.get("precincts")),
                     ("page", g.get("page")), ("block", g.get("block")),
                     ("crop", crop_path(county, g["id"], g.get("crop")))):
            if v not in (None, "", []):
                d[k] = v
        groups.append(d)

    counts = dict(doc.get("counts") or {})
    counts["confirmed"] = sum(1 for f in doc["findings"] if f.get("confirmed_by_person"))
    fd = {"run": doc.get("run_id") or raw["run_id"], "counts": counts, "groups": groups, "items": items}
    if path:
        fd["path"] = path
    if evidence:
        fd["evidence"] = evidence
    if doc.get("sums_check"):
        fd["sums_check"] = doc["sums_check"]

    cells = raw["cells"]
    fig = {"cells": len(cells),
           "right_first": sum(1 for c in cells if c["status"] == "accepted" and not c.get("tries")),
           "right_after": sum(1 for c in cells if c["status"] == "accepted" and c.get("tries")),
           "disagreements": len(items),
           "settled": sum(1 for i in items if i["status"] == "settled_against_file")}
    rr = (raw.get("summary") or {}).get("cells_reread")
    if rr is not None:
        fig["reread"] = rr
    fd["figures"] = fig
    if run:
        info = {k: run[k] for k in ("reader", "sample", "seconds", "phases_seconds", "model_calls_by_model",
                                    "metered_cost_estimate", "resumed_from", "seconds_total") if run.get(k) is not None}
        if info:
            fd["run_info"] = info
    return fd


def build_county(raw: dict, sizes: dict, img_path=lambda county, n: f"data/pages/{county}-p{n}.webp",
                 block_path=lambda county, bid: f"data/blocks/{county}-{bid}.webp", ink=None, rules=None,
                 findings=None, run=None, findings_path=None, evidence=None,
                 crop_path=lambda county, gid, src: None, rows=None, images=None) -> dict:
    """The county's JSON for the page. `sizes` maps page number -> (render_w, render_h, img_w, img_h);
    `ink` maps (page, block, row, column) -> ink box in block-image pixels, `rules` maps (page, block) -> the y of
    the ruled line above the block's first row (see render_blocks); `findings` is the county's findings.json, `run`
    the run's run.json; `rows` the report layout's row crops (see build_rows: {rc, fx, rcix}); `images` the page numbers that
    have an image (None: all of them)."""
    ink, rules, rows = ink or {}, rules or {}, rows or {}
    fx = rows.get("fx") or {}
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
        pages.append({"n": n, "img": img_path(county, n) if images is None or n in images else None,
                      "w": iw, "h": ih, "sc": round(sc, 6)})

    values, index = [], {}

    def add(p, b, r, c, v, box, **extra):
        if (p, b, r, c) in index:
            raise ValueError(f"value {p}:{b}:{r}:{c} appears twice in {county}")
        index[(p, b, r, c)] = len(values)
        d = {"p": p, "b": b, "r": r, "c": c, "v": v, "x": _scale_box(box, sc_of.get(p, 1.0)),
             "ix": ink.get((p, b, r, c))}
        d.update(extra)
        if (p, b, r, c) in fx:
            d["fx"] = fx[(p, b, r, c)]
        values.append(d)

    for c in raw["cells"]:
        add(c["page"], c["block"], c["row_kind"], str(c["column"]), c["value"], c.get("box"),
            s=c["status"], m=c.get("model"), n=c.get("tries"))
    for t in raw["totals"]:
        add(t["page"], t["block"], t["direction"], str(t["key"]), t["value"], t.get("box"))

    checks = []
    for ch in raw["checks"]:
        refs = []
        for term in ch["terms"]:
            p, b, r, c = term if len(term) == 4 and not isinstance(term[0], list) else term[0]   # a key, or [key, value]
            k = (p, b, r, str(c))
            if k not in index:
                raise ValueError(f"check {ch['kind']} {ch['page']}:{ch['block']}:{ch['key']} names a term "
                                 f"{p}:{b}:{r}:{c} that is not a value")
            refs.append(index[k])
        checks.append({"k": "grand" if ch["kind"] == "grand_col" else ch["kind"], "p": ch["page"], "b": ch["block"], "y": str(ch["key"]), "ok": bool(ch["ok"]),
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
    out = {"county": county, "run": raw["run_id"], "layout": raw["layout"], "pages": pages, "blocks": blocks,
           "values": values, "checks": checks,
           "events": [{"t": e["ts"], "k": e["kind"], "p": e["payload"]} for e in raw["events"]]}
    vd = [{"s": v.get("sum"), "v": v.get("verdict"), "r": v.get("reason"), "e": v.get("entity")}
          for v in raw.get("verdicts") or [] if isinstance(v, dict)]
    if vd:
        out["vd"] = vd
    sm = {k: raw["summary"][k] for k in ("sums_failing_before", "sums_failing_after", "items_worked", "cells_reread")
          if (raw.get("summary") or {}).get(k) is not None}
    if sm:
        out["sm"] = sm
    if rows.get("rc"):
        out["rc"] = rows["rc"]
    if findings:
        out["fd"] = build_findings(raw, index, findings, run, findings_path, evidence, crop_path, rows.get("rcix"))
    return out


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


def total_seconds(meta: dict, runs_dir="runs"):
    """This run's seconds plus those of every run it resumed (`resumed_from`, followed back); None when the run, or
    one it resumed, did not record its seconds or its run.json cannot be found."""
    total, seen = 0.0, set()
    while meta:
        if not isinstance(meta.get("seconds"), (int, float)):
            return None
        total += meta["seconds"]
        prior = meta.get("resumed_from")
        if not prior:
            return round(total, 1)
        if prior in seen:
            return None
        seen.add(prior)
        path = Path(runs_dir) / str(prior) / "run.json"
        meta = json.loads(path.read_text()) if path.exists() else None
    return None


def latest_run(runs_dir="runs") -> str:
    """The newest run folder that has a summary.json, else the newest that has a findings.json."""
    ids = sorted(p.parent.name for p in Path(runs_dir).glob("*/summary.json"))
    if not ids:
        ids = sorted(p.parent.parent.name for p in Path(runs_dir).glob("*/*/findings.json"))
    if not ids:
        raise SystemExit(f"no run under {runs_dir} has a summary.json or a findings.json")
    return ids[-1]


def county_entry(key: str, summ: dict | None, findings: dict | None, pages: int, layout: str) -> dict:
    """The county's line in index.json: what the tabs and the whole-run line read. `summ` is the county's entry of the run's
    summary.json (None for a run that has none), `findings` its findings.json."""
    entry = {"key": key, "name": key.replace("_", " ").title(), "file": f"data/{key}.json", "pages": pages,
             "status": (summ or {}).get("status", "audited"), "layout": layout}
    fs = (findings or {}).get("findings") or []
    by = {}
    for f in fs:
        by[f["status"]] = by.get(f["status"], 0) + 1
    if findings is not None:
        entry["disagreements"] = len(fs)
        entry["by_status"] = by
        entry["confirmed"] = sum(1 for f in fs if f.get("confirmed_by_person"))
    sc = (summ or {}).get("sums_check") or (findings or {}).get("sums_check") or {}
    got = {k: sc[k] for k in ("in_all", "holding_with_published", "holding_with_corrected") if k in sc}
    if got:
        entry["sums_check"] = got
    second = (summ or {}).get("second_sum_exists")
    if second is None:
        second = ((findings or {}).get("audit") or {}).get("second_sum_exists")
    if second is not None:
        entry["second_sum"] = bool(second)
    return entry


def unchecked_entry(key: str, summ: dict | None, raw: dict | None) -> dict:
    """A county the run did not check: its reason (the run's own words) and no county file."""
    note = (summ or {}).get("note") or (raw or {}).get("note") or "nothing on this scan can be cross-checked; left as published"
    return {"key": key, "name": key.replace("_", " ").title(), "pages": 0, "status": "unchecked",
            "layout": (summ or {}).get("layout") or (raw or {}).get("layout") or "no_printed_totals", "note": note}


def run_totals(entries: list, summary: dict | None, meta: dict) -> dict:
    """The figures for the whole run, from the entries and the run's own totals."""
    read = [e for e in entries if e.get("status") != "unchecked"]
    by = {}
    for e in read:
        for k, n in (e.get("by_status") or {}).items():
            by[k] = by.get(k, 0) + n
    sc = lambda k: sum((e.get("sums_check") or {}).get(k, 0) for e in read)
    t = {"counties": len(entries), "read": len(read), "findings": sum(e.get("disagreements") or 0 for e in read),
         "settled": by.get("settled_against_file", 0), "cannot_verify": by.get("cannot_verify", 0),
         "confirmed": sum(e.get("confirmed") or 0 for e in read),
         "sums_in_all": sc("in_all"), "holding_published": sc("holding_with_published"),
         "holding_corrected": sc("holding_with_corrected")}
    if by.get("document_inconsistent"):
        t["document_inconsistent"] = by["document_inconsistent"]
    src = (summary or {}).get("totals") or {}
    for k, from_, key in (("model_calls", src, "model_calls"), ("metered_cost", src, "metered_cost"),
                          ("seconds", src, "seconds")):
        v = from_.get(key)
        if v is None:
            v = {"metered_cost": meta.get("metered_cost_estimate"), "seconds": meta.get("seconds_total", meta.get("seconds"))}.get(k, meta.get(k))
        if v is not None:
            t[k] = v
    return t


def _clear(out: Path, key: str):
    for sub in ("pages", "blocks", "rows", "crops"):
        for f in (out / sub).glob(f"{key}-*"):
            f.unlink()


def build(run_id: str, runs_dir="runs", out="site/data", counties=None, data_root=None) -> list[str]:
    if run_id == "latest":
        run_id = latest_run(runs_dir)
    run_dir = Path(runs_dir) / run_id
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    meta = json.loads((run_dir / "run.json").read_text()) if (run_dir / "run.json").exists() else {}
    if meta.get("resumed_from"):
        tot = total_seconds(meta, runs_dir)
        if tot is not None:
            meta["seconds_total"] = tot
    summary = json.loads((run_dir / "summary.json").read_text()) if (run_dir / "summary.json").exists() else None
    if summary:       # a summary run has no run.json: its own span of time stands for the run
        meta = {**{k: summary[k] for k in ("started", "ended") if summary.get(k)}, **meta}
    by_summary = {c["county"]: c for c in (summary or {}).get("counties", [])}
    # the run's own order when it kept one; else the folders' (alphabetical)
    keys = [c["county"] for c in (summary or {}).get("counties", [])] or sorted(p.parent.name for p in run_dir.glob("*/county.json"))
    if counties:
        keys = [k for k in keys if k in counties]
    if not keys:
        raise SystemExit(f"no county.json under {run_dir}")
    index = {"run": run_id, "started": meta.get("started"), "ended": meta.get("ended"), "counties": [], "summary": {},
             "run_totals": {k: meta[k] for k in ("model_calls", "prompt_tokens", "completion_tokens",
                                                 "metered_cost_estimate") if k in meta}}
    for key in keys:
        summ = by_summary.get(key)
        # a summary run names the run each county's figures come from
        cdir = Path(runs_dir) / str((summ or {}).get("from_run") or run_id) / key
        raw = json.loads((cdir / "county.json").read_text())
        if (summ or {}).get("status") == "unchecked" or raw.get("layout") == "no_printed_totals":
            index["counties"].append(unchecked_entry(key, summ, raw))
            continue
        _clear(out, key)
        fpath = cdir / "findings.json"
        findings = json.loads(fpath.read_text()) if fpath.exists() else None
        report = raw.get("layout") == "report"
        rows, images = None, None
        if report:
            # the page images of a report county are written only for the pages that carry a finding, and page 1
            images = {1} | {f["page"] for f in (findings or {}).get("findings", []) if f.get("page")}
            images &= {p["number"] for p in raw["pages"]}
            sizes = frame_sizes(raw)
            sizes.update(render_pages(key, sorted(images), out / "pages", data_root))
            crops, tots = wanted_rows(raw, findings)
            from PIL import Image
            from .render import page_png
            from .sources import DATA
            frame = {p["number"]: p.get("width") or sizes[p["number"]][0] for p in raw["pages"]}

            def im_of(n, _k=key):
                with Image.open(page_png(_k, n, CROP_DPI, data_root or DATA)) as im:
                    return im.convert("L")
            rc, fx, rcix = build_rows(raw, crops, tots, im_of, frame.get, lambda n: sizes[n][2] / frame[n], out / "rows",
                                      lambda county, n: f"data/rows/{county}-r{n}.webp")
            rows = {"rc": rc, "fx": fx, "rcix": rcix}
            inks, rules = {}, {}
        else:
            sizes = render_pages(key, [p["number"] for p in raw["pages"]], out / "pages", data_root)
            inks, rules = render_blocks(raw, sizes, out / "blocks", data_root)
        crops_dir = out / "crops"

        def crop_path(county, gid, src, _dir=cdir):
            if not src or not (_dir / src).exists():
                return None
            crops_dir.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(_dir / src, crops_dir / f"{county}-{gid}.png")
            return f"data/crops/{county}-{gid}.png"

        run = dict(meta)
        for src, dst in (("seconds", "seconds"), ("metered_cost", "metered_cost_estimate"), ("model_calls_by_model", "model_calls_by_model"),
                         ("reader", "reader")):
            if (summ or {}).get(src) is not None:      # a run of every county: the county's own figures, not the run's
                run[dst] = summ[src]
        if raw.get("sample") and not run.get("sample"):
            run["sample"] = raw["sample"]
        d = build_county(raw, sizes, ink=inks, rules=rules, findings=findings, run=run,
                         findings_path=fpath.as_posix() if findings else None,
                         evidence=f"data/{key}-findings.json" if findings else None, crop_path=crop_path,
                         rows=rows, images=images)
        if findings:
            shutil.copyfile(fpath, out / f"{key}-findings.json")
        (out / f"{key}.json").write_text(json.dumps(d, separators=(",", ":")))
        index["counties"].append(county_entry(key, summ, findings, len(d["pages"]), raw.get("layout") or ""))
        index["summary"][key] = raw.get("summary", {})
    if counties and (out / "index.json").exists():
        # a build of some counties keeps the entries of the others that an earlier build of this run wrote
        old = json.loads((out / "index.json").read_text())
        if old.get("run") == run_id:
            built = {c["key"] for c in index["counties"]}
            mine = {c["key"]: c for c in index["counties"]}
            mine.update({c["key"]: c for c in old["counties"] if c["key"] not in built})
            order = [c["county"] for c in (summary or {}).get("counties", [])] or sorted(mine)
            index["counties"] = [mine[k] for k in order if k in mine]
            index["summary"] = {**old.get("summary", {}), **index["summary"]}
    index["totals"] = run_totals(index["counties"], summary, meta)
    (out / "index.json").write_text(json.dumps(index, separators=(",", ":")))
    return keys


def frame_sizes(raw: dict, max_width=MAX_WIDTH) -> dict:
    """The sizes of the pages without rendering them: (frame_w, frame_h, img_w, img_h) from the sizes the run recorded."""
    out = {}
    for pg in raw["pages"]:
        w, h = pg.get("width"), pg.get("height")
        if not w or not h:
            raise ValueError(f"page {pg['number']} of {raw['county']} has no recorded size")
        iw = min(max_width, w)
        out[pg["number"]] = (w, h, iw, round(h * iw / w))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(prog="python -m crossfoot.sitebuild")
    ap.add_argument("--run", required=True, help="a run id, or latest: the newest run that has a findings.json")
    ap.add_argument("--runs-dir", default="runs")
    ap.add_argument("--out", default="site/data")
    ap.add_argument("--county", action="append")
    a = ap.parse_args(argv)
    keys = build(a.run, a.runs_dir, a.out, a.county)
    print(f"wrote {a.out}/index.json and {len(keys)} county file(s): {', '.join(keys)}")


if __name__ == "__main__":
    main()
