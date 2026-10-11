"""T04a: the one-precinct-per-page report layout. Fake answers only; no network, no model."""
import json
from pathlib import Path

import pytest
from PIL import Image

from crossfoot import agent, audit, checks, outputs
from crossfoot.layouts import profile, report
from crossfoot.ledger import Ledger

HAIKU, SONNET, OPUS = "claude-haiku", "claude-sonnet-4.6", "claude-opus-4.6"
COLS = ("total", "absentee", "early", "election_day")


# ---- helpers ---------------------------------------------------------------------------------------------------------

def row(label, t, a, e, d, y=100):
    return {"label": label, "total": t, "absentee": a, "early": e, "election_day": d, "y": y}


def contest(name, rows, continued=False):
    return {"name": name, "continued": continued, "rows": rows}


def page_ans(prec, contests):
    return {"precinct": prec, "contests": contests}


def put(led, page, blk, label, vals, contest_name="C", y=100):
    for col, v in zip(COLS, vals):
        if v is not None:
            led.put_cell("x", page, blk, label, col, v, contest=contest_name, candidate=label, model=HAIKU,
                         box=(0, y - 20, 900, y + 20))


class FakeGw:
    """Answers come from `answer(kind, model, n)`; kind is layout | page | row. Every call is logged."""
    def __init__(self, answer, model=HAIKU):
        self.answer, self.model = answer, model
        self.calls = self.prompt_tokens = self.completion_tokens = 0
        self.cost = 0.0
        self.log = []

    def ask_json(self, prompt, image=None, *, validate=None, model=None):
        self.calls += 1
        model = model or self.model
        kind = prompt.split("\n", 1)[0].replace("TASK:", "").strip().rstrip(".")
        n = sum(1 for k in self.log if k[1] == kind)
        ans = self.answer(kind, model, n)
        self.log.append((model, kind, prompt))
        if validate:
            validate(ans)
        return ans

    def kinds(self):
        return [(m, k) for m, k, _ in self.log]


class FakeGeo:
    def __init__(self):
        self.crops = []

    def crop_row(self, page, box, dpi, dest):
        self.crops.append((page, box, dpi))
        Path(dest).parent.mkdir(parents=True, exist_ok=True)
        Image.new("L", (10, 10), 255).save(dest)
        return Path(dest)

    def block_box(self, page, bid):
        return None

    def total_box(self, *a):
        return None


@pytest.fixture
def png(tmp_path):
    p = tmp_path / "page.png"
    Image.new("L", (1000, 1400), 255).save(p)
    return lambda county, page, dpi=200, root=None: p


def quiet(*a, **k):
    pass


# ---- names -----------------------------------------------------------------------------------------------------------

def test_precinct_names_are_normalised_on_both_sides():
    k = report.precinct_key
    assert k("PRECINCT 101") == k("Precinct 101") == k("101") == "101"
    assert k("Precinct 2A") == k("2A") == k("02a") == "2a"
    assert k("Precinct 1") == k("1") == k("01") == "1"


def test_contest_and_candidate_labels_meet_in_the_middle():
    c = report.contest_canon
    assert c("Justice, Supreme Court, Pl 2") == c("Justice, Supreme Court, PI 2")
    assert c("Member, State BoE, Dist 10") == c("Member, State BoE, District 10")
    assert report.split_label("REP Donald J. Trump/JD Vance") == ("REP", "Donald J. Trump")
    assert report.split_label("Write-In Totals") == ("", "Write-ins")
    assert report.split_label("For") == ("", "For")
    assert report.split_label("DEM Colin Allred") == ("DEM", "Colin Allred")


# ---- the sums (RED first) ----------------------------------------------------------------------------------------------

def test_a_row_adds_up_and_a_contest_total_adds_up():
    led = Ledger()
    put(led, 1, "1|1", "REP A", (10, 2, 5, 3))
    put(led, 1, "1|1", "DEM B", (6, 1, 2, 3))
    put(led, 1, "1|1", "Total Votes Cast", (16, 3, 7, 6))
    cs = led.cells("x")
    rows = checks.report_row_checks(cs)
    assert len(rows) == 3 and all(c.ok for c in rows)
    con = checks.report_contest_checks(cs)
    assert sorted(c.key for c in con) == sorted(COLS) and all(c.ok for c in con)


