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


# ---- the report layout (T07c): row crops, figures from the ink, the run's index --------------------------------------------

def page_image():
    """A made-up portrait page at 300 dpi: a contest heading, column headings, six rows of a label and four figures."""
    from PIL import Image, ImageDraw
    im = Image.new("L", (1000, 1400), 255)
    dr = ImageDraw.Draw(im)
    dr.rectangle([40, 100, 400, 140], fill=0)                       # the contest's title
    dr.rectangle([40, 150, 160, 168], fill=0)                       # "Vote For 1"
    for x in (520, 660, 800, 930):
        dr.rectangle([x - 40, 200, x + 20, 230], fill=0)            # the column headings
    figs = {}
    vals = (1234, 12, 345, 6)                                       # each figure is 14 px wide per character, 25 px tall
    for r in range(6):
        y = 300 + r * 80                                            # a row pitch of 80 px
        dr.rectangle([40, y, 300, y + 24], fill=0)                  # the label
        for c, x in enumerate((520, 660, 800, 930)):
            w = 14 * len(f"{vals[c]:,}")
            dr.rectangle([x - w, y, x - 1, y + 24], fill=0)
            figs[(r, c)] = [x - w, y, x, y + 25]
        dr.line([40, y + 38, 960, y + 38], fill=200, width=1)       # a dotted rule is a faint line
    return im, figs


def test_the_heading_starts_after_the_blank_band_above_it():
    from crossfoot.sitebuild import heading_top, _dark
    im, _ = page_image()
    dark, _ = _dark(im, [0, 0, 1000, 1400])
    ink = dark.sum(axis=1) >= 3
    assert heading_top(ink, 295) == 100                              # the title's first row, not the paper above it
    assert heading_top([False] * 400, 300) == 130                    # nothing found: a fixed reach above the row


def test_a_deep_row_gets_the_heading_and_its_own_neighbourhood_as_two_pieces():
    from crossfoot.sitebuild import row_pieces, cut_pieces, to_crop, to_page, _dark, SPACER
    im, _ = page_image()
    dark, _ = _dark(im, [0, 0, 1000, 1400])
    ink = dark.sum(axis=1) >= 3
    strips = [(290 + r * 80, 335 + r * 80) for r in range(6)]
    top = row_pieces(strips, 0, ink)
    assert len(top) == 1 and 95 <= top[0][0] <= 100                  # a row near the top: heading and rows in one piece
    deep = row_pieces(strips, 5, ink)
    assert len(deep) == 2 and deep[0][1] <= 300                      # the heading ends above the first row
    assert deep[1][0] >= 480 and deep[1][1] <= 1400                  # two rows above the row, none below (it is the last)
    crop, parts = cut_pieces(im, deep, 960)
    assert crop.height == sum(b - a for a, b in deep) + SPACER
    # nothing is drawn into the crop: every pixel of it is a pixel of the page, or white
    assert to_page(parts, 50, to_crop(parts, 50, 700)[1]) == (50, 700)
    assert to_crop(parts, 5, 5) is None
    band = crop.crop((0, parts[0][1] - parts[0][0], 960, parts[0][1] - parts[0][0] + SPACER))
    assert band.getextrema() == (255, 255)


def test_figures_are_found_from_the_ink_right_to_left_and_a_wrong_count_gives_none():
    from crossfoot.sitebuild import figure_boxes, COLS
    im, figs = page_image()
    vals = {"total": 1234, "absentee": 12, "early": 345, "election_day": 6}
    boxes, label, h = figure_boxes(im, [0, 295, 960, 335], values={c: vals[c] for c in COLS})
    # the ink gives each figure's box (within the strip shrunk by 6 px each side): the figure is 25 px tall
    for c, col in enumerate(COLS):
        b, want = boxes[col], figs[(0, c)]
        assert b is not None and abs(b[0] - want[0]) <= 1 and abs(b[2] - want[2]) <= 1 and abs(b[1] - want[1]) <= 1, (col, b, want)
    assert label is not None and label[0] == 40 and h in (24, 25)
    # a strip with fewer clusters than columns (here none): nothing is guessed
    empty, lab, hh = figure_boxes(im, [0, 900, 960, 960], values=None)
    assert all(v is None for v in empty.values()) and lab is None and hh is None
    # widths that do not fit the digits of the values (a 4-digit value that is as wide as a 1-digit one) are not trusted
    odd = figure_boxes(im, [0, 295, 960, 335], values={"total": 1, "absentee": 1234567, "early": 1, "election_day": 1})
    assert all(v is None for v in odd[0].values())


