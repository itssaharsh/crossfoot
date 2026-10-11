"""T05: scoring a claimed list of disagreements against the audit's findings; the printed total on each side of a sum."""
from crossfoot import audit, score


def cell(col, row_kind, value, block="b0", page=1):
    return {"page": page, "block_id": block, "row_kind": row_kind, "column": col, "value": value}


def total(direction, key, value, block="b0", page=1):
    return {"page": page, "block_id": block, "direction": direction, "key": key, "value": value}


# a block of one column "1": early 2, absentee 3, precinct 5, printed subtotal 10
CELLS = [cell("1", "EARLY", 2), cell("1", "ABSENTEE", 3), cell("1", "PRECINCT", 5)]
TOTALS = [total("col", "1", 10), total("row", "EARLY", 2), total("row", "ABSENTEE", 3), total("row", "PRECINCT", 5)]


def test_every_sum_side_holds_exactly_when_computed_equals_its_own_printed_total():
    cases = [(("cell", 1, "b0", "EARLY", "1"), 2, 4),     # a cell: the file has another value
             (("cell", 1, "b0", "EARLY", "1"), 2, 2),
             (("total", 1, "b0", "col", "1"), 10, 7)]     # a printed total: the file's value replaces the printed one
    seen_total_side = False
    for ent, scan_v, file_v in cases:
        sums = audit.sums_for(ent, scan_v, file_v, CELLS, TOTALS)
        assert sums
        for s in sums:
            assert s["holds_with_scan"] == (s["computed_with_scan"] == s["printed_with_scan"])
            assert s["holds_with_file"] == (s["computed_with_file"] == s["printed_with_file"])
            if ent[0] == "total" and s["kind"] == "col":
                seen_total_side = True
                assert s["printed_with_scan"] == 10 and s["printed_with_file"] == 7
                assert s["computed_with_file"] == 10 and not s["holds_with_file"]
    assert seen_total_side


# ---- scoring -----------------------------------------------------------------------------------------------------

def finding(office, cand, prec, part, fv, sv, status, district=""):
    return {"office": office, "district": district, "candidate": cand, "precinct": prec, "part": part,
            "file_value": fv, "scan_value": sv, "status": status, "kind": "wrong_number"}


def prow(office, cand, prec, **parts):
    return {"office": office, "district": "", "candidate": cand, "precinct": prec,
            **{p: str(parts.get(p, 0)) for p in ("votes", "absentee", "early_voting", "election_day")}}


FINDINGS = [
    finding("President", "Jill Stein", "2", "early_voting", 1, 0, "settled_against_file"),
    finding("President", "Jill Stein", "3", "early_voting", 4, 5, "settled_against_file"),
    finding("U.S. Senate", "Ted Cruz", "7", "votes", 10, 12, "cannot_verify"),
    finding("U.S. Senate", "Ted Brown", "7", "votes", 9, 8, "settled_against_file"),
]
ROWS = [prow("President", "Jill Stein", "2", early_voting=1), prow("President", "Donald J. Trump", "2", votes=50),
        prow("U.S. Senate", "Ted Cruz", "7", votes=10)]


def claim(office, cand, prec, part, fv, sv):
    return {"office": office, "candidate": cand, "precinct": prec, "part": part, "file_value": fv, "scan_value": sv}


def test_each_claim_lands_in_one_group_and_the_audits_other_settled_findings_are_listed():
    claims = [
        claim("President", "Jill Stein", "2", "early_voting", 1, 0),          # settled
        claim("U.S. Senate", "Ted  Cruz", "7", "votes", 10, 12),               # same value, no printed total decides
        claim("President", "Donald J. Trump", "2", "votes", 50, 49),          # the ledger holds the file's value
        claim("President", "Nobody Atall", "2", "votes", 1, 2),                # label not found
        claim("U.S. Senate", "Ted Brown", "7", "votes", 9, 11),               # the ledger reads a third value
    ]
    res = score.score(claims, FINDINGS, ROWS)
    by = {k: [c["claim"]["candidate"] for c in v] for k, v in res["groups"].items()}
    assert by["settled"] == ["Jill Stein"]
    assert by["same_but_undecided"] == ["Ted  Cruz"]
    assert by["contradicted"] == ["Donald J. Trump"]
    assert by["not_matched"] == ["Nobody Atall"]
    assert by["other_value"] == ["Ted Brown"]
    assert res["counts"] == {"claims": 5, "settled": 1, "same_but_undecided": 1, "contradicted": 1, "not_matched": 1,
                             "other_value": 1}
    assert [(m["candidate"], m["precinct"]) for m in res["missed_settled"]] == [("Jill Stein", "3")]
    assert res["audit_settled"] == 3


def test_a_label_that_differs_only_in_case_and_punctuation_still_matches():
    res = score.score([claim("president", "JILL STEIN", "2", "early_voting", 1, 0)], FINDINGS, ROWS)
    assert res["counts"]["settled"] == 1 and res["counts"]["not_matched"] == 0
