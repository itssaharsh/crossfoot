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

### 2026-10-11 - T03c the audit against the published file, and the outputs
- Changed: `crossfoot audit --county panola [--resume RUN|latest]` reads (reader chosen by a sample), closes, matches the
  scan's contests and candidates to the file's (normalised labels first; the model once, as two lists, checked in code), looks
  at every disagreeing value on the scan again (400 dpi, `claude-sonnet-4.6`, three at a time, starts 1.1 s apart), and writes
  `findings.json`, one crop per group, `corrected/<file>`, `changes.diff`, `report.md`, `policy.json`, `run.json`.
  `verify-known` and `policy set|show` added. The 22 registered-voters cells now take their sum's verdict; the 76 cells of
  page 1's first block now have boxes (two checked by eye on a crop).
- Measured, one full run from nothing (`runs/20261011-120008/run.json`): 638.7 s, 269 model calls (haiku 19, sonnet-4.6 243,
  opus-4.6 7), metered $0.8845, gateway $4.7283 to $5.6127. 121 findings in 46 groups; 104 re-reads, none changed the ledger.
  `verify-known`: 8 of 8 expected found. Runs on the same ledger (`--resume`) cost $0.1073 and 177.7 s.
- Failed / not solved: the number of `cannot_verify` findings moved between runs (11, 14, 18) because the re-read model
  sometimes gives a third value; the corrected file changes cell values only, so missing and extra rows stay listed.
- Fixed: call-start spacing is applied at the request, not before an import; the report no longer fails on ledger verdict keys.

### 2026-10-11 - T03d the printed sums decide; the corrected file is checked against every printed sum
- Changed: a finding is settled against the file when every printed sum through the value holds with the ledger's value and
  fails with the file's, whatever a single-value re-read gave (the re-read stays as a note, `reread_disagrees`). The re-read is
  made only where the sums do not decide. A row is corrected only if its corrected votes equal its corrected parts, otherwise
  it is listed under "Could not be corrected as a whole row". After writing the corrected file every printed sum of the county
  is recomputed with the published file's values and with the corrected file's (`sums_check` in `findings.json`, a section of
  `report.md`). A `wrong_precinct` group says in one sentence what a person would do.
- Measured (`runs/20261011-122159/panola/findings.json`, resume of the ledger of `20261011-121108`): 121 findings in 46
  groups, 109 settled_against_file, 12 cannot_verify; 80 values changed; 984 printed sums in all, 949 hold with the published
  file's values, 978 with the corrected file's, 6 still fail (the registered row, and page 6's Ivy block: precinct 1, 26 and 28
  missing from the file, six rows not corrected as a whole); rows failing their own total 1 published, 0 corrected. The audit
  step now makes 8 model calls (1 matching, 7 re-reads; 97 re-reads skipped), $0.0118, 36 s (was 105 calls, $0.1073). A second
  run on the same ledger gave the same findings and corrected file; only the `seconds` figure differed. `verify-known`: 8 of 8.
- Failed / not solved: `tests/test_audit.py::test_a_reread_that_gives_a_third_value_is_cannot_verify` (a T03c test) states the
  rule this task replaces, so it fails; it is protected and was not edited (see the report). No re-read now disagrees, so "Look
  at these first" is empty for Panola.
- Gateway spend for the task: $5.7201 to $5.7436.