def report_raw():
    cell = lambda r, c, v, y: {"page": 1, "block": "1|1", "contest": "President", "candidate": "A", "row_kind": r, "column": c,
                               "value": v, "first_read": v, "status": "accepted", "tries": 0, "model": "m", "reason": None,
                               "box": [0, y, 950, y + 40]}
    rows = [("A", [10, 1, 4, 5], 100), ("B", [6, 0, 2, 4], 140), ("Total Votes Cast", [16, 1, 6, 9], 180)]
    cells = [cell(r, c, v, y) for r, vs, y in rows for c, v in zip(("total", "absentee", "early", "election_day"), vs)]
    checks = [{"kind": "report_row", "page": 1, "block": "1|1", "key": r, "terms": [[1, "1|1", r, c] for c in ("absentee", "early", "election_day")],
               "printed": vs[0], "computed": sum(vs[1:]), "ok": True} for r, vs, y in rows]
    checks.append({"kind": "report_contest", "page": 1, "block": "1|1", "key": "total",
                   "terms": [[1, "1|1", "A", "total"], [1, "1|1", "B", "total"]], "printed": 16, "computed": 16, "ok": True})
    return {"county": "tiny", "run_id": "r1", "layout": "report", "pages": [{"number": 1, "width": 1000, "height": 1400, "dpi": 200}],
            "blocks": [{"id": "1|1", "page": 1, "contest": "President", "candidate": "A", "box": None}], "cells": cells,
            "totals": [], "checks": checks, "events": [], "summary": {}}


def report_findings():
    sums = [{"name": "the row adds up", "kind": "report_row", "page": 1, "block": "1|1", "printed": 10, "printed_label": "total",
             "terms": [{"cell": [1, "1|1", "A", c], "value": v} for c, v in (("absentee", 1), ("early", 4), ("election_day", 5))],
             "computed_with_scan": 10, "holds_with_scan": True, "computed_with_file": 11, "holds_with_file": False},
            {"name": "the column adds up", "kind": "report_contest", "page": 1, "block": "1|1", "printed": 16, "printed_label": "contest total",
             "terms": [{"cell": [1, "1|1", "A", "total"], "value": 10}, {"cell": [1, "1|1", "B", "total"], "value": 6}],
             "computed_with_scan": 16, "holds_with_scan": True, "computed_with_file": 17, "holds_with_file": False}]
    f = lambda i, part, fv, sv, **kw: {"id": i, "group": "g1", "county": "tiny", "office": "President", "party": "", "candidate": "A",
                                       "precinct": "Precinct 2", "part": part, "file_value": fv, "scan_value": sv, "kind": "wrong_number",
                                       "status": "settled_against_file", "reason": "r", "sums": sums, "page": 1, "block": "1|1", "row": "A",
                                       "box": [0, 100, 950, 140], "crop": None, "reread": None, "confirmed_by_person": False, **kw}
    return {"county": "tiny", "run_id": "r1", "file": "x.csv",
            "counts": {"findings": 2, "by_kind": {"wrong_number": 2}, "by_status": {"settled_against_file": 2}, "groups": 1},
            "findings": [f("f1", "absentee", 0, 1), f("f2", "early_voting", 5, 4, status="cannot_verify",
                                                      reread={"value": 4, "agrees_with_ledger": True, "error": None})],
            "groups": [{"id": "g1", "kind": "wrong_number", "office": "President", "district": "", "candidate": "A", "precincts": ["Precinct 2"],
                        "page": 1, "block": "1|1", "findings": ["f1", "f2"], "crop": None}]}


