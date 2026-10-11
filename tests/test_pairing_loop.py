"""The loop on located values: re-read where two failing sums cross, step up the ladder, say when the document
disagrees with itself. Fake model, fake page; no network."""
import json

import pytest
from PIL import Image

from crossfoot import agent, checks
from crossfoot.ledger import Ledger
from tests.test_agent import GOOD, HAIKU, SONNET, FakeGeo, FakeGw, make_block

OPUS = "claude-opus-4.6"
ROWS = agent.ROWS
GOOD3 = {"1": (10, 2, 3), "2": (20, 4, 6), "3": (5, 5, 5)}     # EARLY adds to 35, the grand total to 60


class StripGeo(FakeGeo):
    def strip_crops(self, page, bid, row, dpi, dest, per):
        self.targets.append((bid, {"kind": "row_strip", "row": row}, dpi))
        cols = list(GOOD3)
        out = []
        for i in range(0, len(cols), per):
            p = dest.with_name(f"{dest.stem}-s{i}.png")
            p.parent.mkdir(parents=True, exist_ok=True)
            Image.new("L", (10, 10), 255).save(p)
            out.append((p, cols[i:i + per], (0, 0, 10, 10)))
        return out


class Reader:
    """Answers re-reads: `says(target, model)` gives the value (or a list for a strip)."""
    def __init__(self, says):
        self.says, self.asked = says, []

    def __call__(self, bid, t, model, n):
        self.asked.append((t["kind"], model))
        v = self.says(t, model)
        if t["kind"] == "row_strip":
            return {"values": v}
        return {"value": v}


def go(led, says, decide=None, geo=None, **kw):
    geo = geo or StripGeo()
    rd = Reader(says)

    def read(bid, t, model, n):
        if t["kind"] == "row_strip":
            return {"values": rd.says(t, model)}
        return rd(bid, t, model, n)
    gw = FakeGw(geo, decide or (lambda p, n: pytest.fail("the model was asked to decide")), read)
    s = agent.close_county("x", gw, led, geo, run_id="", log=lambda *a: None, **kw)
    return s, gw, geo, rd


def events(led, kind):
    return [json.loads(e["payload_json"]) for e in led.events("x") if e["kind"] == kind]


def test_one_wrong_cell_is_reread_where_the_sums_cross_and_fixed_without_asking_the_model():
    led = Ledger()
    make_block(led, 1, "p1-b1", wrong={("EARLY", "1"): 16})
    s, gw, geo, rd = go(led, lambda t, m: 10)
    assert [t for _, t, _ in geo.targets] == [{"kind": "cell", "row": "EARLY", "column": "1"}]
    assert geo.targets[0][2] >= 400
    assert rd.asked == [("cell", HAIKU)]
    cell = next(c for c in led.cells("x") if (c["row_kind"], c["column"]) == ("EARLY", "1"))
    assert (cell["value"], cell["first_read"], cell["status"]) == (10, 16, "accepted")
    p = events(led, "reread")[0]
    assert p["changes"][0]["old"] == 16 and p["changes"][0]["new"] == 10 and p["changes"][0]["kept"] == "new"
    assert {c["status"] for c in led.cells("x")} == {"accepted"} and led.verdicts("x") == []
    assert s["calls" if "calls" in s else "model_calls"] == 1 and s["sums_failing_after"] == {"row": 0, "col": 0, "grand": 0, "grand_row": 0}


def test_a_wrong_small_total_is_reread_as_a_total_and_the_cells_are_left_alone():
    led = Ledger()
    make_block(led, 1, "p1-b1", col_totals={"2": 35})
    s, gw, geo, rd = go(led, lambda t, m: 30)
    assert [t["kind"] for _, t, _ in geo.targets] == ["col_total"]
    assert {c["value"] for c in led.cells("x")} == {c["first_read"] for c in led.cells("x")}
    assert next(t for t in led.totals("x") if (t["direction"], t["key"]) == ("col", "2"))["value"] == 30


