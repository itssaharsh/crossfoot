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
    kind: str                 # 'row' | 'col' | 'grand'
    page: int
    block_id: str
    key: str                  # row_kind for a row sum, column for a column sum, '' for grand
    terms: list = field(default_factory=list)  # [(cell key, value)]
    printed: int | None = None
    computed: int | None = None  # None when a term is unread
    ok: bool = False


def cell_key(c: dict) -> tuple:
    return (c["page"], c["block_id"], c["row_kind"], c["column"])


def _printed(totals, direction):
    return {(t["page"], t["block_id"], t["key"] if direction != "grand" else ""): t["value"]
            for t in totals if t["direction"] == direction}


def _make(kind, page, block, key, cells, printed) -> Check:
    terms = [(cell_key(c), c["value"]) for c in cells]
    computed = None if any(v is None for _, v in terms) else sum(v for _, v in terms)
    return Check(kind, page, block, key, terms, printed, computed, computed is not None and computed == printed)


def row_checks(cells: list[dict], totals: list[dict]) -> list[Check]:
    """One check per (page, block, row_kind) that has a printed row total: the row's cells must add to it."""
    printed = _printed(totals, "row")
    groups: dict = {}
    for c in cells:
        if c["column"] != ROW_TOTAL_COLUMN:
            groups.setdefault((c["page"], c["block_id"], c["row_kind"]), []).append(c)
    return [_make("row", *k, g, printed[k]) for k, g in groups.items() if k in printed]


def column_checks(cells: list[dict], totals: list[dict]) -> list[Check]:
    """One check per (page, block, column) that has a printed column total: the column's cells must add to it."""
    printed = _printed(totals, "col")
    groups: dict = {}
    for c in cells:
        groups.setdefault((c["page"], c["block_id"], c["column"]), []).append(c)
    return [_make("col", *k, g, printed[k]) for k, g in groups.items() if k in printed]


def grand_checks(totals: list[dict]) -> list[Check]:
    """The printed column totals of a block must add to its printed grand total."""
    grand = _printed(totals, "grand")
    out = []
    for (page, block, _), g in grand.items():
        cols = [t for t in totals if t["direction"] == "col" and t["page"] == page and t["block_id"] == block]
        terms = [((page, block, "col", t["key"]), t["value"]) for t in cols]
        comp = sum(v for _, v in terms)
        out.append(Check("grand", page, block, "", terms, g, comp, comp == g))
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
    return row_checks(cells, totals) + column_checks(cells, totals) + grand_checks(totals)


def crossing(cells: list[dict], totals: list[dict]) -> dict:
    """For each cell key, the row and column checks it sits on (a cell on no printed sum maps to an empty list)."""
    on: dict = {cell_key(c): [] for c in cells if c["column"] != ROW_TOTAL_COLUMN}
    for ch in row_checks(cells, totals) + column_checks(cells, totals):
        for k, _ in ch.terms:
            on[k].append(ch)
    return on
