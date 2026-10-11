# Crossfoot — neatHack build log

## Project
**Crossfoot** audits published data against the scanned documents it was copied from, proves each error with the
document's own printed totals, and proposes the fix.

The problem it addresses: open datasets transcribed from scanned official documents carry silent errors that survive
manual checking. The first target is the eight Texas county files the OpenElections project uses as a manually
verified answer key for grading document-reading models.

## Team
To be filled in by the team (only names and handles the team chooses to publish).

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

## Demo
Not available yet.

## Known limitations and next steps
- Nothing is built yet. This section is rewritten as tasks land.

## Submission
Confirmed requirements (event page, read 11 October 2026): a public quote post on X with team, name, project, public
repository and demo link; a demo video of three minutes or less that covers neatlogs, Entire and cfo.ai; evidence in
the repository. Outstanding: all of them.
