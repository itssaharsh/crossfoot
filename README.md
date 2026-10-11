# Crossfoot

Crossfoot is an agent that audits published data against the scanned documents it was copied from, proves each
error with the document's own printed totals, and proposes the fix.

**Status (11 October 2026):** in progress, built during neatHack. Planning came first: the contract, architecture,
UI specification and task plan in this repository were written before any code, and no code existed before the
event's start. The build log is in [hackathon.md](hackathon.md).

## Why

Open datasets transcribed from scanned official documents carry silent errors that survive manual checking. A
scanned table prints its own totals, so every cell can be tested twice: its row has to add up to the total printed
at the end of the row, and its column to the total printed under it. One wrong cell fails both sums, and the two
failing sums cross at it.

## What it works on first

The eight Texas county files (2024 general election) that the OpenElections project uses as a manually verified
answer key for grading document-reading models. The scans are certified county documents and are the source of
truth. What Crossfoot finds are transcription slips in a volunteer dataset, never anything about the results
themselves.

## How it is being built

- [ARCHITECTURE.md](ARCHITECTURE.md): the design.
- [.prod-build/contract.md](.prod-build/contract.md): what it has to do and how each part is checked.
- [UI-SPEC.md](UI-SPEC.md): the results page.
