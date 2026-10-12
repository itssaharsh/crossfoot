"""Report layout (San Saba, Cottle and others): one precinct per section, one row per candidate with four numbers.

Reading: the county's layout is decided from its first page (`profile.decide_layout`); the first page is read under that
decision and the decision is thrown away if more than a third of its row sums fail. The same sample chooses the reader
(`profile.decide`). One page per model call at 200 dpi, strict JSON, one repair request.

The ledger: a cell is (page, block, row, column). A block is one contest on one precinct, `block_id` "<precinct key>|<n>"
(a contest that runs over a page break is one block: its cells carry different pages and the same block id); the Statistics
rows "Ballots Cast - Total" and "Ballots Cast - Blank" are blocks of their own, named as the published file names them.
`row_kind` is the row's label as printed, `column` is total | absentee | early | election_day. A cell's box is the row's
strip of the page at 200 dpi ([0, y - 20, x_right, y + 20]; y is the model's own estimate, so the box is approximate and
re-read crops are cut with generous padding).

Checks (`checks.report_checks`): each row's total = absentee + early voting + election day; where a contest prints a total
row ("Total Votes Cast", "Cast Votes"), the candidates' figures in a column add to that row's figure in the column. A value
sits on its row's own sum, and, only where the page prints a contest total, on the column's sum too.
"""
from __future__ import annotations

import json
import re
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from PIL import Image

from .. import agent, checks, settings, tracing
from ..model import BudgetExceeded
from ..render import page_png
from . import profile

COLS = checks.REPORT_COLS
HALF_ROW = 20          # half the height of a row's box, pixels at 200 dpi
ROW_PAD = 100          # a re-read crop reaches this far above and below the row's centre, pixels at 200 dpi
GEO_DPI = 200
MAX_ACTIONS = agent.MAX_ACTIONS
NOTE_NO_TOTALS = "nothing on this scan can be cross-checked; left as published"


# ---- names: both sides are normalised before they are compared ---------------------------------------------------------

def precinct_key(name) -> str:
    """"PRECINCT 101", "Precinct 101" and "101" are one precinct; so are "Precinct 2A", "2A" and "02a"."""
    s = re.sub(r"\b(?:precinct|pct)\b", " ", str(name or ""), flags=re.I)
    s = re.sub(r"[^a-z0-9]", "", s.lower())
    return re.sub(r"^0+(?=\d)", "", s)


def contest_canon(label) -> str:
    """A contest's name with the scan's and the file's spellings made one: "Pl 2" = "PI 2", "Dist" = "District" (the word
    is dropped on both sides), "Vote For 1" lines dropped, "United States Senator" = "U.S. Senate", "Representative" =
    "House", "President and Vice President" = "President", "Precinct No. 1" = "Pct 1" = "1", "46th Judicial District" = "46"."""
    s = str(label or "").lower()
    s = re.sub(r"[,;]?\s*vote\s+for\s+\d+\s*$", "", s.strip())
    s = re.sub(r"\s*(?:/|\band\b)\s*vice[\s-]*president\b", "", s)
    s = re.sub(r"\bunited\s+states\b|\bu\.\s?s\.?(?=\s|$)", "us", s)
    s = re.sub(r"\bsenator\b", "senate", s)
    s = re.sub(r"\brepresentative\b", "house", s)
    s = re.sub(r"(\d+)(?:st|nd|rd|th)\s+judicial\b", r"\1", s)
    s = re.sub(r"\b(?:district|dist|precinct|pct|no)\b\.?", " ", s)
    s = re.sub(r"\bplace\b", "pl", s)
    s = re.sub(r"\bp[il](?=\s*\d)", "pl", s)
    return re.sub(r"[^a-z0-9]", "", s)


_PARTY = re.compile(r"^(REP|DEM|LIB|GRN|IND|NPA|UNA|NON)\s+(.+)$")
_WRITE_IN = ("writeintotals", "writeintotal", "writeins", "writein")


def split_label(label) -> tuple[str, str]:
    """(party, name) of a row label as printed: "REP Donald J. Trump/JD Vance" -> ("REP", "Donald J. Trump"). A write-in
    row is "Write-ins" as the published file names it."""
    s = " ".join(str(label or "").split())
    if re.sub(r"[^a-z]", "", s.lower()) in _WRITE_IN:
        return "", "Write-ins"
    m = _PARTY.match(s)
    party, rest = (m.group(1), m.group(2)) if m else ("", s)
    return party, rest.split("/")[0].strip()


# ---- the model's answers --------------------------------------------------------------------------------------------------

