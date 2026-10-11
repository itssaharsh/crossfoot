"""T03d: the printed sums decide; the corrected file is checked against every printed sum. No network, no model."""
import json

from crossfoot import audit, outputs
from crossfoot.ledger import Ledger
from tests.test_agent import make_block
from tests.test_audit import HEAD, Geo, Gw, file_text, parse


def sm(name, scan, file):
    return {"name": name, "holds_with_scan": scan, "holds_with_file": file}


POLICY = {"question_id": "q", "answer": "cells", "answered_by": "test", "meaning": "m"}
URLS = {"scan": "https://example.org/scan", "file": "https://example.org/file"}


def rd(value):
    return {"model": "m", "dpi": 400, "value": value, "crop": None, "error": None}


# ---- the status rule -------------------------------------------------------------------------------------------------

def test_two_sums_that_hold_with_the_ledger_and_fail_with_the_file_decide():
    assert audit.sums_decide([sm("a", True, False), sm("b", True, False)])
    assert audit.sums_decide([sm("a", True, False)])
    assert not audit.sums_decide([])
    assert not audit.sums_decide([sm("a", True, False), sm("b", False, False)])
    assert not audit.sums_decide([sm("a", True, True), sm("b", True, False)])
    assert not audit.sums_decide([sm("a", False, True)])


def test_a_third_value_from_the_reread_does_not_unsettle_what_the_sums_settle():
    st, why, dis = audit.finding_status([sm("a", True, False), sm("b", True, False)], rd(11), 1, 0)
    assert st == "settled_against_file" and dis is True


def test_made_up_case_the_reread_returns_the_files_value_while_both_sums_hold_with_the_ledger():
    st, why, dis = audit.finding_status([sm("a", True, False), sm("b", True, False)], rd(0), 1, 0)
    assert st == "settled_against_file" and dis is True


def test_a_reread_that_agrees_does_not_disagree():
    assert audit.finding_status([sm("a", True, False)], rd(1), 1, 0)[2] is False
    assert audit.finding_status([sm("a", True, False)], None, 1, 0)[2] is False


def test_sums_that_do_not_decide_are_cannot_verify_whatever_the_reread_says():
    for sums in ([sm("a", True, False), sm("b", False, False)], [sm("a", True, True)], [sm("a", False, False)], []):
        for r in (None, rd(1), rd(0), rd(7)):
            assert audit.finding_status(sums, r, 1, 0)[0] == "cannot_verify", (sums, r)
    st, why, dis = audit.finding_status([sm("a", True, False), sm("b", False, False)], rd(7), 1, 0)
    assert dis is True and "either value" in why


def test_document_inconsistent_keeps_its_meaning():
    st, why, dis = audit.finding_status([sm("row", True, False), sm("col", False, True)], rd(1), 1, 0)
    assert st == "document_inconsistent" and "row" in why and "col" in why


# ---- the audit makes no re-read where the sums decide --------------------------------------------------------------

def _small(file_early, row_totals=None):
    led = Ledger()
    make_block(led, 1, "p1-b1", row_totals=row_totals)        # precinct 2: early 20, absentee 4, election day 6, total 30
    rows = [["X", "1", "C", "", "", "cand p1-b1", "15", "2", "10", "3"],
            ["X", "2", "C", "", "", "cand p1-b1", "30", "4", str(file_early), "6"]]
    return led, rows


def test_no_reread_is_made_for_a_value_whose_sums_decide(tmp_path):
    led, rows = _small(21)
    gw = Gw(led, says=lambda r, c, v: 99)
    res = audit.audit_county("x", led, Geo(), gw, parse(file_text(rows)), run_dir=tmp_path, make_crops=False,
                             log=lambda *a: None)
    assert gw.asked == [] and res["audit"]["rereads"] == 0
    f = next(f for f in res["findings"] if f["part"] == "early_voting")
    assert f["status"] == "settled_against_file" and f["reread"] is None and f["reread_disagrees"] is False


def test_a_reread_is_made_where_the_sums_do_not_decide(tmp_path):
    led, rows = _small(22, row_totals={"EARLY": 31})            # the row sum fails with either value
    gw = Gw(led, says=lambda r, c, v: 99)
    res = audit.audit_county("x", led, Geo(), gw, parse(file_text(rows)), run_dir=tmp_path, make_crops=False,
                             log=lambda *a: None)
    assert len(gw.asked) == 1 and res["audit"]["rereads"] == 1
    f = next(f for f in res["findings"] if f["part"] == "early_voting")
    assert f["status"] == "cannot_verify" and f["reread_disagrees"] is True and f["reread"]["value"] == 99


# ---- a corrected row is consistent ----------------------------------------------------------------------------------

def finding(row, part, new, **kw):
    d = {"id": f"f{row}{part}", "file_row": row, "part": part, "file_value": 0, "scan_value": new,
         "kind": "wrong_number", "status": "settled_against_file"}
    d.update(kw)
    return d


