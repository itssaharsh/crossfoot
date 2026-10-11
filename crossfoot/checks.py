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


# ---- the report layout: one row per candidate, four numbers each --------------------------------------------------------
# A row's cells are keyed (page, block, row label, column) with column in REPORT_COLS. A block is one contest on one
# precinct, and may run over a page break (its cells then carry different pages and the same block id).

REPORT_COLS = ("total", "absentee", "early", "election_day")
_CONTEST_TOTAL = ("total votes cast", "cast votes")
_NOT_A_CANDIDATE = ("overvotes", "over votes", "undervotes", "under votes")


def row_label_kind(label) -> str:
    """'total' for the printed contest total, 'skip' for over/under votes (they are not candidates), else 'candidate'."""
    s = " ".join(str(label or "").lower().split())
    return "total" if s in _CONTEST_TOTAL else "skip" if s in _NOT_A_CANDIDATE else "candidate"


def _rows_of(cells):
    rows: dict = {}
    for c in cells:
        rows.setdefault((c["page"], c["block_id"], c["row_kind"]), {})[c["column"]] = c
    return rows


def report_row_checks(cells: list[dict]) -> list[Check]:
    """One check per row that prints a total and all three parts: total = absentee + early voting + election day."""
    out = []
    for (page, block, label), cols in _rows_of(cells).items():
        if "total" not in cols or any(k not in cols for k in REPORT_COLS[1:]):
            continue
        t = cols["total"]
        ch = _make("report_row", page, block, label, [cols[k] for k in REPORT_COLS[1:]], t["value"],
                   (page, block, label, "total"))
        out.append(ch)
    return out


def _norm(label) -> str:
    return " ".join(str(label or "").lower().split())


def is_write_in_total(label) -> bool:
    return _norm(label).replace("-", " ") in ("write in totals", "write in total")


def _write_in_shaped(label) -> bool:
    return _norm(label).replace("-", " ").replace(" :", ":").startswith("write in:")


def contest_shape(rows: list) -> dict:
    """What the rows of one contest block are, from what the page shows. `rows` is [(page, label, {column: cell})] in print
    order. Returns {total, write_in, breakdown, candidates, over, under} (rows, or lists of rows). The rows printed directly
    under the write-in total, up to the contest total or the over/under votes, are a breakdown of it when one of them has the
    label shape "Write-In: ..." or when they add to the write-in total in its total column; otherwise they are candidates."""
    kinds = [row_label_kind(r[1]) for r in rows]
    total = next((r for r, k in zip(rows, kinds) if k == "total"), None)
    wi_i = next((i for i, r in enumerate(rows) if is_write_in_total(r[1])), None)
    breakdown: list = []
    if wi_i is not None:
        end = next((i for i in range(wi_i + 1, len(rows)) if kinds[i] != "candidate"), len(rows))
        between = rows[wi_i + 1:end]
        wt = rows[wi_i][2].get("total")
        sums = [r[2].get("total") for r in between]
        if between and (any(_write_in_shaped(r[1]) for r in between) or
                        (wt is not None and None not in sums and sum(x["value"] for x in sums) == wt["value"])):
            breakdown = between
    out_of = {id(r) for r in breakdown}
    if wi_i is not None:
        out_of.add(id(rows[wi_i]))                       # the write-in total is not a candidate: it is a term of its own
    named = lambda *names: next((r for r in rows if _norm(r[1]) in names), None)
    return {"total": total, "write_in": rows[wi_i] if wi_i is not None else None, "breakdown": breakdown,
            "candidates": [r for r, k in zip(rows, kinds) if k == "candidate" and id(r) not in out_of],
            "over": named("overvotes", "over votes"), "under": named("undervotes", "under votes")}


def _blocks(cells):
    by_block: dict = {}
    for (page, block, label), cols in _rows_of(cells).items():
        by_block.setdefault(block, []).append((page, label, cols))
    return by_block


