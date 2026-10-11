# Crossfoot — neatHack build log

## Project
**Crossfoot** audits published data against the scanned documents it was copied from, proves each error with the
document's own printed totals, and proposes the fix.

The problem it addresses: open datasets transcribed from scanned official documents carry silent errors that survive
manual checking. The first target is the eight Texas county files the OpenElections project uses as a manually
verified answer key for grading document-reading models.

## Team
Team Saharsh.

## Stack
Planned, and updated as each part is actually used:
- Python 3.12 with uv; SQLite for the run ledger; Pillow and pdftoppm for page images.
- Models through the event's LiteLLM gateway (`claude-haiku` first, `claude-sonnet-4.6` only for cells that fail).
- neatlogs for traces of every model and tool call.
- Entire for a checkpoint of the coding session behind every commit.
- cfo.ai for the business plan, built from the measured cost per county.
- A static results page (plain HTML, CSS and JS).

## Build log

### 2026-10-11 (hour 26 of the window)
- Planning came first: the idea, the contract (`.prod-build/contract.md`), the architecture (`ARCHITECTURE.md`), the
  UI specification (`UI-SPEC.md`) and the task plan (`.prod-build/plan.json`) were written before any code.
- Checked before writing code, with plain arithmetic on the public files and no model: two rows in the published
  answer files fail their own totals (one in Panola County, one in San Saba County). Reproduced by
  `crossfoot filecheck --all` once task T01 lands.
- How the code is written: each task is a separate coding session started in this folder, so the checkpoint tool
  records the session behind each commit.

### 2026-10-11 - T01 scaffold, sources, rendering, ledger, checks
- Added the uv project, `fetch`, `filecheck` and `render` commands, the SQLite ledger and the pure checks
  (`row_checks`, `column_checks`, `grid_gaps`, `locate`). No model was called.
- Measured with `uv run crossfoot filecheck --all` on the downloaded files: rows whose votes differ from the sum of
  their parts: Panola 1 of 764 checked, San Saba 1 of 275, the other six 0. Rows skipped for a blank part: Cottle 0,
  Foard 4, Jones 4, Limestone 875 (all rows; checked 0), Lynn 8, Panola 19, San Saba 0, Scurry 11.
- `uv run crossfoot render --county panola --page 1` wrote a 2781x1687 px PNG at 200 dpi.
- Nothing failed. Evidence: `uv run pytest -q` passed (12 tests), recorded in `.prod-build/evidence.jsonl`.

### 2026-10-11 - T02 model client, tracing, block finding, first read of Panola
- Added `crossfoot read --county panola` and `crossfoot budget`; the gateway client (`model.py`) with a cost meter, a
  per-run budget guard, one repair request for bad JSON or a wrong column count, and one retry of a 429 or timeout;
  `tracing.py` (neatlogs, a no-op without the key); `segment.py` (blocks and column lines from the image); and the
  matrix layout reader. `uv run python -m neatlogs doctor --local --json` reported status "pass" (SDK 1.4.26).
- Block finding on the six Panola pages at 200 dpi found 7, 8, 7, 8, 8 and 5 blocks (43 in all; checked by eye on
  pages 1, 2 and 6). Only page 1 prints the precinct header, so its 19 precincts are reused for pages 2 to 6.
- First read, `runs/20261011-090307/first-read.json` (43 model calls with `claude-haiku`, no failed blocks):
  2312 cells; 941 printed totals; row sums 39 pass and 91 fail; column sums 565 pass and 203 fail; grand totals 8 pass
  and 35 fail. Metered cost (token estimate) $0.1031; gateway spend rose by $0.1084 in that run. The failing sums are
  first-read slips to be re-read in a later task; none has been looked at one by one.
- What went wrong on the way: the first block finder merged neighbouring blocks because the thick bar under the TOTAL
  column bridges the gaps; band finding now ignores the right edge. A page-2-only trial (`runs/20261011-085854`) came
  first; two full reads were run.
