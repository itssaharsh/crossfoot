"""T04d: the sums of a contest block in the report layout, with the rows of Jones page 1 (President, precinct 1) as printed
there. Fake answers only; no network, no model."""
from crossfoot import checks
from crossfoot.ledger import Ledger

from tests.test_report_layout import DEM, audit_of, frow, put

# labels and figures as printed on Jones page 1: total, absentee, early voting, election day
JONES_P1 = [
    ("REP Donald J. Trump/JD Vance", (976, 23, 565, 388)),
    ("DEM Kamala D. Harris/Tim Walz", (219, 24, 105, 90)),
    ("LIB Chase Oliver/Mike ter Maat", (6, 1, 3, 2)),
    ("GRN Jill Stein/Rudolph Ware", (4, 0, 0, 4)),
    ("Write-In Totals", (1, 0, 0, 1)),
    ("Write-In: Uncertified", (1, 0, 0, 1)),
    ("Write-In: Peter Sonski/Lauren Onak", (0, 0, 0, 0)),
    ("Not Assigned", (0, 0, 0, 0)),
    ("Total Votes Cast", (1206, 48, 673, 485)),
    ("Overvotes", (0, 0, 0, 0)),
    ("Undervotes", (8, 1, 3, 4)),
]
BALLOTS = (1214, 49, 676, 489)           # Statistics block: "Ballots Cast - Total"


def jones(ballots=BALLOTS, edit=None):
    led = Ledger()
    for i, (label, vals) in enumerate(JONES_P1):
        put(led, 1, "1|1", label, (edit or {}).get(label, vals), contest_name="President/Vice President", y=100 + 40 * i)
    if ballots:
        put(led, 1, "1|st", "Ballots Cast - Total", ballots, contest_name="Ballots Cast", y=60)
    return led.cells("x")


def of_kind(cs, kind):
    return [c for c in checks.report_checks(cs) if c.kind == kind]


def test_candidates_and_write_in_total_add_to_the_contest_total_and_breakdown_rows_are_not_terms():
    con = of_kind(jones(), "report_contest")
    assert sorted(c.key for c in con) == sorted(checks.REPORT_COLS) and all(c.ok for c in con)
    labels = {k[2] for c in con for k, _ in c.terms}
    assert "Write-In Totals" in labels
    assert labels.isdisjoint({"Write-In: Uncertified", "Write-In: Peter Sonski/Lauren Onak", "Not Assigned"})
    assert len(con[0].terms) == 5


def test_the_write_in_breakdown_adds_to_the_write_in_total():
    wi = of_kind(jones(), "report_writein")
    assert sorted(c.key for c in wi) == sorted(checks.REPORT_COLS) and all(c.ok for c in wi)
    assert {k[2] for k, _ in wi[0].terms} == {"Write-In: Uncertified", "Write-In: Peter Sonski/Lauren Onak", "Not Assigned"}
    assert wi[0].printed_key[2] == "Write-In Totals"


def test_a_wrong_breakdown_row_fails_only_the_breakdown_sum():
    cs = jones(edit={"Write-In: Uncertified": (2, 0, 0, 2)})
    bad = {(c.kind, c.key) for c in checks.report_checks(cs) if not c.ok}
    assert bad == {("report_writein", "total"), ("report_writein", "election_day")}


def test_contest_total_plus_over_and_under_votes_adds_to_the_ballots_cast():
    bc = of_kind(jones(), "report_ballots")
    assert sorted(c.key for c in bc) == sorted(checks.REPORT_COLS) and all(c.ok for c in bc)
    assert {k[2] for k, _ in bc[0].terms} == {"Total Votes Cast", "Overvotes", "Undervotes"}
    assert bc[0].printed_key == (1, "1|st", "Ballots Cast - Total", "total")


def test_a_contest_that_covers_only_part_of_the_precinct_does_not_use_the_ballots_sum_and_says_so():
    short = (1300, 60, 700, 540)                    # every column is above the contest's, by the same sign
    cs = jones(ballots=short)
    assert of_kind(cs, "report_ballots") == []
    used, unused = checks.report_ballot_sums(cs)
    assert used == [] and len(unused) == 1
    assert unused[0]["block"] == "1|1" and "any column" in unused[0]["why"]


def test_a_ballots_sum_that_fails_in_one_column_is_used_and_fails():
    cs = jones(edit={"Undervotes": (8, 1, 3, 5)})
    bad = [c for c in of_kind(cs, "report_ballots") if not c.ok]
    assert [c.key for c in bad] == ["election_day"]


def test_no_statistics_row_means_no_ballots_sum():
    assert of_kind(jones(ballots=None), "report_ballots") == []


