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
    args = p.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
