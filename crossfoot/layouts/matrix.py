"""Matrix layout (Panola): precincts as columns, three ruled rows per candidate, totals both ways.

First read only: one crop per block goes to the model, the answer goes into the ledger as `first_read`.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

from .. import checks, tracing
from ..model import BudgetExceeded
from ..render import crop, page_png
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

BLOCK_PROMPT = """This image is one block of a landscape election canvass sheet: a candidate's name at the left (a
contest title may appear above or beside it), three ruled rows labelled EARLY, ABSENTEE and PRECINCT with one cell per
precinct, a row of small printed totals under the columns, and a grand total under the TOTAL column at the far right.
There are {n} precinct columns, in this order: {precincts}. The last printed number at the end of each row is that
row's TOTAL. A solid black cell means the candidate is not in that precinct: use null for it, not 0.
Answer with strict JSON only, no prose:
{{"contest": "the contest title if one is printed in this image, else null",
 "candidate": "the candidate's name as printed, with party in brackets if shown",
 "rows": {{"EARLY": {{"values": [{n} integers or null], "total": integer}},
          "ABSENTEE": {{"values": [{n} integers or null], "total": integer}},
          "PRECINCT": {{"values": [{n} integers or null], "total": integer}}}},
 "col_totals": [{n} integers or null: the small printed total under each precinct],
 "grand": the grand total under the TOTAL column}}
Read digits exactly as printed; do not correct or add anything up."""


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
    """Column edges for a page: from the first block whose lines are exactly the n+1 precinct edges plus TOTAL's."""
    for b in blocks:
        if len(b.lines) == n + 2:
            return b.lines[:n + 1]
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


def read_county(county, gw, led, *, run_id="", pages=None, dpi=200, log=print, data_root=None) -> dict:
    """Read every page of a matrix-layout county block by block into the ledger. Returns the summary dict."""
    from ..sources import DATA
    root = data_root or DATA
    t0 = time.time()
    pages = list(pages or range(1, 7))
    blocks_found = failed_blocks = 0
    block_log, cols, contest, stopped = [], None, None, None
    try:
      with tracing.trace("read_county", kind="WORKFLOW", run=run_id, county=county):
          # the header row is printed on page 1 only (checked by eye); later pages reuse its precinct order
          first = page_png(county, 1, dpi, root)
          for page in sorted(set(pages) | {1}):
              png = page_png(county, page, dpi, root)
              blocks = find_blocks(png)
              blocks_found += len(blocks) if page in pages else 0
              for i, b in enumerate(blocks):
                  is_header = page == 1 and i == 0
                  if page not in pages and not is_header:
                      continue
                  bid = f"p{page}-b{i}"
                  crop_path = Path("runs") / run_id / "crops" / f"{bid}.png" if run_id else Path(f"/tmp/{bid}.png")
                  crop(png, b.box, crop_path)
                  try:
                      with tracing.trace("read_block", kind="TOOL", run=run_id, county=county, page=page, block=bid):
                          if is_header:
                              d = gw.ask_json(HEADER_PROMPT, crop_path, validate=header_validator)
                              cols = d["precincts"]
                              n = _store_header(led, county, page, d, cols, gw.model)
                              what = "header"
                          else:
                              validate = validator(len(cols))
                              d = gw.ask_json(BLOCK_PROMPT.format(n=len(cols), precincts=", ".join(cols)), crop_path,
                                              validate=validate)
                              contest = (d.get("contest") or contest)
                              n = _store(led, county, page, bid, d, cols, contest, d.get("candidate"), gw.model,
                                         _edges(blocks, len(cols)), b)
                              what = d.get("candidate")
                      led.event(county, "block_read", {"page": page, "block": bid, "cells": n, "candidate": what})
                      block_log.append({"block": bid, "page": page, "status": "read", "cells": n, "candidate": what,
                                        "box": list(b.box)})
                  except BudgetExceeded:
                      raise
                  except Exception as e:  # bad JSON twice, wrong shape, or a model error: mark the block failed, go on
                      failed_blocks += 1
                      if cols:
                          for r in ROWS:
                              for col in cols:
                                  led.put_cell(county, page, bid, r, col, None, model=gw.model)
                                  led.set_status(county, page, bid, r, col, "failed")
                      led.event(county, "block_failed", {"page": page, "block": bid, "error": str(e)[:300]})
                      block_log.append({"block": bid, "page": page, "status": "failed", "error": str(e)[:300]})
                      log(f"  {bid}: failed ({str(e)[:100]})")
                      if is_header:
                          raise RuntimeError("the page-1 header could not be read; later pages need its precinct order")
    except BudgetExceeded as e:
        stopped = str(e)
        log(f"stopped: {e}")
    s = summarize(led, county)
    s.update(county=county, run_id=run_id, blocks_found=blocks_found, blocks_failed=failed_blocks,
             precincts=cols, model_calls=gw.calls, prompt_tokens=gw.prompt_tokens,
             completion_tokens=gw.completion_tokens, metered_cost_estimate=round(gw.cost, 4),
             seconds=round(time.time() - t0, 1), stopped=stopped, blocks=block_log)
    return s
