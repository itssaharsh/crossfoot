from crossfoot.checks import column_checks, grid_gaps, locate, row_checks


def cell(row, col, v, block="b1", page=1):
    return dict(page=page, block_id=block, row_kind=row, column=col, value=v)


def tot(direction, key, v, block="b1", page=1):
    return dict(page=page, block_id=block, direction=direction, key=key, value=v)


# 2 rows x 3 columns; row totals 6 and 15, column totals 5, 7, 9
CELLS = [cell("A", "c1", 1), cell("A", "c2", 2), cell("A", "c3", 3),
         cell("B", "c1", 4), cell("B", "c2", 5), cell("B", "c3", 6)]
TOTALS = [tot("row", "A", 6), tot("row", "B", 15),
          tot("col", "c1", 5), tot("col", "c2", 7), tot("col", "c3", 9)]


def test_all_sums_hold():
    r, c = row_checks(CELLS, TOTALS), column_checks(CELLS, TOTALS)
    assert len(r) == 2 and len(c) == 3
    assert all(x.ok for x in r + c)
    assert locate(r, c) == []


def test_check_reports_terms_printed_computed():
    r = row_checks(CELLS, TOTALS)[0]
    assert r.printed == 6 and r.computed == 6 and [v for _, v in r.terms] == [1, 2, 3]


def test_one_wrong_cell_fails_both_and_locates_it():
    cells = [dict(c) for c in CELLS]
    cells[4]["value"] = 8  # B/c2 misread
    r, c = row_checks(cells, TOTALS), column_checks(cells, TOTALS)
    assert [x.key for x in r if not x.ok] == ["B"]
    assert [x.key for x in c if not x.ok] == ["c2"]
    assert locate(r, c) == [(1, "b1", "B", "c2")]


def test_failing_row_alone_locates_nothing():
    cells = [dict(c) for c in CELLS]
    totals = [dict(t) for t in TOTALS]
    totals[0]["value"] = 7  # printed row total wrong; no column fails
    r, c = row_checks(cells, totals), column_checks(cells, totals)
    assert not r[0].ok and all(x.ok for x in c)
    assert locate(r, c) == []


def test_unread_term_fails_and_gap_listed():
    cells = [dict(c) for c in CELLS]
    cells[0]["value"] = None
    r = row_checks(cells, TOTALS)[0]
    assert r.computed is None and not r.ok
    assert grid_gaps(cells) == [(1, "b1", "A", "c1")]


def test_missing_cell_is_a_gap():
    assert grid_gaps(CELLS[:-1]) == [(1, "b1", "B", "c3")]
    assert grid_gaps(CELLS) == []


def test_total_column_cell_is_not_a_term():
    cells = CELLS + [cell("A", "TOTAL", 6)]
    r = row_checks(cells, TOTALS)[0]
    assert len(r.terms) == 3 and r.ok
