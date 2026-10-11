---
name: Crossfoot
scope: sprint
one_line: "Crossfoot audits published election data against the certified scans."
ambition: "L2: the hero object is a physical sheet whose rows and columns carry the proof, so the sheet is staged in depth and the two sums are drawn across it; everything else is L1"
registers: { stage: expressive, findings: serious, numbers: productive, system: system }
direction: "derived: stage = desk blotter green-black · sheet = the scan itself · ink = paper white · marks = an auditor's two-ended checking pencil (red for a sum that fails, blue for a sum that holds) · display and body = Public Sans (the typeface of US government forms) · figures = Courier Prime (adding-machine tape). Candidates considered for display: Public Sans, Libre Franklin, Courier Prime"
personality: mechanical
dials: { variance: 5, motion: 5, density: 6 }
stack: { page: "plain HTML, CSS and JS modules, no build step: it has to deploy as static files and survive with effects off", fonts: "Google Fonts (Public Sans, Courier Prime) with system fallbacks" }
archetype: "spatial scene + HUD (l), in the DOM"
viewports: [320x640, 390x844, 1024x768, 1440x900]
signature: { interaction: "Selecting a finding draws its row sum and its column sum across the sheet until they cross at the cell", visual: "an adding-machine tape that prints the sum, line by line, ending in the printed total" }
wow: "select a finding or press Replay -> the two sums draw across the scan and cross at one cell -> the tape prints the arithmetic and stops on the total that does not match -> the cell keeps its pencil ring and the settled count goes up by one -> the finding opens its crop and its evidence file"
demo: { data: "site/data/ built from a real run", flag: "none needed: the page opens on a finished run", state_param: "?state=", record: "?record=1", flat: "?flat=1", reset: "alt+shift+r", replay: "alt+shift+p" }
live_vs_simulated: [ "every number, cell, sum and crop: from a recorded real run", "the replay: an in-page replay of that run's recorded events at a labelled speed", "nothing is simulated" ]
deviations:
  - "Dark page by default: the sheet is white paper and has to be the brightest thing on screen, on a laptop, a projector and in compressed video."
  - "Depth on a judged first screen: the tilted sheet is the data itself, not decoration; a Lay flat control and ?flat=1 remove it."
---

## 0. Brief and context profile

- **One line:** Crossfoot audits published election data against the certified scans.
- **User and moment:** a dataset maintainer or data reporter at a desk, checking one county's published file against its scan; a judge on a laptop with a few minutes.
- **Promise:** "Cross" and "foot" are an accountant's words for adding a table across and down. The first screen shows a row sum and a column sum crossing at one cell.
- **Primary action:** Replay the audit.
- **Hero object:** the scanned canvass sheet.
- **Product moment:** two sums cross at a cell and the tape shows which number is wrong.
- **Demo moment:** the same thing, on a cell where the public file and the scan differ.
- **Differentiator:** nothing on screen is the model's opinion. Each finding shows the printed total that decides it and a crop anyone can check.
- **Artifact:** the corrected file and the findings list with crops.
- **World inventory:** the ruled canvass sheet; the county's certification line; an auditor's red and blue checking pencil; adding-machine tape with its total line; a desk blotter.
- **Moving truth:** none while idle. The replay moves only when started.
- **Judging:** see `.prod-build/contract.md` section 12. No UI prize is listed.
- **Budget:** about four hours of UI work.

| Factor | This product | What it changes |
|---|---|---|
| Task frequency | occasional | guidance on screen, one expressive moment |
| Data density | a sheet of several hundred cells, a short list of findings | the sheet carries the density; the panel stays sparse |
| Stakes | public election data | calm, high contrast, exact wording, no celebration |
| Audience | general, new to the domain | plain words; the arithmetic is shown, not described |
| Use scene | desk, projector, compressed video | dark stage, large figures, nothing hover-only |
| Emotional target | exact | every element is tested against it |
| Personality | an auditor's desk | mechanical motion, hard stops |

## 1. Judge tests

**Five seconds.** A stranger sees a scanned results sheet, two lines crossing at one cell, and beside it "Public file: 0 · Scan: 1" with a sum that does not match. They can say: it checks a public file against the scan and found a wrong number.

**Thirty seconds.** Replay runs one county: cells fill, one fails two sums and is re-read, the county closes, the differing cells appear. The crop and the evidence file are one click away. Run numbers (cells audited, right on first read, after re-reads, cost) come from the run file.

**Demo-critical screen:** one, the audit view. **Three stills:** the crossing on the sheet; the tape beside the two values; the findings list with the run numbers.

## 2. Demo script

