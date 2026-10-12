# The loop rework as entire-graph sees it

Entire's graph plugin (entire-graph v0.4.0) reads a commit and lists what changed as code entities, with how many other
entities depend on each. This is its answer for the commit that reworked the loop, `4fb474a` (checkpoint
`01M4NBPWG7D7K4TBZJD3FE6JTK`), made on 12 October 2026 with:

```
entire graph commit 4fb474a
```

The answer, 233 lines, is in [entire-graph-4fb474a.txt](entire-graph-4fb474a.txt). Left out of that file: the tool's closing
warnings that it has no parser for three files of that commit (two SQLite ledgers and a JSONL file, none of them in the tree now). In all it lists 142 entities added,
44 changed and 6 removed, across 20 files. For the program and its tests:

| File | Added | Changed | Removed |
|---|---|---|---|
| `crossfoot/agent.py` | 16 | 20 | 4 |
| `crossfoot/checks.py` | 4 | 6 | 0 |
| `crossfoot/cli.py` | 0 | 3 | 0 |
| `crossfoot/layouts/matrix.py` | 5 | 3 | 0 |
| `crossfoot/layouts/profile.py` | 2 | 0 | 0 |
| `crossfoot/ledger.py` | 3 | 1 | 0 |
| `crossfoot/model.py` | 0 | 1 | 0 |
| `crossfoot/outputs.py` | 0 | 2 | 0 |
| `tests/test_agent.py` | 2 | 7 | 2 |
| `tests/test_choose_reader.py` | 10 | 0 | 0 |
| `tests/test_locate.py` | 14 | 0 | 0 |
| `tests/test_pairing_loop.py` | 21 | 0 | 0 |
| `tests/test_parse_json.py` | 6 | 0 | 0 |

The part that carries the idea, in `crossfoot/checks.py`: a value sits on two printed sums, and two failing sums that share
a value point at it.

```text
crossfoot/checks.py (Python)
  ~ class Check body changed (9 dependents)
  ~ function _make signature changed (2 dependents)
  ~ function row_checks body changed (11 dependents)
  ~ function column_checks body changed (7 dependents)
  ~ function grand_checks body changed (2 dependents)
  + function grand_row_checks added
  ~ function all_checks body changed (8 dependents)
  + class Suspect added
  + class Located added
  + function suspects added
```

## What this is not

The coding sessions did not use the graph. Its guide was part of the rules the sessions were given (those files left the tree on 12 October 2026 and are in the
history at commit `e0452da`), but
`entire graph stats` over the 16 recorded sessions reports 0 graph calls against 668 exploration calls (113 whole-file reads,
555 uses of grep, find or a partial read). The agents went on reading files. This page was made after the build, to show the
rework commit; nothing in the program came from it.
