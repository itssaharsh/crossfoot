"""The investigation loop's rules, with a fake model and a fake page. No network, no images of real scans."""
import json

import pytest
from PIL import Image

from crossfoot import agent, outputs, tracing
from crossfoot.ledger import Ledger

ROWS = ("EARLY", "ABSENTEE", "PRECINCT")
GOOD = {"1": (10, 2, 3), "2": (20, 4, 6)}     # column -> EARLY, ABSENTEE, PRECINCT
HAIKU, SONNET = "claude-haiku", "claude-sonnet-4.6"


def make_block(led, page, bid, good=GOOD, wrong=None, row_totals=None, col_totals=None, grand=None):
    """A block whose printed totals are those of `good`; `wrong` maps (row, column) -> the value the first read gave."""
    wrong = wrong or {}
    for col, vals in good.items():
        for r, v in zip(ROWS, vals):
            led.put_cell("x", page, bid, r, col, wrong.get((r, col), v), contest="C", candidate=f"cand {bid}")
        led.put_total("x", page, bid, "col", col, (col_totals or {}).get(col, sum(vals)))
    for i, r in enumerate(ROWS):
        led.put_total("x", page, bid, "row", r, (row_totals or {}).get(r, sum(v[i] for v in good.values())))
    led.put_total("x", page, bid, "grand", "", grand if grand is not None else sum(sum(v) for v in good.values()))


class FakeGeo:
    def __init__(self):
        self.targets = []

    def crop(self, page, bid, target, dpi, dest):
        self.targets.append((bid, dict(target), dpi))
        dest.parent.mkdir(parents=True, exist_ok=True)
        Image.new("L", (10, 10), 255).save(dest)
        return dest, (0, 0, 10, 10)

    def total_box(self, page, bid, direction, key):
        return None

    def block_box(self, page, bid):
        return None


class FakeGw:
    """Decisions come from `decide(prompt, n)`, re-reads from `read(target, model, n)`. Logs every call."""
    def __init__(self, geo, decide, read, model=HAIKU):
        self.geo, self.decide, self.read, self.model = geo, decide, read, model
        self.calls = self.prompt_tokens = self.completion_tokens = 0
        self.cost = 0.0
        self.log = []

    def ask_json(self, prompt, image=None, *, validate=None, model=None):
        self.calls += 1
        model = model or self.model
        if image is None:
            ans = self.decide(prompt, sum(1 for m, k, _ in self.log if k == "decide"))
            self.log.append((model, "decide", prompt))
        else:
            bid, target, dpi = self.geo.targets[-1]
            ans = self.read(bid, target, model, sum(1 for m, k, _ in self.log if k == "read"))
            self.log.append((model, "read", (bid, target, dpi)))
        if validate:
            validate(ans)
        return ans


def reread_col(col, model=HAIKU, dpi=300):
    return {"action": "reread", "rereads": [{"target": {"kind": "column", "column": col}, "dpi": dpi, "model": model}]}


def truth_reader(good=GOOD):
    def read(bid, t, model, n):
        if t["kind"] == "column":
            e, a, p = good[t["column"]]
            return {"EARLY": e, "ABSENTEE": a, "PRECINCT": p, "total": e + a + p}
        if t["kind"] == "cell":
            return {"value": good[t["column"]][ROWS.index(t["row"])]}
        raise AssertionError(t)
    return read


def run(led, decide, read, **kw):
    geo = FakeGeo()
    gw = FakeGw(geo, decide, read)
    s = agent.close_county("x", gw, led, geo, run_id="", log=lambda *a: None, **kw)
    return s, gw, geo


def assert_status_rule(led):
    """AC-1: no accepted cell sits on a failing printed sum, and every cell ends accepted or cannot_verify."""
    from crossfoot import checks
    cells, totals = led.cells("x"), led.totals("x")
    bad = {k for ch in checks.row_checks(cells, totals) + checks.column_checks(cells, totals) if not ch.ok
           for k, _ in ch.terms}
    for c in cells:
        assert c["status"] in ("accepted", "cannot_verify"), c
        if c["status"] == "accepted":
            assert checks.cell_key(c) not in bad


