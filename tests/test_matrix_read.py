"""read_county on a drawn two-block page with a fake gateway: cells, totals, failure handling. No network."""
import json

from PIL import Image, ImageDraw

from crossfoot.layouts import matrix
from crossfoot.ledger import Ledger
from crossfoot.model import Gateway
from tests.test_budget import FakeClient
from tests.test_segment import ruled


def page(tmp_path):
    d = tmp_path / "pages" / "x"
    d.mkdir(parents=True)
    im = Image.new("L", (1000, 600), 255)
    dr = ImageDraw.Draw(im)
    ruled(dr, 60, ncols=7, x0=100)
    ruled(dr, 220, ncols=7, x0=100)
    ruled(dr, 380, ncols=7, x0=100)
    im.save(d / "p01-200.png")


def block(c, e, a, p, tot):
    row = lambda v, t: {"values": [v], "total": t}
    return json.dumps({"contest": c, "candidate": "Cand", "rows": {"EARLY": row(e, e), "ABSENTEE": row(a, a),
                       "PRECINCT": row(p, p)}, "col_totals": [e + a + p], "grand": tot})


def header():
    row = lambda v: {"values": [v], "total": v}
    return json.dumps({"precincts": ["1"], "registered": row(9), "rows": {"EARLY": row(1), "ABSENTEE": row(2),
                       "PRECINCT": row(3)}, "col_totals": [6], "grand": 6})


def test_reads_blocks_into_ledger(tmp_path):
    page(tmp_path)
    c = FakeClient([header(), block("Pres", 1, 2, 3, 6), block(None, 4, 5, 6, 99)])
    led = Ledger()
    s = matrix.read_county("x", Gateway(client=c, sleep=lambda s_: None, min_interval=0), led, pages=[1],
                           data_root=tmp_path, run_id="")
    assert s["blocks_found"] == 3 and s["blocks_failed"] == 0
    cells = led.cells("x")
    assert len(cells) == 10
    assert {c["contest"] for c in cells if c["block_id"] == "p1-b2"} == {"Pres"}  # carried over
    assert s["grand_sums_fail"] == 1 and s["grand_sums_pass"] == 2
    assert s["row_sums_fail"] == 0


def test_wrong_column_count_then_failure_marks_block(tmp_path):
    page(tmp_path)
    bad = json.dumps({"rows": {}})
    c = FakeClient([header(), bad, bad, block("P", 1, 1, 1, 3), block("P", 1, 1, 1, 3)])
    led = Ledger()
    s = matrix.read_county("x", Gateway(client=c, sleep=lambda s_: None, min_interval=0), led, pages=[1],
                           data_root=tmp_path, run_id="")
    assert s["blocks_failed"] == 1 and s["stopped"] is None
    assert any(c["status"] == "failed" for c in led.cells("x"))
