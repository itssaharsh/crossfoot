"""Command-line entry point."""
from __future__ import annotations

import argparse
import sys

from . import sources
from .render import RenderError, page_png


def _counties(args) -> list[str]:
    if getattr(args, "all", False):
        return list(sources.COUNTIES)
    return [args.county]


def cmd_fetch(args) -> int:
    rc = 0
    for key in _counties(args):
        try:
            got = sources.fetch(key)
            print(f"{key}: downloaded {', '.join(got)}" if got else f"{key}: cached, nothing downloaded")
        except sources.FetchError as e:
            print(f"{key}: {e}", file=sys.stderr)
            rc = 1
    return rc


def cmd_filecheck(args) -> int:
    rc = 0
    for key in _counties(args):
        try:
            sources.fetch(key)
        except sources.FetchError as e:
            print(f"{key}: {e}", file=sys.stderr)
            rc = 1
            continue
        bad, checked, skipped = sources.file_mismatches(sources.read_published(key))
        print(f"{key}: {len(bad)} row(s) differ, {checked} checked, {skipped} skipped (blank part)")
        for r in bad:
            print(f"  {r['precinct']} | {r['office']} | {r['candidate']}: votes={r['votes']} "
                  f"but absentee+early_voting+election_day={r['parts_sum']}")
    return rc


def cmd_render(args) -> int:
    try:
        sources.fetch(args.county)
        from PIL import Image
        out = page_png(args.county, args.page, args.dpi)
        with Image.open(out) as im:
            print(f"{out} {im.width}x{im.height} px")
    except (RenderError, sources.FetchError) as e:
        print(e, file=sys.stderr)
        return 1
    return 0


def cmd_budget(args) -> int:
    from .model import gateway_spend
    try:
        spend, limit = gateway_spend()
    except (KeyError, OSError, ValueError) as e:
        print(f"cannot read the gateway's spend: {type(e).__name__} (is LITELLM_BASE_URL / LITELLM_API_KEY set?)",
              file=sys.stderr)
        return 1
    print(f"gateway spend so far: ${spend:.4f}; limit: " + (f"${limit:.2f}" if limit is not None else "none"))
    return 0


def cmd_read(args) -> int:
    import json
    import time
    from pathlib import Path

    from . import tracing
    from .ledger import Ledger
    from .layouts import matrix
    from .model import Gateway, gateway_spend
    note = tracing.init()
    if note:
        print(note)
    if args.county != "panola":
        print(f"{args.county}: only the matrix layout (panola) is built so far", file=sys.stderr)
        return 1
    try:
        sources.fetch(args.county)
    except sources.FetchError as e:
        print(e, file=sys.stderr)
        return 1
    try:
        before = gateway_spend()[0]
    except (KeyError, OSError, ValueError):
        before = None
    run_id = time.strftime("%Y%m%d-%H%M%S")
    out = Path("runs") / run_id
    out.mkdir(parents=True, exist_ok=True)
    led = Ledger(out / "ledger.sqlite")
    gw = Gateway(budget=args.budget)
    pages = [int(x) for x in args.pages.split(",")] if args.pages else None
    print(f"run {run_id}: reading {args.county} ({'reader chosen by a sample' if args.model == 'auto' else args.model}), "
          f"run budget ${args.budget:.2f}")
    try:
        s = matrix.read_county(args.county, gw, led, run_id=run_id, pages=pages, model=args.model)
    except (RenderError, RuntimeError) as e:
        print(e, file=sys.stderr)
        return 1
    finally:
        tracing.shutdown()
    try:
        s["gateway_spend_before"], s["gateway_spend_after"] = before, gateway_spend()[0]
        s["gateway_spend_change"] = round(s["gateway_spend_after"] - before, 4)
    except (KeyError, OSError, ValueError, TypeError):
        pass
    s["ledger"] = str(out / "ledger.sqlite")
    (out / "first-read.json").write_text(json.dumps(s, indent=2))
    print(f"blocks found: {s['blocks_found']} (failed {s['blocks_failed']})")
    print(f"cells read: {s['cells_read']} (failed {s['failed_cells']})")
    print(f"reader: {s['reader']}" + (f" (sample {s['sample']['failing']} of {s['sample']['row_sums']} row sums failing)"
                                      if s.get("sample") and not s["sample"].get("skipped") else ""))
    print(f"row sums: {s['row_sums_pass']} pass, {s['row_sums_fail']} fail")
    print(f"column sums: {s['col_sums_pass']} pass, {s['col_sums_fail']} fail")
    print(f"grand totals: {s['grand_sums_pass']} pass, {s['grand_sums_fail']} fail")
    print(f"model calls: {s['model_calls']}; tokens: {s['prompt_tokens']} in, {s['completion_tokens']} out; "
          f"metered cost (estimate): ${s['metered_cost_estimate']:.4f}; seconds: {s['seconds']}")
    if "gateway_spend_change" in s:
        print(f"gateway spend: ${s['gateway_spend_before']:.4f} -> ${s['gateway_spend_after']:.4f} "
              f"(change ${s['gateway_spend_change']:.4f})")
    print(f"written: {out / 'first-read.json'}")
    return 2 if s["stopped"] else 0


