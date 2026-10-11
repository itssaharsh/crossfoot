"""T04c: every published row is compared with the scan or listed as not compared. Real label lists (labels only, no
figures) of Foard and Scurry as fixtures. No network, no model."""
import json
from pathlib import Path

import pytest

from crossfoot import allrun, audit, outputs
from crossfoot.layouts import report

FIX = Path(__file__).parent / "fixtures"
PARTS = ("votes", "absentee", "early_voting", "election_day")


def labels(county):
    return json.loads((FIX / f"labels_{county}.json").read_text())


def scan_cells(spec):
    cells = []
    for i, (contest, label) in enumerate(spec["scan"]):
        for col, v in zip(("total", "absentee", "early", "election_day"), (1, 0, 1, 0)):
            cells.append({"page": 1 + i // 40, "block_id": f"P1|{contest}", "row_kind": label, "column": col,
                          "value": v, "contest": contest, "candidate": label, "x0": 0, "y0": 0, "x1": 1, "y1": 1})
    return cells


def file_rows(spec):
    """One row per label; the file spells one contest two ways in places ("Pl 7", "PI 7"), which sit in different precincts
    there, so a repeat of a contest and candidate goes to the next precinct."""
    seen, out = {}, []
    for o, d, c in spec["file"]:
        k = (report.contest_canon(o + " " + d), audit.candidate_key(c))
        seen[k] = seen.get(k, 0) + 1
        out.append({"precinct": f"P{seen[k]}", "office": o, "district": d, "candidate": c, "party": "", "votes": "1",
                    "absentee": "0", "early_voting": "1", "election_day": "0"})
    return out


def _unused(spec):
    return [{"precinct": "P1", "office": o, "district": d, "candidate": c, "party": "", "votes": "1",
             "absentee": "0", "early_voting": "1", "election_day": "0"} for o, d, c in spec["file"]]


class CountingGw:
    def __init__(self, answer=None):
        self.calls, self.answer = 0, answer or {"contests": [], "candidates": []}

    def ask_json(self, prompt, image=None, *, validate=None, model=None):
        self.calls += 1
        return self.answer


def pair(county, gw=None):
    spec = labels(county)
    rows = file_rows(spec)
    blocks = audit.report_blocks(scan_cells(spec), {"P1", "P2"})
    fcs = audit.file_contests(rows, keyfn=audit.report_file_key)
    m = audit.match(blocks, fcs, gw, keys=lambda l: [report.contest_canon(l)])
    built = audit.build_rows(blocks, m, fcs, rows)
    return rows, fcs, m, built


@pytest.mark.parametrize("county", ["foard", "scurry"])
def test_real_label_lists_pair_without_the_model_to_95_percent(county):
    rows, fcs, m, built = pair(county)
    cov = audit.coverage(built, m, fcs, rows)
    assert cov["rows_published"] == len(rows)
    assert cov["rows_compared"] / cov["rows_published"] >= 0.95, cov["not_compared"]
    assert audit.coverage_status(cov) == "audited"
    assert sum(x["rows"] for x in cov["not_compared"]) == cov["rows_published"] - cov["rows_compared"]


def test_running_mates_with_or_without_a_slash_and_a_write_in_mark_name_one_candidate():
    k = audit.candidate_key
    assert k("Donald J. Trump/JD Vance (REP)") == k("Donald J. Trump")
    assert k("Cornel West Melinda Abdullah (W)").startswith(k("Cornel West"))
    c = audit.file_contests([{"precinct": "1", "office": "President", "district": "", "candidate": "Jill Stein"}])
    cand = audit.find_candidate(c["president"], audit.candidate_key("Jill Stein Rudolph Ware"))
    assert cand == audit.candidate_key("Jill Stein")


@pytest.mark.parametrize("a,b", [
    ("President and Vice President, Vote For 1", "President"),
    ("President/Vice President", "President"),
    ("United States Senator, Vote For 1", "U.S. Senate"),
    ("US Senator", "U.S. Senate"),
    ("US Representative, Dist 19 ", "U.S. House 19"),
    ("State Representative, Dist 83", "State House 83"),
    ("Justice, Supreme Court, Pl 2", "Justice, Supreme Court, PI 2"),
    ("Justice, Supreme Court, Place 2, Vote For 1", "Justice, Supreme Court, Place 2"),
    ("County Commissioner, Precinct No. 1, Vote For 1", "County Commissioner 1"),
    ("District Attorney, 46th Judicial District, Vote For 1", "District Attorney 46"),
])
def test_contest_wording_is_one_key(a, b):
    assert report.contest_canon(a) == report.contest_canon(b)