def test_a_report_finding_sits_on_its_figure_and_carries_the_rows_both_readings():
    d = build_county(report_raw(), {1: (1000, 1400, 1000, 1400)}, findings=report_findings(),
                     rows={"rc": [{"id": 0, "p": 1, "b": "1|1", "r": "A"}], "fx": {(1, "1|1", "A", "absentee"): [1, 2, 3, 4]},
                           "rcix": {(1, "1|1", "A"): 0}})
    v = {(x["r"], x["c"]): i for i, x in enumerate(d["values"])}
    f1, f2 = d["fd"]["items"]
    assert f1["ref"] == v[("A", "absentee")] and f2["ref"] == v[("A", "early")]
    assert f1["col"] == "absentee" and f2["col"] == "early" and f1["rc"] == 0
    # the row is the label as printed on the scan, not the block's first row
    assert f1["row"] == "A" and d["fd"]["groups"][0]["row"] == "A"
    # both findings are on one row: the file's row has both of the file's values
    assert f1["rv"] == {"file": [10, 0, 5, 5], "scan": [10, 1, 4, 5]} and f2["rv"] == f1["rv"]
    # the contest total row's value in the figure's column
    assert d["values"][f1["tot"]]["r"] == "Total Votes Cast" and d["values"][f1["tot"]]["c"] == "absentee"
    assert f2["reread_agrees"] is True and "reread_agrees" not in f1
    assert d["values"][f1["ref"]]["fx"] == [1, 2, 3, 4] and "fx" not in d["values"][v[("B", "total")]]
    assert d["rc"][0]["id"] == 0


def test_a_page_without_an_image_is_listed_with_its_number_and_size():
    from crossfoot.sitebuild import frame_sizes
    raw = report_raw()
    assert frame_sizes(raw) == {1: (1000, 1400, 1000, 1400)}
    raw["pages"].append({"number": 2, "width": 2400, "height": 3000, "dpi": 200})
    sizes = frame_sizes(raw)
    assert sizes[2] == (2400, 3000, 1600, 2000)
    d = build_county(raw, sizes, images={1})
    assert [p["img"] is None for p in d["pages"]] == [False, True] and d["pages"][1]["w"] == 1600


def test_the_rows_that_need_a_crop_are_the_rows_with_a_finding_and_the_rows_read_again():
    from crossfoot.sitebuild import wanted_rows
    raw = report_raw()
    raw["events"] = [{"ts": 1, "kind": "reread", "payload": {"item": "i1", "page": 1, "block": "1|1", "row": "B"}},
                     {"ts": 2, "kind": "reread", "payload": {"item": "i1", "page": 1, "block": "1|1", "row": "A"}}]
    crops, tots = wanted_rows(raw, report_findings())
    assert crops == [(1, "1|1", "A"), (1, "1|1", "B")]               # A for its findings, B for the first re-read of the item
    assert tots == [(1, "1|1", "Total Votes Cast")]                  # the contest total row only needs its figures


def test_the_index_lists_every_county_with_its_figures_and_the_run_totals():
    from crossfoot.sitebuild import county_entry, unchecked_entry, run_totals
    summ = {"county": "tiny", "status": "audited", "layout": "report", "second_sum_exists": True,
            "sums_check": {"in_all": 10, "holding_with_published": 8, "holding_with_corrected": 9}}
    fs = report_findings()
    e = county_entry("tiny", summ, fs, 3, "report")
    assert (e["name"], e["file"], e["pages"], e["status"], e["layout"]) == ("Tiny", "data/tiny.json", 3, "audited", "report")
    assert e["disagreements"] == 2 and e["by_status"] == {"settled_against_file": 1, "cannot_verify": 1} and e["confirmed"] == 0
    assert e["sums_check"] == summ["sums_check"] and e["second_sum"] is True
    none = county_entry("empty", {"status": "audited"}, {"findings": []}, 2, "report")
    assert none["disagreements"] == 0 and "sums_check" not in none
    un = unchecked_entry("lime", {"layout": "no_printed_totals", "note": "nothing here"}, None)
    assert un == {"key": "lime", "name": "Lime", "pages": 0, "status": "unchecked", "layout": "no_printed_totals", "note": "nothing here"}
    assert "file" not in un
    t = run_totals([e, none, un], {"totals": {"model_calls": 5, "metered_cost": 1.5, "seconds": 60.0}}, {})
    assert t == {"counties": 3, "read": 2, "findings": 2, "settled": 1, "cannot_verify": 1, "confirmed": 0, "sums_in_all": 10,
                 "holding_published": 8, "holding_corrected": 9, "model_calls": 5, "metered_cost": 1.5, "seconds": 60.0}
    assert "model_calls" not in run_totals([e], None, {})


