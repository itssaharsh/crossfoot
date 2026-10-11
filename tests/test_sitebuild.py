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


def findings_doc():
    ref = lambda r, c: [1, "b1", r, c]
    sums = [{"name": "the cells of precinct 1 add to the small total", "kind": "col", "page": 1, "block": "b1",
             "terms": [{"cell": ref("A", "1"), "value": 1}, {"cell": ref("B", "1"), "value": 4}], "printed": 5,
             "printed_label": "small total printed under the column", "computed_with_scan": 5, "holds_with_scan": True,
             "computed_with_file": 4, "holds_with_file": False}]
    f = lambda i, **kw: {"id": i, "group": "g1", "county": "tiny", "office": "X", "district": "", "party": "",
                         "candidate": "A", "precinct": "1", "part": "early_voting", "file_value": 0, "scan_value": 1,
                         "kind": "wrong_column", "status": "settled_against_file", "reason": "r", "sums": sums,
                         "page": 1, "block": "b1", "box": [200, 200, 300, 250], "crop": "crops/g1.png",
                         "reread": None, "confirmed_by_person": False, **kw}
    return {"county": "tiny", "run_id": "r1", "file": "x.csv",
            "counts": {"findings": 2, "by_kind": {"wrong_column": 2}, "by_status": {"settled_against_file": 2},
                       "groups": 1, "corrections": 1},
            "findings": [f("f1"), f("f2", part="votes", precinct="9", box=[1, 1, 2, 2], file_value=None,
                               reread={"value": 7}, reread_disagrees=True)],
            "groups": [{"id": "g1", "kind": "wrong_column", "office": "X", "district": "", "candidate": "A",
                        "precincts": ["1"], "page": 1, "block": "b1", "findings": ["f1", "f2"], "crop": "crops/g1.png"}]}


def test_findings_resolve_to_values_and_leave_out_what_is_missing():
    run = {"reader": "m1", "seconds": 60.0, "sample": {"row_sums": 22, "failing": 6, "sampled_with": "m0"}}
    d = build_county(raw(), {1: (2000, 1000, 1000, 500)}, findings=findings_doc(), run=run,
                     findings_path="runs/r1/tiny/findings.json", evidence="data/tiny-findings.json",
                     crop_path=lambda county, gid, src: f"data/crops/{county}-{gid}.png")
    fd = d["fd"]
    v = {(x["r"], x["c"]): i for i, x in enumerate(d["values"])}
    f1, f2 = fd["items"]
    assert f1["ref"] == v[("A", "1")] and d["values"][f1["ref"]]["v"] == 1
    assert f1["row"] == "A" and f1["file"] == 0 and f1["scan"] == 1          # a zero is a value, not a missing one
    assert [d["values"][t[0]]["v"] for t in f1["sums"][0]["terms"]] == [1, 4]
    assert f1["sums"][0]["holds_file"] is False and f1["sums"][0]["with_file"] == 4
    assert "ref" not in f2 and "file" not in f2                               # no place on the sheet, no file value
    assert f2["reread_disagrees"] is True and f2["reread_value"] == 7 and "reread_disagrees" not in f1
    assert fd["groups"][0]["crop"] == "data/crops/tiny-g1.png" and fd["groups"][0]["row"] == "A"
    assert fd["counts"]["confirmed"] == 0 and fd["counts"]["findings"] == 2
    assert fd["path"] == "runs/r1/tiny/findings.json" and fd["evidence"] == "data/tiny-findings.json"
    assert "sums_check" not in fd
    assert fd["figures"] == {"cells": 4, "right_first": 4, "right_after": 0, "disagreements": 2, "settled": 2}
    assert fd["run_info"] == {"reader": "m1", "seconds": 60.0, "sample": run["sample"]}
    assert "run_info" not in build_county(raw(), {1: (2000, 1000, 1000, 500)}, findings=findings_doc())["fd"]


