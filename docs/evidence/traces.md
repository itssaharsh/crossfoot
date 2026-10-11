# Traces (neatlogs)

Written 11 October 2026 (task T05b; it replaces the T05 note that said the neatlogs server did not answer). The server answered.
Everything below was read from the neatlogs MCP server with `search_traces` and `get_trace_context`, and from `runs/*/run.json` (start times).
Dollar costs are not given: neatlogs reports cost 0 for every trace here.

## How to open one

1. `search_traces` with a word that appears in span text (`read_group`, `read_page`, `reread`, `choose_reader`, `san_saba`, `crossfoot`; limit up to 100).
   Each result has `trace_id`, `start_ts`, `root_span_name`, `span_count`, `total_tokens`.
2. `get_trace_context` with the full 32-character `trace_id` and `limit` 5 (the options `span_types`, `span_names`, `fields`, `max_chars_per_field`
   answer `not_enabled`). Add `include_evaluations: false` to keep the answer short.
3. No run file stores its trace id. A run is paired to a trace by its start time (`run.json` `started`, UTC) against the trace's `start_ts`
   (within a few seconds) and the root span name. 27 distinct traces came back from the searches; those are all that were looked at.

## Runs and their traces

| run | what it was | trace id | root span | spans | tokens |
|---|---|---|---|---|---|
| 20261011-090307 | first Panola read (named in `before-after.md`) | `c0ad0dc20af3f7651960204384229937` | `read_county` | not re-checked | not re-checked |
| 20261011-092655 | Panola read | `a19fe3ca469fb205ca915024e09195d6` | `read_county` | 298 | 120,683 |
| 20261011-093435 | Panola read, same code as the next | `31f18982da0029240fdbd65bbf3ff3b6` | `read_county` | 297 | 119,621 |
| 20261011-094115 | Panola read (made by `pb.py verify`) | `8c2ceec449e02419a8fd147ac260d126` | `read_county` | 297 | 119,621 |
| 20261011-100540 (not committed) | Panola close | `b5b7e9fe34c976be76a1ec32f2acf2a0` | `close_county` | 1,057 | 616,017 |
| 20261011-102700 | Panola close, resumed from 094115 | `dd8cc4c0f0becf93c4313f2088bf583a` | `close_county` | 1,057 | 615,967 |
| 20261011-111955 | Panola read | `3d015fa604249ca8a337ffa7e64dcba3` | `read_county` | 342 | 134,151 |
| 20261011-112935 | Panola close (the recovery case 1 and 2 run) | none found: the only close trace near it starts at 11:27:13, two minutes before this run started (11:29:35) | | | |
| 20261011-120008 | Panola audit | `99c088c08e019a0f8d4d2796721d35e4` | `read_county` | 342 | 134,050 |
| 20261011-123542 | Limestone audit | `36471b261403c7b0865452ac77500410` | `read_county` | 2 | 1,796 |
| 20261011-125310 | San Saba audit | `cda8fe1f09ffd623d04581feefe10c01` | `read_county` | 44 | 67,292 |
| 20261011-130414 | all counties (one trace per county) | see the next table | | | |
| 20261011-135350 | Panola, resumed from 130414 | none found | | | |
| 20261011-135519 | San Saba and Cottle with a $0.25 budget; its resume (started 13:58:22) | resume: `6b289ce0c777683ca054674468c29dbd` (`cottle`, 15 spans, 28,335 tokens); first part (13:55:19): none found | | | |
| 20261011-140556, 140637, 140946, 141015, 141051, 141131, 141152, 141300 | audits and the summary run, 14:05 to 14:13 | none found: no search result starts after 13:58:22 | | | |

