# Architecture

Crossfoot is one Python package with a command-line entry point, files on disk, and a static results page. No
server, no database server, no queue. Each part below names the requirement in `.prod-build/contract.md` that forces it.

## The idea in one paragraph

A scanned table prints its own totals. If every cell is read into a ledger, each value can be tested twice: its
row has to add up to the total printed at the end of the row, and its column has to add up to the total printed
under the column. One wrong cell fails both sums, and the two failing sums cross at it. Crossfoot reads the scan
with a vision model, accepts a value only when both sums hold, re-reads the cells where they do not, and then uses
the closed ledger to audit a published file that was copied from the same scan.

## Layout of the repository

```
crossfoot/
  cli.py        command-line entry point (argparse): audit, read, verify-known, budget, site
  sources.py    the eight benchmark counties: scan URL, published-file URL, cache under data/ (M1, M4)
  render.py     pdftoppm wrapper: page -> PNG at a dpi; crops with Pillow (M1, M3)
  segment.py    finds blocks and column lines on a ruled page from the image itself (M1)
  model.py      gateway client, JSON parsing with one repair attempt, cost meter, budget guard, rate limit (M7)
  tracing.py    neatlogs setup and span helpers; a no-op when the key is absent (M7)
  layouts/
    matrix.py   precincts as columns, three rows per candidate, totals both ways (Panola)
    report.py   one precinct per page, one row per candidate with its own total (San Saba, Cottle and others)
    profile.py  decides which layout a county uses and tests the decision on the first pages (M1)
  ledger.py     SQLite ledger: cells, printed totals, checks, events; resume (M2, M6)
  checks.py     row sums, column sums, grand totals, grid completeness; pure functions (M2)
  agent.py      the investigation loop: a model chooses the next action for each open item; code enforces the rules (M3)
  audit.py      compares the closed ledger with the published file; classifies and settles disagreements (M4)
  outputs.py    county.json, findings.json, corrected CSV, report.md, the site's data bundle (M5, M8)
  policy.py     the one stored answer and its default (S1)
tests/          unit tests for checks, ledger, audit, budget, resume, agent rules; no network
site/           the static results page (plain HTML, CSS and JS; no build step) (M8)
runs/           one folder per run; small results are committed, caches are not
data/           downloaded scans and files; never committed
```

## Inputs

Eight Texas counties from the OpenElections project's 2024 general election benchmark. All eight scans are
image-only PDFs (no text layer): Cottle 12 pages, Foard 16, Jones 20, Limestone 42, Lynn 37, Panola 6, San Saba 21,
Scurry 38.

- Scan: `https://raw.githubusercontent.com/openelections/openelections-sources-tx/master/2024/general/2024%20<County>%20County%2C%20TX%20precinct-level%20results.pdf`
- Published file: `https://raw.githubusercontent.com/openelections/openelections-data-tx/master/2024/counties/20241105__tx__general__<county>__precinct.csv`
  with columns `county, precinct, office, district, party, candidate, votes, absentee, early_voting, election_day`.

## Two layouts

**Matrix (Panola).** A landscape canvass sheet. The header row lists the precincts as columns and ends in a TOTAL
column. Each candidate is a block: a label at the left, three ruled rows (EARLY, ABSENTEE, PRECINCT), a row of
small printed totals under the columns, and a grand total under the TOTAL column. In the published file EARLY is
`early_voting`, ABSENTEE is `absentee`, PRECINCT is `election_day`, and the small total is `votes`.
Checks per block: for each precinct, early + absentee + precinct = the small total; for each row, the precinct cells
add to the row's TOTAL; the small totals add to the grand total.

**Report (San Saba, Cottle and others).** One precinct per page or section. Each candidate is a row with four
numbers: TOTAL, Absentee, Early Voting, Election Day. Checks per row: total = absentee + early + election day.
Where the page prints a total for the contest, the candidates' totals have to add to it.

`layouts/profile.py` asks the model which layout the first page shows and what the column order is, then reads the
first page under that layout and runs the checks. A profile under which more than a third of the sums fail is
rejected; the other layout is tried; if neither holds the county is reported as "layout not supported" and left alone.

## Reading

1. `render.py` renders a page at 200 dpi.
2. Matrix: `segment.py` finds the blocks as bands of ink separated by blank bands, and the column lines inside a
   block as columns of dark pixels that run the height of the ruled rows. Report: the page is read whole.
3. `model.py` sends one crop per block (matrix) or one page (report) to `claude-haiku` and asks for strict JSON.
   Every value comes back with the block, row kind and column it belongs to. The answer is validated (right number
   of columns, integers only); one repair request is allowed.
4. The values go into the ledger as `first_read`, with the page and the pixel box of each cell where it is known.

## The ledger (`ledger.py`, SQLite, one file per run)

- `cells(county, page, block_id, contest, candidate, row_kind, column, value, first_read, status, tries, model, x0, y0, x1, y1)`
  with status in `first_read | accepted | failed | cannot_verify`.