- Evidence: the RED run of `tests/test_budget.py`, then `uv run pytest -q` (23 tests), `uv run crossfoot budget` and
  `uv run crossfoot read --county panola`, all in `.prod-build/evidence.jsonl`.

### 2026-10-11 - T02a first read fixed from its trace: column groups at 300 dpi
- Cause: one 2,600 px crop per block was shrunk by the provider (about 600 prompt tokens a call), and a value lost
  its column (block p2-b2). The neatlogs MCP server listed the trace but could not open spans (`not_enabled`), so the
  evidence is the run files. Detail and both runs: `docs/evidence/before-after.md`.
- Change: blocks are cut into column groups (at most 1,500 px at 300 dpi), joined after reading; a column-edge off-by-one
  was found and fixed on the way (first attempt `runs/20261011-092655` lost one precinct).
- Result, `runs/20261011-094115/first-read.json`: row sums 98 pass / 32 fail (before 39 / 91), column sums 735 / 35
  (565 / 203), grand totals 25 / 18 (8 / 35); 127 calls (43), estimated cost $0.2199 ($0.1031). The goal of under 20
  failing row sums was not met.

### 2026-10-11 - T03a the investigation loop closes Panola's ledger
- Added `crossfoot close --county panola --resume <run>` (`crossfoot/agent.py`, `outputs.py`, boxes and crops in
  `layouts/matrix.py`). `claude-haiku` chooses re-reads from a text description of each failing sum; code enforces six
  actions per item, the stronger model only after two failed re-reads, and statuses from the checks. Images in neatlogs
  spans are masked.
- Found on the way: the first block of page 1 has its small totals inside the ruled box and one more row than other
  blocks; cell and total boxes were checked by eye on crops before the runs.
- Result, `runs/20261011-102700/panola/county.json` (summary field): failing sums before 32 row / 35 column / 18 grand,
  after 16 / 16 / 12. 79 cells re-read, 31 changed, 335 left cannot_verify, 1,993 of 2,328 accepted. 565 model calls,
  565,521 tokens in and 50,446 out, estimated cost $0.8601, gateway change $0.9447, 1,177.5 s. Not all sums close.
- Failed: in 19 items (cells counted, not items) the decision was rejected because it named a model other than the two allowed, and the item was stopped; some answers wrapped
  JSON in prose and needed a repair call (the parser only strips a code fence), which adds calls. Not fixed here.
- Two full runs plus a 5-item trial; task gateway spend about $2.00.

### 2026-10-11 - T03b the reader chosen by measurement; failing sums paired where they cross
- Changed: `read` samples page 1 with `claude-haiku` and reads the county with `claude-sonnet-4.6` if over a tenth of the
  sample's row sums fail; `checks.suspects` pairs failing sums that share one value and agree on its error; the loop re-reads
  those values at 400 dpi up a ladder (reader, `claude-sonnet-4.6`, `claude-opus-4.6`), names `document_inconsistent`, gives
  every failing sum a verdict, and takes a `row_strip` target; `parse_json` finds JSON inside prose or a fence; price table
  from the gateway's list.
- Measured (run `20261011-111955`, `20261011-112935`): the sample had 6 of 22 row sums failing, so the read used sonnet and
  left 3 row, 2 column, 1 + 1 grand sums failing; the close left 1, 1, 1, 0 with 19 calls in 80.0 s. Figures and the comparison
  with T03a's close are in `docs/evidence/before-after.md`.
- Failed / not solved: the registered row (+2) is one sum and cannot be paired; four re-reads agreed; one small total on page 6
  reads the same every time (`document_inconsistent`).
- Fixed: a model that wrote prose around its JSON no longer costs a repair call.
- Gateway spend for the task: $3.6806 to $4.5142.

## Demo
Not available yet.

## Known limitations and next steps
- Nothing is built yet. This section is rewritten as tasks land.

## Submission
Confirmed requirements (event page, read 11 October 2026): a public quote post on X with team, name, project, public
repository and demo link; a demo video of three minutes or less that covers neatlogs, Entire and cfo.ai; evidence in
the repository. Outstanding: all of them.
