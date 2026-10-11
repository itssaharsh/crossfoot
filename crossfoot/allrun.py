"""`crossfoot audit --all`: every county in turn, with no one at the keyboard, inside a budget, able to be stopped and continued.

The run is one folder, runs/<run_id>/, with one ledger (cells are keyed by county) and, per county, the files `audit
--county` writes. After every county the folder gets summary.json and summary.md, so a stopped run still says what it did.
`--resume <run_id>` continues in the same folder: a county that is closed (audited, or left as published because nothing on
its scan can be checked) is not run again; a county that failed, was stopped by the budget or was not reached is run again,
and its ledger keeps every accepted cell, so no accepted cell is read twice. What was spent before counts against the budget.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

from . import tracing
from .model import BudgetExceeded

ORDER = ("panola", "san_saba", "cottle", "jones", "lynn", "scurry", "foard", "limestone")
CLOSED = ("audited", "partly_audited", "unchecked")      # a county in one of these states is final for the run
STATS = ("model_calls", "prompt_tokens", "completion_tokens", "metered_cost", "seconds")


class Ctx:
    """What a county's function is given: the shared ledger and gateway, the run's folder and a log function."""
    def __init__(self, county, run_id, out, led, gw, log):
        self.county, self.run_id, self.out, self.led, self.gw, self.log = county, run_id, out, led, gw, log


def _snap(gw) -> dict:
    return {"calls": gw.calls, "prompt": gw.prompt_tokens, "completion": gw.completion_tokens, "cost": gw.cost,
            "by_model": gw.calls_by_model()}


def _delta(a: dict, b: dict, seconds: float) -> dict:
    by = {}
    for m, v in b["by_model"].items():
        o = a["by_model"].get(m, {})
        d = {k: v[k] - o.get(k, 0) for k in ("calls", "prompt_tokens", "completion_tokens", "cost")}
        if d["calls"]:
            by[m] = {**d, "cost": round(d["cost"], 4)}
    return {"model_calls": b["calls"] - a["calls"], "model_calls_by_model": by,
            "prompt_tokens": b["prompt"] - a["prompt"], "completion_tokens": b["completion"] - a["completion"],
            "metered_cost": round(b["cost"] - a["cost"], 4), "seconds": round(seconds, 1)}


def _add(old: dict, new: dict) -> dict:
    """A county run again after a stop: its figures add to the earlier attempt's."""
    out = dict(new)
    for k in STATS:
        out[k] = round(old.get(k, 0) + new.get(k, 0), 4 if k == "metered_cost" else 1 if k == "seconds" else 0)
    by = {m: dict(v) for m, v in old.get("model_calls_by_model", {}).items()}
    for m, v in new.get("model_calls_by_model", {}).items():
        t = by.setdefault(m, {k: 0 for k in v})
        for k in v:
            t[k] = round(t[k] + v[k], 4) if k == "cost" else t[k] + v[k]
    out["model_calls_by_model"] = by
    return out


def _sum_dicts(rows, key) -> dict:
    out: dict = {}
    for r in rows:
        for k, v in (r.get(key) or {}).items():
            out[k] = out.get(k, 0) + v
    return out


def totals(rows: list[dict]) -> dict:
    done = [r for r in rows if r["status"] in CLOSED]
    by: dict = {}
    for r in rows:
        for m, v in r.get("model_calls_by_model", {}).items():
            t = by.setdefault(m, {k: 0 for k in v})
            for k in v:
                t[k] = round(t[k] + v[k], 4) if k == "cost" else t[k] + v[k]
    t = {"counties": len(rows), "closed": len(done),
         **{s: round(sum(r.get(s, 0) for r in rows), 4 if s == "metered_cost" else 1 if s == "seconds" else 0)
            for s in STATS},
         "model_calls_by_model": by,
         "cells_read": sum(r.get("cells_read", 0) for r in rows),
         "cells_reread": sum(r.get("cells_reread", 0) for r in rows),
         "cells_accepted": sum(r.get("cells_accepted", 0) for r in rows),
         "cannot_verify": sum(r.get("cannot_verify", 0) for r in rows),
         "rows_published": sum(r.get("rows_published", 0) for r in rows),
         "rows_compared": sum(r.get("rows_compared", 0) for r in rows),
         "sums_first_read": _sum_dicts(rows, "sums_first_read"),
         "sums_check": _sum_dicts(rows, "sums_check"),
         "findings_by_kind": _sum_dicts(rows, "findings_by_kind"),
         "findings_by_status": _sum_dicts(rows, "findings_by_status")}
    return t