PAGE_PROMPT = """TASK: page.
This image is one page of a scanned election results report (one precinct per section). At the top left, below the
report's title lines, the precinct's name is printed alone in bold at the left, just above the first horizontal rule
(it is short: a number, or a number with a letter, or a word and a number). It is NOT the county name printed at the top
right of the page, and NOT part of the title lines. A Statistics block may follow, then one block per contest: a
heading, "Vote For 1", then one row per candidate. Each row has a label and four numbers under the headings, left to
right: {order}. Ignore any percentage columns.
Answer with strict JSON only, no prose:
{{"precinct": "<the precinct name as printed>",
 "contests": [{{"name": "<the contest heading as printed; \\"Statistics\\" for the Statistics block>",
               "continued": <true if this block carries on a contest from the previous page (no heading, or a heading marked
                             as continued), else false>,
               "rows": [{{"label": "<the row label exactly as printed, party prefix included>",
                         "total": <integer or null>, "absentee": <integer or null>, "early": <integer or null>,
                         "election_day": <integer or null>,
                         "y": <the row's vertical position as a number from 0 (top of the page) to 1000 (bottom)>}}]}}]}}
In the Statistics block give only the rows "Ballots Cast - Total" and "Ballots Cast - Blank". Include every row of every
contest, including "Write-In Totals", "Total Votes Cast", "Cast Votes", "Overvotes" and "Undervotes" rows where printed.
Use null for a number that is not printed. Read the digits exactly as printed; do not correct or add anything up."""

ROW_PROMPT = """TASK: row.
This image is a crop of one row of a scanned election results report. The row to read is the one whose label reads
"{label}"; rows above or below it may show at the edges, ignore them. The row has up to four numbers under the headings,
left to right: {order}. Ignore any percentage.
Answer with strict JSON only: {{"total": <integer or null>, "absentee": <integer or null>, "early": <integer or null>,
"election_day": <integer or null>}}. Use null for a number that is not printed. Read the digits exactly as printed; do not
correct or add anything up."""

_NAMES = {"total": "TOTAL", "absentee": "Absentee", "early": "Early Voting", "election_day": "Election Day"}


def order_text(order) -> str:
    return ", ".join(_NAMES[c] for c in order)


def _int_or_none(v, what):
    if v is None or (isinstance(v, int) and not isinstance(v, bool)):
        return v
    raise ValueError(f"{what} must be an integer or null, got {v!r}")


def page_validator(d):
    if not isinstance(d, dict):
        raise ValueError("answer must be an object")
    p = d.get("precinct")
    if not isinstance(p, str) or not p.strip():
        raise ValueError('"precinct" must be the precinct name as a non-empty string')
    d["precinct"] = p.strip()
    cs = d.get("contests")
    if not isinstance(cs, list):
        raise ValueError('"contests" must be a list')
    for c in cs:
        if not isinstance(c, dict) or not isinstance(c.get("name", ""), str) or not isinstance(c.get("rows"), list):
            raise ValueError('each contest needs a "name" string and a "rows" list')
        c["continued"] = bool(c.get("continued"))
        for r in c["rows"]:
            if not isinstance(r, dict) or not isinstance(r.get("label"), str) or not r["label"].strip():
                raise ValueError('each row needs a "label" string')
            for col in COLS:
                _int_or_none(r.get(col), f"{col} of {r['label']!r}")
            y = r.get("y")
            if isinstance(y, bool) or not isinstance(y, (int, float)) or not 0 <= y <= Y_SLACK:
                raise ValueError(f'"y" of {r["label"]!r} must be a number from 0 to 1000')
            r["y"] = min(y, 1000)       # the last row of a full page was read at 1108 (Scurry page 18): it is an estimate


Y_SLACK = 1250     # how far past the bottom edge a row's estimated position may be before the answer is refused


def row_validator(d):
    if not isinstance(d, dict):
        raise ValueError("answer must be an object")
    for col in COLS:
        if col not in d:
            raise ValueError(f'"{col}" is missing')
        _int_or_none(d[col], col)


# ---- the page into the ledger ------------------------------------------------------------------------------------------

class State:
    def __init__(self):
        self.names: dict = {}      # precinct key -> name as printed
        self.count: dict = {}      # precinct key -> contests so far
        self.last: dict = {}       # precinct key -> (contest key, block id, contest name)
        self.labels: set = set()   # (block, row label) already stored


def ink_right(png, margin=40) -> int:
    """The right edge of the table on a page, from the middle of the page itself: the last column with ink, plus a margin."""
    import numpy as np
    with Image.open(png) as im:
        g = np.asarray(im.convert("L"))
    h, w = g.shape
    idx = np.nonzero((g[int(h * .25):int(h * .75)] < 128).sum(axis=0) >= 3)[0]
    return int(min(w, idx.max() + margin)) if len(idx) else int(w)


