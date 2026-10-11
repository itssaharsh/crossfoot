import pytest

from crossfoot.sitebuild import build_county


def raw():
    cell = lambda r, c, v, box: {"page": 1, "block": "b1", "contest": "X", "candidate": "A", "row_kind": r,
                                 "column": c, "value": v, "first_read": v, "status": "accepted", "tries": 0,
                                 "model": "m", "reason": None, "box": box}
    tot = lambda d, k, v, box: {"page": 1, "block": "b1", "direction": d, "key": k, "value": v, "box": box}
    ref = lambda r, c: [1, "b1", r, c]
    return {
        "county": "tiny", "run_id": "r1", "layout": "matrix",
        "pages": [{"number": 1, "width": 2000, "height": 1000, "dpi": 200}],
        "blocks": [{"id": "b1", "page": 1, "contest": "X", "candidate": "A", "box": [100, 100, 1900, 500]}],
        "cells": [cell("A", "1", 1, [200, 200, 300, 250]), cell("A", "2", 2, None),
                  cell("B", "1", 4, [200, 250, 300, 300]), cell("B", "2", 5, [300, 250, 400, 300])],
        "totals": [tot("row", "A", 3, [1800, 200, 1900, 250]), tot("col", "1", 5, [200, 300, 300, 350]),
                   tot("grand", "", 9, [1800, 300, 1900, 350])],
        "checks": [
            {"kind": "row", "page": 1, "block": "b1", "key": "A", "terms": [[ref("A", "1"), 1], [ref("A", "2"), 2]],
             "printed": 3, "computed": 3, "ok": True},
            {"kind": "col", "page": 1, "block": "b1", "key": "1", "terms": [[ref("A", "1"), 1], [ref("B", "1"), 4]],
             "printed": 5, "computed": 5, "ok": True},
            {"kind": "grand", "page": 1, "block": "b1", "key": "", "terms": [[ref("col", "1"), 5]],
             "printed": 9, "computed": 5, "ok": False}],
        "events": [{"ts": 1.5, "kind": "check", "payload": {"a": 1}}], "summary": {}}


def test_terms_resolve_to_values():
    d = build_county(raw(), {1: (2000, 1000, 1000, 500)})
    for ch in d["checks"]:
        for i in ch["t"]:
            v = d["values"][i]
            assert (v["p"], v["b"]) == (ch["p"], ch["b"])
    row = d["checks"][0]
    assert [d["values"][i]["v"] for i in row["t"]] == [1, 2]
    assert d["values"][d["checks"][2]["t"][0]]["r"] == "col"


def test_boxes_are_scaled_and_missing_stays_null():
    d = build_county(raw(), {1: (2000, 1000, 1000, 500)})
    assert d["pages"][0]["sc"] == 0.5 and d["pages"][0]["w"] == 1000
    v = {(x["r"], x["c"]): x for x in d["values"]}
    assert v[("A", "1")]["x"] == [100.0, 100.0, 150.0, 125.0]
    assert v[("A", "2")]["x"] is None
    assert d["blocks"][0]["x"] == [50.0, 50.0, 950.0, 250.0]
    assert all(x["x"] is None or any(x["x"]) for x in d["values"])


def test_unresolved_term_is_an_error():
    r = raw()
    r["checks"][0]["terms"][0][0] = [1, "b1", "Z", "9"]
    with pytest.raises(ValueError):
        build_county(r, {1: (2000, 1000, 1000, 500)})


def test_every_block_has_a_300_dpi_image_the_size_of_its_box():
    from crossfoot.sitebuild import block_geometry, cut_block
    from PIL import Image
    d = build_county(raw(), {1: (2000, 1000, 1000, 500)})
    b = d["blocks"][0]
    # the box is 1800 x 400 px at 200 dpi, so 2700 x 600 at 300 dpi
    assert abs(b["bi"]["w"] - 2700) <= 1 and abs(b["bi"]["h"] - 600) <= 1
    assert b["bi"]["img"].endswith("tiny-b1.webp")
    # the cut has exactly that size, also when the box touches the page edge
    page = Image.new("L", (3000, 1500), 255)
    assert cut_block(page, block_geometry([100, 100, 1900, 500], 2000, 2000)).size == (b["bi"]["w"], b["bi"]["h"])
    assert cut_block(page, block_geometry([200, 100, 2000, 500], 2000, 2000)).size == (2700, 600)


def test_block_without_a_box_has_no_image():
    r = raw()
    r["blocks"][0]["box"] = None
    assert build_county(r, {1: (2000, 1000, 1000, 500)})["blocks"][0]["bi"] is None


def test_ink_box_finds_a_figure_printed_low_and_right_in_a_ruled_cell():
    from PIL import Image, ImageDraw
    from crossfoot.sitebuild import ink_box
    im = Image.new("L", (200, 100), 255)
    dr = ImageDraw.Draw(im)
    dr.rectangle([10, 10, 109, 59], outline=0, width=2)        # the ruled cell
    dr.rectangle([70, 38, 100, 52], fill=0)                    # the figure: low and right
    assert ink_box(im, [10, 10, 110, 60]) == [70, 38, 101, 53]
    # a zero is ink
    dr.rectangle([70, 38, 100, 52], fill=255)
    dr.ellipse([80, 40, 98, 52], outline=0, width=2)
    assert ink_box(im, [10, 10, 110, 60]) is not None


def test_ink_box_of_an_empty_ruled_cell_is_none():
    from PIL import Image, ImageDraw
    from crossfoot.sitebuild import ink_box
    im = Image.new("L", (200, 100), 255)
    ImageDraw.Draw(im).rectangle([10, 10, 109, 59], outline=0, width=2)
    assert ink_box(im, [10, 10, 110, 60]) is None
    assert ink_box(im, [10, 10, 12, 12]) is None


def test_values_carry_their_ink_box():
    d = build_county(raw(), {1: (2000, 1000, 1000, 500)}, ink={(1, "b1", "A", "1"): [5, 6, 20, 30]})
    v = {(x["r"], x["c"]): x for x in d["values"]}
    assert v[("A", "1")]["ix"] == [5, 6, 20, 30] and v[("B", "1")]["ix"] is None


def test_rule_top_finds_the_ruled_line_above_a_row():
    from PIL import Image, ImageDraw
    from crossfoot.sitebuild import rule_top
    im = Image.new("L", (300, 120), 255)
    ImageDraw.Draw(im).rectangle([0, 40, 299, 43], fill=0)
    assert rule_top(im, [20, 44, 120, 90]) == 40
    assert rule_top(im, [20, 100, 120, 119]) is None
