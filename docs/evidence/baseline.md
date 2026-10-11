# One prompt to a general coding agent, scored against the audit (Panola County)

Figures come from `docs/evidence/baseline/score.json` (written by
`uv run crossfoot score --findings docs/evidence/baseline/findings.json --county panola --resume latest`),
`docs/evidence/baseline/run.json`, and the audit's run files `runs/20261011-135350/` and `runs/20261011-130414/`.
Every statement the baseline made about the scan is that agent's own reading, quoted as such; nobody has checked it by eye, and
nothing here is a statement about a county's certified results. These are differences between a volunteer dataset and the
printed scan. The county's scan and the volunteer file are public sources and neither has seen or approved this.

## What the baseline was given and how it was run

From `baseline/run.json`: one prompt (`baseline/prompt.txt`) to Claude Code, headless (`claude -p`), model `claude-sonnet-5-5`, in an
empty folder holding only the Panola scan (`scan.pdf`) and the published file (`published.csv`). Tools allowed: Bash, Read, Write, Edit,
Glob, Grep, TodoWrite; web tools and curl/wget disallowed. Started 2026-10-11T09:28:04Z. 79 turns (30 Bash, 25 Read calls),
411 seconds, cost 1.5254 US dollars "api equivalent" (the run file's own label; not a gateway-metered figure). No follow-up prompt.
It listed 74 findings (`findings.json`) and wrote a summary (`summary.md`).

## How it was scored

`crossfoot score` matches each claimed disagreement (office, candidate, precinct, part, file value, scan value) to the audit's
newest Panola findings (run `20261011-135350`) with the audit's own label matching (`audit.nk`, `audit.candidate_key`), then puts it in
one group. Nothing in the audit was changed to suit the list; the only change to `audit.py` in this task adds the printed total used on
each side to the sum records. No model was called.

## The two sides

| | One prompt (baseline) | Crossfoot audit |
|---|---|---|
| Findings listed | 74 | 121 (46 groups) |
| Settled by printed totals | 73 | 109 |
| Contradicted (the audit's accepted value is the file's) | 0 | not applicable: the baseline's list disputes none of the audit's findings |
| Undecided (same value, no printed total decides) | 1 | 12 (`cannot_verify`) |
| A third value (the audit reads neither the claim's) | 0 | not applicable |
| Not found in the other side's findings | 0 of its 74 are missing from the audit | 36 settled findings the baseline's list does not contain |
| Model | claude-sonnet-5-5 | claude-sonnet-4.6 reads, with claude-haiku and claude-opus-4.6 for some steps |
| Cost | 1.5254 USD, api equivalent (`run.json`) | 0.7793 USD, the program's own metered estimate over two runs (`score.json` `audit_side`) |
| Seconds | 411 | 516.4 over two runs (`score.json` `audit_side`) |
| Model calls | 79 turns | 176 |

The audit's two runs are `20261011-130414` (the all-counties run; its Panola share is 168 calls, 0.7675 USD, 474.9 s) and
`20261011-135350` (8 calls, 0.0118 USD, 41.5 s, continued from the first). The two cost figures are not the same kind of number: one is
an api-equivalent figure for an agent session, the other the audit's metered estimate for its gateway calls. They are shown side by side,
not as a like-for-like price.

The 36 findings the baseline's list lacks, from `score.json` `missed_settled`: 26 `wrong_precinct`, 5 `missing_row`, 2 `extra_row`,
2 `wrong_number`, 1 `file_row_fails_own_total`. By office: 25 in Constable, 8 in County Commissioner, 2 in U.S. Senate, 1 in a
District Judge race.

## What each side hands a maintainer

- Baseline: a list of 74 rows, one sentence each ("precinct N column reads X for early voting, while the CSV has Y; scan row totals
  reconcile"), and a summary of caveats. A maintainer has to open the scan and look at each cell themselves.
- Audit: for each finding, the printed totals that decide it (each sum with the cells added, the printed total on each side, and
  whether it holds), a status, a crop of the scan region per group (46 groups), and a corrected file that differs from the published one
  only where printed totals settle it (80 corrections in `findings.json`).

## What the comparison shows

On the 74 cells the baseline listed, the two agree. The audit has a finding at every one of them with the same scan value (0 not found,
0 with a different value), and printed totals settle 73 of the 74 against the file. The one that is not settled is the registered-voters
figure for one precinct: the audit marks it `cannot_verify` because that row has no sum other than its own, so no printed total can say
which of the two readings (the file's or the scan's) is right. The baseline's own evidence line for it says only that the cell reads
1459 on the scan.

Where the baseline did as well or better:
- It reached the same 73 settled findings with one prompt, in 411 seconds, and without a reading step, a ledger or a sum checker.
- It was right on every claim it made against the file: none was contradicted by the audit's accepted values.
- It noticed on page 6 that the file's precinct labels for the Constable and County Commissioner rows do not line up with the scan's
  columns, and said so in its summary ("could not check" section). That is the area of the 26 `wrong_precinct` findings and the
  missing and extra rows it did not list. It left them out of `findings.json` because its schema had no precinct-label field, so they
  count as not listed here. It also reported two places where the scan's own printed numbers disagree with each other (registered
  voters 17923 against a printed 17921, and one candidate's precinct 22 parts adding to 179 against a printed 178), and the
  audit's own event log has the first one (computed 17923, printed 17921: `runs/20261011-112935/panola/county.json`, 11:30:12).

Where the audit did better:
- It lists 36 settled findings the baseline's list does not contain; 33 of them are in Constable and County Commissioner, the offices
  whose labels the baseline said it could not line up.
- For every finding it names the printed sums that decide it, so the claim "the file is wrong here" can be checked without trusting a
  reading, and it marks the 12 it cannot decide instead of listing them as errors.
- It writes a corrected file and a picture of each place, which the baseline does not.

What this does not show: it is one county and one run of each side; the baseline was not run twice, so its spread is unknown. "Settled"
means the printed totals back the audit's value; it does not mean a person has checked the scan. Two readers agreeing is not a
proof either. The baseline's `summary.md` statements about the scan are its own and are unchecked.