def store_page(led, county, page, ans, st: State, *, model, size, x_right) -> int:
    """Put one page's answer into the ledger as first reads. Returns the number of cells stored."""
    w, h = size
    pk = precinct_key(ans["precinct"])
    st.names.setdefault(pk, ans["precinct"])
    n = 0

    def put_row(block, contest, r):
        nonlocal n
        label = " ".join(r["label"].split()).rstrip(":").strip() or r["label"].strip()   # Foard prints "Cast Votes:"
        if (block, label) in st.labels:
            label += " (2)"
        st.labels.add((block, label))
        yp = float(r["y"]) / 1000 * h
        box = (0, max(0, round(yp - HALF_ROW)), x_right, min(h, round(yp + HALF_ROW)))
        for col in COLS:
            if r.get(col) is not None:
                led.put_cell(county, page, block, label, col, r[col], contest=contest, candidate=label, model=model, box=box)
                n += 1

    for i, c in enumerate(ans["contests"]):
        name = c.get("name", "").strip()
        if name.lower().startswith("statistics"):
            for r in c["rows"]:
                low = r["label"].lower()
                if "ballots cast" not in low:
                    continue
                blank = "blank" in low
                put_row(f"{pk}|s{'b' if blank else 't'}", "Ballots Cast Blank" if blank else "Ballots Cast", r)
            continue
        key, last = contest_canon(name), st.last.get(pk)
        if last and (c["continued"] or not name or (i == 0 and last[0] == key)):
            block, cname = last[1], last[2]
        else:
            st.count[pk] = st.count.get(pk, 0) + 1
            block, cname = f"{pk}|{st.count[pk]}", name or "(no heading)"
            st.last[pk] = (key, block, cname)
        for r in c["rows"]:
            put_row(block, cname, r)
    return n


# ---- where the rows are: the model's estimate, snapped to the lines of text on the page --------------------------------

def text_bands(png, x_right) -> list[float]:
    """Centres (pixels of the image) of the lines that look like a row of figures: ink in the label column and ink in the
    number columns on the same line. Found from the page itself."""
    import numpy as np
    with Image.open(png) as im:
        g = np.asarray(im.convert("L"))
    ink = (g[:, :max(50, int(min(g.shape[1], x_right) * 0.45))] < 128).sum(axis=1) >= 2
    right = (g[:, int(x_right * 0.5):int(x_right)] < 128).sum(axis=1) >= 1
    out, start = [], None
    for y, v in enumerate(list(ink) + [False]):
        if v and start is None:
            start = y
        elif not v and start is not None:
            out.append((start, y - 1))
            start = None
    merged: list = []
    for a, b in out:
        if merged and a - merged[-1][1] <= 4:
            merged[-1] = (merged[-1][0], b)
        else:
            merged.append((a, b))
    return [(a + b) / 2 for a, b in merged if b - a >= 6 and right[a:b + 1].sum() >= 6]


def _align(ys, bands):
    """Monotone one-to-one assignment of every row to a line (lines may be left over), minimising the squared distance."""
    import numpy as np
    m, n = len(ys), len(bands)
    cost = np.full((m + 1, n + 1), np.inf)
    cost[0, :] = 0.0
    take = np.zeros((m + 1, n + 1), bool)
    for i in range(1, m + 1):
        for j in range(i, n + 1):
            c = cost[i - 1, j - 1] + (ys[i - 1] - bands[j - 1]) ** 2
            if c <= cost[i, j - 1]:
                cost[i, j], take[i, j] = c, True
            else:
                cost[i, j] = cost[i, j - 1]
    out, j = [0] * m, n
    for i in range(m, 0, -1):
        while not take[i, j]:
            j -= 1
        out[i - 1] = j - 1
        j -= 1
    return out


def snap_rows(png, ys, x_right) -> tuple[list[float], bool]:
    """The model's vertical estimates are compressed and uneven (measured on San Saba: gaps between contests collapse), so
    each row is put on one of the page's own lines of figures: first by rank, then by a fitted scale and offset. Needs at
    least as many lines as rows; otherwise the estimates are returned as given."""
    import numpy as np
    bands = np.array(text_bands(png, x_right))
    ys = np.asarray(ys, float)
    if len(ys) < 3 or len(bands) < len(ys):
        return list(ys), False
    best = None
    for k in range(len(bands) - len(ys) + 1):             # lines before the first row that are not rows: try each count
        idx = list(range(k, k + len(ys)))
        for _ in range(3):                                # fit a scale and offset on the pairs, assign again in pixels
            a, b = np.polyfit(ys, bands[idx], 1)
            idx = _align(ys * a + b, bands)
        err = float(((ys * a + b - bands[idx]) ** 2).sum())
        if best is None or err < best[0]:
            best = (err, idx)
    idx = best[1]
    return [float(bands[i]) for i in idx], True


def refit_boxes(led, county, png_fn=page_png, root=None, x_right=None) -> int:
    """Re-place every row's box from the page itself (one pass per page; the same for a fresh read and for a resumed
    ledger). Returns the number of pages where an alignment was found."""
    from ..sources import DATA
    root = root or DATA
    x_right = x_right or layout_event(led, county).get("x_right") or 800
    cells = led.cells(county)
    n = 0
    for page in sorted({c["page"] for c in cells}):
        rows: dict = {}
        for c in cells:
            if c["page"] == page and c["y0"] is not None:
                rows.setdefault((c["block_id"], c["row_kind"]), (c["y0"] + c["y1"]) / 2)
        keys = list(rows)
        ys, ok = snap_rows(png_fn(county, page, GEO_DPI, root), [rows[k] for k in keys], x_right)
        n += ok
        h = Image.open(png_fn(county, page, GEO_DPI, root)).size[1]
        for (blk, label), y in zip(keys, ys):
            for c in cells:
                if (c["page"], c["block_id"], c["row_kind"]) == (page, blk, label):
                    led.set_box(county, page, blk, label, c["column"], (0, max(0, round(y - HALF_ROW)), x_right,
                                                                           min(h, round(y + HALF_ROW))))
        led.event(county, "boxes_refit", {"page": page, "aligned": ok, "rows": len(keys)})
    return n


