# Run 20261011-161207

Budget $3.40; metered cost (an estimate) $2.3456; 353 model calls; 1227.8 s; 8 of 8 counties closed.

| county | status | layout | pages | cells | sums ok / failing after first read | cells re-read | cells accepted | cannot_verify | findings | printed sums in all / hold with published / hold with corrected | second sum | published rows compared | calls | cost $ | seconds |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| panola | audited | matrix | 6 | 2324 | 936 / 6 | 20 | 2302 | 12 | 121 | 985 / 950 / 979 | row and column | 783 of 783 | 172 | 0.7892 | 507.0 |
| san_saba | audited | report | 21 | 1100 | 273 / 2 | 8 | 1100 | 18 | 21 | 275 / 274 / 275 | row only | 275 of 275 | 33 | 0.2076 | 102.8 |
| cottle | audited | report | 12 | 664 | 166 / 0 | 0 | 664 | 0 | 0 | 166 / 166 / 166 | row only | 166 of 166 | 13 | 0.1039 | 57.7 |
| jones | audited | report | 20 | 1784 | 1102 / 0 | 0 | 1784 | 0 | 26 | 1102 / 1083 / 1102 | row and contest | 335 of 344 | 24 | 0.2544 | 119.9 |
| lynn | audited | report | 37 | 3324 | 2097 / 18 | 36 | 3324 | 0 | 47 | 2115 / 2049 / 2115 | row and contest | 634 of 650 | 51 | 0.4624 | 207.4 |
| scurry | audited | report | 38 | 2180 | 545 / 0 | 0 | 2180 | 0 | 0 | 545 / 545 / 545 | row only | 534 of 545 | 40 | 0.3329 | 139.5 |
| foard | audited | report | 16 | 1616 | 698 / 2 | 4 | 1616 | 0 | 0 | 700 / 700 / 700 | row and contest | 294 of 298 | 19 | 0.1931 | 91.2 |
| limestone | unchecked | no_printed_totals | 0 | 0 | 0 / 0 |  |  |  |  |  /  /  |  |  | 1 | 0.0021 | 2.3 |
| **all** | | | | 12992 | 5817 / 28 | 68 | 12970 | 30 | 215 | 5888 / 5767 / 5882 | | 3021 of 3061 | 353 | 2.3456 | 1227.8 |

## Published rows compared with the scan

- panola: 783 of 783 published rows compared.
- san_saba: 275 of 275 published rows compared.
- cottle: 166 of 166 published rows compared.
- jones: 335 of 344 published rows compared.
  - not compared: Registered Voters, 4 rows. The contest was not paired with a contest on the scan.
  - not compared: Ballots Cast Blank, 4 rows. The contest was not paired with a contest on the scan.
  - not compared: Trustee Roby CISD, 1 row. The contest is paired, but this candidate has no block on the scan.
- lynn: 634 of 650 published rows compared.
  - not compared: Registered Voters, 8 rows. The contest was not paired with a contest on the scan.
  - not compared: School Board New Home ISD, 8 rows. The row repeats a precinct of the same candidate and contest.
- scurry: 534 of 545 published rows compared.
  - not compared: Registered Voters, 11 rows. The contest was not paired with a contest on the scan.
- foard: 294 of 298 published rows compared.
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

- claude-haiku: 187 calls, 339444 tokens in, 213031 out, $1.5451
- claude-opus-4.6: 4 calls, 1503 tokens in, 91 out, $0.0108
- claude-sonnet-4.6: 162 calls, 116748 tokens in, 24524 out, $0.7899

## Not audited

- limestone: nothing on this scan can be cross-checked; left as published

Gateway's own figure: $11.4566 before, $13.7987 after (change $2.3421).
