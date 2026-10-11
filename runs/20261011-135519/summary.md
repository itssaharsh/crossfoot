# Run 20261011-135519

Budget $2.00; metered cost (an estimate) $0.4626; 61 model calls; 235.9 s; 2 of 2 counties closed.

| county | status | layout | pages | cells | sums ok / failing after first read | cells re-read | cells accepted | cannot_verify | findings | printed sums in all / hold with published / hold with corrected | second sum | published rows compared | calls | cost $ | seconds |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| san_saba | audited | report | 21 | 1100 | 273 / 2 | 8 | 1100 | 18 | 21 | 275 / 274 / 275 | no | 275 of 275 | 33 | 0.2076 | 103.7 |
| cottle | audited | report | 12 | 664 | 166 / 0 | 0 | 664 | 0 | 0 | 166 / 166 / 166 | no | 166 of 166 | 28 | 0.2550 | 132.2 |
| **all** | | | | 1764 | 439 / 2 | 8 | 1764 | 18 | 21 | 441 / 440 / 441 | | 441 of 441 | 61 | 0.4626 | 235.9 |

## Published rows compared with the scan

- san_saba: 275 of 275 published rows compared.
- cottle: 166 of 166 published rows compared.

## Findings by kind and status

- san_saba: by kind {'file_row_fails_own_total': 1, 'wrong_number': 20}; by status {'settled_against_file': 3, 'cannot_verify': 18}
- cottle: by kind {}; by status {}

## Model calls by model

- claude-haiku: 52 calls, 114382 tokens in, 55838 out, $0.4329
- claude-sonnet-4.6: 9 calls, 7621 tokens in, 279 out, $0.0298

## Not audited

Every county was audited.

Gateway's own figure: $10.1791 before, $10.3736 after (change $0.1944).
