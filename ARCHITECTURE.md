# Architecture

Crossfoot is one Python package with a command-line entry point, files on disk, and a static results page. No
server, no database server, no queue. Each part below names the requirement that forces it (M1 to M9 and S1, listed
at the end).

## The idea in one paragraph

A scanned table prints its own totals. If every cell is read into a ledger, each value can be tested twice: its
row has to add up to the total printed at the end of the row, and its column has to add up to the total printed
under the column. One wrong cell fails both sums, and the two failing sums cross at it. Crossfoot reads the scan
with a vision model, accepts a value only when its sums hold, looks again where two failing sums cross, and then
uses the closed ledger to audit a published file that was copied from the same scan.

## Layout of the repository

```
crossfoot/
  cli.py        command-line entry point (argparse): fetch, filecheck, render, read, read-page, close, audit,
                verify-known, score, policy, budget, summarize, site build
  sources.py    the eight benchmark counties: scan URL, published-file URL, cache under data/ (M1, M4)
  render.py     pdftoppm wrapper: page -> PNG at a dpi; crops with Pillow (M1, M3)
  segment.py    finds blocks and column lines on a ruled page from the image itself (M1)
  model.py      gateway client, JSON parsing with one repair attempt, cost meter, budget guard, rate limit (M7)
  tracing.py    neatlogs setup and span helpers; image bytes are masked out of spans; a no-op without the key (M7)
  layouts/
    matrix.py   precincts as columns, three rows per candidate, totals both ways (Panola)
    report.py   one precinct per section, one row per candidate with its own total, contest totals where printed
                (the other six counties that are read), with its own re-read loop for rows
    profile.py  decides a county's layout from its first page and chooses its reader from a measured sample (M1)
  ledger.py     SQLite ledger: cells, printed totals, events; resume (M2, M6)
  checks.py     row sums, column sums, grand totals, contest sums, pairing of failing sums; pure functions (M2)
  agent.py      the investigation loop of the matrix layout: where to look again, under rules that code enforces (M3)
  audit.py      lays the published file over the closed ledger; classifies and settles disagreements; says how many
                published rows were compared; checks the corrected file against every printed sum (M4)
  allrun.py     every county in turn, unattended: budget, resume, summary (M6)
  outputs.py    county.json, run.json, findings.json, the corrected CSV, the diff, report.md (M5)
  score.py      scores someone else's list of claimed disagreements against the audit (used for the one-prompt baseline)
  sitebuild.py  builds site/data/ from a run: county JSON, page images, crops for the loupe (M8)
  policy.py     the one stored answer and its default (S1)
tests/          unit tests for checks, ledger, loop rules, audit, budget, resume, the page's data; no network, no model
tools/          the README's tables made from the run files; the page's screenshot, accessibility and replay checks
site/           the static results page (plain HTML, CSS and JS; no build step) (M8)
docs/evidence/  runs before and after two changes, the one-prompt baseline, recoveries, traces, checkpoints (M9)
runs/           one folder per run; results are committed, scans and caches are not
data/           downloaded scans and files; never committed
```

## Inputs

Eight Texas counties from the OpenElections project's 2024 general election benchmark. All eight scans are
image-only PDFs (no text layer): Cottle 12 pages, Foard 16, Jones 20, Limestone 42, Lynn 37, Panola 6, San Saba 21,
Scurry 38.

- Scan: `https://raw.githubusercontent.com/openelections/openelections-sources-tx/master/2024/general/2024%20<County>%20County%2C%20TX%20precinct-level%20results.pdf`
- Published file: `https://raw.githubusercontent.com/openelections/openelections-data-tx/master/2024/counties/20241105__tx__general__<county>__precinct.csv`
  with columns `county, precinct, office, district, party, candidate, votes, absentee, early_voting, election_day`.

## Two layouts, and one that cannot be checked

