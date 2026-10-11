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


def fill_boxes(led, county, geo) -> int:
    """Give every cell that has no box one worked out from the ruled lines of its block (page 1's first block, the
    registered-voters and ballots-cast rows, was read without boxes). Returns how many were filled."""
    n = 0
    for c in led.cells(county):
        if c["x0"] is None and geo is not None:
            try:
                b = geo.cell_box(c["page"], c["block_id"], c["row_kind"], c["column"])
            except Exception:
                b = None
            if b:
                led.set_box(county, c["page"], c["block_id"], c["row_kind"], c["column"], b)
                n += 1
    return n


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


# ---- the audit's files -------------------------------------------------------------------------------------------

CROP_MAX_W = 2000
LABEL_W = 270      # the candidate's name and the row labels, left of the first column, at 200 dpi
CROP_DPI = 300


def group_crop(png, block_box, boxes, caption, dest, dpi=CROP_DPI) -> Path:
    """One picture per group: the block's label strip and the columns around the marked cells, the cells outlined,
    a caption above; at most 2000 px wide. Boxes and block_box are pixels at 200 dpi; `png` is the page at `dpi`."""
    from PIL import ImageDraw, ImageFont
    k = dpi / GEO_DPI
    bx0, by0, bx1, by1 = block_box
    with Image.open(png) as im:
        im = im.convert("RGB")
        d = ImageDraw.Draw(im)
        for x0, y0, x1, y1 in boxes:
            d.rectangle([x0 * k, y0 * k, x1 * k, y1 * k], outline=(220, 0, 0), width=4)
        if boxes:
            lo, hi = min(b[0] for b in boxes) - 110, max(b[2] for b in boxes) + 110
        else:
            lo, hi = bx0, bx1
        lo, hi = max(bx0, lo), min(bx1, hi)
        label = im.crop((round(bx0 * k), round(by0 * k), round((bx0 + LABEL_W) * k), round(by1 * k)))
        if lo <= bx0 + LABEL_W:
            body = im.crop((round(bx0 * k), round(by0 * k), round(hi * k), round(by1 * k)))
            pic = body
        else:
            body = im.crop((round(lo * k), round(by0 * k), round(hi * k), round(by1 * k)))
            pic = Image.new("RGB", (label.width + 12 + body.width, label.height), (255, 255, 255))
            pic.paste(label, (0, 0))
            pic.paste(body, (label.width + 12, 0))
    cap_h = 34
    out = Image.new("RGB", (pic.width, pic.height + cap_h), (255, 255, 255))
    out.paste(pic, (0, cap_h))
    try:
        font = ImageFont.load_default(size=20)
    except TypeError:
        font = ImageFont.load_default()
    ImageDraw.Draw(out).text((8, 6), caption, fill=(0, 0, 0), font=font)
    if out.width > CROP_MAX_W:
        out = out.resize((CROP_MAX_W, round(out.height * CROP_MAX_W / out.width)), Image.LANCZOS)
    dest.parent.mkdir(parents=True, exist_ok=True)
    out.save(dest)
    return dest


def make_group_crops(county, res, geo, data_root=None) -> int:
    """Write crops/<group id>.png for each group and put its path on the group and its findings."""
    from .render import page_png
    from .sources import DATA
    n = 0
    for g in res["groups"]:
        fs = [f for f in res["findings"] if f["group"] == g["id"]]
        boxes = [tuple(f["box"]) for f in fs if f.get("box")]
        if g["page"] is None:
            continue
        try:
            bb = geo.block_box(g["page"], g["block"]) if geo else None
            if bb is None and boxes:
                bb = (min(b[0] for b in boxes) - LABEL_W, min(b[1] for b in boxes) - 20,
                      max(b[2] for b in boxes) + 110, max(b[3] for b in boxes) + 40)
            if bb is None:
                continue
            cap = (f"page {g['page']}, block {g['block']}: {g['candidate'] or g['office']} ({g['office']}"
                   f"{', ' + g['district'] if g['district'] else ''}), precinct {', '.join(g['precincts'])}; "
                   f"scan, cells outlined")
            png = page_png(county, g["page"], CROP_DPI, data_root or DATA)
            group_crop(png, bb, boxes, cap, res["crop_dir"] / f"{g['id']}.png")
            g["crop"] = f"crops/{g['id']}.png"
            for f in fs:
                f["crop"] = g["crop"]
            n += 1
        except Exception:                                   # a picture is evidence, not the finding: go on without it
            continue
    return n


def _count(items, key, order):
    return {k: sum(1 for i in items if i[key] == k) for k in order if any(i[key] == k for i in items)}


def write_findings(run_dir, county, run_id, res, *, policy, raw_file, file_name, file_urls, verdicts=()) -> dict:
    """findings.json, corrected/<file>, changes.diff and report.md next to county.json. Returns the corrections."""
    from . import audit
    out = Path(run_dir) / county
    out.mkdir(parents=True, exist_ok=True)
    fs = res["findings"]
    new, diff, applied = audit.apply_corrections(raw_file, fs)
    done = {a["finding"] for a in applied}
    for f in fs:
        f["corrected"] = f["id"] in done
    (out / "corrected").mkdir(exist_ok=True)
    (out / "corrected" / file_name).write_bytes(new)
    diff = diff.replace("a/published file", f"a/{file_name}").replace("b/published file", f"b/corrected/{file_name}")
    (out / "changes.diff").write_text(diff)
    m = res["matching"]
    d = {"county": county, "run_id": run_id, "file": file_name, "policy": policy,
         "counts": {"findings": len(fs), "by_kind": _count(fs, "kind", audit.KINDS),
                    "by_status": _count(fs, "status", audit.STATUSES), "groups": len(res["groups"]),
                    "corrections": len(applied)},
         "findings": fs, "groups": res["groups"], "corrections": applied,
         "unmatched": {"scan": m.unmatched_scan, "file": m.unmatched_file, "rejected": m.rejected, "model": m.model},
         "corrected_events": res["corrected_events"], "audit": res["audit"]}
    (out / "findings.json").write_text(json.dumps(d, indent=1))
    (out / "report.md").write_text(report_text(d, verdicts, file_urls))
    return d


