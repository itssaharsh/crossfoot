# Run 20261011-140000

Budget $9.00; metered cost (an estimate) $0.2423; 197 model calls; 565.9 s; 8 of 8 counties closed.

| county | status | layout | pages | cells | sums ok / failing after first read | cells re-read | cells accepted | cannot_verify | findings | printed sums in all / hold with published / hold with corrected | second sum | published rows compared | calls | cost $ | seconds |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| panola | audited | matrix | 6 | 2324 | 935 / 6 | 20 | 2302 | 12 | 121 | 984 / 949 / 978 | no | 783 of 783 | 8 | 0.0118 | 41.5 |
| san_saba | audited | report | 21 | 1100 | 273 / 2 | 8 | 1100 | 18 | 21 | 275 / 274 / 275 | no | 275 of 275 | 9 | 0.0298 | 33.8 |
| cottle | audited | report | 12 | 664 | 166 / 0 | 0 | 664 | 0 | 0 | 166 / 166 / 166 | no | 166 of 166 | 0 | 0.0000 | 11.6 |
| jones | audited | report | 20 | 1784 | 738 / 20 | 0 | 1614 | 8 | 26 | 758 / 726 / 738 | yes | 335 of 344 | 121 | 0.1288 | 260.5 |
| lynn | audited | report | 37 | 3324 | 1401 / 26 | 36 | 3256 | 9 | 47 | 1427 / 1393 / 1417 | yes | 634 of 650 | 56 | 0.0674 | 166.8 |
| scurry | audited | report | 38 | 2116 | 529 / 0 | 0 | 2116 | 0 | 0 | 529 / 529 / 529 | no | 518 of 545 | 1 | 0.0009 | 29.3 |
| foard | audited | report | 16 | 1616 | 698 / 2 | 4 | 1616 | 0 | 0 | 700 / 700 / 700 | yes | 294 of 298 | 1 | 0.0015 | 20.6 |
| limestone | unchecked | no_printed_totals | 0 | 0 | 0 / 0 |  |  |  |  |  /  /  |  |  | 1 | 0.0021 | 1.8 |
| **all** | | | | 12928 | 4740 / 56 | 68 | 12668 | 47 | 215 | 4839 / 4737 / 4803 | | 3005 of 3061 | 197 | 0.2423 | 565.9 |

## Published rows compared with the scan

- panola: 783 of 783 published rows compared (figures from run 20261011-135350).
- san_saba: 275 of 275 published rows compared (figures from run 20261011-134552).
- cottle: 166 of 166 published rows compared (figures from run 20261011-134535).
- jones: 335 of 344 published rows compared (figures from run 20261011-134631).
  - not compared: Registered Voters, 4 rows. The contest was not paired with a contest on the scan.
  - not compared: Ballots Cast Blank, 4 rows. The contest was not paired with a contest on the scan.
  - not compared: Trustee Roby CISD, 1 row. The contest is paired, but this candidate has no block on the scan.
- lynn: 634 of 650 published rows compared (figures from run 20261011-135058).
  - not compared: Registered Voters, 8 rows. The contest was not paired with a contest on the scan.
  - not compared: School Board New Home ISD, 8 rows. The row repeats a precinct of the same candidate and contest.
- scurry: 518 of 545 published rows compared (figures from run 20261011-134418).
  - not compared: Registered Voters, 11 rows. The contest was not paired with a contest on the scan.
  - not compared: Justice, Supreme Court, Pl 4, 2 rows. Scan page 18 could not be read and may hold this row.
  - not compared: Justice, Supreme Court, PI 6, 3 rows. Scan page 18 could not be read and may hold this row.
  - not compared: Presiding Judge, Ct of Crim App, 2 rows. Scan page 18 could not be read and may hold this row.
  - not compared: Judge, Ct of Crim App, PI 7, 2 rows. Scan page 18 could not be read and may hold this row.
  - not compared: Judge, Ct of Crim App, PI 8, 2 rows. Scan page 18 could not be read and may hold this row.
  - not compared: Member, State BoE, Dist 15, 3 rows. Scan page 18 could not be read and may hold this row.
  - not compared: State House, district 83, 1 row. Scan page 18 could not be read and may hold this row.
  - not compared: Chief Justice, 11th Ct of App Dist, 1 row. Scan page 18 could not be read and may hold this row.
- foard: 294 of 298 published rows compared (figures from run 20261011-134509).
  - not compared: Ballots Cast, 4 rows. The contest was not paired with a contest on the scan.

## Findings by kind and status

- panola: by kind {'file_row_fails_own_total': 1, 'wrong_number': 64, 'wrong_column': 4, 'wrong_precinct': 44, 'missing_row': 6, 'extra_row': 2}; by status {'settled_against_file': 109, 'cannot_verify': 12}
- san_saba: by kind {'file_row_fails_own_total': 1, 'wrong_number': 20}; by status {'settled_against_file': 3, 'cannot_verify': 18}
- cottle: by kind {}; by status {}
- jones: by kind {'wrong_number': 26}; by status {'settled_against_file': 18, 'cannot_verify': 8}
- lynn: by kind {'wrong_number': 41, 'wrong_column': 6}; by status {'settled_against_file': 38, 'cannot_verify': 9}
- scurry: by kind {}; by status {}
- foard: by kind {}; by status {}

## Model calls by model

- claude-sonnet-4.6: 22 calls, 13911 tokens in, 1076 out, $0.0637
- claude-haiku: 175 calls, 130726 tokens in, 6317 out, $0.1786

## Where each county's figures come from

- panola: run 20261011-135350
- san_saba: run 20261011-134552
- cottle: run 20261011-134535
- jones: run 20261011-134631
- lynn: run 20261011-135058
- scurry: run 20261011-134418
- foard: run 20261011-134509
- limestone: run 20261011-130414

A county taken from a single-county audit reused the ledger of run 20261011-130414, so its calls, cost and seconds are those of the audit alone; the reading was paid for in run 20261011-130414. The cost and calls in the header and the **all** row therefore add the reading of no county that was audited again.

## Not audited

- limestone: nothing on this scan can be cross-checked; left as published
