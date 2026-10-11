# Crossfoot

Crossfoot is an agent that audits published data against the scanned documents it was copied from, proves each
error with the document's own printed totals, and proposes the fix.

<!-- picture:start -->
![crop of the scan: Chase Oliver, precinct 29, the cell outlined](runs/20261011-161207/panola/crops/g003.png)

*Panola County, page 1, Chase Oliver, precinct 29, election day. The published file has 0; the scan has 1. The row's printed total is 12: the cells add to 12 with the scan's value and to 11 with the file's, so the printed total decides (finding f005 in [runs/20261011-161207/panola/findings.json](runs/20261011-161207/panola/findings.json); not confirmed by a person).*
<!-- picture:end -->

Open: **[the live results page](https://crossfoot-zeta.vercel.app/)** ([its source](site/)) · [the design](ARCHITECTURE.md) ·
[the build log](hackathon.md)

The three tools, and where to see each:
- **neatlogs** traces every model and tool call of a run: [one trace as the server returns it](docs/evidence/trace-panola-final.md),
  [every trace and the detection](docs/evidence/traces.md), [what a trace changed in the program](docs/evidence/before-after.md).
- **Entire** records each coding session with its commit: [the checkpoints](docs/evidence/checkpoints.txt).
- **cfo.ai** made the business plan from the measured cost: [the plan](https://app.cfo.ai/s/aRFg86F21pDO1EQN) and
  [what it says](docs/evidence/business-plan.md).

## What it found

Eight Texas county files for the 2024 general election, each checked against its county's own scan. Every figure
below is made from [`runs/20261011-161207/summary.json`](runs/20261011-161207/summary.json) by
[`tools/readme_tables.py`](tools/readme_tables.py); each county's own folder holds its report, corrected file and crops.

<!-- table:start -->
| County | Layout | Published rows compared | Disagreements | Settled by the printed totals | Cannot be verified | Printed sums in all | Holding with the published file | Holding with the corrected file |
|---|---|---|---|---|---|---|---|---|
| Panola | matrix | 783 of 783 | 121 | 109 | 12 | 985 | 950 | 979 |
| San Saba | report | 275 of 275 | 21 | 3 | 18 | 275 | 274 | 275 |
| Cottle | report | 166 of 166 | 0 | 0 | 0 | 166 | 166 | 166 |
| Jones | report | 335 of 344 | 26 | 26 | 0 | 1,102 | 1,083 | 1,102 |
| Lynn | report | 634 of 650 | 47 | 47 | 0 | 2,115 | 2,049 | 2,115 |
| Scurry | report | 534 of 545 | 0 | 0 | 0 | 545 | 545 | 545 |
| Foard | report | 294 of 298 | 0 | 0 | 0 | 700 | 700 | 700 |
| Limestone | no_printed_totals | not checked: nothing printed on the scan can be summed | | | | | | |
| **All** | | 3,021 of 3,061 | 215 | 185 | 30 | 5,888 | 5,767 | 5,882 |
<!-- table:end -->

Confirmed by a person: 0. Nothing has been sent to the project.

What these are: transcription slips in a volunteer dataset, found by comparing it with the counties' certified scans,
which are the source of truth. The scans and the published files are public
([scans](https://github.com/openelections/openelections-sources-tx/tree/master/2024/general),
[published files](https://github.com/openelections/openelections-data-tx/tree/master/2024/counties), from the
[OpenElections](https://github.com/openelections) project). Neither the project nor any county has seen or approved
this. Nothing here says anything about the results themselves.

How to check one: open the county's `report.md` (for example
[Panola's](runs/20261011-161207/panola/report.md)). Each group has a crop of the scan, the cells, and each printed sum
with the value that makes it hold. Add the numbers on the crop yourself.

## How it works

1. Read a sample of the first page with a cheap model and choose the reader by how many printed row sums fail.
2. Read every page into a ledger, one cell at a time.
3. Check every printed sum: a value is accepted only when the sums it sits on hold.
4. Where two failing sums cross, look again at that cell with a bigger crop and, if needed, a stronger model.
5. Lay the published file over the closed ledger, row by row.
6. The printed sums decide: a correction is proposed only when a printed total agrees with the new value and
   disagrees with the old one; otherwise it says "cannot verify" and leaves the value alone.

## Run it

```
uv sync
export LITELLM_API_KEY=... LITELLM_BASE_URL=...      # an OpenAI-compatible gateway; NEATLOGS_API_KEY is optional
uv run crossfoot budget                              # the gateway's spend and limit for the key
uv run crossfoot audit --county panola               # read, close, audit one county; writes runs/<run_id>/panola/
uv run crossfoot audit --all --budget 9              # every county in turn; writes runs/<run_id>/<county>/ and summary.json, summary.md
uv run crossfoot summarize --base <run_id> --use panola=<run_id>   # a new summary from the newest result of each county; no model call
uv run crossfoot verify-known --county panola        # checks the findings against eight slips read by eye
uv run crossfoot site build --run latest             # writes site/data/ from the newest summary run
python3 -m http.server -d site 8000                  # then open http://localhost:8000/
uv run pytest -q                                     # no network, no model calls
```

It needs `pdftoppm` (poppler) to render the scans. `uv run crossfoot --help` lists the other steps.

## Evidence

- Two changes made from what the runs showed, each with a run before and a run after and what got worse:
  [docs/evidence/before-after.md](docs/evidence/before-after.md).
- One prompt to a general coding agent on the same county, scored the same way:
  [docs/evidence/baseline.md](docs/evidence/baseline.md).
- A run stopped by its budget and continued, and other recoveries:
  [docs/evidence/recovery.md](docs/evidence/recovery.md).
- Traces and the detection: [docs/evidence/traces.md](docs/evidence/traces.md).
- Checkpoints, the output of `entire checkpoint list`: [docs/evidence/checkpoints.txt](docs/evidence/checkpoints.txt)
  (the last line says how to open a session from a commit's `Entire-Checkpoint` trailer).
- The results page: [site/](site/) (static; serve it as in "Run it"). Screenshots of it at 1440x900 and 390x844 and the
  accessibility check (axe-core, zero violations) are in [qa/final/](qa/final/).
- The build log, including what failed: [hackathon.md](hackathon.md).

Measured cost and time per county, from the same summary:

<!-- cost:start -->
| County | Pages | Model calls | Metered cost (estimate) | Seconds | Added by later audits from the ledger |
|---|---|---|---|---|---|
| Panola | 6 | 172 | $0.7892 | 507.0 | none |
| San Saba | 21 | 33 | $0.2076 | 102.8 | none |
| Cottle | 12 | 13 | $0.1039 | 57.7 | none |
| Jones | 20 | 24 | $0.2544 | 119.9 | none |
| Lynn | 37 | 51 | $0.4624 | 207.4 | none |
| Scurry | 38 | 40 | $0.3329 | 139.5 | none |
| Foard | 16 | 19 | $0.1931 | 91.2 | none |
| Limestone | 0 | 1 | $0.0021 | 2.3 | none |
| **All** | 150 | 353 | $2.3456 | 1227.8 | none |

Calls, cost and seconds are those of the run that read each county, [`runs/20261011-161207/summary.json`](runs/20261011-161207/summary.json) (one unattended `audit --all` run). The last column is what audits made again from the same ledgers added, where there were any. An audit from nothing costs, for the dearest checked county, Panola (172 model calls, $0.7892, 507.0 seconds), and for the cheapest, Cottle (13 model calls, $0.1039, 57.7 seconds); Limestone, which prints nothing to add up, took 1 call to be listed as not checked.
<!-- cost:end -->

## The three tools

- **neatlogs.** Every model and tool call is a span. Two changes to the program were made from what the runs showed
  ([before-after.md](docs/evidence/before-after.md)), and one detection was created
  ([traces.md](docs/evidence/traces.md)). One trace as the server returns it, with its span tree and a masked image:
  [trace-panola-final.md](docs/evidence/trace-panola-final.md).
- **Entire.** Every coding session's commit carries an `Entire-Checkpoint` trailer
  ([checkpoints.txt](docs/evidence/checkpoints.txt)). The graph plugin's instructions for coding agents are in
  [AGENTS.md](AGENTS.md).
- **cfo.ai.** The business plan, made from the run's measured cost and our stated assumptions:
  [the shared plan](https://app.cfo.ai/s/aRFg86F21pDO1EQN) and what it says
  ([business-plan.md](docs/evidence/business-plan.md)). The model costs $0.29 a file and a person confirming the
  findings $13.21, so two of the three prices we tried lose money on every file.

## Limits

- The sums cannot see two wrong values that cancel out on the same row and the same column.
- A value that sits on one printed sum only cannot be located when that sum fails; it is reported as "cannot verify".
  Three of the counties print only a row sum as the second check (`summary.md`, column "second sum").
- Limestone County prints nothing that can be added up, so it is listed as not checked and left as published.
- Where the scan's own printed totals disagree with each other, Crossfoot says so and lists it for a person. It does
  not say which is right.
- Some published rows were not compared with the scan (the contest did not pair with one on the scan, or the row
  repeats a precinct); each is listed in the run's `summary.md` under "Published rows compared with the scan".
- A missing or extra row is listed, never added or removed.
- A person still has to open the scan for each finding, confirm it, and send it to the project. None has been confirmed.
- Not built: sending anything to anyone, and reading a scan that has no printed totals.

## How and when it was built

Built during neatHack: the first commit is dated 2026-10-11T08:50:59Z and every commit is inside the event window.
The code was written by Claude Code sessions (Anthropic's coding agent, Claude Sonnet), each given one written task
and reporting on it; a planning session wrote the tasks, checked each result against the run files and the scans,
and decided what came next. Every session is recorded with Entire and
tied to its commit. The models that read the scans at run time are `claude-haiku`, `claude-sonnet-4.6` and
`claude-opus-4.6` through the event's gateway.

## What existed before the event

The idea and the plan. The plan (the architecture, a specification of the results page, a list of requirements and
the tasks) was written before any code and is the repository's first commit, `82a6b67`. No code existed before the
event. The planning and task files were taken out of the tree at the end to keep it to what a reader needs; they are
in the history, and each coding session's task and report are in the session recorded with its commit.
