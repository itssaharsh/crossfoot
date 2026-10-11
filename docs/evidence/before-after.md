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

## Later
- The plain `get_trace_context` call (trace id, `limit` 5, `include_evaluations` false) works; the options for
  filtering spans and fields still answer `not_enabled` (11 October 2026).
- Images are masked from commit `84c88a8` (`tracing.mask_images`): a span shows `image 888x173 sha256:036ec329aade`
  instead of the picture. Trace `b5b7e9fe34c976be76a1ec32f2acf2a0` (run `20261011-100540`, not committed) has 1,057
  spans (565 model calls, 491 tool calls); the first 5 spans are about 25,000 characters because each decision prompt
  appears in both the model span and its `work_item` span.

# The loop: before and after (T03b)

## What failed
T03a's close of Panola (run `20261011-102700`) took 565 model calls and 1,177.5 s and still left 16 row, 16 column and
12 grand sums failing, with 335 cells `cannot_verify`. The first read it started from used `claude-haiku`.

## What shows the cause
- Trace `b5b7e9fe34c976be76a1ec32f2acf2a0` (run `20261011-100540`, same code as T03a's close; 1,057 spans). `search_traces`
  for that id returns no rows (11 October 2026); `get_trace_context` with the trace id, `limit` 5 and `offset` 400 works
  and returns the spans. `span_types`, `span_names`, `fields` and `max_chars_per_field` were not tried again here.
- One item from that page (page 3, block `p3-b4`, row EARLY, which fails by -2 while column 3 fails by -2): the decision
  prompt even names the crossing, `EARLY/3`, but `claude-haiku` answered with the JSON inside a code fence followed by prose
  ("The analysis clearly points to cell EARLY/3 ..."). The parser accepted only a fence around the whole answer, so the
  gateway was called again to "repair" it, which cost one more call for an answer that had already been usable.
- The same-target repeats are in the committed ledger of T03a's close (`runs/20261011-102700/ledger.sqlite`, events of
  kind `reread`, counted by page, block, target, model and dpi): 219 re-reads, 172 distinct, so 47 re-reads asked again for
  something already read the same way. The most repeated, three times each, are `row_total EARLY`, `row_total PRECINCT`
  and `grand` of `p2-b5` with `claude-haiku` at 400 dpi. This count is from the committed run, not from the traced one
  (a different run of the same code); I did not open more pages of the trace to quote a repeat from it.
- The loop was working from failing sums one at a time and never used that a wrong value fails two sums at once.

## The change (commits of T03b; the code is in the commit named in the report)
- The reader is chosen by a sample of page 1 (`layouts/profile.py`, `matrix.read_county`): more than a tenth of the sample's
  row sums failing means `claude-sonnet-4.6` reads the county.
- Every value sits on two sums, with grand totals by columns and by rows as kinds of their own (`checks.suspects`). A value on
  two failing sums with the same difference is re-read at 400 dpi: the county's reader, then `claude-sonnet-4.6`, then
  `claude-opus-4.6`. The same reading twice while both sums fail is `document_inconsistent`. Arithmetic never writes a value.
- What pairing cannot place goes to `claude-sonnet-4.6` with a `row_strip` target; the same target is never re-read twice
  with the same model and dpi; JSON in prose or a fence parses without a repair call.

## Both closes (numbers from each run's `county.json` summary, `first-read.json` and `run.json`)
| measure | T03a close `20261011-102700` | T03b read `20261011-111955` + close `20261011-112935` |
|---|---|---|
| model | `claude-haiku` read; loop decisions `claude-haiku` | `claude-sonnet-4.6` (chosen by the sample) |
| sums failing after the first read (row / col / grand by columns / grand by rows) | 32 / 35 / 18 / not counted | 3 / 2 / 1 / 1 |
| sums failing after the loop | 16 / 16 / 12 / not counted | 1 / 1 / 1 / 0 |
| values re-read | 79 cells | 23 (20 cells, 3 totals) |
| values changed | 31 cells | 2 (1 cell, 1 printed total) |
| cannot_verify | 335 cells | 0 cells; 1 sum (registered voters row) |
| document_inconsistent | not a status then | 2 sums (one value: the small total of precinct 1, page 6, block `p6-b3`) |
| model calls | 565 (the first read had 127 more) | read 146 + close 19 = 165 |
| tokens in / out | 565,521 / 50,446 (read: 94,551 / 25,070) | read 108,172 / 25,979 + close 8,004 / 1,496 |
| metered cost estimate | $0.8601 (read $0.2199) | read $0.7114 + close $0.0601 |
| gateway spend change | $0.9447 (read $0.2380) | read $0.6935 + close $0.0601 |
| seconds | 1,177.5 (read 334.6) | read 410.4 + close 80.0 |

The T03a column's first-read figures are those of the haiku read `20261011-094115`; the sample in the T03b read had
6 of 22 row sums failing (27.3%), over the line, so the sample was discarded. The prices behind the "metered" rows differ
between the columns (the price table changed in this task), so compare the gateway rows.

## Plainly
- Better: 3 sums fail after the close against 44, in 80 s of loop time against 1,177 s and 19 calls against 565.
- Worse: the read costs about three times as much per call, and the whole read about three times as much (gateway change
  $0.6935 against $0.2380 for the haiku read). One close of a read this good is cheap, but the read is not.
- Not solved: the registered-voters row sits on one sum only and fails by +2; pairing cannot place it, four re-reads
  (`row_total`, `row_strip`, two models) all confirmed the same values, and 22 of its cells stay `first_read` (not accepted,
  not marked). The small total of precinct 1 on page 6 reads 1,079 each time and the cells add to 1,076; the loop does not
  say which is wrong, only that the page disagrees with itself.
- One full read and two full closes were run in this task (the limit was one and two; the close was run twice, with the same outcome both times, and the second is kept).
