# First read of Panola: before and after (T02a)

## What failed
The first read (T02) sent one crop per block, about 2,600 px wide, to `claude-haiku`. 91 of 130 row sums, 203 of 768
column sums and 35 of 43 grand totals did not add up to the totals printed on the page.

## What shows the cause
- Trace `c0ad0dc20af3f7651960204384229937` (root span `read_county`, 2026-10-11T09:03Z, run `20261011-090307`).
  The neatlogs MCP server could list it (`search_traces`, query `read_block`), but `get_trace_context` answered
  `not_enabled` (server message: disabled until NL-1924 is rolled out), so no model span could be opened. The
  figures below come from the run's own files instead: `runs/20261011-090307/first-read.json`,
  `ledger.sqlite` and `crops/`.
- Prompt tokens: 25,705 over 43 calls, about 598 per call, for images 2,614 px wide. That is far fewer tokens than a
  full-size image of that width would cost, so the provider shrinks it before the model sees it (an inference from
  the token count, not a measurement of the provider).
- Block `p2-b2` (crop `runs/20261011-090307/crops/p2-b2.png`, read by eye): the only non-zero cell is a 2 in the
  PRECINCT row of the seventh precinct column; the small total under that column is 2. The ledger holds that 2 in the
  nineteenth (last) column and 0 under the seventh, so a value lost its column position in the wide image.
- Digits in the 200 dpi crop are about 10 px tall.

## The change (commit `338de15`)
- A block is cut into column groups along the column lines, each image at most 1,500 px wide at 300 dpi (digits
  about 16 px tall). The first group carries the row labels (candidate name), the last carries the TOTAL column;
  rows are named in order EARLY, ABSENTEE, PRECINCT and each group is told which precincts it holds. Answers are
  joined left to right (`plan_groups`, `merge_groups`; tests in `tests/test_groups.py` check every column is
  covered once and values stay with their precinct and row).
- Found on the way: `_edges` took the left edge of the row-label box as the first precinct edge, so every column
  was one off. The first fixed-size attempt (`runs/20261011-092655`, not committed) lost the precinct 8 column
  because of it (cells 2,212; row sums 52 pass / 78 fail). Fixed in `_edges`, which also corrects the cell boxes.
- Each group call is a span `read_group` with block id, column range, crop width and height, dpi and its estimated
  cost. The header block (page 1, first block) still goes as one wide crop; it was not changed.

## Both runs (numbers from each `first-read.json`)
| measure | before `20261011-090307` | after `20261011-094115` |
|---|---|---|
| trace id | `c0ad0dc20af3f7651960204384229937` | `8c2ceec449e02419a8fd147ac260d126` |
| code | commit `438ae3a` | commit `338de15` |
| blocks | 43 | 43 |
| model calls | 43 | 127 |
| cells read | 2312 | 2328 |
| row sums pass / fail | 39 / 91 | 98 / 32 |
| column sums pass / fail | 565 / 203 | 735 / 35 |
| grand totals pass / fail | 8 / 35 | 25 / 18 |
| tokens in / out | 25,705 / 15,469 | 94,551 / 25,070 |
| estimated cost | $0.1031 | $0.2199 |
| gateway spend change | $0.1084 | $0.2380 |
| seconds | 182.0 | 334.6 |

## Plainly
- Better: failing row sums fell from 91 to 32, column sums from 203 to 35, grand totals from 35 to 18.
- Worse: three times the calls, about 2.1 times the cost and 1.8 times the time.
- The target of fewer than 20 failing row sums was **not met** (32). Of the 32, 29 are in group-read blocks (mostly the
  EARLY and PRECINCT rows, the rows with the largest numbers), 3 are in the header block, which was not changed.
  Nothing was tuned to known answers. Next to try: send the header's ballots-cast rows through the group path, and
  re-read only the cells in failing rows or columns (the re-read loop).
- Three full reads were made in this task (the limit): `20261011-092655` (column bug, not committed),
  `20261011-093435` (same code as the run after; identical counts, 127 calls, $0.2199; trace
  `31f18982da0029240fdbd65bbf3ff3b6`; not committed) and `20261011-094115`, the run after, made by `pb.py verify`.