def cmd_close(args) -> int:
    import json
    import shutil
    import time
    from pathlib import Path

    from . import agent, outputs, tracing
    from .layouts import matrix
    from .ledger import Ledger
    from .model import Gateway, gateway_spend
    if args.county != "panola":
        print(f"{args.county}: only the matrix layout (panola) is built so far", file=sys.stderr)
        return 1
    resume = args.resume
    if resume == "latest":
        reads = sorted(p.parent.name for p in Path("runs").glob("*/first-read.json"))
        if not reads:
            print("no run with a first-read.json to resume from", file=sys.stderr)
            return 1
        resume = reads[-1]
    src = Path("runs") / resume / "ledger.sqlite"
    if not src.exists():
        print(f"{src} does not exist", file=sys.stderr)
        return 1
    note = tracing.init()
    if note:
        print(note)
    try:
        before = gateway_spend()[0]
    except (KeyError, OSError, ValueError):
        before = None
    started = time.strftime("%Y-%m-%dT%H:%M:%S")
    run_id = time.strftime("%Y%m%d-%H%M%S")
    out = Path("runs") / run_id
    out.mkdir(parents=True)
    shutil.copy(src, out / "ledger.sqlite")      # the run resumed from is never changed
    led = Ledger(out / "ledger.sqlite")
    cols = matrix.precinct_order(led, args.county)
    if not cols:
        print("the ledger has no header block (registered voters row); nothing to place columns by", file=sys.stderr)
        return 1
    geo = matrix.Geometry(args.county, cols)
    chosen = next((json.loads(e["payload_json"]).get("reader") for e in reversed(led.events(args.county))
                   if e["kind"] == "choose_reader"), None)
    reader = chosen or "claude-haiku"
    gw = Gateway(budget=args.budget, model=reader)
    print(f"run {run_id}: closing {args.county} from {resume} (reader {reader}"
          f"{'' if chosen else ', not recorded in the ledger: the cheapest is assumed'}), run budget ${args.budget:.2f}")
    try:
        s = agent.close_county(args.county, gw, led, geo, run_id=run_id, max_items=args.max_items, reader=reader)
    except RenderError as e:
        print(e, file=sys.stderr)
        return 1
    finally:
        tracing.shutdown()
    try:
        s["gateway_spend_before"], s["gateway_spend_after"] = before, gateway_spend()[0]
        s["gateway_spend_change"] = round(s["gateway_spend_after"] - before, 4)
    except (KeyError, OSError, ValueError, TypeError):
        pass
    outputs.write_county(out, args.county, run_id, led, geo, s)
    outputs.write_run(out, run_id, started=started, ended=time.strftime("%Y-%m-%dT%H:%M:%S"),
                      command="crossfoot " + " ".join(sys.argv[1:]), counties=[args.county], gw=gw,
                      resumed_from=resume)
    b, a = s["sums_failing_before"], s["sums_failing_after"]
    print(f"sums failing before: {b['row']} row, {b['col']} column, {b['grand']} grand (small totals), "
          f"{b['grand_row']} grand (row totals)")
    print(f"sums failing after:  {a['row']} row, {a['col']} column, {a['grand']} grand (small totals), "
          f"{a['grand_row']} grand (row totals)")
    print(f"values re-read: {s['values_reread']}; cells changed: {s['cells_changed']}, totals changed: "
          f"{s['totals_changed']}; cannot_verify: {s['cells_cannot_verify']}; document_inconsistent: "
          f"{s['cells_document_inconsistent']}; accepted: {s['cells_accepted']} of {s['cells_total']}; "
          f"still open: {s['cells_open']}")
    print(f"verdicts on sums still failing: {s['verdicts']['document_inconsistent']} document_inconsistent, "
          f"{s['verdicts']['cannot_verify']} cannot_verify")
    print(f"model calls: {s['model_calls']}; tokens: {s['prompt_tokens']} in, {s['completion_tokens']} out; "
          f"metered cost (estimate): ${s['metered_cost_estimate']:.4f}; seconds: {s['seconds']}")
    if "gateway_spend_change" in s:
        print(f"gateway spend: ${s['gateway_spend_before']:.4f} -> ${s['gateway_spend_after']:.4f} "
              f"(change ${s['gateway_spend_change']:.4f})")
    print(f"written: {out / args.county / 'county.json'}, {out / 'run.json'}")
    return 2 if s["stopped"] else 0