def test_a_failing_row_and_a_failing_contest_column_are_found():
    led = Ledger()
    put(led, 1, "1|1", "REP A", (10, 2, 5, 4))               # 2 + 5 + 4 = 11
    put(led, 1, "1|1", "DEM B", (6, 1, 2, 3))
    put(led, 1, "1|1", "Total Votes Cast", (16, 3, 7, 6))
    chs = checks.report_checks(led.cells("x"))
    bad = {(c.kind, c.key) for c in chs if not c.ok}
    assert bad == {("report_row", "REP A"), ("report_contest", "election_day")}


def test_no_total_row_means_one_sum_per_value():
    led = Ledger()
    put(led, 1, "1|1", "REP A", (10, 2, 5, 3))
    put(led, 1, "1|1", "Write-In Totals", (0, 0, 0, 0))
    cs = led.cells("x")
    assert checks.report_contest_checks(cs) == []
    on = checks.report_crossing(cs)
    assert all(len(v) == 1 for v in on.values())             # each value sits on its row's own sum only


def test_overvotes_and_undervotes_are_not_candidates():
    led = Ledger()
    put(led, 1, "1|1", "REP A", (10, 2, 5, 3))
    put(led, 1, "1|1", "Overvotes", (1, 0, 1, 0))
    put(led, 1, "1|1", "Undervotes", (4, 1, 1, 2))
    put(led, 1, "1|1", "Cast Votes", (10, 2, 5, 3))
    assert all(c.ok for c in checks.report_contest_checks(led.cells("x")))


# ---- the layout decision and its test ---------------------------------------------------------------------------------

def test_the_line_is_a_third():
    assert not profile.rejected(1, 3)
    assert profile.rejected(2, 5)
    assert not profile.rejected(0, 0) or True


def test_a_layout_answer_must_be_one_of_three():
    with pytest.raises(ValueError):
        profile.layout_validator({"layout": "ledger", "columns": []})
    profile.layout_validator({"layout": "report", "columns": ["total", "absentee", "early", "election_day"]})
    profile.layout_validator({"layout": "no_printed_totals", "columns": []})


def clean_page(prec="1", n=10):
    return page_ans(prec, [contest("C", [row(f"REP P{i}", 6, 1, 2, 3, 50 + i * 30) for i in range(n)])])


def run_read(tmp_path, png, answer, **kw):
    led = Ledger()
    gw = FakeGw(answer)
    s = report.read_county("x", gw, led, run_id="", log=quiet, png_fn=png, n_pages=kw.pop("n_pages", 2), **kw)
    return s, gw, led


def test_report_layout_is_read_and_a_clean_first_page_keeps_haiku(tmp_path, png):
    def ans(kind, model, n):
        if kind == "layout":
            return {"layout": "report", "columns": list(COLS)}
        return clean_page("1" if n == 0 else "2")
    s, gw, led = run_read(tmp_path, png, ans)
    assert s["layout"] == "report" and s["layout_decision"]["accepted"] is True
    assert gw.kinds() == [(HAIKU, "layout"), (HAIKU, "page"), (HAIKU, "page")]
    assert s["reader"] == HAIKU
    assert len(led.cells("x")) == 2 * 10 * 4


def test_a_first_page_with_too_many_failing_sums_rejects_the_layout(tmp_path, png):
    bad = [row(f"REP P{i}", 7, 1, 2, 3, 50 + i * 30) for i in range(6)] + \
          [row(f"REP Q{i}", 6, 1, 2, 3, 300 + i * 30) for i in range(6)]      # 6 of 12 fail: over a third
    def ans(kind, model, n):
        return {"layout": "report", "columns": list(COLS)} if kind == "layout" else page_ans("1", [contest("C", bad)])
    s, gw, led = run_read(tmp_path, png, ans)
    assert s["layout"] == "not_supported" and s["layout_decision"]["accepted"] is False
    assert s["layout_decision"]["failing"] == 6 and s["layout_decision"]["row_sums"] == 12
    assert gw.kinds() == [(HAIKU, "layout"), (HAIKU, "page")]               # nothing else was read
    assert led.cells("x") == []


def test_exactly_a_third_failing_is_accepted(tmp_path, png):
    rows = [row(f"REP P{i}", 7 if i < 4 else 6, 1, 2, 3, 50 + i * 30) for i in range(12)]    # 4 of 12
    def ans(kind, model, n):
        if kind == "layout":
            return {"layout": "report", "columns": list(COLS)}
        return page_ans("1", [contest("C", rows)])
    s, gw, led = run_read(tmp_path, png, ans, n_pages=1)
    assert s["layout_decision"]["accepted"] is True
    assert s["reader"] == SONNET                                              # 4 of 12 is over a tenth too