def test_breakdown_rows_are_found_by_their_arithmetic_when_no_label_says_so():
    led = Ledger()
    for i, (label, vals) in enumerate([("REP A", (10, 2, 5, 3)), ("Write-In Totals", (3, 1, 1, 1)),
                                       ("Smith", (2, 1, 0, 1)), ("Jones", (1, 0, 1, 0)),
                                       ("Cast Votes", (13, 3, 6, 4))]):
        put(led, 1, "1|1", label, vals, y=100 + 40 * i)
    cs = led.cells("x")
    assert all(c.ok for c in of_kind(cs, "report_contest")) and len(of_kind(cs, "report_contest")) == 4
    wi = of_kind(cs, "report_writein")
    assert len(wi) == 4 and all(c.ok for c in wi)


def test_rows_under_a_write_in_total_that_do_not_add_up_and_have_no_label_shape_are_candidates():
    led = Ledger()
    for i, (label, vals) in enumerate([("Write-In Totals", (3, 1, 1, 1)), ("REP A", (10, 2, 5, 3)),
                                       ("Cast Votes", (13, 3, 6, 4))]):
        put(led, 1, "1|1", label, vals, y=100 + 40 * i)
    cs = led.cells("x")
    assert of_kind(cs, "report_writein") == []
    assert all(c.ok for c in of_kind(cs, "report_contest"))


def test_a_row_off_by_100_in_its_total_and_one_part_is_settled_by_the_two_column_sums(tmp_path):
    from tests.test_report_layout import scan_ledger
    rows = [frow(110, 2, 105, 3), DEM]               # adds up by itself; the scan's row is 10 = 2 + 5 + 3
    res, gw, geo = audit_of(tmp_path, scan_ledger(with_total=True), rows)
    fs = [f for f in res["findings"] if f["candidate"] == "Ted Cruz"]
    assert {f["part"] for f in fs} == {"votes", "early_voting"}
    assert all(f["status"] == "settled_against_file" for f in fs)
    assert gw.calls == 0


# ---- a page that failed in the first read, read into the ledger afterwards ---------------------------------------------

def test_a_page_read_afterwards_gets_block_ids_that_no_other_page_uses_and_joins_a_contest_that_continues(tmp_path):
    from PIL import Image

    from crossfoot.layouts import report
    from tests.test_report_layout import COLS, HAIKU, FakeGw, row
    led = Ledger()
    put(led, 17, "10|5", "DEM A", (4, 1, 1, 2), contest_name="Justice, Supreme Court, Pl 2")
    put(led, 19, "10|6", "REP B", (4, 1, 1, 2), contest_name="Dist Judge")
    led.event("x", "page_read", {"page": 17, "precinct": "PRECINCT 10", "model": HAIKU, "cells": 4, "contests": 1})
    led.event("x", "layout", {"layout": "report", "columns": list(COLS), "x_right": 900, "size": [1000, 1400]})
    led.event("x", "choose_reader", {"reader": HAIKU})
    ans = {"precinct": "PRECINCT 10", "contests": [
        {"name": "", "continued": True, "rows": [row("DEM C", 3, 1, 1, 1, y=100)]},
        {"name": "Justice, Supreme Court, Pl 4", "continued": False, "rows": [row("REP D", 2, 0, 1, 1, y=200)]}]}
    gw = FakeGw(lambda k, m, n: ans)
    png = tmp_path / "p.png"
    Image.new("L", (1000, 1400), 255).save(png)
    r = report.read_pages_into("x", gw, led, [18], log=lambda *a: None, png_fn=lambda *a: png)
    assert r["pages_read"] == [18] and r["pages_failed"] == []
    blocks = {(c["page"], c["row_kind"]): c["block_id"] for c in led.cells("x")}
    assert blocks[(18, "DEM C")] == "10|5"                  # the contest of page 17 carried on
    assert blocks[(18, "REP D")] == "10|7"                  # above every block id of the precinct, so none is shared
    assert any(e["kind"] == "page_read" and '"page": 18' in e["payload_json"] for e in led.events("x"))


def test_a_row_estimated_a_little_below_the_page_edge_is_clamped_not_refused():
    from crossfoot.layouts import report
    from tests.test_report_layout import row
    d = {"precinct": "10", "contests": [{"name": "C", "continued": False, "rows": [row("REP A", 1, 0, 0, 1, y=1108)]}]}
    report.page_validator(d)
    assert d["contests"][0]["rows"][0]["y"] == 1000
    d["contests"][0]["rows"][0]["y"] = 5000
    try:
        report.page_validator(d)
        raise AssertionError("a position far off the page must still be refused")
    except ValueError:
        pass


def test_the_summary_says_which_second_sum_each_layout_has():
    from crossfoot import allrun
    assert allrun.second_sum_text("matrix", False) == "row and column"
    assert allrun.second_sum_text("report", False) == "row only"
    assert allrun.second_sum_text("report", True) == "row and contest"
    assert allrun.second_sum_text("no_printed_totals", False) == ""