def _latest_closed_run() -> str | None:
    from pathlib import Path
    runs = sorted(p.parent.parent.name for p in Path("runs").glob("*/*/county.json") if (p.parent.parent / "ledger.sqlite").exists())
    return runs[-1] if runs else None


def _print_audit(d, gw, spend, seconds, out, county, reader) -> None:
    c = d["counts"]
    print(f"reader: {reader}; findings: {c['findings']} in {c['groups']} groups; by kind {c['by_kind']}; by status "
          f"{c['by_status']}; values changed in the corrected file: {c['corrections']}")
    print(f"ledger values corrected by a re-read: {d['audit']['ledger_corrected']}; re-reads made: {d['audit']['rereads']} "
          f"(skipped because the printed sums decide: {d['audit']['rereads_skipped_sums_decide']})")
    sc = d["sums_check"]
    print(f"printed sums in all: {sc['in_all']}; holding with the published file's values: {sc['holding_with_published']}; "
          f"holding with the corrected file's values: {sc['holding_with_corrected']}; still failing: {len(sc['still_failing'])}; "
          f"rows failing their own total, published {sc['rows_failing_own_total']['published']}, corrected "
          f"{sc['rows_failing_own_total']['corrected']}; rows not corrected as a whole: {len(d['could_not_correct'])}")
    print(f"model calls: {gw.calls} {gw.calls_by_model()}; tokens: {gw.prompt_tokens} in, {gw.completion_tokens} out; "
          f"metered cost (estimate): ${gw.cost:.4f}; seconds: {seconds}")
    if spend:
        print(f"gateway spend: ${spend['before']:.4f} -> ${spend['after']:.4f} (change ${spend['change']:.4f})")
    print(f"written: {out / county}/ (findings.json, report.md, changes.diff, corrected/, crops/), {out / 'run.json'}")