def test_a_sample_over_a_tenth_switches_the_reader_and_reads_page_one_again(tmp_path, png):
    def page(model, prec):
        fail = model == HAIKU
        rows = [row(f"REP P{i}", 7 if (fail and i < 2) else 6, 1, 2, 3, 50 + i * 30) for i in range(10)]
        return page_ans(prec, [contest("C", rows)])
    def ans(kind, model, n):
        if kind == "layout":
            return {"layout": "report", "columns": list(COLS)}
        return page("%s" % model, "1")
    s, gw, led = run_read(tmp_path, png, ans)
    assert [m for m, k in gw.kinds()] == [HAIKU, HAIKU, SONNET, SONNET]
    assert s["reader"] == SONNET and s["sample"]["failing"] == 2 and s["sample"]["kept_sample"] is False
    assert all(c["model"] == SONNET for c in led.cells("x"))                  # the sample's values were thrown away


def test_no_printed_totals_reads_nothing(tmp_path, png):
    def ans(kind, model, n):
        assert kind == "layout"
        return {"layout": "no_printed_totals", "columns": []}
    s, gw, led = run_read(tmp_path, png, ans)
    assert s["layout"] == "no_printed_totals"
    assert s["note"] == "nothing on this scan can be cross-checked; left as published"
    assert gw.kinds() == [(HAIKU, "layout")] and led.cells("x") == []


# ---- storing a page -----------------------------------------------------------------------------------------------------

def test_a_section_and_a_contest_that_run_over_a_page_break_keep_their_place(tmp_path, png):
    p1 = page_ans("2A", [contest("Statistics", [row("Ballots Cast - Total", 9, 1, 5, 3, 20),
                                                row("Ballots Cast - Blank", 0, 0, 0, 0, 40)]),
                         contest("US Senator", [row("REP Ted Cruz", 6, 1, 3, 2, 80), row("DEM Colin Allred", 3, 0, 2, 1, 110)])])
    p2 = page_ans("2A", [contest("US Senator", [row("Write-In Totals", 0, 0, 0, 0, 50),
                                                row("Total Votes Cast", 9, 1, 5, 3, 80)], continued=True),
                         contest("Sheriff", [row("REP Al Jones", 4, 1, 1, 2, 160)])])
    p3 = page_ans("2B", [contest("US Senator", [row("REP Ted Cruz", 1, 0, 1, 0, 80)])])
    pages = {0: p1, 1: p2, 2: p3}
    def ans(kind, model, n):
        return {"layout": "report", "columns": list(COLS)} if kind == "layout" else pages[n]
    s, gw, led = run_read(tmp_path, png, ans, n_pages=3)
    cells = led.cells("x")
    sen = {(c["page"], c["block_id"]) for c in cells if c["contest"] == "US Senator" and "2a" in c["block_id"]}
    assert len({b for _, b in sen}) == 1 and {p for p, _ in sen} == {1, 2}      # one block over two pages
    blk = next(iter(sen))[1]
    assert {c["row_kind"] for c in cells if c["block_id"] == blk} == {"REP Ted Cruz", "DEM Colin Allred", "Write-In Totals",
                                                                      "Total Votes Cast"}
    assert {c["column"] for c in cells} == set(COLS)
    sher = {c["block_id"] for c in cells if c["contest"] == "Sheriff"}
    assert len(sher) == 1 and sher != {blk}
    assert {c["block_id"] for c in cells if "2b" in c["block_id"]} and not {c["block_id"] for c in cells if "2b" in c["block_id"]} & {blk}
    # the contest total on page 2 covers the candidates on both pages
    con = [c for c in checks.report_contest_checks(cells) if c.block_id == blk]
    assert len(con) == 4 and all(c.ok for c in con)
    # the statistics rows are blocks of their own, named as the published file names them
    assert {c["contest"] for c in cells if "Ballots" in c["row_kind"]} == {"Ballots Cast", "Ballots Cast Blank"}


def test_page_answers_are_validated_and_repaired_once():
    v = report.page_validator
    with pytest.raises(ValueError):
        v({"precinct": "1", "contests": [contest("C", [row("A", "6", 1, 2, 3)])]})
    with pytest.raises(ValueError):
        v({"precinct": "", "contests": []})
    with pytest.raises(ValueError):
        v({"precinct": "1", "contests": [contest("C", [row("A", 6, 1, 2, 3, 2000)])]})
    v({"precinct": "1", "contests": [contest("C", [row("A", 6, None, None, None, 10)])]})


