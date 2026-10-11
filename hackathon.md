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

## Demo
Not available yet.

## Known limitations and next steps
- Nothing is built yet. This section is rewritten as tasks land.

## Submission
Confirmed requirements (event page, read 11 October 2026): a public quote post on X with team, name, project, public
repository and demo link; a demo video of three minutes or less that covers neatlogs, Entire and cfo.ai; evidence in
the repository. Outstanding: all of them.
