# Run 20261011-130414

Budget $9.00; metered cost (an estimate) $2.8692; 552 model calls; 1671.3 s; 8 of 8 counties closed.

| county | status | layout | pages | cells | sums ok / failing after first read | cells re-read | cells accepted | cannot_verify | findings | printed sums in all / hold with published / hold with corrected | second sum | calls | cost $ | seconds |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| panola | audited | matrix | 6 | 2324 | 935 / 6 | 20 | 2302 | 12 | 121 | 984 / 949 / 978 | yes | 168 | 0.7675 | 474.9 |
| san_saba | audited | report | 21 | 1100 | 273 / 2 | 8 | 1100 | 18 | 21 | 275 / 274 / 275 | no | 34 | 0.2146 | 97.6 |
| cottle | audited | report | 12 | 664 | 166 / 0 | 0 | 664 | 0 | 0 | 166 / 166 / 166 | no | 22 | 0.1974 | 103.1 |
| jones | audited | report | 20 | 1784 | 738 / 20 | 0 | 1614 | 8 | 26 | 758 / 726 / 738 | yes | 144 | 0.3844 | 346.3 |
| lynn | audited | report | 37 | 3324 | 1401 / 26 | 36 | 3256 | 5 | 43 | 1427 / 1393 / 1417 | yes | 106 | 0.5333 | 345.0 |
| scurry | audited | report | 38 | 2116 | 529 / 0 | 0 | 2116 | 15 | 15 | 529 / 529 / 529 | no | 58 | 0.5543 | 199.8 |
| foard | audited | report | 16 | 1616 | 698 / 2 | 4 | 1616 | 2 | 2 | 700 / 700 / 700 | yes | 19 | 0.2156 | 102.8 |
| limestone | unchecked | no_printed_totals | 0 | 0 | 0 / 0 |  |  |  |  |  /  /  |  | 1 | 0.0021 | 1.8 |
| **all** | | | | 12928 | 4740 / 56 | 68 | 12668 | 60 | 228 | 4839 / 4737 / 4803 | | 552 | 2.8692 | 1671.3 |

## Findings by kind and status

- panola: by kind {'file_row_fails_own_total': 1, 'wrong_number': 64, 'wrong_column': 4, 'wrong_precinct': 44, 'missing_row': 6, 'extra_row': 2}; by status {'settled_against_file': 109, 'cannot_verify': 12}
- san_saba: by kind {'file_row_fails_own_total': 1, 'wrong_number': 20}; by status {'settled_against_file': 3, 'cannot_verify': 18}
- cottle: by kind {}; by status {}
- jones: by kind {'wrong_number': 26}; by status {'settled_against_file': 18, 'cannot_verify': 8}
- lynn: by kind {'wrong_number': 37, 'wrong_column': 6}; by status {'settled_against_file': 38, 'cannot_verify': 5}
- scurry: by kind {'extra_row': 15}; by status {'cannot_verify': 15}
- foard: by kind {'extra_row': 2}; by status {'cannot_verify': 2}

## Model calls by model

- claude-haiku: 387 calls, 558179 tokens in, 256302 out, $2.0237
- claude-opus-4.6: 4 calls, 1503 tokens in, 91 out, $0.0108
- claude-sonnet-4.6: 161 calls, 118762 tokens in, 26844 out, $0.8348

## Not audited

- limestone: nothing on this scan can be cross-checked; left as published

Gateway's own figure: $6.7693 before, $9.6125 after (change $2.8431).