- `totals(county, page, block_id, direction, key, value)` for printed row totals, column totals and grand totals.
- `events(ts, county, kind, payload_json)` for everything the agent did, in order. The results page replays these.
- A county is `closed` when every sum holds and the grid has no gap, or every open cell is `cannot_verify`.
- Resume: on start, accepted cells are kept and only open ones are worked on.

## Checks (`checks.py`, no model, no I/O)

Pure functions over the ledger's rows. They return, for each sum, its terms, the printed total, the computed total
and pass or fail, and for each failing cell the sums that cross at it. `locate()` returns the cells that sit on a
failing row sum and a failing column sum at once. Grid completeness lists every precinct, contest and candidate that
is present in one place and absent in another.

## The investigation loop (`agent.py`)

This is the agent. Its work list is every cell on a failing sum after the first read, and later every
disagreement with the published file. For each item the model is shown the item, what has been tried, and the
checks' output, and returns one action as JSON:

- `reread {target, dpi, model}`: crop a cell, a column slice or a block half at a higher dpi and read it again
- `accept {cell, value}`: code accepts only if the row and column sums then hold; otherwise it answers with the sums that fail
- `classify {finding, kind}`: name the kind of disagreement with the published file
- `ask_policy {question_id}`: use the stored answer, or the default marked as unconfirmed
- `cannot_verify {item, reason}`: stop work on the item and leave the published value alone
- `done {item}`

Rules that code enforces whatever the model says: at most six actions per item; the stronger model
(`claude-sonnet-4.6`) only after two failed re-reads with `claude-haiku`; no value is accepted without passing
sums; a correction is written only when the printed totals agree with the new value and disagree with the old one.
Every action and its result is an event in the ledger and a span in neatlogs.

## The audit (`audit.py`)

1. Load the published file. Normalise labels (case, punctuation, party suffixes, running mates).
2. Map the scan's contests and candidates to the file's. Exact and normalised matches first; what is left goes to
   the model once per county as two lists, and code checks that the answer is one-to-one and that mapped pairs have
   close county totals.
3. Compare cell by cell. A disagreement is classified:
   `file_row_fails_own_total`, `wrong_number`, `wrong_column`, `wrong_precinct`, `missing_row`, `extra_row`.
4. Settle it. If the scan's value passes both of its sums and the file's value breaks a printed total, the status is
   `settled_against_file`. If no printed total can decide, `cannot_verify`. If the scan's own totals disagree with
   its cells, `document_inconsistent`, and the stored policy answer applies.
5. Keep the evidence: the crop of the block, the sums with their terms, the old and the new value.
   Every finding carries `confirmed_by_person: false` until a person changes it.

## Outputs (`outputs.py`)

`runs/<run_id>/run.json` (start, end, commit, model calls, tokens, cost, counties), and per county
`county.json` (cells, totals, checks, events), `findings.json`, `crops/*.png`, `corrected/<published file name>`,
`changes.diff` and `report.md`. `crossfoot site build --run <id>` copies what the results page needs into
`site/data/`: `index.json`, one JSON per county, the page images that carry findings (at most 1600 px wide) and the crops.

## Tracing and cost (`tracing.py`, `model.py`)

`neatlogs.init(api_key=..., workflow_name="crossfoot")`; the gateway client is wrapped with `neatlogs.wrap(OpenAI(...))`.
A county run is a `WORKFLOW` span, the loop is an `AGENT` span, each tool is a `TOOL` span
(`@neatlogs.span(kind="TOOL", tool_name=...)`), tagged with run, county, page, block and cell. `neatlogs.flush()` and
`neatlogs.shutdown()` run at exit. The cost meter adds up each response's token usage, and `crossfoot budget` reads
the gateway's own figure for the key (`GET <gateway root>/key/info`, where the root is `LITELLM_BASE_URL` without
`/v1`). The guard refuses a call that would pass the limit.

## The results page (`site/`)

Plain HTML, CSS and JavaScript modules, no framework and no build step, so it deploys as static files. It reads
`site/data/`. The scan is an image inside a container with CSS perspective; cells, sums and marks are DOM and SVG
elements placed in the image's own coordinates, so they tilt with it and stay real, selectable elements.
`UI-SPEC.md` is the specification.

## What can fail and what happens

| Dependency | Failure | What the program does |
|---|---|---|
| Model gateway | rate limit, timeout | waits and retries once, then marks the item cannot-verify |
| Model gateway | budget reached | stops before the call, writes what it has, exits with a clear message |
| Model answer | not valid JSON, wrong column count | one repair request, then the block is marked failed and goes to the loop |
| Scan or file | cannot be downloaded | that county stops with the URL; other counties continue |
| neatlogs | key missing or unreachable | the run continues untraced and says so on its first line |
| Position finding | no ruled lines | crops fall back to whole blocks and the page shows crops without cell marks |

## Decisions

- SQLite for the ledger, because a stopped run has to resume and the page replays events in order.
- A JSON action protocol for the loop instead of provider tool-calling, so it runs unchanged on any model the gateway serves.
- CSS 3D for the stage instead of WebGL: the sheet is the only object, text has to stay crisp and selectable, and
  the page has to work with the effect off.