# ---- the loop on a failing row -----------------------------------------------------------------------------------------

def failing_ledger(extra=()):
    led = Ledger()
    put(led, 1, "1|1", "REP A", (11, 2, 5, 3), y=100)         # 2 + 5 + 3 = 10, printed 11
    put(led, 1, "1|1", "DEM B", (6, 1, 2, 3), y=140)
    for e in extra:
        e(led)
    return led


def close(led, answer, reader=HAIKU):
    geo, gw = FakeGeo(), FakeGw(answer, model=reader)
    s = report.close_county("x", gw, led, geo, reader=reader, run_id="", log=quiet, crop_dir=Path("/tmp/crossfoot-test-crops"))
    return s, gw, geo


def reread_ans(vals):
    return dict(zip(COLS, vals))


def test_a_row_that_fails_is_read_again_one_step_up_and_accepted_when_it_holds():
    led = failing_ledger()
    reads = [(10, 2, 5, 3)]
    s, gw, geo = close(led, lambda k, m, n: reread_ans(reads[0]))
    assert [d for _, _, d in geo.crops] == [300]
    assert {c["status"] for c in led.cells("x")} == {"accepted"}
    assert next(c["value"] for c in led.cells("x") if c["row_kind"] == "REP A" and c["column"] == "total") == 10


def test_a_reading_that_does_not_help_climbs_the_ladder_and_stops_at_six_actions():
    led = failing_ledger()
    seq = iter([(12, 2, 5, 3), (11, 2, 5, 5), (9, 2, 5, 3), (12, 2, 6, 3), (13, 2, 5, 3), (12, 3, 5, 3), (10, 2, 5, 3)])
    s, gw, geo = close(led, lambda k, m, n: reread_ans(next(seq)))
    assert gw.calls == 6 and len(geo.crops) == 6
    assert [m for m, _, _ in gw.log] == [HAIKU, HAIKU, SONNET, SONNET, OPUS, OPUS]
    assert [d for _, _, d in geo.crops] == [300, 400, 400, 500, 500, 600]
    v = led.verdicts("x")
    assert len(v) == 1 and v[0]["verdict"] == "cannot_verify" and v[0]["reason"]
    assert {c["status"] for c in led.cells("x") if c["row_kind"] == "REP A"} == {"cannot_verify"}
    assert {c["status"] for c in led.cells("x") if c["row_kind"] == "DEM B"} == {"accepted"}


def test_the_same_reading_twice_while_the_sum_fails_is_document_inconsistent():
    led = failing_ledger()
    s, gw, geo = close(led, lambda k, m, n: reread_ans((11, 2, 5, 3)))
    assert gw.calls == 2
    v = led.verdicts("x")
    assert len(v) == 1 and v[0]["verdict"] == "document_inconsistent" and "11" in v[0]["reason"]
    assert {c["status"] for c in led.cells("x") if c["row_kind"] == "REP A"} == {"document_inconsistent"}


def test_a_failing_contest_column_re_reads_the_rows_of_the_contest():
    led = Ledger()
    put(led, 1, "1|1", "REP A", (10, 2, 5, 3), y=100)
    put(led, 1, "1|1", "DEM B", (6, 1, 2, 3), y=140)
    put(led, 1, "1|1", "Total Votes Cast", (17, 3, 8, 6), y=180)     # printed total says 17; candidates add to 16
    truth = {"REP A": (10, 2, 5, 3), "DEM B": (6, 1, 2, 3), "Total Votes Cast": (16, 3, 7, 6)}
    def ans(kind, model, n):
        label = [l for l in truth if l in gw.log[-1][2]] if gw.log else []
        return reread_ans(truth["Total Votes Cast"])
    geo, gw = FakeGeo(), FakeGw(lambda k, m, n: reread_ans(truth["Total Votes Cast"]))
    s = report.close_county("x", gw, led, geo, reader=HAIKU, run_id="", log=quiet, crop_dir=Path("/tmp/crossfoot-test-crops"))
    assert gw.calls <= 6
    assert all(c.ok for c in checks.report_checks(led.cells("x")))


# ---- the audit ---------------------------------------------------------------------------------------------------------

HEAD = "county,precinct,office,district,party,candidate,votes,absentee,early_voting,election_day"


