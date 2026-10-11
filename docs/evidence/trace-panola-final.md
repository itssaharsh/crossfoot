# One trace as neatlogs returns it (Panola, the final run)

Read on 11 October 2026 at about 21:00 UTC from the neatlogs MCP server: `get_trace_context` with the trace id,
`limit` 40, `offset` 0 and `include_evaluations` false. Nothing here was typed in: the table and the tree are the
server's answer, laid out. The run is `runs/20261011-161207` (`crossfoot audit --all`), county Panola.

## What the server says about the trace

| field | value |
|---|---|
| `trace_id` | `81bf9a637f8f4dcd02c763b1a1ce7592` |
| `name` | `panola` |
| `workflow` | `crossfoot` |
| `status` | `success` |
| `finalization_status` | `finalized` |
| `created_at` | `2026-10-11T16:12:11.032Z` |
| `latency_ms` | 507,019 |
| `span_count` | 394 |
| `llm_calls` | 172 |
| `tool_calls` | 219 |
| `retrieval_calls` | 0 |
| `total_tokens` | 149,455 |
| `prompt_tokens` | 121,734 |
| `completion_tokens` | 27,721 |
| `has_error` | false |
| `error_count` | 0 |
| `span_tree_complete` | true |
| `span_payload_complete` | true |
| `total_cost` | 0 |

Against the run's own files: `runs/20261011-161207/summary.json` gives Panola 172 model calls and 507.0 seconds.
The trace gives 172 `llm_calls` and a latency of 507,019 ms. The two were written by different programs and agree.
`total_cost` is 0: neatlogs reports no cost for these calls. The costs in the README are the gateway's.

## The first 40 of its 394 spans, as a tree

A county is a `workflow` span. Reading it is a `workflow` span inside. Each block of the page is a `tool_call` span,
each group of columns within a block is a `tool_call` span inside that, and each model call is an `llm` span at the leaf.

```text
panola                             workflow     507.0 s
  read_county                      workflow     397.4 s
    read_block                     tool_call      5.5 s
      claude-haiku                 llm            4.8 s
    read_block                     tool_call      8.6 s
      read_group                   tool_call      2.7 s
        claude-haiku               llm            2.6 s
      read_group                   tool_call      2.9 s
        claude-haiku               llm            2.9 s
      read_group                   tool_call      1.8 s
        claude-haiku               llm            1.8 s
    read_block                     tool_call      7.4 s
      read_group                   tool_call      2.5 s
        claude-haiku               llm            2.5 s
      read_group                   tool_call      2.2 s
        claude-haiku               llm            2.2 s
      read_group                   tool_call      1.6 s
        claude-haiku               llm            1.6 s
    read_block                     tool_call      8.4 s
      read_group                   tool_call      2.9 s
        claude-haiku               llm            2.9 s
      read_group                   tool_call      2.9 s
        claude-haiku               llm            2.9 s
      read_group                   tool_call      1.4 s
        claude-haiku               llm            1.4 s
    read_block                     tool_call      6.1 s
      read_group                   tool_call      1.9 s
        claude-haiku               llm            1.9 s
      read_group                   tool_call      1.6 s
        claude-haiku               llm            1.6 s
      read_group                   tool_call      1.4 s
        claude-haiku               llm            1.4 s
    read_block                     tool_call      6.3 s
      read_group                   tool_call      2.2 s
        claude-haiku               llm            2.2 s
      read_group                   tool_call      1.7 s
        claude-haiku               llm            1.7 s
      read_group                   tool_call      1.3 s
        claude-haiku               llm            1.3 s
    read_block                     tool_call      6.7 s
```

## One model span (`claude-haiku`, span `9acd683990e838ef`, 4.8 s)

Its input has two parts. The text is the prompt:

```text
This image is the top of a landscape election canvass sheet. It has a header row of precinct
numbers ending in TOTAL, then a registered-voters row, then a ballots-cast block with rows EARLY, ABSENTEE and
PRECINCT, then a row of small totals under the columns and a grand total under TOTAL.
Answer with strict JSON only, no prose:
{"precincts": [precinct labels left to right, as printed, excluding TOTAL],
 "registered": {"values": [one integer per precinct], "total": integer},
 "rows": {"EARLY": {"values": [...], "total": integer}, "ABSENTEE": {...}, "PRECINCT": {...}},
 "col_totals": [the small printed total under each precinct, integers],
 "grand": the grand total under the TOTAL column}
Read digits exactly as printed. Every list has one entry per precinct, in order.
```

The image is not in the trace. `tracing.mask_images` replaced the base64 picture with its size and a hash before the
span left the machine, so the span holds this instead:

```json
{"type": "image_url", "image_url": {"url": "image 2614x194 sha256:3072e8ba0476"}}
```

Its output, as the server shows it (the first 400 characters of 562):

```text
Precincts: 1
2
3
5
7
8
9
10
12
13
14
18
19
20
22
26
27
28
29
Registered: Values: 1972
2232
1459
505
888
262
726
364
439
383
308
2240
399
360
466
177
1594
2159
366
Total: 17921
Rows: EARLY: Values: 564
1112
639
280
280
93
190
134
280
124
212
1063
280
176
192
69
533
1117
104
Total: 7648
ABSENTEE: Values: 56
50
19
6
12
1
17
7
16
8
5
52
8
2
8
2
27
49
1
Total: 346
PRECINCT: Values: 254
307
328
157
288
```

## How to read it yourself

With access to the project in neatlogs: open trace `81bf9a637f8f4dcd02c763b1a1ce7592`. With the MCP server (`.mcp.json`):
`get_trace_context` with `{"trace_id": "81bf9a637f8f4dcd02c763b1a1ce7592", "limit": 40, "offset": 0, "include_evaluations": false}`.
The other traces of the final run are listed in [traces.md](traces.md).
