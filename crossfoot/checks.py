"""Row sums, column sums and grid completeness. Pure functions: no I/O, no model.

Inputs are plain dicts as the ledger returns them. A cell needs `page, block_id, row_kind, column, value`
(value None means unread). A printed total is `page, block_id, direction, key, value` with direction
'row' (key = row_kind), 'col' (key = column) or 'grand' (key ignored).
A cell is identified by the tuple (page, block_id, row_kind, column), called a cell key below.
"""
from __future__ import annotations

from dataclasses import dataclass, field

ROW_TOTAL_COLUMN = "TOTAL"  # a cell in this column is the row's printed total, not a term


@dataclass
class Check:
    kind: str                 # 'row' | 'col' | 'grand_col' (small totals add to the grand total) | 'grand_row' (row totals do)
    page: int
    block_id: str
    key: str                  # row_kind for a row sum, column for a column sum, '' for grand
    terms: list = field(default_factory=list)  # [(cell key, value)]
    printed: int | None = None
    computed: int | None = None  # None when a term is unread
    ok: bool = False
    printed_key: tuple | None = None   # the printed total as a value of its own: (page, block, 'row'|'col'|'grand', key)
    note: str = ""                     # what is special about this sum (the registered-voters row sits on one sum only)


def cell_key(c: dict) -> tuple:
    return (c["page"], c["block_id"], c["row_kind"], c["column"])


def _printed(totals, direction):
    return {(t["page"], t["block_id"], t["key"] if direction != "grand" else ""): t["value"]
            for t in totals if t["direction"] == direction}


ONE_SUM = "registered voters: this row has no column sums, so its values sit on one sum only"


def _make(kind, page, block, key, cells, printed, printed_key=None, note="") -> Check:
    terms = [(cell_key(c), c["value"]) for c in cells]
    computed = None if any(v is None for _, v in terms) else sum(v for _, v in terms)
    return Check(kind, page, block, key, terms, printed, computed, computed is not None and computed == printed,
                 printed_key, note)


def row_checks(cells: list[dict], totals: list[dict]) -> list[Check]:
    """One check per (page, block, row_kind) that has a printed row total: the row's cells must add to it."""
    printed = _printed(totals, "row")
    groups: dict = {}
    for c in cells:
        if c["column"] != ROW_TOTAL_COLUMN:
            groups.setdefault((c["page"], c["block_id"], c["row_kind"]), []).append(c)
    return [_make("row", *k, g, printed[k], (k[0], k[1], "row", k[2]), ONE_SUM if k[2] == "REGISTERED" else "")
            for k, g in groups.items() if k in printed]


def column_checks(cells: list[dict], totals: list[dict]) -> list[Check]:
    """One check per (page, block, column) that has a printed column total: the column's cells must add to it."""
    printed = _printed(totals, "col")
    groups: dict = {}
    for c in cells:
        groups.setdefault((c["page"], c["block_id"], c["column"]), []).append(c)
    return [_make("col", *k, g, printed[k], (k[0], k[1], "col", k[2])) for k, g in groups.items() if k in printed]


def grand_checks(totals: list[dict]) -> list[Check]:
    """The printed column totals of a block must add to its printed grand total (kind 'grand_col')."""
    grand = _printed(totals, "grand")
    out = []
    for (page, block, _), g in grand.items():
        cols = [t for t in totals if t["direction"] == "col" and t["page"] == page and t["block_id"] == block]
        terms = [((page, block, "col", t["key"]), t["value"]) for t in cols]
        comp = sum(v for _, v in terms)
        out.append(Check("grand_col", page, block, "", terms, g, comp, comp == g, (page, block, "grand", "")))
    return out


def grand_row_checks(totals: list[dict]) -> list[Check]:
    """The printed row totals of a block must add to its printed grand total (kind 'grand_row'). The registered-voters
    row is not a term: it is not a count of ballots."""
    grand = _printed(totals, "grand")
    out = []
    for (page, block, _), g in grand.items():
        rows = [t for t in totals if t["direction"] == "row" and t["page"] == page and t["block_id"] == block and
                t["key"] != "REGISTERED"]
        if not rows:
            continue
        terms = [((page, block, "row", t["key"]), t["value"]) for t in rows]
        comp = sum(v for _, v in terms)
        out.append(Check("grand_row", page, block, "", terms, g, comp, comp == g, (page, block, "grand", "")))
    return out