### 2026-10-11 - T04a the one-precinct-per-page report layout; San Saba audited end to end
- Changed: `layouts/profile.py` decides a county's layout from its first page (`matrix`, `report` with the column order found,
  or `no_printed_totals`) and rejects the decision when more than a third of the first page's row sums fail.
  `layouts/report.py` reads one page per call (200 dpi, strict JSON, one repair), stores every number as a ledger cell
  (block = the contest on that precinct, row kind = the row label, column = total, absentee, early, election_day; a contest or
  section over a page break keeps its block and precinct), checks every row (total = absentee + early voting + election day)
  and, where a page prints one, every contest total, and works each failing sum through the ladder (reader at 300 and 400 dpi,
  `claude-sonnet-4.6` at 400 and 500, `claude-opus-4.6` at 500 and 600; at most six actions; verdict `document_inconsistent` or
  `cannot_verify` with a reason). `audit.py` compares with the file's whole row; where a published row differs from the scan in
  two or more values, adds up to its own total and no contest total covers it, no printed total can tell the rows apart: the
  finding is `cannot_verify`, nothing is corrected, and the scan's row is read once more one step up the ladder. Outputs are
  those of Panola's audit; `report.md` says what the sums cannot see. `crossfoot audit --county limestone` reads nothing.
- Measured (`runs/20261011-125310/san_saba/findings.json`, a fresh full read made by `pb.py verify T04a`, the fourth full San Saba
  read; the plan's verify command runs the audit, so the brief's cap of three reads was passed by that one. The third read's
  ledger, resumed after the crop and position fixes, gave the same counts): 275 file rows compared against 21 pages; sample 0 of 19 row sums failing, reader `claude-haiku`; 1,100
  cells, all accepted after the loop (2 rows failed their own sum on the first read; 2 re-reads fixed them); 275 printed row
  sums, 274 hold with the published file's values, 275 with the corrected file's; 21 findings in 11 groups: 3 settled against
  the file (a row failing its own total, and two values of the same row), 18 cannot_verify (nine rows with two values off
  that still add up; their second reading of the scan agreed with the first in every case). San Saba prints no contest total,
  so the second sum does not exist there (0 of 142 contest blocks, a contest on one precinct). Limestone: the layout call alone, `nothing on this scan can be
  cross-checked; left as published` (`runs/20261011-123542/limestone/report.md`).
- Failed / fixed: the first full read took the county name at the page's top right for the precinct name on 7 pages (the
  prompt now says where the name is); a misspelt candidate name in one precinct split a block (names within 0.85 alike in one
  contest are joined, values untouched); the first re-read crop used a missing data root; the model's vertical positions are
  compressed and uneven (about 0.75 of the true scale, gaps between contests collapse), so row positions are snapped to the
  page's own lines of figures; an all-null re-read is not a reading (it had been counted as the same reading twice).
- Gateway spend for the task: $5.7436 to $6.6731 (four full San Saba reads, two resumes, one Limestone layout call).

### 11 October 2026, T04b: every county in one unattended command
- Changed: `crossfoot audit --all [--budget 9] [--resume <run_id>]` (`crossfoot/allrun.py`, `cli.py`) takes panola, san_saba, cottle,
  jones, lynn, scurry, foard, limestone in that order, prints one line at each county's start and end, never asks for input, and writes
  `summary.json` and `summary.md` after every county. One county failing is recorded and the next one runs; the budget stops the run
  before the next call and lists the counties not reached; `--resume` continues the same folder, skips closed counties and keeps
  accepted cells (what was spent before counts against the budget). Each county is one neatlogs WORKFLOW span named for it. Report-layout
  pages are read with up to three model calls in flight (call starts stay 1.1 s apart); the ledger is written from one thread.
  Foard's first three pages showed one fix: a row label printed with a colon ("Cast Votes:") hid the contest total row; the colon is
  now dropped when the row is stored. Foard's column order and percentage columns were handled by the page-1 layout call.
- Measured (`runs/20261011-130414/summary.json`, one full run, 1,671 s, 552 model calls, metered estimate $2.8692; the gateway's own
  figure went from $6.7693 to $9.6125): 7 counties audited, limestone left as published (nothing on its scan can be cross-checked).
  Printed sums in all 4,839; holding with the published files 4,737; holding with the corrected files 4,803. Findings 228 in all.
- Failed / not done: Foard (40 scan blocks and 71 file contests) and Scurry (3 and 3) have contests the matcher could not pair, so
  their findings are all `extra_row` and `cannot_verify`; this is a matching gap, not a measurement of those files. Not fixed here.