**Matrix (Panola).** A landscape canvass sheet. The header row lists the precincts as columns and ends in a TOTAL
column. Each candidate is a block: a label at the left, three ruled rows (EARLY, ABSENTEE, PRECINCT), a row of
small printed totals under the columns, and a grand total under the TOTAL column. In the published file EARLY is
`early_voting`, ABSENTEE is `absentee`, PRECINCT is `election_day`, and the small total is `votes`.
Checks per block: for each precinct, early + absentee + precinct = the small total; for each row, the precinct cells
add to the row's TOTAL; the small totals add to the grand total, and so do the three row totals.

**Report (San Saba, Cottle, Jones, Lynn, Scurry, Foard).** One precinct per section. Each candidate is a row with
four numbers: TOTAL, Absentee, Early Voting, Election Day (Foard prints them in another order, each followed by a
percentage, which is ignored). Every row is checked: total = absentee + early voting + election day. Where the page
prints a contest total row ("Total Votes Cast", "Cast Votes"), three more sums exist, each per column: the
candidates and the write-in total add to the contest total; the rows that break the write-in total down add to it
(they are not terms of the contest total); and the contest total plus overvotes plus undervotes equals the
precinct's ballots cast, where the contest was on every ballot of the precinct. San Saba, Cottle and Scurry print no
contest total, so a value there sits on its row's sum only.

**Nothing to add up (Limestone).** The scan prints votes and percentages only. Nothing on it can be cross-checked,
so it is not read and is reported as left as published.

`layouts/profile.py` asks the model which layout the first page shows and in what order the columns come, then
reads the first page under that layout and runs the checks. A layout under which more than a third of the sums fail
is rejected and the county is reported as not supported and left alone.

## Reading

1. `render.py` renders a page at 200 dpi; positions in the ledger are in those pixels.
2. Matrix: `segment.py` finds the blocks as bands of ink separated by blank bands, and the column lines inside a
   block as columns of dark pixels that run the height of the ruled rows. Report: the page is read whole, and each
   row's position is snapped to the page's own lines of figures.
3. Matrix: each block is cut into column groups no wider than 1,500 px at 300 dpi, one model call per group; report:
   one page per call. The answer is strict JSON, validated (right number of columns, integers only), with one repair
   request. Every value comes back with the block, row kind and column it belongs to.
4. Which model reads a county is decided by measurement, not fixed. A sample of the first page is read with
   `claude-haiku`; if more than a tenth of the sample's row sums fail, the county is read with `claude-sonnet-4.6`.
   Measured on Panola on 11 October 2026, same code and crops: `claude-haiku` left 85 of 943 printed sums failing
   (44 after a 20-minute re-read loop with 565 more calls); `claude-sonnet-4.6` left 6 of 942.
5. The values go into the ledger as `first_read`, with the page and the pixel box of each value where it is known.

## The ledger (`ledger.py`, SQLite, one file per run)

- `cells(county, page, block_id, contest, candidate, row_kind, column, value, first_read, status, tries, model, x0, y0, x1, y1)`
  with status in `first_read | accepted | failed | cannot_verify | document_inconsistent`.
- `totals(county, page, block_id, direction, key, value)` for printed row totals, column totals and grand totals.
- `events(ts, county, kind, payload_json)` for everything the agent did, in order. The results page replays these.
- A county is closed when every value is accepted or carries a verdict with its reason.
- Resume: on start, accepted values are kept and only open ones are worked on.

## Checks (`checks.py`, no model, no I/O)

Pure functions over the ledger's rows. They return, for each sum, its terms, the printed total, the computed total
and pass or fail. `suspects()` returns the values that sit on two failing sums whose differences agree, with the
value each would have to be.

## The investigation loop (`agent.py`)

Every value on a matrix sheet sits on two printed sums. A cell sits on its row and its column. The small total under
a column sits on that column and on the grand total (the small totals add to it). A row's printed total sits on its
row and on the grand total (the three row totals add to it). So one wrong value makes exactly two sums fail, and they
cross at it. `checks.suspects()` pairs failing sums that share one value and whose differences agree: that value is
the suspect, and the difference says what it would have to be. (The grand total is checked two ways, kinds `grand_col`
and `grand_row`. The registered-voters row of Panola sits on one sum only and cannot be located this way.)