def test_row_crops_are_cut_from_the_page_and_every_figure_is_placed(tmp_path):
    from PIL import Image
    from crossfoot.sitebuild import build_rows
    raw = report_raw()
    raw["pages"][0].update(width=1000, height=1400)
    img, figs = page_image()
    vals = (1234, 12, 345, 6)
    for c in raw["cells"]:                       # three rows on the page's first rows: the strips of page_image()
        r = ("A", "B", "Total Votes Cast").index(c["row_kind"])
        c["box"] = [0, 290 + r * 80, 950, 335 + r * 80]
        c["value"] = vals[("total", "absentee", "early", "election_day").index(c["column"])]
    rc, fx, index = build_rows(raw, [(1, "1|1", "B")], [(1, "1|1", "Total Votes Cast")], lambda n: img, lambda n: 1000, lambda n: 0.5,
                               tmp_path, lambda county, n: f"data/rows/{county}-r{n}.webp")
    assert index == {(1, "1|1", "B"): 0} and len(rc) == 1
    r = rc[0]
    assert (r["p"], r["b"], r["r"]) == (1, "1|1", "B") and r["img"] == "data/rows/tiny-r0.webp"
    assert Image.open(tmp_path / "tiny-r0.webp").size == (r["w"], r["h"])
    # every figure is placed inside the crop, in column order (left to right), and sits inside the row's box
    boxes = [r["fb"][c] for c in ("total", "absentee", "early", "election_day")]
    assert all(b is not None for b in boxes) and [b[0] for b in boxes] == sorted(b[0] for b in boxes)
    assert all(r["rb"][1] <= b[1] and b[3] <= r["rb"][3] + 1 and b[2] <= r["w"] for b in boxes)
    assert 0 <= r["pb"][0] < r["pb"][2] <= 500 and 0 < r["pb"][1] < r["pb"][3] <= 700   # in page-image pixels (half of 1000 x 1400)
    # the contest total row has the figures' boxes in page-image pixels, and no crop of its own
    assert fx[(1, "1|1", "Total Votes Cast", "total")] is not None and (1, "1|1", "Total Votes Cast") not in index
    assert [f.name for f in tmp_path.iterdir()] == ["tiny-r0.webp"]
    # the blank bands between the lines are listed (their middles), in order, inside the crop and clear of the row's figures
    assert r["gp"] == sorted(r["gp"]) and r["gp"] and all(0 <= g <= r["h"] for g in r["gp"])
    assert not any(b[1] <= g <= b[3] for g in r["gp"] for b in boxes)


def test_the_replay_timeline_of_the_report_counties_follows_their_events():
    """qa/t07c/timeline.mjs builds the timelines of San Saba, Jones, Lynn and Cottle from the real data and checks them."""
    import pathlib, shutil, subprocess
    root = pathlib.Path(__file__).resolve().parents[1]
    node = shutil.which("node")
    if not node or not (root / "site" / "data" / "san_saba.json").exists():
        pytest.skip("needs node and the built county data")
    r = subprocess.run([node, str(root / "qa" / "t07c" / "timeline.mjs")], capture_output=True, text=True, cwd=root)
    assert r.returncode == 0, r.stdout + r.stderr