def cmd_audit(args) -> int:
    import json
    import shutil
    import time
    from pathlib import Path

    from . import agent, audit, outputs, policy, tracing
    from .layouts import matrix
    from .ledger import Ledger
    from .model import BudgetExceeded, gateway_spend
    from .render import RenderError
    if args.county != "panola":
        return _audit_report(args)
    src = None
    if args.resume:
        resume = _latest_closed_run() if args.resume == "latest" else args.resume
        src = Path("runs") / str(resume) / "ledger.sqlite"
        if not resume or not src.exists():
            print(f"no closed run to resume from ({src})", file=sys.stderr)
            return 1
    try:
        sources.fetch(args.county)
    except sources.FetchError as e:
        print(e, file=sys.stderr)
        return 1
    note = tracing.init()
    if note:
        print(note)
    try:
        before = gateway_spend()[0]
    except (KeyError, OSError, ValueError):
        before = None
    t0 = time.time()
    started = time.strftime("%Y-%m-%dT%H:%M:%S")
    run_id = time.strftime("%Y%m%d-%H%M%S")
    out = Path("runs") / run_id
    out.mkdir(parents=True)
    log = lambda *a: print(*a, flush=True)
    phases, sample, summary, stopped, reader = {}, None, None, None, None
    gw = audit.AuditGateway(budget=args.budget)
    try:
        if src:
            shutil.copy(src, out / "ledger.sqlite")           # the run resumed from is never changed
            led = Ledger(out / "ledger.sqlite")
            src_json = src.parent / args.county / "county.json"
            if src_json.exists():
                old = json.loads(src_json.read_text())
                summary, sample = old.get("summary"), old.get("sample")
            print(f"run {run_id}: auditing {args.county} on the ledger of {src.parent.name} (no new read)")
        else:
            led = Ledger(out / "ledger.sqlite")
            print(f"run {run_id}: reading, closing and auditing {args.county}, run budget ${args.budget:.2f}")
            t1 = time.time()
            s_read = matrix.read_county(args.county, gw, led, run_id=run_id, model="auto", log=log)
            phases["read"] = round(time.time() - t1, 1)
            sample = s_read.get("sample")
            if s_read["stopped"]:
                print(s_read["stopped"], file=sys.stderr)
                return 2
        cols = matrix.precinct_order(led, args.county)
        if not cols:
            print("the ledger has no header block (registered voters row); nothing to place columns by", file=sys.stderr)
            return 1
        geo = matrix.Geometry(args.county, cols)
        chosen = next((json.loads(e["payload_json"]) for e in reversed(led.events(args.county))
                       if e["kind"] == "choose_reader"), None)
        reader = (chosen or {}).get("reader") or "claude-haiku"
        sample = sample or chosen
        gw.model = reader
        t1 = time.time()
        closed = agent.close_county(args.county, gw, led, geo, run_id=run_id, reader=reader, log=log)
        agent.finalize_open(led, args.county)
        phases["close"] = round(time.time() - t1, 1)
        summary = dict(summary if src and summary else closed)
        cs = led.cells(args.county)
        summary.update(cells_accepted=sum(c["status"] == "accepted" for c in cs),
                       cells_cannot_verify=sum(c["status"] == "cannot_verify" for c in cs),
                       cells_document_inconsistent=sum(c["status"] == "document_inconsistent" for c in cs),
                       cells_open=sum(c["status"] not in ("accepted", "cannot_verify", "document_inconsistent")
                                      for c in cs))
        stopped = closed["stopped"]
        if not stopped:
            outputs.fill_boxes(led, args.county, geo)
            t1 = time.time()
            pol = policy.write_for_run(out)
            rows = sources.read_published(args.county)
            fname = sources.file_url(args.county).rsplit("/", 1)[1]
            raw = sources.file_path(args.county).read_bytes()
            res = audit.audit_county(args.county, led, geo, gw, rows, run_dir=out, log=log, run_id=run_id, file_name=fname)
            phases["audit"] = round(time.time() - t1, 1)
            outputs.make_group_crops(args.county, res, geo)
            outputs.write_county(out, args.county, run_id, led, geo, summary)
            d = outputs.write_findings(out, args.county, run_id, res, policy=pol, raw_file=raw, file_name=fname,
                                       file_urls={"scan": sources.scan_url(args.county), "file": sources.file_url(args.county)},
                                       verdicts=led.verdicts(args.county))
    except BudgetExceeded as e:
        stopped = str(e)
        print(f"stopped: {e}", file=sys.stderr)
    except RenderError as e:
        print(e, file=sys.stderr)
        return 1
    finally:
        tracing.shutdown()
    spend = None
    try:
        after = gateway_spend()[0]
        spend = {"before": before, "after": after, "change": round(after - before, 4)}
    except (KeyError, OSError, ValueError, TypeError):
        pass
    seconds = round(time.time() - t0, 1)
    outputs.write_audit_run(out, run_id, started=started, ended=time.strftime("%Y-%m-%dT%H:%M:%S"), seconds=seconds,
                            command="crossfoot " + " ".join(sys.argv[1:]), county=args.county, gw=gw,
                            reader=reader, sample=sample, resumed_from=(src.parent.name if src else None),
                            phases=phases, spend=spend)
    if stopped:
        print("the run stopped before the audit finished; nothing was written beyond run.json", file=sys.stderr)
        return 2
    _print_audit(d, gw, spend, seconds, out, args.county, reader)
    return 0