def reopen(led, county) -> None:
    """A resumed ledger is closed again from its first reads: verdicts and final statuses are dropped."""
    led.db.execute("DELETE FROM verdicts WHERE county=?", (county,))
    led.db.execute("UPDATE cells SET status='first_read', reason=NULL WHERE county=? AND status IN "
                   "('cannot_verify','document_inconsistent','accepted','failed')", (county,))
    led.db.commit()


# ---- reading a county --------------------------------------------------------------------------------------------------

def page_count(county, root=None) -> int:
    from ..sources import DATA, scan_path
    out = subprocess.run(["pdfinfo", str(scan_path(county, root or DATA))], capture_output=True, text=True, check=True).stdout
    return int(re.search(r"^Pages:\s+(\d+)", out, re.M).group(1))


def row_sums(led, county) -> tuple[int, int]:
    """(row sums, failing) over the ledger's cells."""
    chs = checks.report_row_checks(led.cells(county))
    return len(chs), sum(1 for c in chs if not c.ok)


def summarize(led, county) -> dict:
    cells = led.cells(county)
    rows, con = checks.report_row_checks(cells), checks.report_contest_checks(cells)
    more = checks.report_writein_checks(cells) + checks.report_ballot_sums(cells)[0]       # write-in breakdown, ballots cast
    return {"cells_read": len(cells), "row_sums_pass": sum(c.ok for c in rows), "row_sums_fail": sum(not c.ok for c in rows),
            "contest_sums_pass": sum(c.ok for c in con + more), "contest_sums_fail": sum(not c.ok for c in con + more),
            "contests_with_a_printed_total": len({c.block_id for c in con}),
            "contests": len({c["block_id"] for c in cells})}


def read_county(county, gw, led, *, run_id="", log=print, png_fn=page_png, n_pages=None, pages=None, data_root=None,
                model="auto") -> dict:
    """Decide the layout from page 1, read it under that decision, reject the decision if more than a third of the page's
    row sums fail, choose the reader by the sample, read every page. Returns the summary dict."""
    from ..sources import DATA
    root = data_root or DATA
    t0 = time.time()
    out = {"county": county, "run_id": run_id, "layout": None, "layout_decision": None, "reader": None, "sample": None,
           "pages_read": [], "pages_failed": [], "stopped": None, "note": None}

    def finish():
        out.update(summarize(led, county))
        out.update(model_calls=gw.calls, prompt_tokens=gw.prompt_tokens, completion_tokens=gw.completion_tokens,
                   metered_cost_estimate=round(gw.cost, 4), seconds=round(time.time() - t0, 1))
        return out
    try:
        with tracing.trace("read_county", kind="WORKFLOW", run=run_id, county=county):
            png1 = png_fn(county, 1, GEO_DPI, root)
            gw.model = profile.SAMPLE_MODEL
            try:
                lay = profile.decide_layout(gw, png1)
            except ValueError as e:
                out.update(layout="not_supported", note=f"layout not supported: the first page's layout was not decided ({str(e)[:120]})")
                led.event(county, "layout", {"layout": None, "error": str(e)[:200]})
                return finish()
            out["layout_decision"] = dict(lay, accepted=None)
            if lay["layout"] == "no_printed_totals":
                out.update(layout="no_printed_totals", note=NOTE_NO_TOTALS)
                led.event(county, "layout", dict(lay, accepted=True, note=NOTE_NO_TOTALS))
                log(f"{county}: {NOTE_NO_TOTALS}")
                return finish()
            if lay["layout"] != "report":
                out.update(layout=lay["layout"], note=f"the {lay['layout']} layout is not read by this command")
                led.event(county, "layout", dict(lay, accepted=False))
                return finish()
            order = lay["columns"]
            size = Image.open(png1).size
            x_right = ink_right(png1)
            st = State()

            def ask_page(page, mdl):
                """The model call for one page (safe to run on a worker thread: it touches no ledger)."""
                png = png_fn(county, page, GEO_DPI, root)
                with tracing.trace("read_page", kind="TOOL", run=run_id, county=county, page=page, model=mdl):
                    return png, gw.ask_json(PAGE_PROMPT.format(order=order_text(order)), png, validate=page_validator, model=mdl)

            def put_page(page, png, ans, mdl):
                n = store_page(led, county, page, ans, st, model=mdl, size=Image.open(png).size, x_right=x_right)
                led.event(county, "page_read", {"page": page, "precinct": ans["precinct"], "model": mdl, "cells": n,
                                                "contests": len(ans["contests"])})
                return n

            def read_page(page, mdl):
                return put_page(page, *ask_page(page, mdl), mdl)

            try:
                read_page(1, profile.SAMPLE_MODEL)
            except ValueError as e:
                led.event(county, "page_failed", {"page": 1, "error": str(e)[:300]})
                log(f"  page 1: failed ({str(e)[:100]})")
            total, failing = row_sums(led, county)
            dec = {"layout": lay["layout"], "columns": order, "row_sums": total, "failing": failing,
                   "line": "one third", "accepted": not profile.rejected(failing, total)}
            out["layout_decision"] = dec
            led.event(county, "layout", dict(dec, x_right=x_right, size=list(size)))
            if not dec["accepted"]:
                led.clear_values(county)
                out.update(layout="not_supported", note=(f"layout not supported: {failing} of {total} row sums of the first "
                                                         f"page fail under the {lay['layout']} layout, over a third; left alone"))
                log(out["note"])
                return finish()
            out["layout"] = "report"
            if model == "auto":
                sample = profile.decide(failing, total)
                led.event(county, "choose_reader", sample)
                log(profile.sentence(sample))
                out["sample"] = sample
                gw.model = sample["reader"]
                if not sample["kept_sample"]:
                    led.clear_values(county)
                    st = State()
                    try:
                        read_page(1, gw.model)
                    except ValueError as e:
                        led.event(county, "page_failed", {"page": 1, "error": str(e)[:300]})
                        out["pages_failed"].append(1)
            else:
                gw.model = model
                out["sample"] = {"reader": model, "skipped": True, "kept_sample": False}
                led.event(county, "choose_reader", out["sample"])
            out["reader"] = gw.model
            out["pages_read"].append(1)
            n = n_pages or page_count(county, root)
            todo = [p for p in (pages or range(2, n + 1)) if p != 1]
            # up to `settings.workers` model calls in flight; the answers are put in the ledger here, one thread, in page order
            with ThreadPoolExecutor(settings.workers) as ex:
                futs = [(p, ex.submit(ask_page, p, gw.model)) for p in todo]
                try:
                    for page, f in futs:
                        try:
                            png, ans = f.result()
                            put_page(page, png, ans, gw.model)
                            out["pages_read"].append(page)
                        except BudgetExceeded:
                            raise
                        except ValueError as e:
                            led.event(county, "page_failed", {"page": page, "error": str(e)[:300]})
                            out["pages_failed"].append(page)
                            log(f"  page {page}: failed ({str(e)[:100]})")
                finally:
                    for _, f in futs:
                        f.cancel()
    except BudgetExceeded as e:
        out["stopped"] = str(e)
        log(f"stopped: {e}")
    return finish()


