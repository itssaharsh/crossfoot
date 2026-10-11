# Run 20261011-150000

Budget $9.00; the runs that read the counties: 552 model calls, metered cost (an estimate) $2.8692, 1671.3 s; the audits made again from their ledgers added 209 calls, $0.2888, 767.0 s; 8 of 8 counties closed.

| county | status | layout | pages | cells | sums ok / failing after first read | cells re-read | cells accepted | cannot_verify | findings | printed sums in all / hold with published / hold with corrected | second sum | published rows compared | read: calls | read: cost $ | read: seconds | audit again: calls | audit again: cost $ | audit again: seconds |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| panola | audited | matrix | 6 | 2324 | 935 / 6 | 20 | 2302 | 12 | 121 | 984 / 949 / 978 | row and column | 783 of 783 | 168 | 0.7675 | 474.9 | 8 | 0.0118 | 41.5 |
| san_saba | audited | report | 21 | 1100 | 273 / 2 | 8 | 1100 | 18 | 21 | 275 / 274 / 275 | row only | 275 of 275 | 34 | 0.2146 | 97.6 | 18 | 0.0596 | 70.7 |
| cottle | audited | report | 12 | 664 | 166 / 0 | 0 | 664 | 0 | 0 | 166 / 166 / 166 | row only | 166 of 166 | 22 | 0.1974 | 103.1 | 0 | 0.0000 | 29.8 |
| jones | audited | report | 20 | 1784 | 738 / 20 | 0 | 1784 | 0 | 26 | 1102 / 1083 / 1102 | row and contest | 335 of 344 | 144 | 0.3844 | 346.3 | 122 | 0.1363 | 297.1 |
| lynn | audited | report | 37 | 3324 | 1401 / 26 | 36 | 3324 | 0 | 47 | 2115 / 2049 / 2115 | row and contest | 634 of 650 | 106 | 0.5333 | 345.0 | 57 | 0.0763 | 217.4 |
| scurry | audited | report | 38 | 2180 | 529 / 0 | 0 | 2180 | 0 | 0 | 545 / 545 / 545 | row only | 534 of 545 | 58 | 0.5543 | 199.8 | 2 | 0.0018 | 58.8 |
| foard | audited | report | 16 | 1616 | 698 / 2 | 4 | 1616 | 0 | 0 | 700 / 700 / 700 | row and contest | 294 of 298 | 19 | 0.2156 | 102.8 | 2 | 0.0030 | 51.7 |
| limestone | unchecked | no_printed_totals | 0 | 0 | 0 / 0 |  |  |  |  |  /  /  |  |  | 1 | 0.0021 | 1.8 |  |  |  |
| **all** | | | | 12992 | 4740 / 56 | 68 | 12970 | 30 | 215 | 5887 / 5766 / 5881 | | 3021 of 3061 | 552 | 2.8692 | 1671.3 | 209 | 0.2888 | 767.0 |

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

- claude-haiku: 561 calls, 687133 tokens in, 262595 out, $2.2002
- claude-opus-4.6: 4 calls, 1503 tokens in, 91 out, $0.0108
- claude-sonnet-4.6: 196 calls, 142811 tokens in, 28836 out, $0.9471

## Where each county's figures come from

- panola: run 20261011-135350
- san_saba: run 20261011-141051
- cottle: run 20261011-141131
- jones: run 20261011-140556
- lynn: run 20261011-140637
- scurry: run 20261011-141015
- foard: run 20261011-141152
- limestone: run 20261011-130414

A county audited again reused the ledger of the run that read it. Its row shows the reading run's calls, cost and seconds first and what the later audits added after them; the figures in the header and the **all** row add both.

## Not audited

- limestone: nothing on this scan can be cross-checked; left as published