- Tests: `tests/test_all_run.py` (12 tests, fake model); `uv run pytest -q` 160 passed.

### 11 October 2026, T04c: every published row compared, or listed as not compared; a real stop and resume
- Changed: every county's `findings.json` and `report.md` now carry `rows_published`, `rows_compared` and `not_compared`
  (contest, rows, reason); `summary.json`/`summary.md` carry them per county and in all; a county is `audited` only when at least 95
  percent of its published rows were compared, else `partly_audited`. A row of a contest that was not paired is `not_compared`, never
  `extra_row`. Pairing rules by label shape (`layouts/report.py contest_canon`, `audit.py find_candidate`/`fuzzy`): "Vote For 1"
  dropped, United States/U.S./US, Senator/Senate, Representative/House, "President and Vice President", Precinct No./Pct,
  "46th Judicial District", Place/Pl/PI, running mates joined with or without a slash, a one-letter spelling slip inside a paired
  contest; over/under votes are compared like candidates; a contest the model pairs must name the same candidates and have close
  totals. A page that could not be read leaves its precinct's rows `not_compared`, not `extra_row`. `crossfoot audit --all --only a,b`
  and `crossfoot summarize --base <run> --use county=run` (new folder, names the run each county's figures come from) were added.
- Measured (`runs/20261011-140000/summary.md`, built from the committed run 20261011-130414 and seven single-county audits on its
  ledger, no scan read again): published rows compared 3,005 of 3,061. Foard 294 of 298 (Ballots Cast, 4 rows, not paired); Scurry 518
  of 545 (95.05 percent; Registered Voters 11 rows not paired, 16 rows of Precinct 10 not compared because scan page 18 failed to
  read in the first run); Jones 335 of 344; Lynn 634 of 650; Panola, San Saba, Cottle all rows. Foard and Scurry findings went from 2
  and 15 (all `extra_row`/`cannot_verify`, the matcher's doing) to 0 and 0. Lynn 47 findings and Jones 26 (Lynn rose from 43 because
  its over/under rows are now compared). Calls, cost and seconds of a re-audited county in that summary are those of the re-audit only.
- Stop and resume (`docs/evidence/recovery.md`): `audit --all --only san_saba,cottle --budget 0.25` stopped in Cottle (exit 2), the
  resume with `--budget 2` closed it; no accepted cell was read again. Cottle's 3 half-read pages were paid twice (7 calls).
- Failed / not done: Scurry page 18 was never read (a first-run page failure); it is still unread, and the 95 percent line is met
  only just. Not fixed here: reading it again needs a scan read.
- Gateway's own figure: $9.6386 before, $10.3736 after (change $0.7350).

### 11 October 2026, T04d: contest sums that leave out the write-in breakdown, Scurry's page 18, the final summary
- Cause seen on Jones page 1 (block 1|1): the block prints "Write-In Totals" 1, then "Write-In: Uncertified" 1, "Write-In: Peter
  Sonski/Lauren Onak" 0, "Not Assigned" 0 (rows that break the total down), then "Total Votes Cast" 1,206, "Overvotes" 0, "Undervotes" 8;
  the Statistics block prints "Ballots Cast - Total" 1,214. The contest sum added the breakdown on top of the write-in total (1,207).
- Changed (`checks.py`): three sums per contest block, each its own kind and each per column: `report_contest` (candidates + write-in
  total = contest total; breakdown rows are not terms), `report_writein` (breakdown rows = write-in total), `report_ballots` (total +
  overvotes + undervotes = the precinct's ballots cast). Breakdown rows are found from the page: the rows directly under the write-in total
  that carry the label shape "Write-In: ..." or add to the write-in total; no list of names. The ballots equation is not used for a block
  where it fails in every printed column on the same side (the contest was not on every ballot); those blocks are listed in
  `findings.json` (`audit.ballot_sums_not_used`) with the reason and named in `report.md`. A row now counts as covered by a second sum when it
  sits on any contest sum, so the rule "a row that differs in two values and adds up cannot be verified" stays for rows no second sum covers.
- Scurry page 18: the first read failed because the model put the last row of the page at y 1108 (the scale is 0 to 1000) and the
  validator refused the page. The validator now clamps up to 1250 to 1000 and still refuses anything further off. `crossfoot read-page` reads
  only the named pages into a copy of a run's ledger (new block numbers above the precinct's existing ones). Page 18 read on the second try
  (the first try, run folder removed again, failed with the same refusal; the one probe call that showed the 1108 is not kept).
- `summary.md`/`summary.json`: the column for the second sum says "row and column", "row and contest" or "row only".
- Measured, audits on existing ledgers, no scan read (figures from `runs/20261011-140556` Jones, `-140637` Lynn, `-141015` Scurry,
  `-141051` San Saba, `-141131` Cottle, `-141152` Foard, summary `runs/20261011-141300/summary.md`):
  Jones: contest sums failing 20 -> 0, cells `cannot_verify` 170 -> 0, findings 18 settled + 8 `cannot_verify` -> 26 settled, printed sums in
  all 758 -> 1,102 (all hold with the corrected file). Lynn: contest sums failing 9 after the old closing (26 on the first read) -> 0, cells
  `cannot_verify` 68 -> 0, findings 38 settled + 9 `cannot_verify` -> 47 settled, sums in all 1,427 -> 2,115. Scurry: published rows compared
  518 -> 534 of 545 (the 11 not compared are the Registered Voters rows); findings 0. San Saba, Cottle and Foard audited again with the new
  sums, findings unchanged (21, 0, 0). Published rows compared in all: 3,021 of 3,061.
- Gateway's own figure: $10.3736 before, $10.4624 after (change $0.0888). 196 tests passed before the last test was added; 197 after.
- Failed / not done: nothing in Jones or Lynn is still failing, so the 8 + 9 earlier `cannot_verify` findings were settled by the new
  sums only; they are findings against a volunteer file, not checked by a person. The ballots equation was not used for 4 Jones blocks and 1
  Lynn block.

### 11 October 2026, T05: the one-prompt baseline scored against the audit; recovery evidence
- Carried over: every sum record in `findings.json` now carries `printed_with_scan` and `printed_with_file`, the printed total as it
  stands on each side (a finding on a printed total replaces that total on the file's side). Test: for every sum and side, `holds` is
  exactly `computed == printed` on that side (`tests/test_score.py`). Runs made before this change do not have the two fields.
- `crossfoot score --findings <list> --county panola --resume latest` (`crossfoot/score.py`) puts each claimed disagreement in one
  group (settled, same_but_undecided, contradicted, other_value, not_matched) and lists the audit's settled findings the list lacks.
  `other_value` is a fifth group not in the brief: the audit has a finding there but reads neither the claim's value. No model call.
  Result in `docs/evidence/baseline/score.json` against run `20261011-135350`: of 74 claims, 73 settled, 1 same_but_undecided (the
  registered-voters figure for one precinct, whose row has no second sum), 0 contradicted, 0 other_value, 0 not_matched; 36 of the audit's
  109 settled findings are not in the list. Written up in `docs/evidence/baseline.md`; cost and time of each side are from `run.json`
  and the run files, and are different kinds of figure (api equivalent against the program's metered estimate).
- `docs/evidence/recovery.md`: three places from the committed runs (a re-read that gave the same value and went up the ladder to
  `document_inconsistent`; a value that ended `cannot_verify` after six actions; a model answer refused by the checks, Scurry page 18).
- Failed / not done: the neatlogs server did not connect in this session (HTTP 503), so no detection was created and no trace id was
  looked up; `docs/evidence/traces.md` says so. The run files hold no trace ids. No event in the runs records an answer that was not
  JSON; the third recovery case is a refused answer that parsed as JSON.
- Evidence: E0086 (red), E0088, E0090, and `uv run pytest -q` (200 passed). No model spend.

### 11 October 2026, T05b: trace ids and one detection in neatlogs
- The neatlogs server answered. `docs/evidence/traces.md` now pairs committed runs with trace ids by start time (27 distinct traces came back
  from the searches; 11 committed runs paired, others "none found" with the reason), says how to open one, and quotes spans from two
  traces (Panola run 130414; Cottle, the resume of 135519). `docs/evidence/recovery.md` has the trace ids of the runs its cases come from (case 1 and 2: none found).
- One detection created: "Crossfoot slow haiku call (over 20 s)", id `ee3ce3bc-f2cc-44f6-aecb-387ebfdb3727`, conditional, latency over 20,000 ms and model
  claude-haiku. Preview matched 1 span (a close-county planning call, not a page read). The brief's first two choices could not be written: a `reread*` span has no
  output and the repair call has no span. No code changed.
- Found: some images in the traces show as `image WxH sha256:...`, others as a `neatlogs_media` record with state `failed` ("upload unavailable:
  backend_upload_contract_unavailable"). Server refused: search with `fields`, and the `get_trace_context` options (`not_enabled`).
- Evidence: see `.prod-build/reports/T05b.md`. No model spend.

### 11 October 2026, T08: the evidence page, the page from the final run, the security pass, the cleanup
- `crossfoot site build --run <run_id>|latest` added (`crossfoot/cli.py`); `latest` is the newest run folder with a `summary.json`,
  else the newest with a `findings.json`. On a summary run the builder takes each county from the run that `summary.json` names
  (`from_run`), and the run's start and end from the summary. Built from `20261011-141300`; the page's headline line (8 counties, 7 read,
  215 disagreements, 185 settled, 0 confirmed, 5,887 / 5,766 / 5,881 printed sums) equals `runs/20261011-141300/summary.json`.
- Screenshots (Chromium already downloaded by Playwright, 1440x900 and 390x844, nine states over every county) and the axe-core results
  (11 states at both sizes, 22 runs, 0 violations) are in `qa/final/`; the scripts moved to `tools/qa/`.
- README rewritten; its two tables and the picture are written from the files by `tools/readme_tables.py` (`--check` verifies them).
  `docs/evidence/checkpoints.txt` is `entire checkpoint list` as of this task. No link is given for anything that does not exist yet.
- Security pass: no key-shaped string or email address (other than the assistant's `noreply` commit trailer) in the tree or the whole history; no
  value of `LITELLM_API_KEY` or `NEATLOGS_API_KEY` in any tracked file or in the history; no `.env` file tracked or ever committed; `data/`
  and `.env` are ignored; the only absolute home paths in tracked files are in `.prod-build/evidence.jsonl` (the machine's working
  folder). A dependency audit (`pip-audit` on the exported lock) reported no known vulnerability; it could not audit the project itself.
- Cleanup, tracked files only (what history keeps stays in history): 132.6 MB in 1,153 files before, 44.0 MB in 664 files after (with
  `qa/final/`, 2.6 MB). Removed: the run folders no document names (`20261011-134418`, `-134509`, `-134535`, `-134552`, `-135058`,
  `-140946`); `ledger.sqlite` everywhere except the three a document quotes (`20261011-090307`, `-102700`, `-135519`); crops and
  `corrected/` of runs that are earlier steps; `county.json` of earlier-step runs unless a document names or quotes it; the
  `qa/t06*`, `qa/t07*` screenshots and scripts no document links. `tools/named_paths.py --check` lists every run id and path under
  `runs/` and `qa/` that the README, this log, `docs/`, the reports and the tests name, and reports that none is missing.
  Two earlier documents were touched to keep that true: a "not committed" added to one run mention in `docs/evidence/before-after.md`, and
  `qa/axe.min.js` renamed to `tools/qa/axe.min.js` in `.prod-build/reports/T07a.md`. Files that were not tracked (the run-level
  `crops/` folders, which `.gitignore` already excluded) were left on disk.
- Removed from the code (each hit of `vulture` checked by search): `SUM_KINDS`, `FIG_NEED`, `REJECT_SHARE`, `tracing.enabled`.
  Not removed because tests use them: `grid_gaps`, `open_cells`, `to_page`, and the `make_crops` argument.
- Not measured: whether a person reading the README's first screen finds the links without scrolling.

### 11 October 2026, T08b: two defects from the fresh-clone test

- **Seen in a fresh clone** (`git clone`, then the README's commands): `crossfoot site build --run latest` ended in a Python
  traceback (the scan `data/scans/panola.pdf` was missing) after it had already deleted the files under `site/data/blocks/`; and
  the README's cost table, the summary and the page gave, for each county, the figures of the last audit made again from an
  existing ledger (Panola 8 calls, $0.0118, 41.5 s), not those of the run that read the county.
- **Page build.** It now downloads a scan that is not in `data/` (`sources.fetch`, one line per county), builds into
  `site/data.new/` and swaps it in only when every county was built; a failure removes the new folder and leaves `site/data/`
  as it was. A failed download is one line naming the county and the URL, exit code 1. `tests/test_site_build_safe.py` (red first,
  E0100) covers a build that fails half way, a missing scan, a present scan, a failed download and a build of one county.
- **Other commands.** `tests/test_cli_missing_input.py` runs `fetch`, `filecheck`, `render`, `read`, `read-page`, `close`, `audit`
  (matrix, report, `--all --resume`), `summarize`, `score`, `verify-known` and `site build` with the input missing and the
  downloader faked to fail: each prints one line and exits 1. Three ended in a traceback before: `summarize` with no base summary,
  `score` with no claims file, and `read-page` with no scan; fixed.
- **Cost and time.** `crossfoot summarize` now keeps per county `read_run` (the run that read the scan, from its own summary) and
  `audit_again` (the later audits from that ledger, added up), and the totals do the same; `summary.md` shows the reading first.
  New final summary `runs/20261011-150000` (no model calls; the committed runs are unchanged). Its totals, from the files:
  the reading run `20261011-130414` 552 calls, $2.8692, 1,671.3 s; audits made again 209 calls, $0.2888, 767.0 s. Panola: read
  168 calls, $0.7675, 474.9 s; later audits 8 calls, $0.0118, 41.5 s. Jones: read 144 calls, $0.3844, 346.3 s; later audits 122
  calls, $0.1363, 297.1 s. The audit ids inside `audit_again` are taken from the earlier summaries (`20261011-140000`,
  `20261011-141300`); some of those run folders were removed in T08, so their figures survive only in those summaries.
- **README table** is written from it by `tools/readme_tables.py` (the results table did not change). **Page**: a county's
  `model cost` and `minutes` are the reading run's plus the later audits'; the replay's label divides those seconds by the
  replay's length (Panola 17x, Jones 16x; Jones read 1x before). Measured in the browser at 1440x900: `qa/final/costs.json`
  (page text and county file side by side) and `qa/final/*-run-numbers-1440.png`.
- **Paths check.** `tools/named_paths.py --check` skips a bullet that says something was removed or renamed; `qa/final/checks.json`
  now exists (`tools/qa/check.py` wrote it). `runs/20261011-140000` is kept: this log names it and `summarize` follows it back.
- Not measured: the cost of an audit from nothing for a county other than as the one unattended run recorded it.

## Known limitations
See the Limits section of [README.md](README.md).

## Submission
Confirmed requirements (event page, read 11 October 2026): a public quote post on X with team, name, project, public
repository and demo link; a demo video of three minutes or less that covers neatlogs, Entire and cfo.ai; evidence in
the repository. Outstanding: all of them.