def _audit_report(args) -> int:
    """`audit` for a county that is not a matrix sheet: decide the layout from page 1, read, close, audit."""
    import json
    import shutil
    import time
    from pathlib import Path

    from . import agent, audit, outputs, policy, tracing
    from .layouts import report
    from .ledger import Ledger
    from .model import BudgetExceeded, gateway_spend
    from .render import RenderError
    county = args.county
    src = None
    if args.resume:
        resume = _latest_closed_run() if args.resume == "latest" else args.resume
        src = Path("runs") / str(resume) / "ledger.sqlite"
        if not resume or not src.exists():
            print(f"no closed run to resume from ({src})", file=sys.stderr)
            return 1
    try:
        sources.fetch(county)
    except sources.FetchError as e:
        print(e, file=sys.stderr)
        return 1
    note = tracing.init()
    if note:
        print(note)
    try:
        before = gateway_spend()[0]
    except (KeyError, OSError, ValueError):
        before = None
    t0 = time.time()
    started = time.strftime("%Y-%m-%dT%H:%M:%S")
    run_id = time.strftime("%Y%m%d-%H%M%S")
    out = Path("runs") / run_id
    out.mkdir(parents=True)
    log = lambda *a: print(*a, flush=True)
    phases, stopped, reader, sample, d = {}, None, None, None, None
    gw = audit.AuditGateway(budget=args.budget)
    urls = {"scan": sources.scan_url(county), "file": sources.file_url(county)}
    try:
        if src:
            shutil.copy(src, out / "ledger.sqlite")
            led = Ledger(out / "ledger.sqlite")
            print(f"run {run_id}: auditing {county} on the ledger of {src.parent.name} (no new read)")
            lay = report.layout_event(led, county)
            read = {"layout": "report", "layout_decision": lay, "pages_failed": []}
        else:
            led = Ledger(out / "ledger.sqlite")
            print(f"run {run_id}: deciding the layout of {county} from its first page, then reading, closing and "
                  f"auditing it, run budget ${args.budget:.2f}")
            t1 = time.time()
            read = report.read_county(county, gw, led, run_id=run_id, log=log)
            phases["read"] = round(time.time() - t1, 1)
        sample = read.get("sample")
        if read.get("stopped"):
            stopped = read["stopped"]
        elif read["layout"] != "report":
            outputs.write_unchecked(out, county, run_id, read, urls)
            print(f"{county}: layout {read['layout']}: {read.get('note')}")
        else:
            lay = report.layout_event(led, county)
            if src:
                report.reopen(led, county)
            report.refit_boxes(led, county, x_right=lay.get("x_right"))
            geo = report.ReportGeometry(county, x_right=lay.get("x_right"))
            chosen = next((json.loads(e["payload_json"]) for e in reversed(led.events(county))
                           if e["kind"] == "choose_reader"), None)
            reader = (chosen or {}).get("reader") or "claude-haiku"
            sample = sample or chosen
            gw.model = reader
            t1 = time.time()
            closed = report.close_county(county, gw, led, geo, reader=reader, run_id=run_id, log=log)
            phases["close"] = round(time.time() - t1, 1)
            stopped = closed["stopped"]
            if not stopped:
                summary = dict(closed, layout="report", layout_decision=read.get("layout_decision"), sample=sample,
                               pages_failed=read.get("pages_failed"))
                t1 = time.time()
                pol = policy.write_for_run(out)
                rows = sources.read_published(county)
                fname = sources.file_url(county).rsplit("/", 1)[1]
                raw = sources.file_path(county).read_bytes()
                res = audit.audit_report_county(county, led, geo, gw, rows, run_dir=out, log=log, file_name=fname,
                                                reader=reader, run_id=run_id)
                phases["audit"] = round(time.time() - t1, 1)
                outputs.make_row_crops(county, res, geo)
                outputs.write_county(out, county, run_id, led, geo, summary, layout="report")
                d = outputs.write_findings(out, county, run_id, res, policy=pol, raw_file=raw, file_name=fname,
                                           file_urls=urls, verdicts=led.verdicts(county))
    except BudgetExceeded as e:
        stopped = str(e)
        print(f"stopped: {e}", file=sys.stderr)
    except RenderError as e:
        print(e, file=sys.stderr)
        return 1
    finally:
        tracing.shutdown()
    spend = None
    try:
        after = gateway_spend()[0]
        spend = {"before": before, "after": after, "change": round(after - before, 4)}
    except (KeyError, OSError, ValueError, TypeError):
        pass
    seconds = round(time.time() - t0, 1)
    outputs.write_audit_run(out, run_id, started=started, ended=time.strftime("%Y-%m-%dT%H:%M:%S"), seconds=seconds,
                            command="crossfoot " + " ".join(sys.argv[1:]), county=county, gw=gw, reader=reader,
                            sample=sample, resumed_from=(src.parent.name if src else None), phases=phases, spend=spend)
    if stopped:
        print("the run stopped before the audit finished; nothing was written beyond run.json", file=sys.stderr)
        return 2
    if d is None:
        if spend:
            print(f"gateway spend: ${spend['before']:.4f} -> ${spend['after']:.4f} (change ${spend['change']:.4f})")
        print(f"written: {out / county}/ (county.json, report.md), {out / 'run.json'}")
        return 0 if read["layout"] == "no_printed_totals" else 1
    _print_audit(d, gw, spend, seconds, out, county, reader)
    return 0