0:00 the audit view on a finished run of Panola County, with one finding already drawn on the sheet. 0:05 Replay at a labelled speed. 0:25 pick a second finding; the sheet turns to it. 0:35 open its crop. 0:45 the run numbers and the limits line. Recording mode: `?record=1` (the judge card is hidden, toasts dock under the panel, headings hold at 1.6x zoom).

## 3. Screen inventory

| id | route | why it exists | primary action | states |
|---|---|---|---|---|
| S1 | `/` | the audit view: the scan, the sums, the findings, the run numbers | Replay the audit | ideal, loading, error, empty (no disagreements), partial (crops only), first-run (no data built) |

No other screens. No sign-in, no settings, no landing page.

## 4. Flow

S1(finished run) --Replay--> S1(replaying; Pause) --end--> S1(finished) ; S1 --select finding--> S1(sheet turns, sums draw, tape prints) ; S1 --Open crop--> dialog(crop + sums) ; S1 --county tab--> S1(other county).

## 5. The audit view

Grid at 1440: top bar 52px; below it two regions, stage (flex, min 760px) and panel (420px), 24px gutter, 24px page padding. At 1024: panel 360px. Under 900: one column, stage first (56vh, sheet laid flat), panel after, the primary action sticky at the bottom with safe-area padding.

| Element | Tier | Register | Levers (grayscale first) | States | Transition |
|---|---|---|---|---|---|
| The sheet (scan page image) with marks drawn on it | primary | expressive | the largest thing on screen; the only white surface; tilted in depth (`perspective: 1800px`, `rotateX(34deg) rotateZ(-3deg)`), soft contact shadow on the blotter; marks are SVG in the image's coordinates | loading: a scan line crosses the sheet while "Loading run…" counts files · error: the sheet area says which file failed · partial: no page image, the crop is shown flat instead | on select, the sheet eases so the cell sits at the optical centre (600ms) |
| Row sum and column sum lines | primary (part of the sheet) | expressive | 6px bands at 35% opacity over the row and the column, pencil blue when the sum holds, pencil red when it fails; a ring on the cell where they cross | reduced motion: drawn at once | draw-on from the label to the total, 350ms each, row then column |
| The tape | secondary | serious | a white strip, Courier Prime, right-aligned figures, one term per line, a rule, the computed total, then the printed total with a tick or a cross and the word "matches" or "does not match" | long sums show the first three terms, "… 14 more", the last term | lines print one by one, 60ms steps; instant under reduced motion |
| Finding card: "Public file" and "Scan" values | secondary | serious | two large figures side by side with their labels above; the kind of slip in words under them; status line under that | unconfirmed: "Read from the scan by the agent. A person has not confirmed this yet." · cannot verify: "No printed total can decide this. Left as published." | figures roll to the new finding's values (200ms) |
| Findings list | secondary | productive | rows, not cards: precinct, row label, file value, scan value, kind as a word with a leading glyph; the selected row has a 2px left bar in ink | empty: "No disagreements in this county." | none |
| "Replay the audit" | interactive (the one filled button) | system | paper-white fill, dark label, at the bottom-left of the stage; becomes "Pause replay" while running | blocked when no events were recorded, with the reason under it | none (keyboard trigger does not animate) |
| Stage controls: Lay flat, page back and forward, speed label | interactive | system | quiet text buttons beside the primary | Lay flat is on by default under 900px and under reduced motion | sheet eases flat (400ms) |
| County tabs | tertiary | system | a segmented control in the top bar listing only counties in the run | one county: no control | none |
| Run numbers | tertiary | productive | one quiet row under the list: cells audited · right on first read · right after re-reads · re-read · disagreements · settled · cost · minutes; tabular figures; each with its unit | a number that the run did not record is left out, never shown as 0 | figures count to their value once on load (400ms) |
| How to judge this in 90 seconds | tertiary | system | a small numbered list at the bottom of the panel: 1 Replay the audit 2 Pick a finding 3 Open its crop and add it up yourself | hidden under `?record=1` | none |
| Limits and sources line | tertiary | system | one line in the footer, 13px | always present | none |

**First ten seconds with no input:** the page opens on the finished run, the first settled finding selected, its sums already drawn, the tape already printed. Nothing is hidden behind a click.

## 7. Choreography