def state_from(led, county, before_page) -> State:
    """The reading state as it stood before `before_page`, rebuilt from the ledger: the precinct names, how many blocks each
    precinct has (a new block gets a number above every existing one, so none collides with a later page's), the last contest of
    each precinct on the pages before, and the labels already stored."""
    st = State()
    for e in led.events(county):
        if e["kind"] == "page_read":
            d = json.loads(e["payload_json"])
            st.names.setdefault(precinct_key(d["precinct"]), d["precinct"])
    cells = led.cells(county)
    for c in cells:
        pk, _, n = c["block_id"].partition("|")
        if n.isdigit():
            st.count[pk] = max(st.count.get(pk, 0), int(n))
        st.labels.add((c["block_id"], c["row_kind"]))
    for c in sorted((c for c in cells if c["page"] < before_page and c["block_id"].partition("|")[2].isdigit()),
                    key=lambda c: (c["page"], int(c["block_id"].partition("|")[2]))):
        st.last[c["block_id"].partition("|")[0]] = (contest_canon(c["contest"]), c["block_id"], c["contest"])
    return st


def read_pages_into(county, gw, led, pages, *, log=print, png_fn=page_png, data_root=None) -> dict:
    """Read only `pages` (pages a first read failed on) into a ledger that already holds the others, with the reader and the
    page geometry that ledger recorded. Returns {pages_read, pages_failed, stopped}."""
    from ..sources import DATA
    root = data_root or DATA
    lay = layout_event(led, county)
    order = lay.get("columns") or list(COLS)
    chosen = next((json.loads(e["payload_json"]) for e in reversed(led.events(county)) if e["kind"] == "choose_reader"), None)
    gw.model = (chosen or {}).get("reader") or agent.HAIKU
    out = {"pages_read": [], "pages_failed": [], "stopped": None}
    for page in pages:
        try:
            png = png_fn(county, page, GEO_DPI, root)
            ans = gw.ask_json(PAGE_PROMPT.format(order=order_text(order)), png, validate=page_validator, model=gw.model)
            st = state_from(led, county, page)
            n = store_page(led, county, page, ans, st, model=gw.model, size=Image.open(png).size, x_right=lay.get("x_right"))
            led.event(county, "page_read", {"page": page, "precinct": ans["precinct"], "model": gw.model, "cells": n,
                                            "contests": len(ans["contests"])})
            out["pages_read"].append(page)
            log(f"  page {page}: read ({n} cells, {ans['precinct']})")
        except BudgetExceeded as e:
            out["stopped"] = str(e)
            break
        except ValueError as e:
            led.event(county, "page_failed", {"page": page, "error": str(e)[:300]})
            out["pages_failed"].append(page)
            log(f"  page {page}: failed ({str(e)[:100]})")
    return out


# ---- where a row is: crops for re-reads and for the findings --------------------------------------------------------------

