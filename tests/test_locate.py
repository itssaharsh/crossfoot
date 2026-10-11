"""Pairing: a value sits on two sums; two failing sums that share it, with agreeing differences, point at it."""
from crossfoot import checks

ROWS = ("EARLY", "ABSENTEE", "PRECINCT")
GOOD = {"1": (10, 2, 3), "2": (20, 4, 6), "3": (5, 5, 5)}   # column -> EARLY, ABSENTEE, PRECINCT


def block(cells=None, row_totals=None, col_totals=None, grand=None, reg=None):
    """A block whose printed totals are those of GOOD; the arguments override what the first read gave."""
    cells, row_totals, col_totals = cells or {}, row_totals or {}, col_totals or {}
    cs, ts = [], []
    for col, vals in GOOD.items():
        for r, v in zip(ROWS, vals):
            cs.append(dict(page=1, block_id="b", row_kind=r, column=col, value=cells.get((r, col), v)))
        ts.append(dict(page=1, block_id="b", direction="col", key=col, value=col_totals.get(col, sum(vals))))
    for i, r in enumerate(ROWS):
        ts.append(dict(page=1, block_id="b", direction="row", key=r,
                       value=row_totals.get(r, sum(v[i] for v in GOOD.values()))))
    ts.append(dict(page=1, block_id="b", direction="grand", key="",
                   value=grand if grand is not None else sum(sum(v) for v in GOOD.values())))
    return cs, ts


def found(cs, ts):
    return checks.suspects(checks.all_checks(cs, ts))


def test_a_block_that_holds_has_no_suspects():
    r = found(*block())
    assert r.suspects == [] and r.unlocated == []


def test_one_wrong_cell_is_found_with_the_value_it_must_have():
    r = found(*block(cells={("EARLY", "2"): 26}))
    assert [(s.entity, s.read, s.would_be) for s in r.suspects] == [((1, "b", "EARLY", "2"), 26, 20)]
    assert {c.kind for c in r.suspects[0].sums} == {"row", "col"}
    assert r.unlocated == []


def test_one_wrong_small_total_sits_on_its_column_and_the_grand_total():
    r = found(*block(col_totals={"2": 35}))                       # printed 35 for 30
    assert [(s.entity, s.read, s.would_be) for s in r.suspects] == [((1, "b", "col", "2"), 35, 30)]
    assert {c.kind for c in r.suspects[0].sums} == {"col", "grand_col"}


def test_one_wrong_row_total_sits_on_its_row_and_the_grand_total_by_rows():
    r = found(*block(row_totals={"ABSENTEE": 14}))                # printed 14 for 11
    assert [(s.entity, s.read, s.would_be) for s in r.suspects] == [((1, "b", "row", "ABSENTEE"), 14, 11)]
    assert {c.kind for c in r.suspects[0].sums} == {"row", "grand_row"}


def test_a_wrong_grand_total_fails_both_grand_checks_and_is_found():
    r = found(*block(grand=100))
    assert [(s.entity, s.would_be) for s in r.suspects] == [((1, "b", "grand", ""), 60)]
    assert {c.kind for c in r.suspects[0].sums} == {"grand_col", "grand_row"}


def test_two_wrong_cells_in_different_rows_and_columns_are_both_found():
    r = found(*block(cells={("EARLY", "1"): 13, ("PRECINCT", "3"): 9}))      # +3 and +4: the differences differ
    got = {(s.entity, s.would_be) for s in r.suspects}
    assert got == {((1, "b", "EARLY", "1"), 10), ((1, "b", "PRECINCT", "3"), 5)}


def test_two_wrong_cells_with_the_same_error_are_ambiguous_not_guessed():
    r = found(*block(cells={("EARLY", "1"): 12, ("PRECINCT", "3"): 7}))      # both +2: four crossings agree
    assert r.suspects == []
    assert r.unlocated and all("more than one" in why for _, why in r.unlocated)


def test_two_wrong_cells_in_one_row_cannot_be_paired_and_it_says_so():
    r = found(*block(cells={("EARLY", "1"): 12, ("EARLY", "2"): 23}))        # +2, +3 on one row: row fails by 5
    assert r.suspects == []
    assert {c.kind for c, _ in r.unlocated} == {"row", "col"}
    assert all("cannot be paired" in why for _, why in r.unlocated)


def test_the_registered_row_sits_on_one_sum_and_says_so():
    cs = [dict(page=1, block_id="reg", row_kind="REGISTERED", column=c, value=v) for c, v in (("1", 50), ("2", 61))]
    ts = [dict(page=1, block_id="reg", direction="row", key="REGISTERED", value=100)]
    chs = checks.all_checks(cs, ts)
    assert [c.kind for c in chs] == ["row"] and "one sum only" in chs[0].note
    r = checks.suspects(chs)
    assert r.suspects == [] and "one sum only" in r.unlocated[0][1]


def test_an_unread_term_is_not_paired():
    cs, ts = block()
    cs[0]["value"] = None
    r = found(cs, ts)
    assert r.suspects == [] and all("unread" in why for _, why in r.unlocated)


def test_the_sign_of_the_error_is_carried_both_ways():
    r = found(*block(cells={("EARLY", "1"): 3}))     # -7 on the cell: it would have to be 10, fine; now a total
    assert [s.would_be for s in r.suspects] == [10]
    r2 = found(*block(col_totals={"1": 2}))          # small total read 2 for 15 (-13): would be 15
    assert [s.would_be for s in r2.suspects] == [15]


def test_both_grand_checks_are_kinds_of_their_own():
    cs, ts = block()
    assert [c.kind for c in checks.all_checks(cs, ts) if c.kind.startswith("grand")] == ["grand_col", "grand_row"]