def grid_gaps(cells: list[dict]) -> list[tuple]:
    """Cell keys that are absent or unread where the block's grid says they should be.

    Within a block the grid is every row_kind crossed with every column that appears in it.
    Returns sorted (page, block_id, row_kind, column) tuples.
    """
    blocks: dict = {}
    for c in cells:
        b = blocks.setdefault((c["page"], c["block_id"]), {"rows": set(), "cols": set(), "have": set()})
        b["rows"].add(c["row_kind"]); b["cols"].add(c["column"])
        if c["value"] is not None:
            b["have"].add((c["row_kind"], c["column"]))
    return sorted((p, bid, r, col) for (p, bid), b in blocks.items()
                  for r in b["rows"] for col in b["cols"] if (r, col) not in b["have"])


def locate(rows: list[Check], cols: list[Check]) -> list[tuple]:
    """Cell keys that sit on a failing row sum and on a failing column sum at once."""
    bad_rows = {k for ch in rows if not ch.ok for k, _ in ch.terms}
    bad_cols = {k for ch in cols if not ch.ok for k, _ in ch.terms}
    return sorted(bad_rows & bad_cols)


def all_checks(cells: list[dict], totals: list[dict]) -> list[Check]:
    return row_checks(cells, totals) + column_checks(cells, totals) + grand_checks(totals) + grand_row_checks(totals)


@dataclass
class Suspect:
    entity: tuple     # a cell key (page, block, row_kind, column) or a printed total (page, block, 'row'|'col'|'grand', key)
    read: int         # the value now in the ledger
    would_be: int     # the value both of its sums need
    error: int        # read - would_be
    sums: tuple       # the two failing Checks it sits on


@dataclass
class Located:
    suspects: list = field(default_factory=list)
    unlocated: list = field(default_factory=list)   # [(Check, why)]: failing sums no single value explains


def suspects(chs: list[Check]) -> Located:
    """Pair failing sums. A value that sits on exactly two failing sums, and is off by the same amount on both (the sign
    its place in each sum gives), is a suspect, and the value both sums need is `would_be`. A value read too high by e
    makes a sum it is a term of too high by e, and a sum it is the printed total of too low by e. Pure arithmetic:
    it says where to look, never what to write. A failing sum that no unique suspect explains is `unlocated`, with the
    reason (an unread term, one sum only, more than one candidate, or differences that do not pair)."""
    failing = [c for c in chs if not c.ok]
    out = Located()
    on: dict = {}                                  # entity -> [(Check, error it implies, value)]
    unread = []
    for c in failing:
        if c.computed is None or c.printed is None:
            unread.append(c)
            continue
        d = c.computed - c.printed
        for k, v in c.terms:
            on.setdefault(k, []).append((c, d, v))
        if c.printed_key is not None:
            on.setdefault(c.printed_key, []).append((c, -d, c.printed))
    cand = []
    for e, lst in on.items():
        if len(lst) == 2 and lst[0][1] == lst[1][1] != 0 and lst[0][2] - lst[0][1] >= 0:
            cand.append(Suspect(e, lst[0][2], lst[0][2] - lst[0][1], lst[0][1], (lst[0][0], lst[1][0])))
    uses: dict = {}
    for s in cand:
        for c in s.sums:
            uses[id(c)] = uses.get(id(c), 0) + 1
    out.suspects = [s for s in cand if all(uses[id(c)] == 1 for c in s.sums)]
    explained = {id(c) for s in out.suspects for c in s.sums}
    for c in failing:
        if id(c) in explained:
            continue
        if c in unread:
            why = "a term is unread"
        elif c.note:
            why = f"one sum only: {c.note}"
        elif uses.get(id(c), 0) > 1:
            why = "more than one value could be the one: several pairs of failing sums agree"
        else:
            why = "its difference cannot be paired with another failing sum (two or more wrong values may share it)"
        out.unlocated.append((c, why))
    return out


def crossing(cells: list[dict], totals: list[dict]) -> dict:
    """For each cell key, the row and column checks it sits on (a cell on no printed sum maps to an empty list)."""
    on: dict = {cell_key(c): [] for c in cells if c["column"] != ROW_TOTAL_COLUMN}
    for ch in row_checks(cells, totals) + column_checks(cells, totals):
        for k, _ in ch.terms:
            on[k].append(ch)
    return on