def test_closes_a_misread_cell_and_records_both_readings():
    led = Ledger()
    make_block(led, 1, "p1-b1", wrong={("EARLY", "1"): 16})
    s, gw, geo = run(led, lambda p, n: reread_col("1"), truth_reader())
    assert_status_rule(led)
    assert {c["status"] for c in led.cells("x")} == {"accepted"}
    cell = next(c for c in led.cells("x") if c["row_kind"] == "EARLY" and c["column"] == "1")
    assert (cell["value"], cell["first_read"]) == (10, 16)
    ev = [e for e in led.events("x") if e["kind"] == "reread"]
    p = json.loads(ev[0]["payload_json"])
    assert p["changes"][0]["old"] == 16 and p["changes"][0]["new"] == 10 and p["model"] == HAIKU and p["dpi"] == 300
    kinds = [e["kind"] for e in led.events("x")]
    assert kinds.index("decision") < kinds.index("reread") < kinds.index("check")
    assert s["cells_changed"] == 1 and s["sums_failing_before"]["row"] == 1 and s["sums_failing_after"]["row"] == 0


def test_a_worse_reading_is_not_kept():
    led = Ledger()
    make_block(led, 1, "p1-b1", wrong={("EARLY", "1"): 16})
    # first the re-read makes it worse (EARLY 99), then it is right
    def read(bid, t, model, n):
        e, a, p = GOOD[t["column"]]
        return {"EARLY": 99 if n == 0 else e, "ABSENTEE": a, "PRECINCT": p, "total": e + a + p}
    s, gw, geo = run(led, lambda p, n: reread_col("1"), read)
    ev = [json.loads(e["payload_json"]) for e in led.events("x") if e["kind"] == "reread"]
    assert ev[0]["changes"][0]["new"] == 99 and ev[0]["changes"][0]["kept"] == "old"
    assert ev[1]["changes"][0]["kept"] == "new"
    assert_status_rule(led)


def test_row_total_misread_is_fixed_by_rereading_the_total_not_the_cells():
    led = Ledger()
    make_block(led, 1, "p1-b1", row_totals={"EARLY": 35})        # printed EARLY total misread: 35 for 30
    seen = []
    def decide(prompt, n):
        seen.append(prompt)
        return {"action": "reread", "rereads": [{"target": {"kind": "row_total", "row": "EARLY"}, "dpi": 400,
                                                 "model": HAIKU}]}
    s, gw, geo = run(led, decide, lambda b, t, m, n: {"value": 30})
    assert "look at the row's printed total first" in seen[0]
    assert [t[1]["kind"] for t in geo.targets] == ["row_total"]
    assert {c["status"] for c in led.cells("x")} == {"accepted"}
    assert all(c["value"] == c["first_read"] for c in led.cells("x"))
    assert_status_rule(led)


def test_small_total_hint_when_the_rows_pass():
    led = Ledger()
    make_block(led, 1, "p1-b1", col_totals={"1": 99})
    seen = []
    def decide(prompt, n):
        seen.append(prompt)
        return {"action": "cannot_verify", "reason": "test"}
    run(led, decide, truth_reader())
    assert "look at the small total first" in seen[0]


def test_six_actions_then_cannot_verify_and_the_loop_goes_on():
    led = Ledger()
    make_block(led, 1, "p1-b1", wrong={("EARLY", "1"): 16})
    make_block(led, 1, "p1-b2", wrong={("EARLY", "2"): 21})
    stuck = lambda bid, t, m, n: ({"EARLY": 16, "ABSENTEE": 2, "PRECINCT": 3, "total": 15} if bid == "p1-b1"
                                  else {"EARLY": 20, "ABSENTEE": 4, "PRECINCT": 6, "total": 30})
    def decide(prompt, n):
        col = "1" if "p1-b1" in prompt else "2"
        return reread_col(col, model=HAIKU)
    s, gw, geo = run(led, decide, stuck)
    first = [t for t in geo.targets if t[0] == "p1-b1"]
    assert len(first) == 6
    stat = {(c["block_id"], c["row_kind"], c["column"]): c["status"] for c in led.cells("x")}
    assert stat[("p1-b1", "EARLY", "1")] == "cannot_verify"
    assert all(v == "accepted" for k, v in stat.items() if k[0] == "p1-b2")
    stops = [json.loads(e["payload_json"]) for e in led.events("x") if e["kind"] == "stop"]
    assert any("six actions" in p["reason"] for p in stops)
    assert s["cells_cannot_verify"] == 2 + 0 or s["cells_cannot_verify"] >= 1
    assert_status_rule(led)


