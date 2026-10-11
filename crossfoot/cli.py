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
    s = sub.add_parser("budget", help="print the gateway's spend and limit for the key")
    s.set_defaults(fn=cmd_budget)
    args = p.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
