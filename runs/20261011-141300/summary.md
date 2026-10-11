# Run 20261011-141300

Budget $9.00; metered cost (an estimate) $0.0625; 22 model calls; 246.2 s; 8 of 8 counties closed.

| county | status | layout | pages | cells | sums ok / failing after first read | cells re-read | cells accepted | cannot_verify | findings | printed sums in all / hold with published / hold with corrected | second sum | published rows compared | calls | cost $ | seconds |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| panola | audited | matrix | 6 | 2324 | 935 / 6 | 20 | 2302 | 12 | 121 | 984 / 949 / 978 | row and column | 783 of 783 | 8 | 0.0118 | 41.5 |
| san_saba | audited | report | 21 | 1100 | 273 / 2 | 8 | 1100 | 18 | 21 | 275 / 274 / 275 | row only | 275 of 275 | 9 | 0.0298 | 36.9 |
| cottle | audited | report | 12 | 664 | 166 / 0 | 0 | 664 | 0 | 0 | 166 / 166 / 166 | row only | 166 of 166 | 0 | 0.0000 | 18.2 |
| jones | audited | report | 20 | 1784 | 738 / 20 | 0 | 1784 | 0 | 26 | 1102 / 1083 / 1102 | row and contest | 335 of 344 | 1 | 0.0075 | 36.6 |
| lynn | audited | report | 37 | 3324 | 1401 / 26 | 36 | 3324 | 0 | 47 | 2115 / 2049 / 2115 | row and contest | 634 of 650 | 1 | 0.0089 | 50.6 |
| scurry | audited | report | 38 | 2180 | 529 / 0 | 0 | 2180 | 0 | 0 | 545 / 545 / 545 | row only | 534 of 545 | 1 | 0.0009 | 29.5 |
| foard | audited | report | 16 | 1616 | 698 / 2 | 4 | 1616 | 0 | 0 | 700 / 700 / 700 | row and contest | 294 of 298 | 1 | 0.0015 | 31.1 |
| limestone | unchecked | no_printed_totals | 0 | 0 | 0 / 0 |  |  |  |  |  /  /  |  |  | 1 | 0.0021 | 1.8 |
| **all** | | | | 12992 | 4740 / 56 | 68 | 12970 | 30 | 215 | 5887 / 5766 / 5881 | | 3021 of 3061 | 22 | 0.0625 | 246.2 |

## Published rows compared with the scan

- panola: 783 of 783 published rows compared (figures from run 20261011-135350).
- san_saba: 275 of 275 published rows compared (figures from run 20261011-141051).
- cottle: 166 of 166 published rows compared (figures from run 20261011-141131).
- jones: 335 of 344 published rows compared (figures from run 20261011-140556).
  - not compared: Registered Voters, 4 rows. The contest was not paired with a contest on the scan.
  - not compared: Ballots Cast Blank, 4 rows. The contest was not paired with a contest on the scan.
  - not compared: Trustee Roby CISD, 1 row. The contest is paired, but this candidate has no block on the scan.
- lynn: 634 of 650 published rows compared (figures from run 20261011-140637).
  - not compared: Registered Voters, 8 rows. The contest was not paired with a contest on the scan.
  - not compared: School Board New Home ISD, 8 rows. The row repeats a precinct of the same candidate and contest.
- scurry: 534 of 545 published rows compared (figures from run 20261011-141015).
  - not compared: Registered Voters, 11 rows. The contest was not paired with a contest on the scan.
- foard: 294 of 298 published rows compared (figures from run 20261011-141152).
  - not compared: Ballots Cast, 4 rows. The contest was not paired with a contest on the scan.

## Findings by kind and status

- panola: by kind {'file_row_fails_own_total': 1, 'wrong_number': 64, 'wrong_column': 4, 'wrong_precinct': 44, 'missing_row': 6, 'extra_row': 2}; by status {'settled_against_file': 109, 'cannot_verify': 12}
- san_saba: by kind {'file_row_fails_own_total': 1, 'wrong_number': 20}; by status {'settled_against_file': 3, 'cannot_verify': 18}
- cottle: by kind {}; by status {}
- jones: by kind {'wrong_number': 26}; by status {'settled_against_file': 26}
- lynn: by kind {'wrong_number': 41, 'wrong_column': 6}; by status {'settled_against_file': 47}
- scurry: by kind {}; by status {}
- foard: by kind {}; by status {}

## Model calls by model

- claude-sonnet-4.6: 21 calls, 13065 tokens in, 1045 out, $0.0604
- claude-haiku: 1 calls, 1772 tokens in, 24 out, $0.0021

## Where each county's figures come from

- panola: run 20261011-135350
- san_saba: run 20261011-141051
- cottle: run 20261011-141131
- jones: run 20261011-140556
- lynn: run 20261011-140637
- scurry: run 20261011-141015
- foard: run 20261011-141152
- limestone: run 20261011-130414

A county taken from a single-county audit reused the ledger of an earlier run, so its calls, cost and seconds are those of the audit alone; the reading was paid for in the earlier run. The cost and calls in the header and the **all** row therefore add the reading of no county that was audited again.

## Not audited

- limestone: nothing on this scan can be cross-checked; left as published
