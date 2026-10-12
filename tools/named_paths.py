"""List every run id and qa path that the documents name, and whether it still exists in the tree.

    python3 tools/named_paths.py          print the table
    python3 tools/named_paths.py --check  exit 1 if a named run folder (or a path under it) or qa path is missing

Documents read: README.md, hackathon.md, docs/, tests/. A run id counts as present when runs/<id> exists;
a path like runs/<id>/<rest> counts as present when that file exists. Lines that say "not committed", raw diff-stat lines of
old reports and the made-up ids in tests/ are skipped, and so is a sentence that says something was removed, deleted or
renamed (and the lines that continue its bullet): what it names is meant to be gone.

Ten run folders that only the build log named were taken out of the tree on 12 October 2026 (REMOVED below). They are in
the history, last at commit 38507b8. A mention of one of them is listed as removed, and it is an error if it is back.
The page's screenshots and check results (qa/final/) left the tree the same day, last at commit e0452da; the same holds for them."""
import re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCES = ["README.md", "hackathon.md", "docs", "tests"]
RUN = re.compile(r"\b(2026\d{4}-\d{6})\b")
RUNPATH = re.compile(r"runs/(2026\d{4}-\d{6})/([\w./*<>-]+)")
GONE = re.compile(r"\b(removed|deleted|renamed)\b", re.I)
QA = re.compile(r"(?<![\w/])qa/[\w./-]+")
REMOVED = {"20261011-085854", "20261011-121108", "20261011-122159", "20261011-140000", "20261011-140637", "20261011-141051",
           "20261011-141131", "20261011-141152", "20261011-141300", "20261011-150000"}
REMOVED_QA = "qa/final"


def files():
    for s in SOURCES:
        p = ROOT / s
        for f in ([p] if p.is_file() else sorted(p.rglob("*"))):
            if f.is_file() and f.suffix in {".md", ".py", ".txt", ".json", ".mjs"} and "__pycache__" not in f.parts and "score" != f.stem:
                yield f


def scan():
    runs, paths, qa = {}, {}, {}
    for f in files():
        gone = False         # inside a bullet or paragraph that says something was removed
        for line in f.read_text(errors="replace").splitlines():
            rel = f.relative_to(ROOT).as_posix()
            gone = bool(GONE.search(line)) or (gone and line.startswith(" ") and bool(line.strip()))
            if gone or "not committed" in line or re.search(r"\|\s+\d+\s+[+-]*\s*$", line) or rel.startswith("tests/"):
                continue      # a run said not to be committed, a raw `git diff --stat` line (history), a test's made-up ids
            for m in RUN.finditer(line):
                runs.setdefault(m.group(1), set()).add(rel)
            for m in RUNPATH.finditer(line):
                if not re.search(r"[*<>]", m.group(2)):
                    paths.setdefault(f"runs/{m.group(1)}/{m.group(2).rstrip('.,;:)')}", set()).add(rel)
            for m in QA.finditer(line):
                qa.setdefault(m.group(0).rstrip(".,;:)"), set()).add(rel)
    return runs, paths, qa


def main(argv=None) -> int:
    runs, paths, qa = scan()
    bad = []
    print("run ids named, and whether runs/<id> exists:")
    for r in sorted(runs):
        if r in REMOVED:
            ok = not (ROOT / "runs" / r).exists()
            print(f"  {r}  {'removed on purpose, in the history' if ok else 'LISTED AS REMOVED BUT PRESENT'}  ({len(runs[r])} file(s))")
        else:
            ok = (ROOT / "runs" / r).is_dir()
            print(f"  {r}  {'present' if ok else 'MISSING'}  ({len(runs[r])} file(s))")
        if not ok:
            bad.append(r)
    print("paths under runs/ named:")
    for p in sorted(paths):
        if p.split("/")[1] in REMOVED:
            print(f"  {p}  removed on purpose, in the history")
            continue
        ok = (ROOT / p).exists()
        if not ok:
            bad.append(p)
        print(f"  {p}  {'present' if ok else 'MISSING'}")
    print("qa paths named:")
    for p in sorted(qa):
        if p.startswith(REMOVED_QA):
            ok = not (ROOT / REMOVED_QA).exists()
            print(f"  {p}  {'removed on purpose, in the history' if ok else 'LISTED AS REMOVED BUT PRESENT'}")
        else:
            ok = (ROOT / p).exists()
            print(f"  {p}  {'present' if ok else 'MISSING'}")
        if not ok:
            bad.append(p)
    print(f"{len(bad)} named path(s) missing")
    return 1 if (bad and "--check" in (argv or sys.argv[1:])) else 0


if __name__ == "__main__":
    sys.exit(main())