def _cov(r) -> str:
    return "" if r.get("rows_published") is None else f"{r.get('rows_compared', 0)} of {r['rows_published']}"


def write_summary(run_dir, summary: dict) -> None:
    """summary.json (the results page and the README read it) and summary.md.

    summary.json
      run_id, command, budget, started, ended, resumed   the run; budget in dollars, resumed true when `--resume` continued it
      counties  [one per county in the run's order, with
        county, status       status: audited | unchecked | failed | stopped | not_reached; reason says why when it is not
                             audited; note says why an unchecked county is left as published
        layout, pages        matrix | report | no_printed_totals | not_supported; pages = pages read
        cells_read           cells in the ledger
        sums_first_read      {passing, failing}: printed sums after the first read, before any re-read
        cells_reread         cells read more than once; cells_accepted: cells on a printed sum that holds
        cannot_verify        findings left cannot_verify (a row with one sum only)
        rows_published       rows of the published file that carry figures; rows_compared: those compared with the scan;
                             not_compared [{contest, rows, reason}]: the rest. status is audited only when at least 95 percent
                             were compared, else partly_audited
        from_run             (a summary made by `crossfoot summarize`) the run the county's figures come from
        findings_by_kind, findings_by_status
        second_sum_exists    true when the scan prints a second sum (contest totals) to check a row against
        sums_check           {in_all, holding_with_published, holding_with_corrected}: printed sums, counted from findings.json
        model_calls, model_calls_by_model {model: {calls, prompt_tokens, completion_tokens, cost}}, prompt_tokens,
        completion_tokens, metered_cost (an estimate from the gateway's price list), seconds]
      totals     the same figures added up over the counties
      not_reached  counties the run did not get to (budget or stop)
      skipped      [{county, reason}] counties not audited, and why
      gateway_spend {before, after, change} from the gateway's own figure, when it could be read
    """
    run_dir = Path(run_dir)
    (run_dir / "summary.json").write_text(json.dumps(summary, indent=1))
    rows, t = summary["counties"], summary["totals"]
    f = lambda v: "" if v is None else v
    L = [f"# Run {summary['run_id']}", "",
         f"Budget ${summary['budget']:.2f}; metered cost (an estimate) ${t['metered_cost']:.4f}; {t['model_calls']} model calls; "
         f"{t['seconds']} s; {t['closed']} of {t['counties']} counties closed.", "",
         "| county | status | layout | pages | cells | sums ok / failing after first read | cells re-read | cells accepted | "
         "cannot_verify | findings | printed sums in all / hold with published / hold with corrected | second sum | "
         "published rows compared | calls | cost $ | seconds |",
         "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        s1, sc = r.get("sums_first_read") or {}, r.get("sums_check") or {}
        L.append(f"| {r['county']} | {r['status']} | {f(r.get('layout'))} | {f(r.get('pages'))} | {f(r.get('cells_read'))} | "
                 f"{s1.get('passing', '')} / {s1.get('failing', '')} | {f(r.get('cells_reread'))} | "
                 f"{f(r.get('cells_accepted'))} | {f(r.get('cannot_verify'))} | "
                 f"{sum((r.get('findings_by_status') or {}).values()) if r.get('findings_by_status') is not None else ''} | "
                 f"{sc.get('in_all', '')} / {sc.get('holding_with_published', '')} / {sc.get('holding_with_corrected', '')} | "
                 f"{'yes' if r.get('second_sum_exists') else 'no' if r.get('second_sum_exists') is not None else ''} | "
                 f"{_cov(r)} | {r.get('model_calls', 0)} | {r.get('metered_cost', 0):.4f} | {r.get('seconds', 0)} |")
    s1, sc = t["sums_first_read"], t["sums_check"]
    L.append(f"| **all** | | | | {t['cells_read']} | {s1.get('passing', 0)} / {s1.get('failing', 0)} | {t['cells_reread']} | "
             f"{t['cells_accepted']} | {t['cannot_verify']} | {sum(t['findings_by_status'].values())} | "
             f"{sc.get('in_all', 0)} / {sc.get('holding_with_published', 0)} / {sc.get('holding_with_corrected', 0)} | | "
             f"{t['rows_compared']} of {t['rows_published']} | {t['model_calls']} | {t['metered_cost']:.4f} | {t['seconds']} |")
    L += ["", "## Published rows compared with the scan", ""]
    for r in rows:
        if r.get("rows_published") is not None:
            L.append(f"- {r['county']}: {_cov(r)} published rows compared" +
                     (f" (figures from run {r['from_run']})" if r.get("from_run") else "") +
                     (f"; {r['status']}" if r["status"] == "partly_audited" else "") + ".")
            L += [f"  - not compared: {x['contest']}, {x['rows']} row{'' if x['rows'] == 1 else 's'}. {x['reason'][0].upper() + x['reason'][1:]}."
                  for x in r.get("not_compared") or []]
    L += ["", "## Findings by kind and status", ""]
    for r in rows:
        if r.get("findings_by_kind") is not None:
            L.append(f"- {r['county']}: by kind {r['findings_by_kind']}; by status {r['findings_by_status']}")
    L += ["", "## Model calls by model", ""]
    for m, v in t["model_calls_by_model"].items():
        L.append(f"- {m}: {v['calls']} calls, {v['prompt_tokens']} tokens in, {v['completion_tokens']} out, ${v['cost']:.4f}")
    if any(r.get("from_run") for r in rows):
        L += ["", "## Where each county's figures come from", ""]
        L += [f"- {r['county']}: run {r.get('from_run')}" for r in rows]
        base = (summary.get("made_from") or {}).get("base")
        if base:
            L += ["", f"A county taken from a single-county audit reused the ledger of run {base}, so its calls, cost and seconds "
                  f"are those of the audit alone; the reading was paid for in run {base}. The cost and calls in the header "
                  "and the **all** row therefore add the reading of no county that was audited again."]
    L += ["", "## Not audited", ""]
    if not summary["skipped"] and not summary["not_reached"]:
        L.append("Every county was audited.")
    for x in summary["skipped"]:
        L.append(f"- {x['county']}: {x['reason']}")
    if summary["not_reached"]:
        L.append(f"- Not reached: {', '.join(summary['not_reached'])}. Continue with `crossfoot audit --all --resume "
                 f"{summary['run_id']}`.")
    sp = summary.get("gateway_spend")
    if sp:
        L += ["", f"Gateway's own figure: ${sp['before']:.4f} before, ${sp['after']:.4f} after (change ${sp['change']:.4f})."]
    L.append("")
    (run_dir / "summary.md").write_text("\n".join(L))


def run_all(run_dir, run_id, gw, led, county_fn, *, counties=ORDER, resume=False, log=print, command="", budget=None,
            started=None) -> dict:
    """Run `county_fn(county, ctx) -> result dict` for each county in order. Never asks for input. A county that raises is
    recorded as failed and the run goes on; the budget (`gw.budget`) stops the run before the next call and lists the
    counties not reached. Returns the summary, which is also written."""
    run_dir = Path(run_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    prior: dict = {}
    if resume and (run_dir / "summary.json").exists():
        prior = {r["county"]: r for r in json.loads((run_dir / "summary.json").read_text())["counties"]}
        gw.cost = max(gw.cost, sum(r.get("metered_cost", 0) for r in prior.values()))   # what was spent counts again
    summary = {"run_id": run_id, "command": command, "budget": gw.budget if budget is None else budget,
               "started": started or time.strftime("%Y-%m-%dT%H:%M:%S"), "ended": None, "resumed": bool(prior),
               "counties": [], "totals": {}, "not_reached": [], "skipped": []}
    rows: dict = {c: prior[c] for c in counties if c in prior and prior[c]["status"] in CLOSED}

    def save(final=False):
        if final:
            summary["ended"] = time.strftime("%Y-%m-%dT%H:%M:%S")
        out = [rows[c] if c in rows else prior.get(c) or {"county": c, "status": "not_reached", "reason": "not reached yet"}
               for c in counties]
        summary["counties"] = out
        summary["totals"] = totals(out)
        summary["not_reached"] = [r["county"] for r in out if r["status"] == "not_reached"]
        summary["skipped"] = [{"county": r["county"], "reason": r.get("note") or r.get("reason") or r["status"]}
                              for r in out if r["status"] in ("unchecked", "failed", "stopped")]
        write_summary(run_dir, summary)

    stop = None
    for county in counties:
        if county in rows:
            log(f"{county} skipped: closed in the run being continued")
            continue
        if stop is None and gw.cost >= gw.budget:
            stop = f"run budget ${gw.budget:.2f} reached (estimated spend ${gw.cost:.4f}); no further call is made"
        if stop:
            rows[county] = {"county": county, "status": "not_reached", "reason": stop}
            continue
        log(f"{county} start")
        t0, a = time.time(), _snap(gw)
        row: dict
        try:
            with tracing.trace(county, kind="WORKFLOW", run=run_id, county=county):
                res = county_fn(county, Ctx(county, run_id, run_dir, led, gw, log))
            row = {"county": county, "status": res.get("outcome", "audited"), **{k: v for k, v in res.items() if k != "outcome"}}
        except BudgetExceeded as e:
            stop = str(e)
            row = {"county": county, "status": "stopped", "reason": stop}
        except Exception as e:
            row = {"county": county, "status": "failed", "reason": f"{type(e).__name__}: {str(e)[:300]}"}
        d = _delta(a, _snap(gw), time.time() - t0)
        row.update(d if county not in prior else _add(prior[county], d))
        rows[county] = row
        log(f"{county} end: {row['status']}" + (f" ({row['reason']})" if row.get("reason") else "") +
            f"; {d['model_calls']} calls, ${d['metered_cost']:.4f}, {d['seconds']} s")
        save()
    save(final=True)
    return summary


# ---- one county, for real ------------------------------------------------------------------------------------------------

def _event(led, county, kind):
    return next((json.loads(e["payload_json"]) for e in reversed(led.events(county)) if e["kind"] == kind), None)


def _first_sums(s: dict, report_layout: bool) -> dict:
    keys = ("row", "contest") if report_layout else ("row", "col", "grand")
    return {"passing": sum(s[f"{k}_sums_pass"] for k in keys), "failing": sum(s[f"{k}_sums_fail"] for k in keys)}


def audit_one(county, ctx) -> dict:
    """The county's whole audit, on the run's shared ledger: fetch, read (unless the ledger says the read finished), close,
    audit, write the county's files. Raises on a failure (the run records it) and BudgetExceeded when the budget stops it."""
    from . import agent, audit, outputs, policy, sources
    from .layouts import matrix, report
    led, gw, out, run_id, log = ctx.led, ctx.gw, ctx.out, ctx.run_id, ctx.log
    sources.fetch(county)
    urls = {"scan": sources.scan_url(county), "file": sources.file_url(county)}
    is_report = county != "panola"
    info = _event(led, county, "read_done")
    if info is None:
        led.clear_values(county)                   # a read that was cut short is read again whole; nothing half-read stays
        led.db.execute("DELETE FROM verdicts WHERE county=?", (county,))
        led.db.commit()
        if is_report:
            read = report.read_county(county, gw, led, run_id=run_id, log=log)
            if read.get("stopped"):
                raise BudgetExceeded(read["stopped"])
            if read["layout"] == "no_printed_totals":
                outputs.write_unchecked(out, county, run_id, read, urls)
                info = {"outcome": "unchecked", "layout": read["layout"], "note": read.get("note"), "cells_read": 0,
                        "pages": 0, "sums_first_read": {"passing": 0, "failing": 0}}
            elif read["layout"] != "report":
                raise RuntimeError(read.get("note") or f"layout {read['layout']} not read")
            else:
                info = {"outcome": "audited", "layout": "report", "pages": len(read["pages_read"]) + len(read["pages_failed"]),
                        "cells_read": read["cells_read"], "sums_first_read": _first_sums(read, True),
                        "pages_failed": read["pages_failed"]}
        else:
            s = matrix.read_county(county, gw, led, run_id=run_id, model="auto", log=log)
            if s["stopped"]:
                raise BudgetExceeded(s["stopped"])
            info = {"outcome": "audited", "layout": "matrix", "pages": len({c["page"] for c in led.cells(county)}),
                    "cells_read": s["cells_read"], "sums_first_read": _first_sums(s, False)}
        led.event(county, "read_done", info)
    if info["outcome"] == "unchecked":
        return info
    chosen = _event(led, county, "choose_reader")
    reader = (chosen or {}).get("reader") or "claude-haiku"
    gw.model = reader
    pol = policy.write_for_run(out)
    rows = sources.read_published(county)
    fname = sources.file_url(county).rsplit("/", 1)[1]
    raw = sources.file_path(county).read_bytes()
    if is_report:
        lay = report.layout_event(led, county)
        report.refit_boxes(led, county, x_right=lay.get("x_right"))
        geo = report.ReportGeometry(county, x_right=lay.get("x_right"))
        closed = report.close_county(county, gw, led, geo, reader=reader, run_id=run_id, log=log)
        if closed["stopped"]:
            raise BudgetExceeded(closed["stopped"])
        summary = dict(closed, layout="report", sample=chosen, pages_failed=info.get("pages_failed"))
        res = audit.audit_report_county(county, led, geo, gw, rows, run_dir=out, log=log, file_name=fname, reader=reader,
                                        run_id=run_id)
        outputs.make_row_crops(county, res, geo)
        outputs.write_county(out, county, run_id, led, geo, summary, layout="report")
    else:
        cols = matrix.precinct_order(led, county)
        if not cols:
            raise RuntimeError("the ledger has no header block (registered voters row); nothing to place columns by")
        geo = matrix.Geometry(county, cols)
        closed = agent.close_county(county, gw, led, geo, run_id=run_id, reader=reader, log=log)
        if closed["stopped"]:
            raise BudgetExceeded(closed["stopped"])
        agent.finalize_open(led, county)
        summary = dict(closed)
        outputs.fill_boxes(led, county, geo)
        res = audit.audit_county(county, led, geo, gw, rows, run_dir=out, log=log, run_id=run_id, file_name=fname)
        outputs.make_group_crops(county, res, geo)
        outputs.write_county(out, county, run_id, led, geo, summary)
    d = outputs.write_findings(out, county, run_id, res, policy=pol, raw_file=raw, file_name=fname, file_urls=urls,
                               verdicts=led.verdicts(county))
    cells = led.cells(county)
    sc = d["sums_check"]
    return {"outcome": audit.coverage_status(res["coverage"]), "layout": info["layout"], "pages": info["pages"],
            "cells_read": len(cells), **res["coverage"],
            "sums_first_read": info["sums_first_read"], "cells_reread": sum(c["tries"] > 0 for c in cells),
            "cells_accepted": sum(c["status"] == "accepted" for c in cells),
            "cannot_verify": d["counts"]["by_status"].get("cannot_verify", 0),
            "findings_by_kind": d["counts"]["by_kind"], "findings_by_status": d["counts"]["by_status"],
            "second_sum_exists": bool(d["audit"].get("second_sum_exists", bool(led.totals(county)))),
            "sums_check": {k: sc[k] for k in ("in_all", "holding_with_published", "holding_with_corrected")},
            "reader": reader}


# ---- a summary over runs --------------------------------------------------------------------------------------------------

def _row_from_folder(folder: Path, county: str, old: dict) -> dict:
    """A county's summary row from the folder of a single-county audit: the audit's figures from findings.json and the cells
    from its ledger; the read's figures (layout, pages, first-read sums) stay those of the row it replaces. Calls, cost and
    seconds are those of that audit alone."""
    from . import audit
    from .ledger import Ledger
    f = json.loads((folder / county / "findings.json").read_text())
    run = json.loads((folder / "run.json").read_text())
    cells = Ledger(folder / "ledger.sqlite").cells(county)
    sc = f["sums_check"]
    cov = {k: f[k] for k in ("rows_published", "rows_compared", "not_compared")}
    by = run.get("model_calls_by_model") or {}
    return {**{k: v for k, v in old.items() if k not in ("reason", "note")}, "county": county,
            "status": audit.coverage_status(cov), "cells_read": len(cells),
            "cells_reread": sum(c["tries"] > 0 for c in cells), "cells_accepted": sum(c["status"] == "accepted" for c in cells),
            "cannot_verify": f["counts"]["by_status"].get("cannot_verify", 0),
            "findings_by_kind": f["counts"]["by_kind"], "findings_by_status": f["counts"]["by_status"],
            "second_sum_exists": bool(f["audit"].get("second_sum_exists")),
            "sums_check": {k: sc[k] for k in ("in_all", "holding_with_published", "holding_with_corrected")}, **cov,
            "model_calls": run.get("model_calls", 0), "model_calls_by_model": by,
            "prompt_tokens": run.get("prompt_tokens", 0), "completion_tokens": run.get("completion_tokens", 0),
            "metered_cost": run.get("metered_cost_estimate", 0), "seconds": run.get("seconds", 0)}


def combine(out, base: str, use: dict, command: str = "") -> dict:
    """A new run folder whose summary covers every county of run `base` with the newest result of each: a county in `use`
    ({county: run id}) takes its audit from that run's folder, the others stay as `base` has them. Every row says which run its
    figures come from. Nothing is read and no model is called; the runs it names are not changed."""
    out = Path(out)
    root = out.parent
    old = json.loads((root / base / "summary.json").read_text())
    rows = []
    for r in old["counties"]:
        run = use.get(r["county"], base)
        row = _row_from_folder(root / run, r["county"], r) if r["county"] in use else dict(r)
        rows.append({**row, "from_run": run})
    now = time.strftime("%Y-%m-%dT%H:%M:%S")
    summary = {"run_id": out.name, "command": command, "budget": old["budget"], "started": now, "ended": now,
               "resumed": False, "counties": rows, "totals": totals(rows), "not_reached": [],
               "skipped": [{"county": r["county"], "reason": r.get("note") or r.get("reason") or r["status"]}
                           for r in rows if r["status"] in ("unchecked", "failed", "stopped")],
               "made_from": {"base": base, "use": use}}
    out.mkdir(parents=True, exist_ok=True)
    write_summary(out, summary)
    return summary
