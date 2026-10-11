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