The loop works the sums that still fail after the first read. For a located suspect it looks at the scan again: a
re-read of that one value, cut at 400 dpi or more and enlarged. A value changes only because a re-read of the scan
gave the new value; arithmetic says where to look, never what to write. What pairing cannot locate goes to the model,
which is shown the failing sums and what has been tried and returns one action as JSON:

- `reread {target, dpi, model}`: a single value, a column slice or a row strip
- `conclude {item, verdict, reason}`: `document_inconsistent` or `cannot_verify`
- `ask_policy {question_id}`: use the stored answer, or the default marked as unconfirmed
- `done {item}`

Rules that code enforces whatever the model says: at most six actions per item; re-reads climb one step at a time
(the county's reader, then `claude-sonnet-4.6`, then `claude-opus-4.6`), a step only after the one below has failed
to settle the value; the same target is never re-read twice with the same model and dpi; no value is accepted unless
its sums hold; a value the scan shows the same way twice while its two sums still fail is `document_inconsistent`
(the document disagrees with itself there) and the stored policy answer applies.
Every action and its result is an event in the ledger and a span in neatlogs.

In the report layout the same rules run in `layouts/report.py`: a row whose sum fails is read again from its own
crop at a higher resolution, one step up the ladder per failed re-read.

## The audit (`audit.py`)

1. Load the published file. Normalise labels (case, punctuation, party prefixes and suffixes, running mates,
   "Pl", "Place", "Dist", "District").
2. Pair the scan's contests and candidates with the file's. Exact and normalised matches first; what is left goes to
   the model once per county as two lists, and code checks that the answer is one-to-one, that paired contests name
   the same candidates, and that their county totals are close. Rows of a contest that could not be paired are
   listed as not compared, with the reason. A county counts as audited only when at least 95 percent of its
   published rows that carry parts were compared.
3. Compare value by value. A disagreement is classified:
   `file_row_fails_own_total`, `wrong_number`, `wrong_column`, `wrong_precinct`, `missing_row`, `extra_row`.
4. Settle it. The printed sums decide: if every printed sum through the value holds with the scan's value and fails
   with the file's, the status is `settled_against_file`, whatever a single-value re-read says. If no printed total
   can decide (a sum that holds with both values or fails with both; a published row that differs from the scan's
   row in two values, still adds up, and has no contest total over it), the status is `cannot_verify` and nothing
   is changed. If the scan's own totals disagree with each other there, `document_inconsistent`.
5. Correct only whole rows: if a row's corrected parts would not add to its corrected total, none of it is corrected
   and the row is listed. Missing and extra rows are listed, never added or removed.
6. Check the result: every printed sum is recomputed with the published file's values and with the corrected file's
   (`sums_check`), and what still fails is listed with its reason.
7. Keep the evidence: a crop, the sums with their terms, the old and the new value.
   Every finding carries `confirmed_by_person: false` until a person changes it.

## Outputs (`outputs.py`, `allrun.py`, `sitebuild.py`)

`runs/<run_id>/run.json` (start, end, commit, reader, model calls by model, tokens, cost), and per county
`county.json` (cells, totals, checks, events, verdicts), `findings.json` (findings, groups, coverage, `sums_check`),
`crops/*.png`, `corrected/<published file name>`, `changes.diff` and `report.md`. A run over all counties also
writes `summary.json` and `summary.md`; `crossfoot summarize` writes a summary that takes each county's newest
result and keeps the cost of the run that read it apart from later audits made again from the same ledger.
`crossfoot site build --run <id>|latest` builds `site/data/` (an index, one JSON per county, the page images that
carry findings, crops for the loupe) into a new folder and swaps it in only when every county was built.

## Tracing and cost (`tracing.py`, `model.py`)

`neatlogs.init(api_key=..., workflow_name="crossfoot")`; the gateway client is wrapped with `neatlogs.wrap(OpenAI(...))`.
A county's run is a `WORKFLOW` span (one trace per county in a run over all of them), the loop is an `AGENT` span,
each tool is a `TOOL` span tagged with run, county, page, block and cell. A mask replaces image bytes in a span with
the image's size and a hash, so a trace stays small enough to read back. `neatlogs.flush()` and `neatlogs.shutdown()`
run at exit. The cost meter adds up each response's token usage, and `crossfoot budget` reads the gateway's own
figure for the key (`GET <gateway root>/key/info`). The guard refuses a call that would pass the run's budget.

## The results page (`site/`)

Plain HTML, CSS and JavaScript modules, no framework and no build step, so it deploys as static files. It reads
`site/data/`. The scan is an image inside a container with CSS perspective; values, sums and marks are DOM and SVG
elements placed in the image's own coordinates, so they tilt with it and stay real, selectable elements. The page
opens on a finished run with a settled finding selected: the value ringed in a loupe that shows the scan's own
pixels, the public file's value beside the scan's, and a tape that adds the deciding sum both ways. `Replay the
audit` plays the run's recorded events. Query parameters: `?county=`, `?finding=`, `?cell=`, `?flat=1`,
`?record=1`, `?state=loading|error|empty|partial|first-run`, `?reset=1`.

## What can fail and what happens

| Dependency | Failure | What the program does |
|---|---|---|
| Model gateway | rate limit, timeout | waits and retries once, then leaves the item open for the loop |
| Run budget | reached | stops before the call, writes what it has, lists the counties not reached; `--resume` continues |
| Model answer | not valid JSON, wrong shape | one repair request, then the block or page is marked failed and can be read again with `read-page` |
| Scan or file | cannot be downloaded | one line naming the county and the URL; other counties continue |
| neatlogs | key missing or unreachable | the run continues untraced and says so on its first line |
| Position finding | no ruled lines, no ink found | marks fall back to the block or the row; the page shows the crop without a ring on the figure |
| Page build | a county fails | `site/data/` stays exactly as it was |

## Decisions

- SQLite for the ledger, because a stopped run has to resume and the page replays events in order.
- A JSON action protocol for the loop instead of provider tool-calling, so it runs unchanged on any model the gateway serves.
- The reader is chosen from a measured sample instead of "cheap first, then repair": on the dense sheet the cheap
  reader plus a repair loop cost more and closed less than one read with the stronger model
  (`docs/evidence/before-after.md`).
- The printed sums decide a finding, not a second look at one value: a crop of one figure is the weakest evidence in
  the program, two printed sums over twenty accepted values the strongest.
- CSS 3D for the stage instead of WebGL: the sheet is the only object, text has to stay crisp and selectable, and
  the page has to work with the effect off.

## Requirements this design answers

- M1 Read an image-only county scan into a ledger of values with page and position.
- M2 Accept a value only when the printed totals that cross at it agree, and report what is missing.
- M3 Look again at failing values from tighter crops, step up the model after repeated failure, stop after a bounded
  number of tries with a verdict.
- M4 Compare the closed ledger with the published file, classify each disagreement, settle it by the printed
  totals, and keep the evidence (crop, sums, old and new value).
- M5 Write a corrected file that contains only settled corrections, a report, and machine-readable findings.
- M6 Run unattended over all eight counties with state that resumes after a stop.
- M7 Trace every model call and tool call with county, page and cell; keep a running cost and stop at the budget.
- M8 A static results page that shows the scan, the crossing sums and the findings from real run output.
- M9 Evidence: a run before a change and a run after it with numbers, a recovery, a recorded coding session for
  every commit a session made, measured cost per county.
- S1 One question for a person, asked once and stored: when a document disagrees with itself, which does the
  corrected file follow?