| id | trigger | from -> to | what moves | pattern | timing |
|---|---|---|---|---|---|
| T-01 | select a finding | list -> sheet | the sheet turns so the cell is centred; the row line draws, then the column line; the ring closes | draw-on onto its cause | turn 600ms ease-in-out; lines 350ms each; ring 180ms |
| T-02 | T-01 ends | sheet -> tape | the tape prints its lines; the total line lands last | stepped print | 60ms a line, at most 900ms |
| T-03 | Replay | finished -> replaying | recorded events play in order: cells appear, failing sums show red, a re-read cell flips, sums turn blue | in-page replay, labelled "Replay · run of <date>, at <n>x" | 40 events a second by default |
| T-04 | Lay flat | tilted -> flat | the sheet's rotation eases to zero | same thing, different view | 400ms |

Under `prefers-reduced-motion: reduce`: no turn, no draw-on, no stepped print; states change with a 150ms fade. Replay still steps through events, with a visible Pause.

## 9. Copy deck

- Top bar: `Crossfoot` · `audits public election data against the certified scans`
- Primary: `Replay the audit` / `Pause replay`
- Controls: `Lay flat` / `Tilt sheet` · `Previous page` · `Next page`
- Finding card labels: `Public file` · `Scan` · `Kind of slip` · `Decided by`
- Kinds: `wrong number` · `wrong column` · `wrong precinct` · `missing row` · `row fails its own total`
- Statuses: `Settled by the printed totals` · `Read from the scan by the agent. A person has not confirmed this yet.` · `No printed total can decide this. Left as published.` · `The document disagrees with itself. Listed for a person.`
- Tape: `adds to` · `printed total` · `matches` · `does not match`
- Buttons on the card: `Open crop` · `Evidence file`
- Run numbers: `cells audited` · `right on first read` · `right after re-reads` · `re-read` · `disagreements` · `settled` · `model cost` · `minutes`
- Replay label: `Replay · run of {date} · {n}x`
- Empty: `No disagreements in this county.`
- Error: `Couldn't load {file}. Reload, or open the repository's runs folder.`
- First-run: `No run has been built into this page yet. Run crossfoot site build.`
- Footer: `These are transcription slips in a volunteer dataset. Each county's certified scan is the source of truth. Sources: the OpenElections sources and data repositories for the 2024 Texas general election.` (with links)
- Judge list: `Judge this in 90 seconds` · `1 Replay the audit` · `2 Pick a finding` · `3 Open its crop and add it up yourself`

## 10. Brand

Mark: on a 48 grid, a horizontal stroke and a vertical stroke crossing, with a ring where they cross; two flat colours (pencil blue, pencil red) on the dark stage, ink on light. Wordmark: `Crossfoot` in Public Sans 800, -0.03em. Favicon: the mark as `favicon.svg`.

## 11. Real-product checks

Value: it shows which cells to fix and why. Clarity: the first screen is a finished run. Trust: every finding shows the printed total and a crop; nothing shows a confidence percentage. Feedback: selection responds in under 100ms. Failure: a missing file names itself and the rest of the page still renders. 10x data: page images are loaded one at a time and the list is virtualised above 200 rows. Maintainability: no dependencies.

## 12. Don'ts

No gradients, glows or glass. No confetti, no sounds. No percentages of confidence. No candidate, party or official mentioned outside the scan's own row labels. No number that is not in the run's files. Nothing that moves without a visible Pause.

## 13. Acceptance

Sprint gates: cut pass; the anti-slop grep; axe with zero violations at 1440; keyboard path through Replay, list and crop; reflow at 320; the first screen measured at 1440x900 and 390x844 with the action and a finding visible and no input.

## 14. Tokens

```css
:root{
  color-scheme: dark;
  --ff-display:"Public Sans",system-ui,sans-serif; --ff-body:"Public Sans",system-ui,sans-serif; --ff-mono:"Courier Prime",ui-monospace,monospace;
  --canvas:#14211B; --surface-1:#1B2B24; --surface-2:#243830; --surface-sunken:#0F1A15;
  --line:#34493F; --line-input:#6F867A;
  --ink:#EEF2EC; --ink-muted:#A9B8AE;
  --accent:#F4F1E8; --accent-ink:#14211B; --focus:#F4F1E8;
  --sheet:#FBFAF5; --sheet-ink:#17181A;
  --data-fails:#F0624D; --data-holds:#7FAEFF;
  --danger:#F0624D; --success:#7FAEFF; --warning:#E9B84A;
  --r-sm:2px; --r-md:4px; --r-lg:8px;
  --ease-out:cubic-bezier(.23,1,.32,1); --ease-in-out:cubic-bezier(.77,0,.175,1);
  --dur-press:120ms; --dur-hover:150ms; --dur-line:350ms; --dur-turn:600ms;
}
```
Every pair of text and background above has to be checked for 4.5:1 before it ships; adjust the muted ink first if a pair fails.
