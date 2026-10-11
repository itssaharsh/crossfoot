# Recovery evidence

## A run stopped by its budget and continued

Two small counties (San Saba, Cottle), real model calls, run 20261011-135519 (`runs/20261011-135519/`; trace of the resumed part, Cottle: `6b289ce0c777683ca054674468c29dbd`; none found for the first part). Ledger events and
the counts come from `runs/20261011-135519/ledger.sqlite` and `summary.json`. Evidence ids (E0071 and the like) are entries of the build's command ledger, which is in the repository's history.

1. `crossfoot audit --all --only san_saba,cottle --budget 0.25` (E0071, exit 2, expected)
   - Last lines of the run's summary: San Saba `audited` (33 calls, $0.2076); Cottle `stopped`: "run budget $0.25 reached
     (estimated spend $0.2573 after 39 calls); refusing the next call". "1 of 2 counties closed."
   - Ledger after the stop: San Saba 1,100 cells, 1,100 accepted, 21 page reads, `read_done` written. Cottle 168 cells read from 3
     pages, 0 accepted, no `read_done`.
2. `crossfoot audit --all --only san_saba,cottle --resume 20261011-135519 --budget 2` (E0072, exit 0)
   - Last lines: "san_saba skipped: closed in the run being continued"; "cottle end: audited; 21 calls, $0.1944, 95.5 s";
     "2 of 2 counties closed; model calls 61; metered cost (estimate) $0.4626".
   - Ledger after: San Saba still 1,100 cells, 1,100 accepted, 8 re-read tries, 21 page reads (unchanged: no page of it was
     read again). Cottle 664 cells, all accepted, 12 pages.

Counts: model calls San Saba 33 (first run only; the resume added none), Cottle 7 in the first run plus 21 in the resume = 28,
all 61 in the run. So nothing accepted was read again. What was paid twice: Cottle's three half-read pages (7 calls, about $0.06)
were read again from the start, because a county whose read did not finish is read whole again (its half-read cells are cleared,
none of them had been accepted). Gateway's own figure for the two commands: $9.9109 to $10.1791, then to $10.3736.

## Where a read failed and what the program did next

Quoted from the events kept in the committed runs' `county.json` files. Times are the event clock (UTC, as the runs record it).
Neatlogs trace ids are in `docs/evidence/traces.md`; no run file stores one, so each is paired by start time.

### 1. A re-read gave the same value and went one step up the ladder, and the document disagreed with itself

Run `20261011-112935` (trace: none found, see `traces.md`) (`crossfoot close --county panola --resume latest`), `runs/20261011-112935/panola/county.json`, item
`col:6:p6-b3:1` (page 6, the small total under precinct 1's column):

    11:29:58 suspect   read 1079, would_be 1076 (the three cells above add to 1076)
    11:30:01 reread    claude-sonnet-4.6, 400 dpi, ladder_step 0: old 1079, new 1079, kept "same"
    11:30:01 check     ok false, computed 1076, printed 1079, failing_in_block 2
    11:30:04 reread    claude-opus-4.6, 400 dpi, ladder_step 1: old 1079, new 1079, kept "same"
    11:30:04 check     ok false, computed 1076, printed 1079, failing_in_block 2
    11:30:04 verdict   document_inconsistent: "the scan shows 1079 there on every re-read (claude-sonnet-4.6 read 1079,
                       claude-opus-4.6 read 1079) while both sums it sits on still fail ... The document disagrees with itself."
    11:30:04 item_end  document_inconsistent

The first re-read agreed with the first reading, so the program asked a stronger model at the same size (one step up) and got the
same value; two readers and two failing sums ended it as `document_inconsistent`. No value was changed.

### 2. A value that ended `cannot_verify`

Same run, item `row:1:reg:REGISTERED` (the registered-voters row on page 1; its cells add to 17923, the printed total reads 17921):

    11:30:04 item_start
    11:30:12 reread  claude-sonnet-4.6, row total, 400 dpi        11:30:12 check ok false, computed 17923, printed 17921
    11:30:19 reread  claude-sonnet-4.6, row strip, 400 dpi        11:30:19 check ok false, computed 17923, printed 17921
    11:30:35 reread  claude-opus-4.6, row strip, 500 dpi          11:30:35 check ok false, computed 17923, printed 17921
    11:30:40 reread  claude-opus-4.6, row total, 500 dpi          11:30:40 check ok false, computed 17923, printed 17921
    11:30:54 reread  claude-opus-4.6, row strip, 400 dpi          11:30:55 check ok false, computed 17923, printed 17921
    11:30:57 reread  claude-opus-4.6, row total, 400 dpi          11:30:57 check ok false, computed 17923, printed 17921
    11:30:58 verdict cannot_verify: "six actions used on this item and its sum still fails"
    11:30:58 stop / item_end cannot_verify

Six actions, then the program stopped rather than loop. The cells stayed as read, marked `cannot_verify`.

### 3. A model answer the program refused

Run `20261011-130414` (`crossfoot audit --all --budget 9`; Scurry trace `50d31f20696f092c1bad57ab707a3a55`), `runs/20261011-130414/scurry/county.json`, Scurry page 18:

    13:28:47 page_failed  page 18, error: "y" of 'REP John Bailey' must be a number from 0 to 1000

This is the case the runs record: a model answer that parsed as JSON but failed the program's checks. The model client asks once more
for a corrected answer before giving up (`crossfoot/model.py`, `ask_json`), and the repair request is not an event of its own, so the
runs hold the final refusal only; no event in the committed runs records an answer that was not JSON at all. What the program did next:
the page was left unread and listed (the rest of the county went on: pages 16, 17 and 19 were read at 13:28:32 to 13:28:47), then the
validator was changed (`hackathon.md`, T04d) and `crossfoot read-page` read page 18 into a copy of the ledger: in
`runs/20261011-141015/scurry/county.json`, `14:09:58 page_read page 18, PRECINCT 10, claude-haiku, 64 cells, 8 contests`.