class ReportGeometry:
    """Crops of whole rows of a report-layout county. A box is [x0, y0, x1, y1] in pixels of the 200 dpi page."""

    def __init__(self, county, x_right=None, png_fn=page_png, root=None):
        from ..sources import DATA
        self.county, self.x_right, self.png_fn, self.root = county, x_right, png_fn, root or DATA

    def crop_row(self, page, box, dpi, dest) -> Path:
        k = dpi / GEO_DPI
        cy = (box[1] + box[3]) / 2
        with Image.open(self.png_fn(self.county, page, dpi, self.root)) as im:
            x1 = self.x_right or box[2]
            c = im.crop((0, max(0, round((cy - ROW_PAD) * k)), min(im.width, round(x1 * k)),
                         min(im.height, round((cy + ROW_PAD) * k))))
        Path(dest).parent.mkdir(parents=True, exist_ok=True)
        c.save(dest)
        return Path(dest)

    def block_box(self, page, bid):
        return None

    def total_box(self, *a):
        return None


def layout_event(led, county) -> dict:
    """The page-1 decision as the ledger recorded it: {columns, x_right, size, ...}; an empty dict if there is none."""
    return next((json.loads(e["payload_json"]) for e in reversed(led.events(county)) if e["kind"] == "layout"), {})


# ---- the loop on a failing sum ---------------------------------------------------------------------------------------------