def test_a_decision_may_list_several_rereads_and_they_count_one_each():
    led = Ledger()
    make_block(led, 1, "p1-b1", wrong={("EARLY", "1"): 16})
    many = {"action": "reread", "rereads": [{"target": {"kind": "cell", "row": "EARLY", "column": "1"},
                                             "dpi": 300, "model": HAIKU}] * 8}
    s, gw, geo = run(led, lambda p, n: many if n == 0 else {"action": "done"},
                     lambda b, t, m, n: {"value": 16})
    assert len(geo.targets) == 6


def test_stronger_model_is_refused_until_two_haiku_rereads_failed():
    led = Ledger()
    make_block(led, 1, "p1-b1", wrong={("EARLY", "1"): 16})
    plan = [reread_col("1", model=SONNET), reread_col("1"), reread_col("1"), reread_col("1", model=SONNET)]
    def read(bid, t, model, n):
        e, a, p = GOOD["1"]
        return {"EARLY": 16 if model == HAIKU else 10, "ABSENTEE": a, "PRECINCT": p, "total": e + a + p}
    s, gw, geo = run(led, lambda p, n: plan[min(n, 3)], read)
    models = [m for m, k, _ in gw.log if k == "read"]
    assert models == [HAIKU, HAIKU, SONNET]            # the first Sonnet request never reached the model
    refused = [json.loads(e["payload_json"]) for e in led.events("x") if e["kind"] == "refused"]
    assert len(refused) == 1 and "two re-reads" in refused[0]["reason"]
    assert {c["status"] for c in led.cells("x")} == {"accepted"}


def test_check_model_rule_directly():
    item = agent.Item("row", 1, "b", "EARLY")
    with pytest.raises(agent.StrongModelRefused):
        agent.check_model(item, SONNET)
    item.weak_failures = 2
    agent.check_model(item, SONNET)
    agent.check_model(item, HAIKU)
    with pytest.raises(ValueError):
        agent.check_model(item, "some-other-model")


def test_resume_never_asks_about_accepted_cells():
    led = Ledger()
    make_block(led, 1, "p1-b1")                                    # holds: will be accepted
    make_block(led, 1, "p1-b2", wrong={("EARLY", "1"): 16})
    agent.derive_status(led, "x")
    assert {c["status"] for c in led.cells("x") if c["block_id"] == "p1-b1"} == {"accepted"}
    s, gw, geo = run(led, lambda p, n: reread_col("1"), truth_reader())
    assert all(t[0] == "p1-b2" for t in geo.targets)
    assert all("p1-b1" not in m[2] for m in gw.log if m[1] == "decide")
    # a second close over the finished ledger asks nothing at all
    s2, gw2, geo2 = run(led, lambda p, n: pytest.fail("asked"), lambda *a: pytest.fail("read"))
    assert gw2.calls == 0


def test_rereading_an_accepted_cell_is_refused_by_code():
    led = Ledger()
    make_block(led, 1, "p1-b1", wrong={("EARLY", "1"): 16})
    cell = {"action": "reread", "rereads": [{"target": {"kind": "cell", "row": "ABSENTEE", "column": "2"},
                                             "dpi": 300, "model": HAIKU}]}
    # ABSENTEE col 2 sits on passing sums, so it is accepted at the start and must not be re-read
    s, gw, geo = run(led, lambda p, n: cell if n == 0 else {"action": "cannot_verify", "reason": "no"},
                     truth_reader())
    assert geo.targets == []
    assert any(e["kind"] == "refused" for e in led.events("x"))


def test_max_items_leaves_the_rest_open():
    led = Ledger()
    make_block(led, 1, "p1-b1", wrong={("EARLY", "1"): 16})
    make_block(led, 1, "p1-b2", wrong={("EARLY", "2"): 21})
    s, gw, geo = run(led, lambda p, n: reread_col("1" if "p1-b1" in p else "2"), truth_reader(), max_items=1)
    open_ = [c for c in led.cells("x") if c["status"] not in ("accepted", "cannot_verify")]
    assert open_ and all(c["block_id"] == "p1-b2" for c in open_)