Not paired: `97f464407eaffed1b643c916eb7373af` (root span `crossfoot`, 13:46:49, 133 spans, 51,119 tokens). It is a run that made row re-reads;
the committed runs started near it are 20261011-134631 (13:46:31) and the one before, and its length did not match either, so no run is named.
Also unpaired: traces `1b2b6d9d3ed2b79d2b6c3ba23a29ab27` (10:03), `af57604a4e1d3c6709c1a4993681becb` (11:27), `4be491108743faf252bea983a54458bc` (12:06),
`7cc3a836964499a68c7d1915f7a4bbb3` (12:40), `dd71ba7133ee1e39c69fde33ccb84f01` (12:43), `f5f725230b92cc9e56cb9137eda6a45f`, `5d8d3ff6195914395742bb47374ea408`,
`072045a15d6725216f71654491d05021`, `bfe2cf9c3481bc66d00c15a120bb9024` (12:46 to 12:56): runs not committed.

Run 20261011-130414 (`crossfoot audit --all --budget 9`, started 13:04:17), one trace per county:

| county | trace id | spans | tokens |
|---|---|---|---|
| panola | `9a165c6af083b2efcd4dbefd82774b92` | 384 | 144,697 |
| san_saba | none found (no trace of that root name between 13:04 and 13:32 came back) | | |
| cottle | `a97a0281ca9622b1fcb8d196506af167` | 37 | 77,807 |
| jones | `abac15ed55e1e45223d2aa32af3a47af` | 287 | 178,972 |
| lynn | `4691b894519c6fc6c70c80cafdb5bf4e` | 209 | 202,704 |
| scurry | `50d31f20696f092c1bad57ab707a3a55` | 99 | 212,183 |
| foard | `ebf0bd74797782c55a481726e8f62f4a` | 39 | 66,003 |
| limestone | `0be0eecf243bc963896e378fc69f870a` | 3 | 1,796 |

## Two traces opened with `get_trace_context`