def test_no_findings_file_means_no_fd_and_a_missing_crop_is_left_out():
    assert "fd" not in build_county(raw(), {1: (2000, 1000, 1000, 500)})
    d = build_county(raw(), {1: (2000, 1000, 1000, 500)}, findings=findings_doc())
    assert "crop" not in d["fd"]["groups"][0]


def test_sums_check_is_passed_on_when_the_file_has_one():
    doc = findings_doc()
    doc["sums_check"] = {"checked": 3, "failing": 0}
    assert build_county(raw(), {1: (2000, 1000, 1000, 500)}, findings=doc)["fd"]["sums_check"] == doc["sums_check"]


def test_terms_without_values_and_the_two_grand_sums():
    r = raw()
    r["checks"][2]["kind"] = "grand_col"
    r["checks"][2]["terms"] = [[1, "b1", "col", "1"]]
    r["checks"].append({"kind": "grand_row", "page": 1, "block": "b1", "key": "", "terms": [[1, "b1", "row", "A"]],
                        "printed": 9, "computed": 3, "ok": False})
    d = build_county(r, {1: (2000, 1000, 1000, 500)})
    assert [c["k"] for c in d["checks"]] == ["row", "col", "grand", "grand_row"]
    assert d["values"][d["checks"][3]["t"][0]]["r"] == "row"


def test_latest_is_the_newest_run_with_findings(tmp_path):
    from crossfoot.sitebuild import latest_run
    for rid, has in (("20261011-100000", True), ("20261011-110000", True), ("20261011-120000", False)):
        (tmp_path / rid / "c").mkdir(parents=True)
        if has:
            (tmp_path / rid / "c" / "findings.json").write_text("{}")
    assert latest_run(tmp_path) == "20261011-110000"


def test_verdicts_and_the_summary_figures_are_passed_on():
    r = raw()
    r["verdicts"] = [{"sum": "col:1:b1:1", "page": 1, "block": "b1", "verdict": "cannot_verify", "reason": "why", "entity": None}]
    r["summary"] = {"sums_failing_before": {"row": 1}, "model_calls": 3}
    d = build_county(r, {1: (2000, 1000, 1000, 500)})
    assert d["vd"] == [{"s": "col:1:b1:1", "v": "cannot_verify", "r": "why", "e": None}]
    assert d["sm"] == {"sums_failing_before": {"row": 1}}               # only the figures the replay reads
    bare = build_county(raw(), {1: (2000, 1000, 1000, 500)})
    assert "vd" not in bare and "sm" not in bare


def test_total_seconds_adds_the_runs_a_run_resumed(tmp_path):
    import json
    from crossfoot.sitebuild import total_seconds
    for rid, meta in (("a", {"seconds": 600.0, "resumed_from": None}), ("b", {"seconds": 100.0, "resumed_from": "a"}),
                      ("c", {"resumed_from": "b"})):
        (tmp_path / rid).mkdir()
        (tmp_path / rid / "run.json").write_text(json.dumps(meta))
    read = lambda rid: json.loads((tmp_path / rid / "run.json").read_text())
    assert total_seconds(read("a"), tmp_path) == 600.0
    assert total_seconds(read("b"), tmp_path) == 700.0
    assert total_seconds({"seconds": 5.0, "resumed_from": "c"}, tmp_path) is None   # c never recorded its seconds
    assert total_seconds({"seconds": 5.0, "resumed_from": "gone"}, tmp_path) is None
    assert total_seconds({"resumed_from": "a"}, tmp_path) is None


def test_the_replay_timeline_follows_the_runs_own_events():
    """qa/t07b/timeline.mjs builds the timeline from the real county data and checks its order and counts against the events."""
    import pathlib, shutil, subprocess
    root = pathlib.Path(__file__).resolve().parents[1]
    node = shutil.which("node")
    if not node or not (root / "site" / "data" / "panola.json").exists():
        pytest.skip("needs node and the built county data")
    r = subprocess.run([node, str(root / "qa" / "t07b" / "timeline.mjs")], capture_output=True, text=True, cwd=root)
    assert r.returncode == 0, r.stdout + r.stderr