def cmd_verify_known(args) -> int:
    import json
    from pathlib import Path
    known = Path("tests") / f"known_{args.county}.json"
    runs = sorted(p for p in Path("runs").glob(f"*/{args.county}/findings.json"))
    if not known.exists() or not runs:
        print(f"need {known} and a run with {args.county}/findings.json", file=sys.stderr)
        return 1
    want = json.loads(known.read_text())["expected"]
    d = json.loads(runs[-1].read_text())
    fs = d["findings"]
    missing = []
    for e in want:
        hit = [f for f in fs if (not e.get("kind") or f["kind"] == e["kind"]) and
               e.get("office_contains", "").lower() in f["office"].lower() and
               e.get("candidate_contains", "").lower() in f["candidate"].lower() and
               (not e.get("precinct") or f["precinct"] == e["precinct"])]
        if not hit:
            missing.append(e)
    found = len(want) - len(missing)
    print(f"findings file: {runs[-1]}")
    print(f"expected {len(want)}, found {found}, findings in all {len(fs)}")
    for e in missing:
        print(f"  missing: {e}", file=sys.stderr)
    return 1 if missing else 0


def cmd_policy(args) -> int:
    from . import policy
    if args.action == "set":
        if args.answer not in policy.ANSWERS:
            print(f"--answer must be one of {', '.join(policy.ANSWERS)}", file=sys.stderr)
            return 1
        d = policy.set_answer(args.answer)
        print(f"stored: {d['question_id']} = {d['answer']} ({policy.TEXT[d['answer']]}); answered by {d['answered_by']}")
        return 0
    d = policy.current()
    print(f"{d['question_id']} = {d['answer']} ({policy.TEXT[d['answer']]}); answered by {d['answered_by']}")
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="crossfoot")
    sub = p.add_subparsers(dest="cmd", required=True)
    for name, fn, h in (("fetch", cmd_fetch, "download a county's scan and published file"),
                        ("filecheck", cmd_filecheck, "list published rows whose votes differ from their parts")):
        s = sub.add_parser(name, help=h)
        g = s.add_mutually_exclusive_group(required=True)
        g.add_argument("--county", choices=list(sources.COUNTIES))
        g.add_argument("--all", action="store_true")
        s.set_defaults(fn=fn)
    s = sub.add_parser("render", help="render one scan page to PNG")
    s.add_argument("--county", required=True, choices=list(sources.COUNTIES))
    s.add_argument("--page", type=int, required=True)
    s.add_argument("--dpi", type=int, default=200)
    s.set_defaults(fn=cmd_render)
    s = sub.add_parser("read", help="first read of a county's scan into a new run's ledger")
    s.add_argument("--county", required=True, choices=list(sources.COUNTIES))
    s.add_argument("--budget", type=float, default=2.00, help="dollars this run may meter (default 2.00)")
    s.add_argument("--pages", help="comma-separated pages, default all (the sample of --model auto always reads page 1)")
    s.add_argument("--model", default="auto", help="auto (default): read a sample of page 1 with claude-haiku and choose "
                   "the reader by how many of its row sums fail; or a model name, which skips the sample")
    s.set_defaults(fn=cmd_read)
    s = sub.add_parser("close", help="work every failing sum of a first-read ledger until each cell is accepted or "
                                     "cannot_verify")
    s.add_argument("--county", required=True, choices=list(sources.COUNTIES))
    s.add_argument("--resume", required=True, help="run id whose ledger is copied into a new run, or 'latest' for the "
                   "newest read (a run with a first-read.json)")
    s.add_argument("--budget", type=float, default=1.50, help="dollars this run may meter (default 1.50)")
    s.add_argument("--max-items", type=int, help="work at most this many failing sums (for trials)")
    s.set_defaults(fn=cmd_close)
    s = sub.add_parser("audit", help="read (or reuse a ledger), close it, compare it with the published file, write "
                                     "findings, a corrected file, a diff and a report")
    s.add_argument("--county", required=True, choices=list(sources.COUNTIES))
    s.add_argument("--resume", help="run id whose ledger is reused instead of reading again, or 'latest' for the "
                   "newest run with a county.json")
    s.add_argument("--budget", type=float, default=2.00, help="dollars this run may meter (default 2.00)")
    s.set_defaults(fn=cmd_audit)
    s = sub.add_parser("verify-known", help="check the newest findings.json against the answer key in tests/")
    s.add_argument("--county", required=True, choices=list(sources.COUNTIES))
    s.set_defaults(fn=cmd_verify_known)
    s = sub.add_parser("policy", help="the one question the audit asks a person")
    s.add_argument("action", choices=["set", "show"])
    s.add_argument("--answer", help="cells or totals (with `set`)")
    s.set_defaults(fn=cmd_policy)
    s = sub.add_parser("budget", help="print the gateway's spend and limit for the key")
    s.set_defaults(fn=cmd_budget)
    args = p.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
