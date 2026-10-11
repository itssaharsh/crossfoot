# Implementation contract - crossfoot
mode: hackathon | channel: relay (coding sessions started inside this folder; a separate session plans and verifies) | created: 2026-10-11
Upstream read: the idea brief (kept outside this repository) and UI-SPEC.md

## 1. Intent
- User and moment of use: a maintainer or contributor of a public dataset that was typed or read from scanned tables, or anyone who grades a model against it, when they want to know which cells are wrong.
- What they can do: point Crossfoot at the scans and the published files; get back every disagreement, each settled by the totals printed on the scan, with a crop that shows it, and a corrected file.
- What changes after they use it: a wrong cell is found by arithmetic on the day of the audit, where today it waits for a reader to notice it.

## 2. Scope
MUST (core product, main workflow, judged/required):
- M1 Read an image-only county scan into a ledger of cells with page and position.
- M2 Accept a value only when the printed totals that cross at it agree (row and column), and report what is missing from the grid.
- M3 Re-read failing cells from tighter crops, escalate the model after repeated failure, stop after a bounded number of tries and mark the cell "cannot verify".
- M4 Compare the closed ledger with the published file, classify each disagreement (wrong number, wrong column, wrong precinct, missing row), settle it by the printed totals, and keep the evidence (crop, sums, old and new value).
- M5 Write a corrected file that contains only settled corrections, a report, and machine-readable findings.
- M6 Run unattended over all eight counties with state that resumes after a stop.
- M7 Trace every model call and tool call in neatlogs with county, page and cell; keep a running cost and stop at the budget.
- M8 A static results page that shows the scan, the crossing sums and the findings from real run output (UI-SPEC.md).
- M9 Evidence the event asks for: a run before a change and a run after it with numbers, a failure-recovery run, checkpoints for every commit, measured cost per county.
SHOULD:
- S1 One question for a person, asked once and stored: when a document disagrees with itself, which does the corrected file follow?
- S2 The open project's own data tests run on the corrected files.
- S3 One prompt to a general coding agent on the same county, scored by the same comparison.
COULD (later; not in this build): documents with a text layer; other datasets; a hosted service.
WON'T now: any automatic write to someone else's repository; accounts; a database server; queues.

## 3. Core journeys
J1 Audit one county: `crossfoot audit --county panola` -> ledger, checks, re-reads, comparison -> findings, corrected file, report.
J2 Audit the benchmark unattended: `crossfoot audit --all` -> per-county results, resumable -> a summary.
J3 Read the results: open the results page -> see a finding on the scan with the sums that decide it -> open its evidence.

## 4. Surfaces
A command-line program; files under `runs/`; a static results page under `site/`.

## 5. States per journey
| Journey | initial | loading | success | error | empty | partial | retry | disabled | permission-denied | offline/degraded |
|---|---|---|---|---|---|---|---|---|---|---|
| J1 | county not yet audited | named steps with counts on the terminal | county closed, findings written | the failing step and its cause are printed, the ledger keeps what was read | a county with no disagreements says so | some cells "cannot verify", listed | failed cells are re-read up to the limit; a stopped run resumes | n/a: no sign-in | n/a: public inputs | scan or file cannot be downloaded: stop that county, say which URL |
| J2 | nothing run | per-county progress | summary of all counties | one county failing does not stop the others | n/a | counties skipped for budget are listed | resume continues from the ledger | n/a | n/a | the budget guard stops the run and says why |
| J3 | page opens on a finished run | skeleton of the stage while data loads | finding shown on the scan | "Couldn't load this run's data" with the file name | "No disagreements in this county" | counties without page images show crops only | reload | n/a | n/a | fonts or images fail: text and numbers still render |

## 6. Data
| Entity | Key fields | Relationships | Owner | Persistence | Source of truth | PII/retention |
|---|---|---|---|---|---|---|
| Cell | county, page, block, row kind, column, value, first_read, status, tries, bbox | belongs to a block | the run | SQLite ledger per run | the scan | none |
| Printed total | county, page, block, direction, value | checks a row or a column | the run | ledger | the scan | none |
| Finding | county, contest, candidate, precinct, kind, file value, scan value, status, evidence paths, confirmed_by_person | refers to cells | the run | findings.json | the scan's printed totals | none |
| Run | id, started, finished, commit, model calls, tokens, cost, cells | has counties | the run | run.json | the program | none |
| Policy answer | question id, answer, answered_by, date | applies to all counties | a person | policy.json | a person | none |

## 7. Interfaces
| Interface | Purpose | Contract file | Failure mode | Fallback |
|---|---|---|---|---|
| Model gateway (OpenAI-compatible) | read images, choose actions | crossfoot/model.py | 429, timeout, bad JSON, budget reached | wait and retry once; re-ask for JSON once; then mark the cell "cannot verify"; stop cleanly at the budget |
| neatlogs SDK | traces, cost | crossfoot/tracing.py | key missing or network down | the run continues untraced and says so on the first line |
| Public scans and files (GitHub raw) | inputs | crossfoot/sources.py | 404 or network | stop that county with the URL |
| pdftoppm | render pages | crossfoot/render.py | not installed | say what to install and stop |