def test_different_contests_stay_apart():
    c = report.contest_canon
    assert c("Justice, Supreme Court, Place 2") != c("Justice, Supreme Court, Place 4")
    assert c("County Commissioner, Precinct No. 1") != c("County Commissioner, Precinct No. 3")


def test_the_model_is_asked_once_and_its_pairs_are_checked_by_candidates():
    spec = {"scan": [["Governor", "Ann Lee"], ["Governor", "Bo Chan"], ["Mayor", "Cy Dunn"]],
            "file": [["Chief Executive", "", "Ann Lee"], ["Chief Executive", "", "Bo Chan"], ["Dog Catcher", "", "Zed Q"]]}
    rows, blocks = file_rows(spec), audit.report_blocks(scan_cells(spec), {"P1"})
    fcs = audit.file_contests(rows, keyfn=audit.report_file_key)
    # the model pairs Governor=Chief Executive (same candidates: accepted) and Mayor=Dog Catcher (different: rejected)
    gw = CountingGw({"contests": [[0, 0], [1, 1]], "candidates": []})
    m = audit.match(blocks, fcs, gw, keys=lambda l: [report.contest_canon(l)])
    assert gw.calls == 1
    assert {v for v in m.block_map.values()} == {(next(iter(fcs)), "annlee"), (next(iter(fcs)), "bochan")}
    assert any("Mayor" in r["what"] for r in m.rejected)


def test_a_row_of_an_unpaired_contest_is_not_compared_and_never_extra_row():
    spec = {"scan": [["Governor", "Ann Lee"]], "file": [["Governor", "", "Ann Lee"], ["Dog Catcher", "", "Zed Q"]]}
    rows = file_rows(spec) + [dict(file_rows(spec)[1], precinct="P2")]
    blocks = audit.report_blocks(scan_cells(spec), {"P1", "P2"})
    fcs = audit.file_contests(rows, keyfn=audit.report_file_key)
    m = audit.match(blocks, fcs, None, keys=lambda l: [report.contest_canon(l)])
    built = audit.build_rows(blocks, m, fcs, rows)
    slots = audit.classify(built)
    assert all(s.kind != "extra_row" for s in slots)
    cov = audit.coverage(built, m, fcs, rows)
    assert (cov["rows_published"], cov["rows_compared"]) == (3, 1)
    nc = cov["not_compared"]
    assert nc[0]["contest"].startswith("Dog Catcher") and nc[0]["rows"] == 2 and "not paired" in nc[0]["reason"]
    assert audit.coverage_status(cov) == "partly_audited"


def test_a_row_of_a_paired_contest_that_the_scan_lacks_is_still_extra_row():
    spec = {"scan": [["Governor", "Ann Lee"]], "file": [["Governor", "", "Ann Lee"]]}
    rows = file_rows(spec) + [dict(file_rows(spec)[0], precinct="P2")]
    blocks = audit.report_blocks(scan_cells(spec), {"P1", "P2"})
    fcs = audit.file_contests(rows, keyfn=audit.report_file_key)
    m = audit.match(blocks, fcs, None, keys=lambda l: [report.contest_canon(l)])
    built = audit.build_rows(blocks, m, fcs, rows)
    assert [s.kind for s in audit.classify(built)] == ["extra_row"]
    assert audit.coverage(built, m, fcs, rows)["rows_compared"] == 2


def test_the_95_percent_line():
    assert audit.coverage_status({"rows_published": 100, "rows_compared": 95}) == "audited"
    assert audit.coverage_status({"rows_published": 100, "rows_compared": 94}) == "partly_audited"
    assert audit.coverage_status({"rows_published": 0, "rows_compared": 0}) == "audited"


def county_row(county, status, pub, comp, nc=()):
    return {"county": county, "status": status, "layout": "report", "pages": 1, "cells_read": 1,
            "sums_first_read": {"passing": 1, "failing": 0}, "findings_by_kind": {}, "findings_by_status": {},
            "sums_check": {}, "rows_published": pub, "rows_compared": comp, "not_compared": list(nc),
            "model_calls": 0, "metered_cost": 0, "seconds": 0}


def test_the_summary_carries_coverage_per_county_and_in_all(tmp_path):
    rows = [county_row("a", "audited", 100, 98), county_row("b", "partly_audited", 50, 10,
            [{"contest": "Mayor", "rows": 40, "reason": "contest not paired with a contest on the scan"}])]
    t = allrun.totals(rows)
    assert (t["rows_published"], t["rows_compared"]) == (150, 108)
    s = {"run_id": "R", "command": "", "budget": 1.0, "started": "", "ended": "", "resumed": False, "counties": rows,
         "totals": t, "not_reached": [], "skipped": []}
    allrun.write_summary(tmp_path, s)
    md = (tmp_path / "summary.md").read_text()
    assert "published rows" in md and "108 of 150" in md and "partly_audited" in md
    assert "Mayor" in md and "40 rows" in md
    assert json.loads((tmp_path / "summary.json").read_text())["totals"]["rows_compared"] == 108