def steps(reader) -> list[tuple[str, int]]:
    """The (model, dpi) of each re-read of a row, weakest first: the county's reader at 300 and 400 dpi, then
    claude-sonnet-4.6 at 400 and 500, then claude-opus-4.6 at 500 and 600. At most six; none repeats."""
    lad = agent.ladder_for(reader)
    out: list = []
    for i, d in enumerate((300, 400, 400, 500, 500, 600)):
        s = (lad[min(i // 2, len(lad) - 1)], d)
        if s not in out:
            out.append(s)
    return out


def derive_status(led, county) -> list[dict]:
    """accepted iff the cell sits on at least one printed sum and every one holds; final statuses stay."""
    cells = led.cells(county)
    on = checks.report_crossing(cells)
    out = []
    for c in cells:
        if c["status"] in agent.FINAL:
            continue
        cs = on.get(checks.cell_key(c), [])
        new = "accepted" if cs and all(x.ok for x in cs) else ("failed" if c["status"] == "failed" else "first_read")
        if new != c["status"]:
            led.set_status(county, c["page"], c["block_id"], c["row_kind"], c["column"], new)
            out.append({"cell": list(checks.cell_key(c)), "old": c["status"], "new": new})
    return out


def _holding(cells, page, block, label) -> int:
    """How many printed sums through the row (its own, and the contest's columns) hold."""
    keys = {(page, block, label, col) for col in COLS}
    return sum(ch.ok for ch in checks.report_checks(cells)
               if any(k in keys for k, _ in ch.terms) or ch.printed_key in keys)


def _vals(cells, page, block, label) -> dict:
    return {c["column"]: c["value"] for c in cells if (c["page"], c["block_id"], c["row_kind"]) == (page, block, label)}


class Closer:
    def __init__(self, county, gw, led, geo, *, reader, run_id="", log=print, crop_dir=None, order=COLS):
        self.county, self.gw, self.led, self.geo, self.run_id, self.log = county, gw, led, geo, run_id, log
        self.reader = agent.norm(reader or getattr(gw, "model", None) or agent.HAIKU)
        self.steps = steps(self.reader)
        self.order = list(order)
        self.crop_dir = Path(crop_dir) if crop_dir else Path("runs") / run_id / "crops"
        self.n_crops = 0
        self.rereads = 0

    def ev(self, kind, **payload):
        self.led.event(self.county, kind, payload)

    def box_of(self, page, block, label):
        c = next((c for c in self.led.cells(self.county)
                  if (c["page"], c["block_id"], c["row_kind"]) == (page, block, label) and c["x0"] is not None), None)
        return [c["x0"], c["y0"], c["x1"], c["y1"]] if c else None

    def reread(self, item, page, block, label, step) -> dict | None:
        """One action: the row's strip at the step's dpi with the step's model. Keeps the new reading only if more of the
        sums through the row hold with it. Returns {values, kept, model, dpi} or None when no crop could be cut."""
        model, dpi = self.steps[step]
        box = self.box_of(page, block, label)
        self.n_crops += 1
        dest = self.crop_dir / f"reread-{self.n_crops:04d}-{block.replace('|', '-')}.png"
        try:
            if box is None:
                raise ValueError("the row has no box on the page")
            path = self.geo.crop_row(page, box, dpi, dest)
        except Exception as e:
            self.ev("refused", item=item, target=[page, block, label], reason=f"no crop: {str(e)[:120]}")
            return None
        with tracing.trace("reread_row", kind="TOOL", run=self.run_id, county=self.county, page=page, block=block,
                           row=label, dpi=dpi, model=model):
            ans = self.gw.ask_json(ROW_PROMPT.format(label=label, order=order_text(self.order)), path,
                                   validate=row_validator, model=model)
        self.rereads += 1
        if all(ans[c] is None for c in COLS):          # nothing read: not a reading
            self.ev("reread", item=item, page=page, block=block, row=label, model=model, dpi=dpi, ladder_step=step,
                    crop=str(path), box=box, reading=None, kept="old", unreadable=True)
            return {"values": None, "kept": False, "model": model, "dpi": dpi}
        cells = self.led.cells(self.county)
        old = _vals(cells, page, block, label)
        new = {c: ans[c] for c in COLS if c in old and ans[c] is not None}
        trial = [dict(c, value=new.get(c["column"], c["value"])) if (c["page"], c["block_id"], c["row_kind"]) ==
                 (page, block, label) else c for c in cells]
        kept = _holding(trial, page, block, label) > _holding(cells, page, block, label)
        for col, v in (new if kept else {}).items():
            self.led.reread_cell(self.county, page, block, label, col, v, model)
        derive = derive_status(self.led, self.county)
        self.ev("reread", item=item, page=page, block=block, row=label, model=model, dpi=dpi, ladder_step=step,
                crop=str(path), box=box, old=old, reading={c: ans[c] for c in COLS}, kept="new" if kept else "old")
        if derive:
            self.ev("status_change", changes=derive)
        return {"values": tuple(ans[c] for c in COLS), "kept": kept, "model": model, "dpi": dpi}

    def verdict(self, ch, verdict, reason):
        self.led.set_verdict(self.county, agent.sum_id(ch), ch.page, ch.block_id, verdict, reason)
        keys = {k for k, _ in ch.terms} | ({ch.printed_key} if ch.printed_key else set())
        for c in self.led.cells(self.county):
            if checks.cell_key(c) in keys and c["status"] not in agent.FINAL and c["status"] != "accepted":
                self.led.set_status(self.county, c["page"], c["block_id"], c["row_kind"], c["column"], verdict, reason)
        self.ev("verdict", sums=[agent.sum_id(ch)], verdict=verdict, reason=reason)

    def find(self, kind, page, block, key):
        return next((c for c in checks.report_checks(self.led.cells(self.county))
                     if (c.kind, c.page, c.block_id, c.key) == (kind, page, block, key)), None)

    def work_row(self, ch):
        item = agent.sum_id(ch)
        self.ev("item_start", item=item, page=ch.page, block=ch.block_id)
        readings, actions = [], 0
        for step in range(len(self.steps)):
            if actions >= MAX_ACTIONS:
                break
            actions += 1
            r = self.reread(item, ch.page, ch.block_id, ch.key, step)
            if r is None:
                break
            me = self.find(ch.kind, ch.page, ch.block_id, ch.key)
            if me is None or me.ok:
                self.ev("item_end", item=item, result="holds")
                return
            if r["values"] is None:
                readings.append((r["model"], r["dpi"], None))
                continue
            if r["values"] in [v for _, _, v in readings]:
                me = self.find(ch.kind, ch.page, ch.block_id, ch.key)
                parts = " + ".join(str(v) for _, v in me.terms)
                self.verdict(me, "document_inconsistent",
                             f"the scan shows {r['values']} (total, absentee, early voting, election day) on {len(readings) + 1} "
                             f"re-reads ({', '.join(f'{m} at {d} dpi' for m, d, _ in readings)}, and {r['model']} at "
                             f"{r['dpi']} dpi), and the row's own sum still fails: {parts} = {me.computed}, printed "
                             f"{me.printed}. The document disagrees with itself.")
                self.ev("item_end", item=item, result="document_inconsistent")
                return
            readings.append((r["model"], r["dpi"], r["values"]))
        me = self.find(ch.kind, ch.page, ch.block_id, ch.key) or ch
        gave = "; ".join(f"{m} at {d} dpi: {v if v else 'nothing could be read'}" for m, d, v in readings) or "no re-read could be made"
        self.verdict(me, "cannot_verify",
                     f"{actions} re-read(s) did not make the row's sum hold ({gave}); the row adds to {me.computed}, "
                     f"printed {me.printed}")
        self.ev("item_end", item=item, result="cannot_verify")

    def work_contest(self, ch):
        item = agent.sum_id(ch)
        self.ev("item_start", item=item, page=ch.page, block=ch.block_id)
        # the rows of this sum: its terms, and its printed total last
        rows = list(dict.fromkeys(tuple(k[:3]) for k, _ in ch.terms))
        if ch.printed_key and tuple(ch.printed_key[:3]) not in rows:
            rows.append(tuple(ch.printed_key[:3]))
        actions = 0
        for step in range(len(self.steps)):
            for page, block, label in rows:
                if actions >= MAX_ACTIONS:
                    break
                actions += 1
                self.reread(item, page, block, label, step)
                me = self.find(ch.kind, ch.page, ch.block_id, ch.key)
                if me is None or me.ok:
                    self.ev("item_end", item=item, result="holds")
                    return
            if actions >= MAX_ACTIONS:
                break
        me = self.find(ch.kind, ch.page, ch.block_id, ch.key) or ch
        self.verdict(me, "cannot_verify",
                     f"{actions} re-read(s) of the rows of this sum did not make its {ch.key} column hold: the "
                     f"the terms add to {me.computed}, the printed total is {me.printed}")
        self.ev("item_end", item=item, result="cannot_verify")


def finalize(led, county) -> list[dict]:
    """Every cell ends accepted, document_inconsistent or cannot_verify: a cell on no printed sum is cannot_verify; a cell on
    a failing sum takes that sum's verdict. A failing sum without a verdict gets one. Safe to run again."""
    cells = led.cells(county)
    on = checks.report_crossing(cells)
    vs = {v["sum_id"]: v for v in led.verdicts(county)}
    for chs in on.values():
        for ch in chs:
            if not ch.ok and agent.sum_id(ch) not in vs:
                why = "the sum was not worked: the run stopped first"
                led.set_verdict(county, agent.sum_id(ch), ch.page, ch.block_id, "cannot_verify", why)
                vs[agent.sum_id(ch)] = {"verdict": "cannot_verify", "reason": why}
    out = []
    for c in cells:
        if c["status"] in ("accepted", *agent.FINAL):
            continue
        cs = on.get(checks.cell_key(c), [])
        mine = [vs[agent.sum_id(x)] for x in cs if not x.ok]
        if not cs:
            new, why = "cannot_verify", "no printed sum covers this value"
        elif mine:
            v = next((x for x in mine if x["verdict"] == "document_inconsistent"), mine[0])
            new, why = v["verdict"], v["reason"]
        else:
            continue
        led.set_status(county, c["page"], c["block_id"], c["row_kind"], c["column"], new, why)
        out.append({"cell": list(checks.cell_key(c)), "old": c["status"], "new": new, "reason": why})
    if out:
        led.event(county, "status_change", {"changes": out})
    return out


def count_failing(chs) -> dict:
    return {"row": sum(c.kind == "report_row" and not c.ok for c in chs),
            "contest": sum(c.kind == "report_contest" and not c.ok for c in chs),
            "writein": sum(c.kind == "report_writein" and not c.ok for c in chs),
            "ballots": sum(c.kind == "report_ballots" and not c.ok for c in chs)}


def close_county(county, gw, led, geo, *, reader=None, run_id="", log=print, crop_dir=None, order=None) -> dict:
    """Work every failing sum of the ledger: rows first (a row's own sum), then contest columns. At most six actions per
    sum; each ends holding or with a verdict (document_inconsistent or cannot_verify) and a reason."""
    t0 = time.time()
    calls0, cost0 = gw.calls, gw.cost
    cl = Closer(county, gw, led, geo, reader=reader, run_id=run_id, log=log, crop_dir=crop_dir,
                order=order or layout_event(led, county).get("columns") or COLS)
    before = count_failing(checks.report_checks(led.cells(county)))
    cl.ev("close_start", failing_before=before, reader=cl.reader, steps=[list(s) for s in cl.steps])
    derive_status(led, county)
    stopped, worked = None, 0
    try:
        with tracing.trace("close_county", kind="AGENT", run=run_id, county=county):
            for kind, work in (("report_row", cl.work_row), ("report_writein", cl.work_contest),
                              ("report_contest", cl.work_contest), ("report_ballots", cl.work_contest)):
                done = {v["sum_id"] for v in led.verdicts(county)}
                todo = [c for c in checks.report_checks(led.cells(county))
                        if c.kind == kind and not c.ok and agent.sum_id(c) not in done]
                todo.sort(key=lambda c: (c.page, c.block_id, c.key))
                for c in todo:
                    now = cl.find(c.kind, c.page, c.block_id, c.key)
                    if now is None or now.ok or agent.sum_id(now) in {v["sum_id"] for v in led.verdicts(county)}:
                        continue
                    worked += 1
                    log(f"item {worked}: {agent.sum_id(c)}")
                    work(now)
    except BudgetExceeded as e:
        stopped = str(e)
        log(f"stopped: {e}")
        cl.ev("stop", item=None, reason=stopped)
    finalize(led, county)
    cells = led.cells(county)
    vs = led.verdicts(county)
    s = {"county": county, "run_id": run_id, "reader": cl.reader, "steps": [list(x) for x in cl.steps],
         "items_worked": worked, "sums_failing_before": before,
         "sums_failing_after": count_failing(checks.report_checks(cells)), "rereads": cl.rereads,
         "cells_total": len(cells), "cells_accepted": sum(c["status"] == "accepted" for c in cells),
         "cells_cannot_verify": sum(c["status"] == "cannot_verify" for c in cells),
         "cells_document_inconsistent": sum(c["status"] == "document_inconsistent" for c in cells),
         "cells_open": sum(c["status"] not in ("accepted", *agent.FINAL) for c in cells),
         "verdicts": {k: sum(1 for v in vs if v["verdict"] == k) for k in ("document_inconsistent", "cannot_verify")},
         "model_calls": gw.calls - calls0, "metered_cost_estimate": round(gw.cost - cost0, 4),
         "seconds": round(time.time() - t0, 1), "stopped": stopped}
    cl.ev("close_end", summary=s)
    return s