## 8. Constraints
- Budget: $20 of model spend for the whole team; stop at $15. 60 requests a minute.
- Deadline: code stops Monday 12 October 2026 at 12:30 IST unless the organisers say otherwise.
- Required tools (event page, read 11 October 2026): "Your project must use neatlogs, Entire and cfo.ai. Use neatlogs and Entire to build and improve your agent, and cfo.ai to plan its business."
- Judging criteria (event page, read 11 October 2026): "The agent" 30%, "Use of neatlogs, Entire and cfo.ai" 25%, "Demo video" 20%, "Building in public" 15%, "Usefulness and originality" 10%.
- Privacy: no personal data is processed. The inputs are public documents.
- Performance (results page): first paint under 2.5 s on a laptop; works with scripts' 3D effects off.

## 9. Acceptance criteria
AC-1: WHEN `crossfoot audit --county panola` finishes THE SYSTEM SHALL report every cell as accepted, failed or cannot-verify, and no cell is accepted unless its row check and column check pass. Verify: `uv run pytest -q tests/test_checks.py` and the run's `county.json`. Priority: must
AC-2: WHEN the Panola audit finishes THE SYSTEM SHALL list, without being told where they are, the published file's row that fails its own total and the two candidates whose rows disagree with the scan's printed totals. Verify: `uv run crossfoot verify-known --county panola`. Priority: must
AC-3: WHEN a re-read of a failing cell does not make its sums hold within the limit THE SYSTEM SHALL mark it cannot-verify and leave the published value alone. Verify: `uv run pytest -q tests/test_agent.py`. Priority: must
AC-4: WHEN a run is stopped and started again THE SYSTEM SHALL continue from the ledger without re-reading accepted cells. Verify: `uv run pytest -q tests/test_resume.py`. Priority: must
AC-5: WHEN spend reaches the budget THE SYSTEM SHALL stop before the next model call and say so. Verify: `uv run pytest -q tests/test_budget.py`. Priority: must
AC-6: WHEN the results page opens THE SYSTEM SHALL show a finished run with a finding drawn on the scan and its sums, with no input, at 1440x900 and 390x844. Verify: the first-screen measurement recorded in the ledger. Priority: must
AC-7: WHEN a correction is written THE SYSTEM SHALL include it only if the printed totals agree with the new value and disagree with the old one. Verify: `uv run pytest -q tests/test_audit.py`. Priority: must

## 10. Assumptions
A-1 [reversible]: block and column positions on ruled sheets can be found from the image itself; if not, the model supplies approximate positions - validate on Panola pages 1 to 6.
A-2 [reversible, disproved on 11 October 2026]: `claude-haiku` reads block crops well enough for a first pass. Measured on Panola: it left 85 of 943 printed sums failing, against 6 of 942 for `claude-sonnet-4.6` on the same crops. Replaced by: the reader is chosen per county from a measured sample of its first page (ARCHITECTURE.md, Reading).
A-3 [safe]: the scans and published files may be downloaded and quoted with attribution; the project publishes them openly.
A-4 [reversible]: the default answer to the policy question is "follow the cells as printed and list the printed total as inconsistent", recorded as a default until a person confirms it.

## 11. Demo script
1. The certified scan and the public file made from it, side by side.
2. One county audited: cells fill the ledger, one fails two sums and is re-read, the county closes.
3. The public file laid beside it: the cells that differ, each with its crop and the sums that decide.
4. The first failure that really happened, found in the traces, fixed, and the run after it with the numbers.
5. The checkpoints behind the commits; the business plan built from the measured cost per county.
6. Limits: what the sums cannot see; what a person still has to confirm.

## 12. Event and judged path
- Window: start 2026-10-10T07:00:00Z (Sat 10 Oct 12:30 IST); 48-hour mark 2026-10-12T07:00:00Z (Mon 12 Oct 12:30 IST), used here as the code stop; submissions 2026-10-12 from 19:00 IST with a "planned close around 11:55 PM IST". Source: https://neatlogs.com/hackathon, read 11 October 2026 06:15 UTC. Rule on earlier work, verbatim: "You can plan your idea in advance, but all code must be written between the start on October 10 and the deadline on October 12. Finished or half-built projects cannot be brought into the event."
- How an entry is judged: one project per team is submitted as a public quote post on X with team, name, project, public repository and demo link; a demo video of three minutes or less and supporting evidence in the repository. Minutes per project and whether anyone runs the build: not published.
- Criteria: as quoted in section 8, from the event page.
- Criteria coverage: The agent - one county audited from scan to closed with re-reads and the public file audited (met by plan). Use of the three tools - traces with a before and after, checkpoints for every commit, a plan from measured cost (met by plan). Demo video - the run, then the three tools (partial until recorded). Building in public - posts from the second day only (partial). Usefulness and originality - errors found in a public, manually verified file, proved by the scan's own totals (partial until a person confirms each).
- Capability coverage: neatlogs traces - every model and tool call of a run, linked from the README; Entire checkpoints - one per commit, listed in the README; cfo.ai business plan - built from the measured cost per county, linked from the README.
- Main result: a number with crops - the cells where the public file and the scan disagree, each shown on the scan with the sums that decide it, on Panola County's certified 2024 canvass (a public document we did not author). The staged failure the product holds through: a cell whose sums cannot be made to hold is marked "cannot verify" and the published value is left alone.
- Promise coverage: "Cross" and "foot" - the row sum and the column sum drawn across the scan and crossing at one cell on the first screen.
- Before the clock: the idea and this plan were written before the first commit; no code existed. The README says so.