def test_partly_audited_is_final_for_a_run_like_audited():
    assert "partly_audited" in allrun.CLOSED


def test_findings_and_report_say_how_many_rows_were_compared():
    cov = {"rows_published": 10, "rows_compared": 4,
           "not_compared": [{"contest": "Mayor", "rows": 6, "reason": "contest not paired with a contest on the scan"}]}
    d = {"county": "x", "run_id": "R", "layout": "report", "counts": {"findings": 0, "by_kind": {}, "by_status": {},
         "groups": 0, "corrections": 0}, "findings": [], "groups": [], "corrections": [], "could_not_correct": [],
         "sums_check": {"in_all": 0, "holding_with_published": 0, "holding_with_corrected": 0, "still_failing": [],
                        "rows_failing_own_total": {"published": 0, "corrected": 0}},
         "unmatched": {"scan": [], "file": [], "rejected": [], "model": {}}, "corrected_events": [],
         "audit": {}, "policy": {"answer": "cells", "meaning": "m", "answered_by": "x"}, **cov}
    text = outputs.report_text(d, [], {"scan": "s", "file": "f"})
    assert "4 of 10" in text and "Mayor" in text and "6 rows" in text


def test_only_limits_the_counties_of_an_all_run(tmp_path):
    from crossfoot import cli
    ns = cli.build_parser().parse_args(["audit", "--all", "--only", "san_saba,cottle"])
    assert ns.only == "san_saba,cottle"
    assert cli.only_counties("san_saba,cottle") == ("san_saba", "cottle")
    assert cli.only_counties(None) == allrun.ORDER
    with pytest.raises(SystemExit):
        cli.only_counties("nowhere")


def test_combine_names_the_run_each_county_comes_from(tmp_path):
    from crossfoot.ledger import Ledger
    base = tmp_path / "BASE"
    base.mkdir()
    rows = [county_row("a", "audited", None, None), county_row("b", "audited", 5, 5)]
    for r in rows[:1]:
        for k in ("rows_published", "rows_compared", "not_compared"):
            r.pop(k)             # a run from before coverage was counted
    s = {"run_id": "BASE", "command": "", "budget": 9.0, "started": "", "ended": "", "resumed": False, "counties": rows,
         "totals": allrun.totals(rows), "not_reached": [], "skipped": []}
    allrun.write_summary(base, s)
    new = tmp_path / "NEW"
    (new / "a").mkdir(parents=True)
    Ledger(new / "ledger.sqlite")
    (new / "run.json").write_text(json.dumps({"model_calls": 2, "metered_cost_estimate": 0.01, "seconds": 3}))
    (new / "a" / "findings.json").write_text(json.dumps({
        "counts": {"by_status": {}, "by_kind": {}}, "audit": {}, "rows_published": 10, "rows_compared": 8,
        "not_compared": [{"contest": "Mayor", "rows": 2, "reason": "the contest was not paired with a contest on the scan"}],
        "sums_check": {"in_all": 1, "holding_with_published": 1, "holding_with_corrected": 1}}))
    out = tmp_path / "ALL"
    got = allrun.combine(out, "BASE", {"a": "NEW"})
    assert [r["from_run"] for r in got["counties"]] == ["NEW", "BASE"]
    assert got["counties"][0]["status"] == "partly_audited"
    md = (out / "summary.md").read_text()
    assert "a: run NEW" in md and "b: run BASE" in md and "8 of 10" in md


def test_a_page_that_could_not_be_read_makes_not_compared_rows_not_extra_rows():
    assert audit.unread_gaps({17: "10", 19: "10", 21: "11"}, [18]) == {"10": [18]}
    assert audit.unread_gaps({17: "10", 19: "11"}, [18]) == {"10": [18], "11": [18]}
    spec = {"scan": [["Governor", "Ann Lee"]], "file": [["Governor", "", "Ann Lee"]]}
    rows = file_rows(spec) + [dict(file_rows(spec)[0], precinct="P2")]
    blocks = audit.report_blocks(scan_cells(spec), {"P1", "P2"})
    fcs = audit.file_contests(rows, keyfn=audit.report_file_key)
    m = audit.match(blocks, fcs, None, keys=lambda l: [report.contest_canon(l)])
    built = audit.build_rows(blocks, m, fcs, rows)
    cov = audit.coverage(built, m, fcs, rows, {1: "scan page 3 could not be read and may hold this row"})
    assert (cov["rows_published"], cov["rows_compared"]) == (2, 1)
    assert cov["not_compared"][0]["reason"].startswith("scan page 3")