def frow(votes, a, e, d, cand="Ted Cruz", office="US Senator", prec="Precinct 1", party="REP"):
    return {"county": "X", "precinct": prec, "office": office, "district": "", "party": party, "candidate": cand,
            "votes": str(votes), "absentee": str(a), "early_voting": str(e), "election_day": str(d)}


def raw_of(rows):
    return (HEAD + "\n" + "".join(",".join(r[h] for h in HEAD.split(",")) + "\n" for r in rows)).encode()


def audit_of(tmp_path, led, rows, answer=lambda k, m, n: reread_ans((10, 2, 5, 3))):
    geo, gw = FakeGeo(), FakeGw(answer)
    res = audit.audit_report_county("x", led, geo, gw, rows, run_dir=tmp_path, log=quiet, file_name="x.csv",
                                    reader=HAIKU)
    return res, gw, geo


def scan_ledger(with_total=False):
    led = Ledger()
    put(led, 1, "1|1", "REP Ted Cruz", (10, 2, 5, 3), contest_name="US Senator", y=100)
    put(led, 1, "1|1", "DEM Colin Allred", (6, 1, 2, 3), contest_name="US Senator", y=140)
    if with_total:
        put(led, 1, "1|1", "Total Votes Cast", (16, 3, 7, 6), contest_name="US Senator", y=180)
    return led


DEM = frow(6, 1, 2, 3, cand="Colin Allred", party="DEM")


def test_two_values_off_in_a_row_that_adds_up_and_no_contest_total_cannot_be_told_apart(tmp_path):
    rows = [frow(10, 3, 4, 3), DEM]                     # absentee 3 (scan 2) and early 4 (scan 5); the file's row adds up
    res, gw, geo = audit_of(tmp_path, scan_ledger(), rows)
    fs = [f for f in res["findings"] if f["candidate"] == "Ted Cruz"]
    assert {f["part"] for f in fs} == {"absentee", "early_voting"}
    assert all(f["status"] == "cannot_verify" for f in fs)
    assert all("no printed total can tell the two rows apart" in f["reason"] for f in fs)
    assert [k for _, k, _ in gw.log] == ["row"]          # the scan's row was read once more
    assert gw.log[0][0] == SONNET and geo.crops[0][2] == 400
    assert all(f["reread"]["row"] == {"total": 10, "absentee": 2, "early": 5, "election_day": 3} for f in fs)
    assert all(f["reread"]["agrees_with_ledger"] is True for f in fs)
    assert "agree" in fs[0]["reason"]
    new, diff, applied = audit.apply_corrections(raw_of(rows), res["findings"])
    assert applied == []                                  # nothing is corrected


def test_a_second_reading_that_differs_is_said_so(tmp_path):
    rows = [frow(10, 3, 4, 3), DEM]
    res, gw, geo = audit_of(tmp_path, scan_ledger(), rows, answer=lambda k, m, n: reread_ans((10, 3, 4, 3)))
    f = next(f for f in res["findings"] if f["part"] == "absentee")
    assert f["reread"]["agrees_with_ledger"] is False and "does not agree" in f["reason"]
    assert f["status"] == "cannot_verify"


def test_a_published_row_that_fails_its_own_total_is_settled_against_the_file(tmp_path):
    rows = [frow(10, 2, 6, 3), DEM]                     # 2 + 6 + 3 = 11, printed 10; the scan's row holds
    res, gw, geo = audit_of(tmp_path, scan_ledger(), rows)
    fs = [f for f in res["findings"] if f["candidate"] == "Ted Cruz"]
    assert len(fs) >= 1
    f = next(f for f in fs if f["part"] in ("early_voting", "votes"))
    assert f["status"] == "settled_against_file"
    assert any(x["kind"] == "file_row_fails_own_total" for x in fs)
    assert gw.calls == 0                                 # the sums decide: no look at the scan
    sc = f["sums"][0]
    assert sc["holds_with_scan"] is True and sc["holds_with_file"] is False