def test_a_row_whose_corrected_votes_do_not_equal_its_parts_is_not_corrected_at_all():
    raw = file_text([["X", "1", "C", "", "", "A", "15", "2", "10", "3"],
                     ["X", "2", "C", "", "", "A", "31", "4", "21", "6"],
                     ["X", "3", "C", "", "", "A", "9", "1", "4", "4"]]).encode()
    fs = [finding(1, "votes", 30),                                  # row 1: votes 30, parts 4 + 21 + 6 = 31
          finding(2, "early_voting", 5), finding(2, "votes", 10)]   # row 2: 1 + 5 + 4 = 10
    ok, could = audit.whole_rows(raw, fs)
    assert [f["file_row"] for f in ok] == [2, 2]
    assert len(could) == 1 and could[0]["file_row"] == 1 and could[0]["findings"] == ["f1votes"]
    assert "30" in could[0]["reason"] and "31" in could[0]["reason"]
    new, diff, applied = audit.apply_corrections(raw, ok)
    assert new.decode().splitlines()[2] == "X,2,C,,,A,31,4,21,6"
    assert new.decode().splitlines()[3] == "X,3,C,,,A,10,1,5,4"


def test_write_findings_lists_the_rows_it_could_not_correct_and_marks_the_findings(tmp_path):
    led, rows = _small(21)
    rows[1][6] = "31"                                              # votes 31 = 4 + 21 + 6; the scan says 30 = 4 + 20 + 6
    raw = file_text(rows).encode()
    res = audit.audit_county("x", led, Geo(), Gw(led), parse(raw.decode()), run_dir=tmp_path, make_crops=False,
                             log=lambda *a: None)
    d = outputs.write_findings(tmp_path, "x", "r", res, policy=POLICY, raw_file=raw, file_name="f.csv",
                               file_urls=URLS)
    assert d["counts"]["corrections"] == 2 and not d["could_not_correct"]
    # the same, but only the part is settled: votes left alone makes the row inconsistent, so nothing is changed
    raw2 = file_text(rows).encode()
    fs = [f for f in res["findings"] if f["part"] == "early_voting"]
    ok, could = audit.whole_rows(raw2, [dict(f, file_row=f["file_row"]) for f in fs])
    assert ok == [] and len(could) == 1


# ---- every printed sum, with the published file and with the corrected file ---------------------------------------

def _run(tmp_path, led, rows, n=0):
    raw = file_text(rows).encode()
    res = audit.audit_county("x", led, Geo(), Gw(led), parse(raw.decode()), run_dir=tmp_path / str(n), make_crops=False,
                             log=lambda *a: None)
    return outputs.write_findings(tmp_path / str(n), "x", "r", res, policy=POLICY, raw_file=raw, file_name="f.csv",
                                  file_urls=URLS), tmp_path / str(n)


def test_sums_check_counts_every_printed_sum_with_each_file(tmp_path):
    led, rows = _small(21)
    rows[1][6] = "31"                                               # file votes 31 = its parts; the scan has 30 and 20
    d, out = _run(tmp_path, led, rows)
    sc = d["sums_check"]
    assert sc["in_all"] == 7 and sc["holding_with_published"] < sc["holding_with_corrected"] == 7
    assert sc["still_failing"] == []
    assert "7 printed sums" in (out / "x" / "report.md").read_text()


def test_sums_check_lists_what_still_fails_with_its_reason(tmp_path):
    led, rows = _small(22, row_totals={"EARLY": 31})
    d, out = _run(tmp_path, led, rows)
    sc = d["sums_check"]
    assert sc["holding_with_corrected"] < sc["in_all"]
    assert sc["still_failing"] and all(s["reasons"] for s in sc["still_failing"])
    assert any("could not be verified" in r for s in sc["still_failing"] for r in s["reasons"])
    assert "could not be verified" in (out / "x" / "report.md").read_text()


def test_a_missing_row_is_the_reason_for_a_sum_that_still_fails(tmp_path):
    led = Ledger()
    make_block(led, 1, "p1-b1", row_totals={"EARLY": 31})           # fails with the ledger's own cells
    rows = [["X", "1", "C", "", "", "cand p1-b1", "15", "2", "10", "3"]]    # precinct 2 is not in the file
    d, _ = _run(tmp_path, led, rows)
    reasons = [r for s in d["sums_check"]["still_failing"] for r in s["reasons"]]
    assert any("missing from the file" in r for r in reasons)


# ---- the same ledger twice ---------------------------------------------------------------------------------------

def test_two_audits_of_the_same_ledger_write_the_same_findings(tmp_path):
    outs = []
    for n in range(2):
        led, rows = _small(22, row_totals={"EARLY": 31})
        d, out = _run(tmp_path, led, rows, n)
        d["run_id"] = "r"
        outs.append(((out / "x" / "findings.json").read_text().replace(str(out), "R"),     # paths may differ
                     (out / "x" / "report.md").read_text().replace(str(out), "R"),
                     (out / "x" / "corrected" / "f.csv").read_bytes()))
    assert outs[0] == outs[1]
    json.loads(outs[0][0])


def test_a_wrong_precinct_group_says_what_a_person_would_do():
    big = [audit.Row(audit.Block("b", 1, "C", "A", cols=["1", "2", "3"]), p, dict(zip(audit.PARTS, f)), 0, {},
                     dict(zip(audit.PARTS, s))) for p, f, s in
           (("1", (320, 14, 168, 138), (181, 5, 102, 74)), ("2", (181, 5, 102, 74), (311, 3, 195, 113)),
            ("3", (311, 3, 195, 113), (320, 14, 168, 138)))]
    for r in big:
        r.block = big[0].block
    slots = audit.classify(big)
    s = audit.what_to_do(slots[0].group, slots)
    assert "3 rows" in s and "precinct" in s and s.count(".") <= 2
