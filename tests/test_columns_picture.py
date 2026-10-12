"""Which columns of a block are blacked out is read from the picture, and a block whose answer disagrees is realigned
or failed. Real crops of Panola page 6 (tests/fixtures) and a drawn page with a fake model. No network."""
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from crossfoot.layouts import matrix
from crossfoot.ledger import Ledger
from crossfoot.model import Gateway
from tests.test_budget import FakeClient
from tests.test_segment import ruled

FX = Path(__file__).parent / "fixtures"
GEO = json.loads((FX / "panola_p6_geometry.json").read_text())
# the 19 precinct labels of Panola in the order the page-1 header gives them (the ledger's `reg` row)
PRECINCTS = ["1", "2", "3", "5", "7", "8", "9", "10", "12", "13", "14", "18", "19", "20", "22", "26", "27", "28", "29"]


def filled(name):
    g = GEO[name]
    gray = np.asarray(Image.open(FX / f"panola_p6_{name}.png").convert("L"))
    return matrix.filled_columns(gray, tuple(g["origin"]), GEO["edges"], g["rule_y0"], g["rule_y1"])


def labels(idx):
    return [PRECINCTS[i] for i in idx]


def test_p6_b2_is_filled_under_7_8_9_10_22_27():
    assert labels(filled("b2")) == ["7", "8", "9", "10", "22", "27"]


def test_p6_b4_is_filled_under_2_3_5_7_8_9_10_22_27():
    assert labels(filled("b4")) == ["2", "3", "5", "7", "8", "9", "10", "22", "27"]


def test_a_block_with_no_black_cell_has_all_19_columns_filled():
    assert filled("b0") == list(range(19))


def test_a_cell_that_is_only_partly_dark_is_not_blacked_out():
    gray = np.full((100, 400), 255, dtype=np.uint8)
    gray[10:90, 100:200] = 0          # column 1: solid in all three rows
    gray[10:40, 200:300] = 0          # column 2: only the top row
    out = matrix.blacked_out(gray, (0, 0), [0, 100, 200, 300, 400], 10, 90)
    assert out == [False, True, False, False]


# ---- the read: a drawn page, five precincts, block 1 has columns 1 and 3 blacked out ----

N = 5
X0, COLW = 100, 100


def page(tmp_path):
    d = tmp_path / "pages" / "x"
    d.mkdir(parents=True)
    im = Image.new("L", (800, 60 + 160 * 3), 255)
    dr = ImageDraw.Draw(im)
    for k in range(3):
        ruled(dr, 60 + 160 * k, ncols=N + 1, x0=X0, colw=COLW)
    y = 60 + 160
    for c in (1, 3):
        dr.rectangle([X0 + (c + 1) * COLW + 3, y + 3, X0 + (c + 2) * COLW - 3, y + 69], fill=0)
    im.save(d / "p01-200.png")
    im.resize((int(im.width * 1.5), int(im.height * 1.5))).save(d / "p01-300.png")


def header():
    row = lambda v: {"values": [v] * N, "total": v * N}
    return json.dumps({"precincts": [f"p{k}" for k in range(N)], "registered": row(9),
                       "rows": {"EARLY": row(1), "ABSENTEE": row(2), "PRECINCT": row(3)}, "col_totals": [6] * N,
                       "grand": 6 * N})


def block(at):
    """A block answer with a value (the column's index + 1) under each column in `at`, null elsewhere."""
    vals = lambda k: [(c + 1) * k if c in at else None for c in range(N)]
    row = lambda k: {"values": vals(k), "total": 7}
    return json.dumps({"contest": "C", "candidate": "Cand", "rows": {"EARLY": row(1), "ABSENTEE": row(2),
                       "PRECINCT": row(3)}, "col_totals": vals(6), "grand": 7})


def read(tmp_path, middle):
    page(tmp_path)
    c = FakeClient([header(), middle, block(range(N))])
    led = Ledger()
    s = matrix.read_county("x", Gateway(client=c, sleep=lambda s_: None, min_interval=0), led, pages=[1],
                           data_root=tmp_path, run_id="", model="m")
    return s, led


def cols_of(led, bid):
    return sorted({c["column"] for c in led.cells("x") if c["block_id"] == bid})


def test_the_drawn_page_has_the_blacked_out_columns_the_test_means(tmp_path):
    page(tmp_path)
    from crossfoot.segment import find_blocks
    from crossfoot.render import page_png
    png = page_png("x", 1, 200, tmp_path)
    bl = find_blocks(png)
    edges = matrix._edges(bl, N)
    gray = np.asarray(Image.open(png).convert("L"))
    assert matrix.filled_columns(gray, (0, 0), edges, bl[1].rule_y0, bl[1].rule_y1) == [0, 2, 4]


def test_an_answer_that_agrees_with_the_picture_is_untouched(tmp_path):
    s, led = read(tmp_path, block([0, 2, 4]))
    assert s["blocks_failed"] == 0
    assert cols_of(led, "p1-b1") == ["p0", "p2", "p4"]
    assert not [e for e in led.events("x") if e["kind"] == "columns_realigned"]


def test_an_answer_shifted_by_one_column_is_realigned_and_the_event_is_written(tmp_path):
    s, led = read(tmp_path, block([0, 2, 3]))      # the model put the last two filled columns one place early
    assert s["blocks_failed"] == 0
    assert cols_of(led, "p1-b1") == ["p0", "p2", "p4"]
    got = {(c["row_kind"], c["column"]): c["value"] for c in led.cells("x") if c["block_id"] == "p1-b1"}
    assert got[("EARLY", "p0")] == 1 and got[("EARLY", "p2")] == 3 and got[("EARLY", "p4")] == 4   # values moved with it
    assert {(t["direction"], t["key"]): t["value"] for t in led.totals("x") if t["block_id"] == "p1-b1"}[("col", "p4")] == 24
    ev = [json.loads(e["payload_json"]) for e in led.events("x") if e["kind"] == "columns_realigned"]
    assert len(ev) == 1
    assert ev[0]["block"] == "p1-b1" and ev[0]["columns_model"] == ["p0", "p2", "p3"] and \
        ev[0]["columns_picture"] == ["p0", "p2", "p4"]


def test_a_different_count_of_filled_columns_fails_the_block(tmp_path):
    s, led = read(tmp_path, block([0, 2]))
    assert s["blocks_failed"] == 1
    assert {c["status"] for c in led.cells("x") if c["block_id"] == "p1-b1"} == {"failed"}
    assert [e["kind"] for e in led.events("x")].count("block_failed") == 1
    assert not [e for e in led.events("x") if e["kind"] == "columns_realigned"]
