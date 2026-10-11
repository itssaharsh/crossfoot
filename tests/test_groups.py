"""A block wider than the model's size limit is cut into column groups that cover every precinct once."""
from crossfoot.layouts import matrix


def edges(n, x0=500, step=110):
    return [x0 + i * step for i in range(n + 1)]


def test_groups_cover_every_column_once_in_order():
    n = 19
    gs = matrix.plan_groups(edges(n), 100, edges(n)[-1] + 150, scale=1.5, max_w=1500)
    cols = [c for g in gs for c in range(g.c0, g.c1)]
    assert cols == list(range(n))
    assert len(gs) > 1


def test_each_group_is_within_limit_and_labels_only_first_total_only_last():
    n = 19
    e = edges(n)
    gs = matrix.plan_groups(e, 100, e[-1] + 150, scale=1.5, max_w=1500)
    for g in gs:
        assert g.width <= 1500
    assert [g.labels for g in gs] == [True] + [False] * (len(gs) - 1)
    assert [g.total for g in gs] == [False] * (len(gs) - 1) + [True]


def test_narrow_block_is_one_group():
    e = edges(3)
    gs = matrix.plan_groups(e, 100, e[-1] + 150, scale=1.0, max_w=1500)
    assert len(gs) == 1 and gs[0].labels and gs[0].total and (gs[0].c0, gs[0].c1) == (0, 3)


def test_merge_keeps_values_tied_to_precinct_and_row_kind():
    a = {"candidate": "X", "contest": "C", "rows": {r: {"values": [1, 2], "total": None} for r in matrix.ROWS},
         "col_totals": [3, 3], "grand": None}
    b = {"candidate": None, "contest": None, "rows": {r: {"values": [7], "total": 10} for r in matrix.ROWS},
         "col_totals": [21], "grand": 30}
    m = matrix.merge_groups([a, b])
    assert m["rows"]["EARLY"]["values"] == [1, 2, 7] and m["rows"]["EARLY"]["total"] == 10
    assert m["col_totals"] == [3, 3, 21] and m["grand"] == 30 and m["candidate"] == "X"


def test_edges_skip_the_row_label_box_line():
    n = 19

    class B:
        lines = [478] + [602 + 101 * i for i in range(n + 1)]
    e = matrix._edges([B], n)
    assert len(e) == n + 1 and e[0] == 602 and e[-1] == 602 + 101 * n