def test_a_wrong_row_total_and_a_wrong_grand_total_are_reread_as_totals():
    led = Ledger()
    make_block(led, 1, "p1-b1", good=GOOD3, row_totals={"EARLY": 40})
    make_block(led, 1, "p1-b2", good=GOOD3, grand=99)
    s, gw, geo, rd = go(led, lambda t, m: 35 if t["kind"] == "row_total" else 60)
    assert sorted(t["kind"] for _, t, _ in geo.targets) == ["grand", "row_total"]
    assert s["sums_failing_after"] == {"row": 0, "col": 0, "grand": 0, "grand_row": 0}


def test_the_old_value_again_goes_one_step_up_and_the_stronger_reading_wins():
    led = Ledger()
    make_block(led, 1, "p1-b1", wrong={("EARLY", "1"): 16})
    s, gw, geo, rd = go(led, lambda t, m: 16 if m == HAIKU else 10)
    assert rd.asked == [("cell", HAIKU), ("cell", SONNET)]
    assert [e["changes"][0]["kept"] for e in events(led, "reread")] == ["same", "new"]
    assert {c["status"] for c in led.cells("x")} == {"accepted"}


def test_the_same_reading_twice_while_both_sums_fail_is_document_inconsistent():
    led = Ledger()
    make_block(led, 1, "p1-b1", wrong={("EARLY", "1"): 16})
    s, gw, geo, rd = go(led, lambda t, m: 16)
    assert rd.asked == [("cell", HAIKU), ("cell", SONNET)]            # two readings are enough; Opus is not asked
    cell = next(c for c in led.cells("x") if (c["row_kind"], c["column"]) == ("EARLY", "1"))
    assert cell["value"] == 16 and cell["status"] == "document_inconsistent"           # arithmetic never wrote 10
    v = {x["sum_id"]: x for x in led.verdicts("x")}
    assert set(v) == {"row:1:p1-b1:EARLY", "col:1:p1-b1:1"}
    assert all(x["verdict"] == "document_inconsistent" for x in v.values())
    reason = v["row:1:p1-b1:EARLY"]["reason"]
    assert "row sum EARLY" in reason and "column sum of precinct 1" in reason and "disagrees with itself" in reason
    assert s["verdicts"] == {"document_inconsistent": 2, "cannot_verify": 0}
    assert s["sums_failing_after"]["row"] == 1 and s["sums_failing_after"]["col"] == 1


def test_three_different_readings_end_cannot_verify_after_the_whole_ladder():
    led = Ledger()
    make_block(led, 1, "p1-b1", wrong={("EARLY", "1"): 16})
    s, gw, geo, rd = go(led, lambda t, m: {HAIKU: 17, SONNET: 18, OPUS: 19}[m])
    assert [m for _, m in rd.asked] == [HAIKU, SONNET, OPUS]
    assert {x["verdict"] for x in led.verdicts("x")} == {"cannot_verify"}
    cell = next(c for c in led.cells("x") if (c["row_kind"], c["column"]) == ("EARLY", "1"))
    assert cell["status"] == "cannot_verify" and cell["value"] == 16


def test_a_reading_that_does_not_fit_the_sums_is_not_written():
    led = Ledger()
    make_block(led, 1, "p1-b1", wrong={("EARLY", "1"): 16})
    go(led, lambda t, m: 12 if m == HAIKU else 10)       # 12 is wrong too: kept old; Sonnet's 10 fits
    ev = events(led, "reread")
    assert [e["changes"][0]["kept"] for e in ev] == ["old", "new"] and ev[0]["changes"][0]["new"] == 12


def test_a_cell_whose_column_holds_is_not_marked_when_its_row_fails_for_another_value():
    led = Ledger()
    # two wrong cells in one row (+2, +3): not locatable by pairing; the model is asked and gives up
    make_block(led, 1, "p1-b1", good=GOOD3, wrong={("EARLY", "1"): 12, ("EARLY", "2"): 23})
    s, gw, geo, rd = go(led, lambda t, m: 0, decide=lambda p, n: {"action": "cannot_verify", "reason": "cannot tell"})
    st = {(c["row_kind"], c["column"]): c["status"] for c in led.cells("x")}
    assert st[("EARLY", "1")] == st[("EARLY", "2")] == "cannot_verify"      # their columns fail too: they cannot be cleared
    assert st[("EARLY", "3")] == "first_read"                                # its column holds: not marked
    assert all(x["verdict"] == "cannot_verify" for x in led.verdicts("x")) and len(led.verdicts("x")) == 3


