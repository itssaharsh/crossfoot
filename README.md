# Crossfoot

Crossfoot is an agent that audits published data against the scanned documents it was copied from, proves each
error with the document's own printed totals, and proposes the fix.

**Status (11 October 2026, in progress):** built during neatHack. One county is audited end to end; the second
layout, the run over all eight counties and the results page are being built now. The plan, the architecture and the
UI specification in this repository were written before any code, and no code existed before the event's start. The
build log is in [hackathon.md](hackathon.md).

## The idea

A scanned table prints its own totals. On a canvass sheet every value sits on two printed sums: a cell on its row
and its column, the small total under a column on that column and on the grand total. So one wrong value makes
exactly two sums fail, and they cross at it. Crossfoot reads the scan with a vision model, accepts a value only when
its sums hold, looks again where two failing sums cross, and then uses the closed ledger to audit the public file
that was copied from the same scan. A correction is proposed only when printed totals agree with the new value and
disagree with the old one. Where no printed total can decide, it says "cannot verify" and leaves the value alone.

## What it works on

The eight Texas county files (2024 general election) that the [OpenElections](https://github.com/openelections)
project uses as a manually verified answer key for grading document-reading models
([scans](https://github.com/openelections/openelections-sources-tx/tree/master/2024/general),
[published files](https://github.com/openelections/openelections-data-tx/tree/master/2024/counties)). The scans
are the counties' own documents and are the source of truth. What Crossfoot finds are transcription slips in a
volunteer dataset, never anything about the results themselves. No finding below has been confirmed by a person yet,
and nothing has been sent to the project.

## Where it stands: Panola County (6 scanned pages, 783 published rows)

Figures from `runs/20261011-120008` (one full run from nothing) and `runs/20261011-122159` (the audit of that
ledger with the current rules):

| | |
|---|---|
| Places where the published file disagrees with the scan | 121 values, in 46 groups |
| Settled by the scan's printed totals | 109 |
| Cannot be verified, left as published | 12 |
| Confirmed by a person | 0 |
| Printed sums on the scan | 984 |
| ... that hold with the published file's values | 949 |
| ... that hold with the corrected file's values | 978 (6 still fail, each with its reason in the report) |
| Published rows that fail their own total | 1, and 0 in the corrected file |
| One full run | 639 seconds, 269 model calls, $0.88 (metered estimate) |

The report with a crop and the deciding sums for every group is
[runs/20261011-122159/panola/report.md](runs/20261011-122159/panola/report.md); the corrected file and the diff are
next to it.

How the reader was chosen, from the run's own record: a sample of the first page read with `claude-haiku`
failed 6 of 22 row sums, so the county was read with `claude-sonnet-4.6`.

## Run it

```
uv sync
export LITELLM_API_KEY=... LITELLM_BASE_URL=...   # an OpenAI-compatible gateway; NEATLOGS_API_KEY is optional
uv run crossfoot audit --county panola             # read, close, audit; writes runs/<run_id>/panola/
uv run crossfoot verify-known --county panola      # checks the findings against eight slips read by eye
uv run pytest -q
```

It needs `pdftoppm` (poppler) to render the scans.

## Evidence so far

- [docs/evidence/before-after.md](docs/evidence/before-after.md): two changes made from what the runs showed, each
  with a run before and a run after and what got worse.
- [docs/evidence/baseline/](docs/evidence/baseline/): one prompt to a general coding agent on the same county, kept
  as it was written. It is being scored with the audit's own rules.
- [hackathon.md](hackathon.md): the build log, including what failed.
- Every commit made by a coding session carries an `Entire-Checkpoint` trailer; the session is stored with it.

## Limits

- The sums cannot see two wrong values that cancel out on the same row and the same column.
- A value that sits on one printed sum only (the registered-voters row of this county) cannot be located when that
  sum fails; it is reported as "cannot verify".
- Where the scan's own printed totals disagree with each other, Crossfoot says so and lists it for a person. It does
  not say which is right.
- A missing or extra row is listed, never added or removed.

## How it is being built

- [ARCHITECTURE.md](ARCHITECTURE.md): the design, and the measurements that changed it.
- [.prod-build/contract.md](.prod-build/contract.md): what it has to do and how each part is checked.
- [UI-SPEC.md](UI-SPEC.md): the results page.
- `.prod-build/briefs/` and `.prod-build/reports/`: the task given to each coding session and what it reported.
