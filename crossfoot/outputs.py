"""Files a run leaves behind: `county.json` and `run.json`.

runs/<run_id>/<county>/county.json
  county, run_id, layout            names the county, the run and the layout ("matrix")
  pages     [{number, width, height, dpi}]   image size at the dpi the boxes use (200)
  blocks    [{id, page, contest, candidate, box}]          box = [x0, y0, x1, y1] in pixels of that image, or null
  cells     [{page, block, contest, candidate, row_kind, column, value, first_read, status, tries, model, reason, box}]
            status is accepted or cannot_verify when the run is closed; first_read is what the first read gave
  totals    [{page, block, direction, key, value, box}]    direction row (key = row kind), col (key = precinct), grand
  checks    [{kind, page, block, key, terms, printed, computed, ok, note}]    kind row | col | grand_col | grand_row;
            terms = [[page, block, row_kind, column], ...] (cell keys only; values are in cells and totals; a small
            total or a row total that is a term is keyed [page, block, 'col' | 'row', key])
  reader    the model that read the county; sample = the figures of the choice (row sums in the sample, failing, rate,
            whether its values were kept), or {skipped: true} when the model was named
  verdicts  [{sum, page, block, verdict, reason, entity}]    one per sum still failing after the loop;
            verdict document_inconsistent | cannot_verify
  events    [{ts, kind, payload}]    in order: item_start, decision, reread, check, status_change, refused, stop, item_end
  summary   sums failing before and after, cells re-read / changed / cannot_verify, model calls, tokens, metered cost,
            seconds (the figures of the close)
runs/<run_id>/run.json
  run_id, started, ended, commit, command, counties, model_calls, prompt_tokens, completion_tokens,
  metered_cost_estimate
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

from PIL import Image

from . import checks

LAYOUT = "matrix"
GEO_DPI = 200


def _page_sizes(county, pages, root=None):
    from .render import page_png
    from .sources import DATA
    root = root or DATA
    out = []
    for n in pages:
        try:
            with Image.open(page_png(county, n, GEO_DPI, root)) as im:
                out.append({"number": n, "width": im.width, "height": im.height, "dpi": GEO_DPI})
        except Exception:
            out.append({"number": n, "width": None, "height": None, "dpi": GEO_DPI})
    return out


def write_county(run_dir, county, run_id, led, geo, summary, *, pages=None, data_root=None) -> Path:
    cells, totals = led.cells(county), led.totals(county)
    if pages is None:
        pages = sorted({c["page"] for c in cells})
    box = lambda c: [c[k] for k in ("x0", "y0", "x1", "y1")] if c["x0"] is not None else None
    seen, blocks = set(), []
    for c in cells:
        k = (c["page"], c["block_id"])
        if k not in seen:
            seen.add(k)
            bb = geo.block_box(*k) if geo else None
            blocks.append({"id": c["block_id"], "page": c["page"], "contest": c["contest"],
                           "candidate": c["candidate"], "box": list(bb) if bb else None})
    chs = [{"kind": ch.kind, "page": ch.page, "block": ch.block_id, "key": ch.key,
            "terms": [list(k) for k, _ in ch.terms], "printed": ch.printed, "computed": ch.computed, "ok": ch.ok,
            "note": ch.note} for ch in checks.all_checks(cells, totals)]
    evs = led.events(county)
    chosen = next((json.loads(e["payload_json"]) for e in reversed(evs) if e["kind"] == "choose_reader"), None)
    tbox = lambda t: (lambda b: list(b) if b else None)(
        geo.total_box(t["page"], t["block_id"], t["direction"], t["key"]) if geo else None)
    d = {"county": county, "run_id": run_id, "layout": LAYOUT,
         "pages": _page_sizes(county, pages, data_root) if pages else [],
         "blocks": blocks,
         "cells": [{"page": c["page"], "block": c["block_id"], "contest": c["contest"], "candidate": c["candidate"],
                    "row_kind": c["row_kind"], "column": c["column"], "value": c["value"],
                    "first_read": c["first_read"], "status": c["status"], "tries": c["tries"], "model": c["model"],
                    "reason": c.get("reason"), "box": box(c)} for c in cells],
         "totals": [{"page": t["page"], "block": t["block_id"], "direction": t["direction"], "key": t["key"],
                     "value": t["value"], "box": tbox(t)} for t in totals],
         "checks": chs,
         "reader": (chosen or {}).get("reader") or summary.get("reader"),
         "sample": chosen,
         "verdicts": [{"sum": v["sum_id"], "page": v["page"], "block": v["block_id"], "verdict": v["verdict"],
                       "reason": v["reason"], "entity": json.loads(v["entity"]) if v["entity"] else None}
                      for v in led.verdicts(county)],
         "events": [{"ts": e["ts"], "kind": e["kind"], "payload": json.loads(e["payload_json"])} for e in evs],
         "summary": summary}
    out = Path(run_dir) / county / "county.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(d, separators=(",", ":")))   # no indentation: it was 2.3 MB with
    return out


def git_commit() -> str | None:
    try:
        return subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def write_run(run_dir, run_id, *, started, ended, command, counties, gw, resumed_from=None) -> Path:
    d = {"run_id": run_id, "started": started, "ended": ended, "commit": git_commit(), "command": command,
         "counties": counties, "resumed_from": resumed_from, "model_calls": gw.calls,
         "prompt_tokens": gw.prompt_tokens, "completion_tokens": gw.completion_tokens,
         "metered_cost_estimate": round(gw.cost, 4)}
    out = Path(run_dir) / "run.json"
    out.write_text(json.dumps(d, indent=1))
    return out