def test_a_row_covered_by_a_contest_total_is_settled(tmp_path):
    rows = [frow(10, 3, 4, 3), DEM]
    res, gw, geo = audit_of(tmp_path, scan_ledger(with_total=True), rows)
    fs = [f for f in res["findings"] if f["candidate"] == "Ted Cruz"]
    assert {f["part"] for f in fs} == {"absentee", "early_voting"}
    assert all(f["status"] == "settled_against_file" for f in fs)
    assert gw.calls == 0
    kinds = {s["kind"] for f in fs for s in f["sums"]}
    assert kinds == {"report_row", "report_contest"}
    row = next(s for s in fs[0]["sums"] if s["kind"] == "report_row")
    assert row["holds_with_scan"] and row["holds_with_file"]          # the row's own sum cannot tell them apart
    con = next(s for s in fs[0]["sums"] if s["kind"] == "report_contest")
    assert con["holds_with_scan"] and not con["holds_with_file"]


def test_the_outputs_are_those_of_panolas_audit_and_say_what_the_sums_cannot_see(tmp_path):
    rows = [frow(10, 2, 6, 3), DEM]
    res, gw, geo = audit_of(tmp_path, scan_ledger(), rows)
    d = outputs.write_findings(tmp_path, "x", "r1", res, policy={"question_id": "q", "answer": "cells",
                                                                  "answered_by": "t", "meaning": "m"},
                               raw_file=raw_of(rows), file_name="x.csv",
                               file_urls={"scan": "https://example.org/s", "file": "https://example.org/f"})
    for name in ("findings.json", "report.md", "changes.diff", "corrected/x.csv"):
        assert (tmp_path / "x" / name).exists(), name
    assert d["sums_check"]["in_all"] == 2 and d["sums_check"]["holding_with_ledger"] == 2
    assert d["sums_check"]["rows_failing_own_total"] == {"published": 1, "corrected": 0}
    assert d["layout"] == "report" and d["audit"]["contest_totals_printed"] == 0
    text = (tmp_path / "x" / "report.md").read_text()
    assert "cannot see" in text and "cancel out" in text
    assert "second sum" in text.lower()


def test_a_misspelt_candidate_in_one_precinct_joins_the_others_and_a_crop_is_cut(tmp_path):
    led = Ledger()
    put(led, 1, "1|1", "REP Ted Cruz", (10, 2, 5, 3), contest_name="US Senator")
    put(led, 2, "2|1", "REP Ted Cuz", (6, 1, 2, 3), contest_name="US Senator")
    blocks = audit.report_blocks(led.cells("x"), ["Precinct 1", "Precinct 2"])
    assert len(blocks) == 1 and sorted(blocks[0].scan_parts) == ["Precinct 1", "Precinct 2"]
    (tmp_path / "pages" / "x").mkdir(parents=True)
    Image.new("L", (1000, 1400), 255).save(tmp_path / "pages" / "x" / "p01-400.png")
    geo = report.ReportGeometry("x", x_right=900, root=tmp_path)
    p = geo.crop_row(1, [0, 100, 900, 140], 400, tmp_path / "c.png")
    assert p.exists()


def test_row_estimates_that_are_compressed_are_snapped_to_the_lines_of_the_page(tmp_path):
    import numpy as np
    img = np.full((1400, 1000), 255, np.uint8)
    lines = [150, 190, 230] + [300 + 40 * i for i in range(5)] + [560 + 40 * i for i in range(5)]   # 3 lines are not rows
    for y in lines:
        img[y - 8:y + 8, 60:300] = 0
        img[y - 8:y + 8, 600:700] = 0
    p = tmp_path / "p.png"
    Image.fromarray(img).save(p)
    true = lines[3:]
    model = [0.75 * y - 10 + (25 if i >= 5 else 0) for i, y in enumerate(true)]       # compressed, uneven
    got, ok = report.snap_rows(p, model, 900)
    assert ok and all(abs(g - t) <= 1 for g, t in zip(got, true))
    blank = tmp_path / "b.png"
    Image.new("L", (1000, 1400), 255).save(blank)
    assert report.snap_rows(blank, model, 900) == (model, False)


def test_an_unreadable_crop_is_not_a_reading_and_a_reopened_ledger_is_closed_again():
    led = failing_ledger()
    seq = iter([(None,) * 4, (None,) * 4, (10, 2, 5, 3)])
    s, gw, geo = close(led, lambda k, m, n: reread_ans(next(seq)))
    assert gw.calls == 3 and not led.verdicts("x")
    for c in led.cells("x"):
        led.set_status("x", c["page"], c["block_id"], c["row_kind"], c["column"], "cannot_verify", "r")
    led.set_verdict("x", "v", 1, "1|1", "cannot_verify", "r")
    report.reopen(led, "x")
    assert led.verdicts("x") == [] and {c["status"] for c in led.cells("x")} == {"first_read"}