def _sum_line(s) -> str:
    w = "holds" if s["holds_with_scan"] else "does not hold"
    f = "holds" if s["holds_with_file"] else "does not hold"
    return (f"  - {s['name']}: printed {s['printed']}; with the scan's value the cells add to {s['computed_with_scan']} "
            f"({w}); with the file's value they add to {s['computed_with_file']} ({f}).")


def report_text(d, verdicts, urls) -> str:
    """report.md in plain words. Counts, one section per group, then what could not be verified."""
    c = d["counts"]
    L = [f"# Crossfoot audit: {d['county'].replace('_', ' ').title()} County, run {d['run_id']}", "",
         "The published spreadsheet was copied from a scanned canvass. This audit compares the two. What it finds are "
         "transcription slips in a volunteer dataset; the county's scan is the source. Each finding is proved with the "
         "totals printed on the scan itself. No finding has been confirmed by a person.", "",
         f"- Scan: {urls['scan']}", f"- Published file: {urls['file']}", "",
         "## Counts", "", f"{c['findings']} findings in {c['groups']} groups; {c['corrections']} values changed in the "
         "corrected file.", "", "| kind | findings |", "|---|---|"]
    L += [f"| {k} | {v} |" for k, v in c["by_kind"].items()] or ["| none | 0 |"]
    L += ["", "| status | findings |", "|---|---|"] + ([f"| {k} | {v} |" for k, v in c["by_status"].items()] or ["| none | 0 |"])
    p = d["policy"]
    L += ["", f"Where the scan disagrees with itself, the answer in use is '{p['answer']}' ({p['meaning']}); "
          f"answered by: {p['answered_by']}. It never changes a value; only a printed total that decides can.", ""]
    by = {f["id"]: f for f in d["findings"]}
    L += ["## Groups", ""]
    for g in d["groups"]:
        place = f"{g['office']}{', ' + g['district'] if g['district'] else ''}"
        L += [f"### {g['id']}: {g['kind']}, {g['candidate'] or g['office']}, precinct {', '.join(g['precincts'])}", "",
              f"{place}. Page {g['page']}, block {g['block']}. Statuses: " +
              ", ".join(f"{k} {v}" for k, v in g["statuses"].items()) + ".", ""]
        if g["crop"]:
            L += [f"![{g['id']}]({g['crop']})", ""]
        for fid in g["findings"]:
            f = by[fid]
            fv = "no row" if f["file_value"] is None else f["file_value"]
            sv = "no row" if f["scan_value"] is None else f["scan_value"]
            L += [f"- Precinct {f['precinct']}, {f['part']}: the file has {fv}, the scan has {sv}. "
                  f"Status {f['status']}: {f['reason']}" + (" Changed in the corrected file." if f["corrected"] else "")]
            L += [_sum_line(s) for s in f["sums"]]
            if f["reread"] and f["reread"]["value"] is not None:
                L += [f"  - Looked at the scan again ({f['reread']['model']}, {f['reread']['dpi']} dpi): it reads "
                      f"{f['reread']['value']}."]
        L += [""]
    L += ["## What could not be verified, and why", ""]
    open_ = [f for f in d["findings"] if f["status"] != "settled_against_file"]
    if not open_:
        L += ["Every finding is settled by a printed total.", ""]
    for f in open_:
        L += [f"- {f['id']} (group {f['group']}), {f['candidate'] or f['office']}, precinct {f['precinct']}, "
              f"{f['part']}: {f['status']}. {f['reason']}"]
    u = d["unmatched"]
    for v in verdicts:
        L += [f"- The ledger itself: {v.get('sum_id') or v.get('sum')} ended {v['verdict']}. {v['reason']}"]
    if u["scan"] or u["file"] or u["rejected"]:
        L += ["", "Not matched between the scan and the file, so not compared:"]
        L += [f"- scan block {x['block']}: {x['contest']}, {x['candidate']}" for x in u["scan"]]
        L += [f"- file: {x['contest']} {x['district']}, {x['candidate']} ({x['rows']} rows)" for x in u["file"]]
        L += [f"- rejected pairing, {x['what']}: {x['why']}" for x in u["rejected"]]
    L += [""]
    return "\n".join(L)


def write_audit_run(run_dir, run_id, *, started, ended, seconds, command, county, gw, reader, sample, resumed_from,
                    phases, spend=None) -> Path:
    """One run.json for the whole `audit` command."""
    d = {"run_id": run_id, "started": started, "ended": ended, "seconds": seconds, "commit": git_commit(),
         "command": command, "counties": [county], "resumed_from": resumed_from, "reader": reader,
         "sample": sample, "phases_seconds": phases, "model_calls": gw.calls,
         "model_calls_by_model": gw.calls_by_model(), "prompt_tokens": gw.prompt_tokens,
         "completion_tokens": gw.completion_tokens, "metered_cost_estimate": round(gw.cost, 4)}
    if spend:
        d["gateway_spend"] = spend
    out = Path(run_dir) / "run.json"
    out.write_text(json.dumps(d, indent=1))
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