def report_contest_checks(cells: list[dict]) -> list[Check]:
    """For a contest that prints a total row: per column, the candidates' figures and the write-in total's figure add to the
    total row's figure. Rows that break the write-in total down are not terms (they are the terms of report_writein)."""
    out = []
    for block, rows in _blocks(cells).items():
        sh = contest_shape(rows)
        if sh["total"] is None:
            continue
        tp, tl, tcols = sh["total"]
        terms_rows = [r for r in rows if r in sh["candidates"] or r is sh["write_in"]]
        for col in REPORT_COLS:
            if col not in tcols:
                continue
            terms = [r[2][col] for r in terms_rows if col in r[2]]
            out.append(_make("report_contest", tp, block, col, terms, tcols[col]["value"], (tp, block, tl, col)))
    return out


def report_writein_checks(cells: list[dict]) -> list[Check]:
    """Where a contest prints a write-in total and rows that break it down: per column, the breakdown adds to the total."""
    out = []
    for block, rows in _blocks(cells).items():
        sh = contest_shape(rows)
        if not sh["write_in"] or not sh["breakdown"]:
            continue
        wp, wl, wcols = sh["write_in"]
        for col in REPORT_COLS:
            if col in wcols:
                out.append(_make("report_writein", wp, block, col, [r[2][col] for r in sh["breakdown"] if col in r[2]],
                                 wcols[col]["value"], (wp, block, wl, col)))
    return out


def report_ballot_sums(cells: list[dict]) -> tuple[list[Check], list[dict]]:
    """(sums used, sums not used). Where a precinct's Statistics block prints its ballots cast and a contest prints a total,
    overvotes and undervotes, per column: total + overvotes + undervotes = ballots cast. If the equation fails in every column
    printed and always on the same side, the contest was not on every ballot of the precinct: it is not a sum for that block, and
    the block is listed in the second list with the reason."""
    stats: dict = {}
    for (page, block, label), cols in _rows_of(cells).items():
        if block.endswith("|st"):
            stats.setdefault(block.split("|")[0], (page, block, label, cols))
    used, unused = [], []
    for block, rows in _blocks(cells).items():
        sh = contest_shape(rows)
        st = stats.get(block.split("|")[0])
        if st is None or block.endswith(("|st", "|sb")) or not (sh["total"] and sh["over"] and sh["under"]):
            continue
        tp = sh["total"][0]
        mine = []
        for col in REPORT_COLS:
            if all(col in r[2] for r in (sh["total"], sh["over"], sh["under"])) and col in st[3]:
                mine.append(_make("report_ballots", tp, block, col, [sh[k][2][col] for k in ("total", "over", "under")],
                                  st[3][col]["value"], (st[0], st[1], st[2], col)))
        if not mine:
            continue
        signs = {(c.computed > c.printed) - (c.computed < c.printed) for c in mine if c.computed is not None}
        if all(not c.ok and c.computed is not None for c in mine) and len(signs) == 1:
            unused.append({"block": block, "page": tp, "why": (
                f"the contest total, overvotes and undervotes do not add to the precinct's ballots cast in any column "
                f"({', '.join(f'{c.key} {c.computed} against {c.printed}' for c in mine)}), always on the same side: the "
                f"contest was not on every ballot of the precinct, so the equation is not a sum for this block")})
        else:
            used += mine
    return used, unused


def report_checks(cells: list[dict]) -> list[Check]:
    return (report_row_checks(cells) + report_contest_checks(cells) + report_writein_checks(cells) +
            report_ballot_sums(cells)[0])


def report_crossing(cells: list[dict]) -> dict:
    """For each cell key, the report checks it sits on (as a term or as the printed total); empty when none."""
    on: dict = {cell_key(c): [] for c in cells}
    for ch in report_checks(cells):
        for k in [k for k, _ in ch.terms] + ([ch.printed_key] if ch.printed_key else []):
            if k in on:
                on[k].append(ch)
    return on