- `9a165c6af083b2efcd4dbefd82774b92` (panola, run 130414): 384 spans, 168 model calls, 213 tool calls. First spans: `claude-haiku` (llm) whose input
  carries `{"type":"image_url","image_url":{"url":"image 2614x194 sha256:3072e8ba0476"}}`, its parent `read_block` (tool_call, 5.4 s, input "This image is the top of a
  landscape election canvass sheet ..."), then `read_county` and the root `panola` (workflow, 474.9 s). A page or block is named in the span text, not as a separate attribute.
- `6b289ce0c777683ca054674468c29dbd` (cottle, the resume of run 135519): 15 spans, 7 model calls. First spans: `read_county` (workflow, 81.0 s), root `cottle`,
  two `read_page` (tool_call, 19.7 s and 17.8 s), `claude-haiku` (llm, 9.1 s) with the page prompt "TASK: page ...". Here the image does **not** show as
  `image WxH sha256:...`: it is a `neatlogs_media` record with `state: failed` and `safe_preview: "upload unavailable: backend_upload_contract_unavailable"`
  (png, 455,204 bytes, sha256 `57094643...`). The same appears in the close trace `af57604a...`: some images show as `image WxH sha256:...` and others as this failed record.
  The span's `read_page` input/output was empty; the page number is in the model's answer text only (here the precinct "401").

## The detection

- Name: **Crossfoot slow haiku call (over 20 s)**; id `ee3ce3bc-f2cc-44f6-aecb-387ebfdb3727`; kind: conditional; group Neutral; runs on spans of type LLM.
- Rule: `latency > 20000` ms AND `model = claude-haiku`.
- Why this one: the brief's first two choices could not be written. (a) A `reread*` tool span has an empty output; the value read is on its child model span, and
  "the value changed" is not on any span. (b) The repair request is not recorded as a span of its own (`crossfoot/model.py` `ask_json`). (c) a slow model call is on the span (`latency`, `model`).
  I did not change `crossfoot/tracing.py`.
- Preview (`preview_detection`, 14-day window, once): **1 span matched**, nothing else. The match: span `13de33922ba4b1e1`, a `claude-haiku` call whose input is the
  close-county planning prompt for "page 4, block p4-b6, Presiding Judge, Court of Criminal Appeals ... failing sum: row EARLY" and whose answer was `Action: reread ... row_total ... EARLY ... 400 ... claude-sonnet-4.6`.
  It is a planning call, not a page read, so the name says "haiku call" and not "read". I did not look up which trace holds that span, so no trace id is given for the match.
- Created with `create_detection`: the server answered "Detection created. A 14-day backfill is running"; `backfill_status` was `pending`. Whether it is active was not
  re-read with `list_detections` after creation, so "active" is the server's creation answer, not a second check.
- The three existing detections (Expensive LLM Call, Slow LLM Response, Execution Failed) were not touched; the fourth listed in the capabilities, "Invalid Output Format Detector", is inactive and was not touched.

## What the server refused

- `search_traces` with `fields` and `get_trace_context` with `span_types`, `span_names`, `fields` or `max_chars_per_field`: `not_enabled` (as the brief said).
- `search_traces` with the query `audit`: 0 results. Large queries (`read_page`, `reread`) return over 200,000 characters and were read from the saved output.

## The final run, `20261011-161207` (one `audit --all` from nothing on the final code)

Looked up on 11 October 2026 at about 16:40 UTC with `search_traces` (several queries, `date_from` 16:10 and `date_to` 16:40).
Each county's run is one trace whose root span is the county's name.

| county (root span) | trace id | created | spans | tokens |
|---|---|---|---|---|
| panola | `81bf9a637f8f4dcd02c763b1a1ce7592` | 2026-10-11T16:12:19Z | 394 | 149455 |
| cottle | `bd1891d1fe758139df0ad98bd57615ce` | 2026-10-11T16:22:26Z | 28 | 39130 |
| lynn | `14b7e792e783d5699783d7690b82232a` | 2026-10-11T16:25:20Z | 100 | 158331 |
| scurry | `cbca178cafefe029836b68e7a8ca802d` | 2026-10-11T16:28:48Z | 81 | 122622 |
| foard | `e1f8a232dd82db5e05ba6949c0aba98e` | 2026-10-11T16:31:10Z | 39 | 62610 |
| limestone | `f161cb8d27c4723bb29ad10e7022bdcd` | 2026-10-11T16:32:38Z | 3 | 1796 |

Not found: the traces of San Saba (started 16:20:34 UTC) and Jones (started 16:23:15 UTC). The run's log shows no
export error and the SDK reported a clean shutdown, so why these two did not arrive is not known. The same search
finds San Saba's trace of an earlier single-county run (`cda8fe1f09ffd623d04581feefe10c01`, 12:53 UTC) and Jones's
trace in the earlier run over all counties (`abac15ed55e1e45223d2aa32af3a47af`, 13:15 UTC). The runs made between
about 13:58 and 14:50 UTC have no traces at all: the service answered 503 in that time.

## San Saba and Jones on the final code, audited again for their traces

The final run's traces for these two counties never arrived, so each county was audited again by itself on the same
commit (`aefdc2e`, the commit `run.json` records) on 11 October 2026. Both traces arrived.

| county | run | command | trace id | trace started (UTC) | spans | tokens |
|---|---|---|---|---|---|---|
| san_saba | `20261011-201637` | `crossfoot audit --county san_saba --budget 0.5` | `0e8bfd5bb30d9e85fbc6276c60f1b15c` | 20:16:42 | 44 | 67,292 |
| jones | `20261011-201830` | `crossfoot audit --county jones --budget 0.5` | `4f0c85b77e6895161b8bce9675f5fe8b` | 20:18:33 | 44 | 83,954 |

- Looked up with `search_traces` (queries `san_saba`, `jones`, `read_page`, `read_county`; `date_from` 20:15, `date_to` 20:30). The search for
  `read_county` in that window returns exactly these two. Neither has an errored span. The root span of a single-county audit is `read_county`,
  not the county's name as in `audit --all`.
- The findings are those of the final run, record for record: San Saba 21 (3 settled, 18 that cannot be verified), Jones 26 (all settled).
  Compared field by field against `runs/20261011-161207/<county>/findings.json`; the only text that differs is the run id inside the path of a
  re-read crop.
- While San Saba's spans were exported the SDK logged one "Bad Gateway ... retrying"; the trace still arrived whole. That is the only hint so far
  at why two traces of the final run are missing, and it is a guess, not a finding.
- Gateway spend: $0.2010 and $0.2611. No figure in the README or on the page comes from these two runs; those are built from `20261011-161207`.