def test_unlocated_sums_go_to_the_model_and_a_row_strip_can_be_asked_for():
    led = Ledger()
    make_block(led, 1, "p1-b1", good=GOOD3, wrong={("EARLY", "1"): 12, ("EARLY", "2"): 23})
    strip = {"action": "reread", "rereads": [{"target": {"kind": "row_strip", "row": "EARLY"}, "dpi": 400,
                                              "model": "  CLAUDE-HAIKU "}]}      # a name to be trimmed and lower-cased
    seen = []
    s, gw, geo, rd = go(led, lambda t, m: [10, 20, 5], decide=lambda p, n: seen.append(p) or strip)
    assert gw.log[0][0] == agent.DECIDER == SONNET                # decisions are made by claude-sonnet-4.6
    assert "row_strip" in seen[0]
    assert [t["kind"] for _, t, _ in geo.targets] == ["row_strip"]
    assert {c["status"] for c in led.cells("x")} == {"accepted"}
    assert [c["value"] for c in led.cells("x") if c["row_kind"] == "EARLY"] == [10, 20, 5]


def test_an_unknown_model_name_falls_back_to_the_next_step_instead_of_stopping_the_item():
    led = Ledger()
    make_block(led, 1, "p1-b1", good=GOOD3, wrong={("EARLY", "1"): 12, ("EARLY", "2"): 23})
    asks = [{"action": "reread", "rereads": [{"target": {"kind": "cell", "row": "EARLY", "column": c}, "dpi": 400,
                                              "model": "claude-banana-9"}]} for c in ("1", "2")]
    geo = StripGeo()
    s, gw, geo, rd = go(led, lambda t, m: {"1": 10, "2": 20}[t["column"]], decide=lambda p, n: asks[min(n, 1)], geo=geo)
    assert [m for _, m in rd.asked] == [HAIKU, HAIKU]
    assert not [e for e in events(led, "decision") if "error" in e]
    assert {c["status"] for c in led.cells("x")} == {"accepted"}


def test_a_target_is_not_reread_twice_with_the_same_model_and_dpi_and_the_refusal_counts():
    led = Ledger()
    make_block(led, 1, "p1-b1", good=GOOD3, wrong={("EARLY", "1"): 12, ("EARLY", "2"): 23})
    same = {"action": "reread", "rereads": [{"target": {"kind": "cell", "row": "EARLY", "column": "1"}, "dpi": 400,
                                             "model": HAIKU}] * 3}
    s, gw, geo, rd = go(led, lambda t, m: 12, decide=lambda p, n: same if n == 0 else {"action": "done"})
    assert len(geo.targets) == 1
    ref = events(led, "refused")
    assert len(ref) == 2 and "already been re-read" in ref[0]["reason"]


def test_resume_skips_accepted_values_and_does_not_ask_again():
    led = Ledger()
    make_block(led, 1, "p1-b1", wrong={("EARLY", "1"): 16})
    go(led, lambda t, m: 10)
    s, gw, geo, rd = go(led, lambda t, m: pytest.fail("re-read"))
    assert gw.calls == 0 and geo.targets == []


def test_every_failing_sum_at_the_end_has_a_verdict_and_a_reason():
    led = Ledger()
    make_block(led, 1, "p1-b1", wrong={("EARLY", "1"): 16})
    make_block(led, 1, "p1-b2", col_totals={"2": 35})
    s, gw, geo, rd = go(led, lambda t, m: 16 if t["kind"] == "cell" else 35)
    cells, totals = led.cells("x"), led.totals("x")
    failing = {agent.sum_id(c) for c in checks.all_checks(cells, totals) if not c.ok}
    assert failing == {v["sum_id"] for v in led.verdicts("x")}
    assert all(v["reason"] and v["verdict"] in ("document_inconsistent", "cannot_verify") for v in led.verdicts("x"))