def test_unusable_decision_marks_the_item_cannot_verify():
    led = Ledger()
    make_block(led, 1, "p1-b1", wrong={("EARLY", "1"): 16})
    s, gw, geo = run(led, lambda p, n: {"action": "dance"}, truth_reader())
    assert_status_rule(led)
    assert s["cells_cannot_verify"] > 0


def test_every_cell_is_closed_one_way_or_the_other():
    led = Ledger()
    make_block(led, 1, "p1-b1", wrong={("EARLY", "1"): 16})
    s, gw, geo = run(led, lambda p, n: {"action": "cannot_verify", "reason": "cannot see it"}, truth_reader())
    assert_status_rule(led)
    assert {c["status"] for c in led.cells("x") if c["column"] == "1" and c["row_kind"] == "EARLY"} == {"cannot_verify"}


def test_enlarge_makes_digits_at_least_40_px():
    assert agent.scale_for(300, "cell") * agent.digit_px(300, "cell") >= 40
    assert agent.scale_for(400, "col_total") * agent.digit_px(400, "col_total") >= 40
    assert agent.scale_for(400, "cell") >= 1


def test_county_json_has_the_documented_fields(tmp_path):
    led = Ledger()
    make_block(led, 1, "p1-b1", wrong={("EARLY", "1"): 16})
    s, gw, geo = run(led, lambda p, n: reread_col("1"), truth_reader())
    out = outputs.write_county(tmp_path, "x", "run1", led, FakeGeo(), s, pages=[])
    d = json.loads(out.read_text())
    for k in ("county", "run_id", "layout", "pages", "blocks", "cells", "totals", "checks", "events", "summary"):
        assert k in d
    assert {"page", "block", "row_kind", "column", "value", "first_read", "status", "tries", "model", "box"} <= set(d["cells"][0])
    assert {"kind", "page", "block", "key", "terms", "printed", "computed", "ok"} <= set(d["checks"][0])
    assert {"ts", "kind", "payload"} <= set(d["events"][0])


def test_mask_replaces_images_with_a_short_reference():
    import base64, io
    buf = io.BytesIO()
    Image.new("L", (30, 20), 200).save(buf, format="PNG")
    url = "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()
    span = {"name": "x", "input": [{"content": [{"type": "image_url", "image_url": {"url": url}}, "text"]}],
            "attributes": {"k": url}}
    out = tracing.mask_images(span)
    ref = out["input"][0]["content"][0]["image_url"]["url"]
    assert ref.startswith("image 30x20 sha256:") and len(ref.split("sha256:")[1]) == 12
    assert out["attributes"]["k"] == ref and "base64" not in json.dumps(out)
    assert out["input"][0]["content"][1] == "text"


def test_two_rereads_that_agree_win_a_tie():
    led = Ledger()
    # EARLY col 1 and col 2 both wrong, so fixing one cell alone changes no count of holding sums
    make_block(led, 1, "p1-b1", wrong={("EARLY", "1"): 16, ("EARLY", "2"): 25})
    seq = iter([("1", 11), ("1", 11)])
    def read(bid, t, model, n):
        e, a, p = GOOD[t["column"]]
        return {"EARLY": 11 if t["column"] == "1" else 25, "ABSENTEE": a, "PRECINCT": p, "total": e + a + p}
    s, gw, geo = run(led, lambda p, n: reread_col("1") if n < 2 else {"action": "cannot_verify", "reason": "x"}, read)
    ev = [json.loads(e["payload_json"]) for e in led.events("x") if e["kind"] == "reread"]
    assert [x["changes"][0]["kept"] for x in ev] == ["old", "new"]


def test_decision_prompt_names_crossing_cells():
    led = Ledger()
    make_block(led, 1, "p1-b1", wrong={("EARLY", "1"): 16})
    seen = []
    run(led, lambda p, n: seen.append(p) or {"action": "cannot_verify", "reason": "x"}, truth_reader())
    assert "EARLY/1" in seen[0] and "cross" in seen[0]
