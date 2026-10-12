# crossfoot

## What this project is
Crossfoot is an agent that audits published data against the scanned documents it was copied from, proves each
error with the document's own printed totals, and proposes the fix. Built during neatHack (10 to 12 October 2026).
Read `README.md` and `ARCHITECTURE.md` before changing anything.

## Rules that always apply
- **This repository is public and so are the coding sessions.** Session transcripts are stored with the repository.
  Never write a key, token, password, email address or other personal detail into any file, commit message or
  command output. Never print, echo, log or `cat` environment values; refer to variables by name only.
- Keys arrive as environment variables: `LITELLM_API_KEY`, `LITELLM_BASE_URL`, `NEATLOGS_API_KEY`. Read them with
  `os.environ`. There is no `.env` file in this repository and none may be created.
- Do not push, open issues or pull requests anywhere, deploy, sign up for anything or post anywhere. Commit only.
- Do not disable or edit the hooks in `.claude/settings.json` or the files in `.entire/`.
- **No invented numbers.** A figure goes into `README.md`, `hackathon.md`, the site or a report only after a run
  produced it, and the file that holds it is named. Sample or synthetic material is labelled as such where it shows.
- **Election material.** The counties' certified scans are the source of truth. What this tool finds are
  transcription slips in a volunteer dataset. Never write anything about the results themselves, and never comment
  on a party, candidate or official. The project and the counties are named only as public sources, with links;
  never say or imply that either has seen or approved this.
- **Model budget.** The model gateway key has a hard $20 budget shared by the whole team. Development runs use
  Panola County only unless the brief says otherwise. Check spend with `uv run crossfoot budget` before and after
  any run, never start a run that could pass $18 total (the line was $15 until 12 October 2026, the event's last
  day), and never loop on a failing call.
- The gateway allows 60 requests a minute: keep model calls under one a second.

## How to work here
- Python 3.12 with `uv`. Run things as `uv run ...`. Tests: `uv run pytest -q` (no network, no model calls).
- One task per session, from a written brief. Finish with a dated entry in the build log in `hackathon.md` (what
  changed, what failed, what was fixed, the evidence) and commit everything as `<task>: <outcome>`.
- Plain words in every file a person reads. Say what was measured and what was not.

<!-- entire-graph:begin -->
This repo has the entire-graph code graph installed. Before exploring code with
grep/find/whole-file reads, read .entire/graph-agent.md — resolution-first guidance
for using graph retrieval, focused source inspection, and verification.
@.entire/graph-agent.md
<!-- entire-graph:end -->
