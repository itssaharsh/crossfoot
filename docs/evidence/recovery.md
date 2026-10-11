# Recovery evidence

## A run stopped by its budget and continued

Two small counties (San Saba, Cottle), real model calls, run 20261011-135519 (`runs/20261011-135519/`). Ledger events and
the counts come from `runs/20261011-135519/ledger.sqlite` and `summary.json`. Evidence ids are in `.prod-build/evidence.jsonl`.

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
