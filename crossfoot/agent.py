"""The investigation loop: pairing finds where to look, re-reads of the scan decide, code holds it to the rules.

Every printed value sits on two sums (see `checks.suspects`). A value that sits on two failing sums whose differences
agree is a suspect: it is re-read at 400 dpi or more with the county's reader, then one step up the ladder, and the
value changes only because a re-read gave the value both sums need. The same reading twice while both sums still
fail is `document_inconsistent`. A failing sum that pairing cannot place goes to `claude-sonnet-4.6`, which is shown
the sum in words and what has been tried, and answers with one JSON action: `reread` (one or more targets),
`cannot_verify` (a reason) or `done`. Code carries the action out and answers with the checks' new result. A model never
sets a status: a cell is accepted when every printed sum it sits on holds, and only then.

Rules that code enforces whatever the model says:
- at most MAX_ACTIONS actions per item (a refused request counts as one);
- the ladder: the county's reader first, then `claude-sonnet-4.6`, then `claude-opus-4.6`; a step is allowed on a target
  only after the step below has been tried on it (and failed to settle it); model names are matched after trimming and
  lower-casing, and an unknown name falls back to the next step of the ladder;
- the same target is never re-read twice with the same model and dpi (a refusal, and it counts as an action);
- a cell that is already accepted is never re-read; a total is re-read only while a sum it sits on fails;
- a re-read value replaces the old one only if more of that value's sums hold with it; both readings are kept in the event;
- when an item stops, only the cells that pairing or the model could not clear become cannot_verify (a cell whose other
  sum holds is not marked); every sum still failing at the end has a verdict and a reason.
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path

from . import checks, tracing
from .layouts.matrix import ROWS, GeometryError, digit_px, scale_for  # noqa: F401  (re-exported for callers)
from .model import BudgetExceeded

HAIKU = "claude-haiku"
SONNET = "claude-sonnet-4.6"
OPUS = "claude-opus-4.6"
DECIDER = SONNET          # the model that chooses what to look at for sums pairing cannot place
MAX_ACTIONS = 6
DPIS = (300, 400, 500, 600)
SUSPECT_DPI = 400
STRIP_CELLS = 7           # a row strip is cut into pieces of at most this many cells
KINDS = ("cell", "column", "row_total", "col_total", "grand", "row_strip")
SUM_KINDS = ("row", "col", "grand_col", "grand_row")
FINAL = ("cannot_verify", "document_inconsistent")
ORDER = {"row": 0, "col": 1, "grand_col": 2, "grand_row": 3}


def norm(name) -> str:
    return str(name or "").strip().lower()


def ladder_for(reader: str) -> list[str]:
    """The reader of the county first, then the stronger models above it, each once."""
    out = [norm(reader) or HAIKU]
    for m in (SONNET, OPUS):
        if m not in out:
            out.append(m)
    return out


def pick_model(name, ladder: list[str], tried: set) -> tuple[int | None, str | None]:
    """(step, None) for the ladder step to use, or (None, reason) when the request is refused. `tried` holds the steps
    already used on this target. A name that is not on the ladder falls back to the lowest step not yet tried."""
    names = [norm(m) for m in ladder]
    n = norm(name)
    if n in names:
        i = names.index(n)
    else:
        i = next((j for j in range(len(names)) if j not in tried), len(names) - 1)
    if i > 0 and (i - 1) not in tried:
        return None, (f"{ladder[i]} is allowed on a target only after {ladder[i - 1]} has been tried on it "
                      "and failed to settle the value")
    return i, None


@dataclass
class Item:
    kind: str                 # 'row' | 'col' | 'grand_col' | 'grand_row': the kind of failing sum
    page: int
    block: str
    key: str
    actions: int = 0
    history: list = field(default_factory=list)

    @property
    def id(self) -> str:
        return f"{self.kind}:{self.page}:{self.block}:{self.key}"


def sum_id(ch) -> str:
    return f"{ch.kind}:{ch.page}:{ch.block_id}:{ch.key}"


def entity_of(key: tuple) -> tuple:
    """A checks entity key as the settle()/ledger entity: a cell key or a printed total."""
    return ("total", *key) if key[2] in ("row", "col", "grand") else ("cell", *key)


def target_of(key: tuple) -> dict:
    """The re-read target that shows one value: a cell, a row's printed total, a small total or the grand total."""
    page, block, x, y = key
    if x == "row":
        return {"kind": "row_total", "row": y}
    if x == "col":
        return {"kind": "col_total", "column": y}
    if x == "grand":
        return {"kind": "grand"}
    return {"kind": "cell", "row": x, "column": y}


def tkey(t: dict) -> str:
    return json.dumps(t, sort_keys=True)


# ---- state from the ledger -------------------------------------------------------------------------------------

def _state(led, county):
    cells, totals = led.cells(county), led.totals(county)
    return cells, totals, checks.all_checks(cells, totals)


def _ck(ch) -> tuple:
    return (ch.kind, ch.page, ch.block_id, ch.key)


def _ckey(c) -> tuple:
    return checks.cell_key(c)


def derive_status(led, county) -> list[dict]:
    """Set every cell's status from the checks: accepted iff it sits on at least one printed sum and all hold.
    cannot_verify and document_inconsistent are final. Returns the changes [{cell, old, new}]."""
    cells, totals = led.cells(county), led.totals(county)
    on = checks.crossing(cells, totals)
    out = []
    for c in cells:
        if c["status"] in FINAL:
            continue
        cs = on.get(_ckey(c), [])
        new = "accepted" if cs and all(x.ok for x in cs) else ("failed" if c["status"] == "failed" else "first_read")
        if new != c["status"]:
            led.set_status(county, c["page"], c["block_id"], c["row_kind"], c["column"], new)
            out.append({"cell": list(_ckey(c)), "old": c["status"], "new": new})
    return out


def count_failing(chs) -> dict:
    """Failing sums by kind: grand = the small totals against the grand total (as in T03a), grand_row = the row totals."""
    out = {"row": 0, "col": 0, "grand": 0, "grand_row": 0}
    for ch in chs:
        out["grand" if ch.kind == "grand_col" else ch.kind] += not ch.ok
    return out


def _holding(entity, cells, totals) -> int:
    """How many printed sums that this cell or total sits on hold, given the lists as they are."""
    chs = checks.all_checks(cells, totals)
    if entity[0] == "cell":
        _, page, bid, row, col = entity
        return sum(ch.ok for ch in chs if ch.kind in ("row", "col") and ch.page == page and ch.block_id == bid and
                   any(k == (page, bid, row, col) for k, _ in ch.terms))
    _, page, bid, direction, key = entity
    return sum(ch.ok for ch in chs if ch.page == page and ch.block_id == bid and (
        (direction == "row" and ch.kind == "row" and ch.key == key) or
        (direction == "col" and ((ch.kind == "col" and ch.key == key) or ch.kind == "grand_col")) or
        (direction == "row" and ch.kind == "grand_row") or
        (direction == "grand" and ch.kind in ("grand_col", "grand_row"))))


def settle(led, county, updates: list[dict], seen: dict | None = None) -> list[dict]:
    """Decide for each proposed new value whether it replaces the old one: it does only if more of the sums it sits on
    hold with it than with the old value, the other proposed values being taken as they are. Writes the kept values.
    Each update: {entity: ('cell', page, block, row, col) | ('total', page, block, direction, key), old, new}.
    `seen` maps an entity to the values earlier re-reads gave it. Returns the updates with 'kept' ('new' | 'old' |
    'same') added."""
    cells, totals = led.cells(county), led.totals(county)

    def with_values(chosen):
        cs = [dict(c) for c in cells]
        ts = [dict(t) for t in totals]
        for u, v in chosen:
            e = u["entity"]
            if e[0] == "cell":
                for c in cs:
                    if _ckey(c) == tuple(e[1:]):
                        c["value"] = v
            else:
                for t in ts:
                    if (t["page"], t["block_id"], t["direction"], t["key"]) == tuple(e[1:]):
                        t["value"] = v
        return cs, ts

    live = [u for u in updates if u["new"] is not None and u["new"] != u["old"]]
    all_new = [(u, u["new"]) for u in live]
    for u in updates:
        if u not in live:
            u["kept"] = "same"
            continue
        reverted = [(x, x["old"] if x is u else x["new"]) for x in live]
        n_new = _holding(u["entity"], *with_values(all_new))
        n_old = _holding(u["entity"], *with_values(reverted))
        # a tie goes to the old value, unless an earlier re-read of the same thing already gave this new value
        agreed = seen is not None and u["new"] in seen.get(u["entity"], ())
        u["kept"] = "new" if n_new > n_old or (n_new == n_old and agreed) else "old"
        u["agreed"] = agreed
        u["sums_hold_new"], u["sums_hold_old"] = n_new, n_old
    for u in updates:
        e = u["entity"]
        if e[0] == "cell":
            keep = u["new"] if u.get("kept") == "new" else u["old"]
            led.reread_cell(county, e[1], e[2], e[3], e[4], keep, u["model"] if u.get("kept") == "new" else None)
        elif u.get("kept") == "new":
            led.put_total(county, e[1], e[2], e[3], e[4], u["new"])
    return updates


# ---- prompts -----------------------------------------------------------------------------------------------------

DECISION_PROMPT = """You are checking a scanned election canvass sheet that has been read into a ledger. Each ruled
block holds one candidate: columns are precincts; rows are EARLY, ABSENTEE, PRECINCT; under the columns a small printed
total (the "small total"), and at the far right a TOTAL column (the "row total" for each row) and a grand total. In a
correct reading every row adds up to its row total, every column adds up to its small total, and the small totals add up
to the grand total. One sum does not hold. Decide what to look at again. The scan itself is not shown to you; a re-read
shows a crop of it to a model and returns what it reads. Pairing of failing sums (a value that sits on two failing
sums with the same difference) has already been tried and could not place the value that is wrong.

ITEM: {title}
{sums}
{hint}
Tried so far on this block:
{history}

Actions used on this item: {used} of {limit}. A re-read that does not make the sums hold counts as an action, and so
does a refused one. Models, weakest first: {ladder}. A stronger one is allowed on a target only after the one below it
has been tried on that same target; the same target is never re-read twice with the same model and dpi.

ACTIONS. Answer with one JSON object and nothing else:
{{"action": "reread", "rereads": [{{"target": TARGET, "dpi": 400 or 500, "model": "{first}"}}, ...]}}
{{"action": "cannot_verify", "reason": "<why this cannot be settled from the scan>"}}
{{"action": "done"}}
TARGET is one of:
{{"kind": "cell", "row": "EARLY" | "ABSENTEE" | "PRECINCT", "column": "<precinct>"}}
{{"kind": "column", "column": "<precinct>"}}   the three cells of one precinct and the small total under them
{{"kind": "row_strip", "row": "EARLY" | "ABSENTEE" | "PRECINCT" | "REGISTERED"}}   every cell of one row, read in pieces of at most seven cells
{{"kind": "row_total", "row": "EARLY" | "ABSENTEE" | "PRECINCT" | "REGISTERED"}}   the row's printed total
{{"kind": "col_total", "column": "<precinct>"}}   the small total under one precinct
{{"kind": "grand"}}   the block's grand total
Several re-reads in one answer must be for this block. A printed total can be the misread value, not only a cell."""


def _fmt_terms(ch) -> str:
    return ", ".join(f"{k[2] if ch.kind == 'col' else k[3]}={v}" for k, v in ch.terms)


def _fmt_check(ch) -> str:
    what = {"row": f"row sum {ch.key}", "col": f"column sum, precinct {ch.key}",
            "grand_col": "grand total against the small totals", "grand_row": "grand total against the row totals"}[ch.kind]
    comp = "unread term" if ch.computed is None else ch.computed
    diff = "" if ch.computed is None else f", off by {ch.computed - ch.printed:+d}"
    return f"{what}: {'HOLDS' if ch.ok else 'FAILS'}; terms {_fmt_terms(ch)}; they add to {comp}; printed {ch.printed}{diff}"


def _crossing_checks(item: Item, chs) -> list:
    """The checks that cross the item's sum at its cells (other row/column sums through its terms)."""
    me = next((c for c in chs if _ck(c) == (item.kind, item.page, item.block, item.key)), None)
    if me is None or me.kind.startswith("grand"):
        return []
    want = "col" if me.kind == "row" else "row"
    keys = {k for k, _ in me.terms}
    return [c for c in chs if c.kind == want and c.page == item.page and c.block_id == item.block and
            any(k in keys for k, _ in c.terms)]


def hint_for(item: Item, me, others) -> str:
    if me is None:
        return ""
    if me.kind == "col" and others and all(c.ok for c in others):
        return ("Note: this column sum fails while the three row sums it crosses all hold, so look at the small total "
                "first (the printed value may be the misread one).")
    if me.kind == "row" and others and all(c.ok for c in others):
        return ("Note: this row sum fails while every column sum on it holds, so look at the row's printed total first "
                "(the printed value may be the misread one).")
    if me.kind.startswith("grand"):
        return "Note: the small totals do not add to the grand total; either a small total or the grand total is misread."
    return ""


def build_prompt(item: Item, led, county, ladder=(HAIKU, SONNET, OPUS)) -> str:
    cells, totals, chs = _state(led, county)
    me = next((c for c in chs if _ck(c) == (item.kind, item.page, item.block, item.key)), None)
    others = _crossing_checks(item, chs)
    who = next((c for c in cells if c["block_id"] == item.block and c["page"] == item.page), None)
    title = (f"page {item.page}, block {item.block}"
             f"{', ' + str(who['contest']) if who and who.get('contest') else ''}"
             f"{', ' + str(who['candidate']) if who and who.get('candidate') else ''}; failing sum: "
             f"{ {'row': 'row ' + item.key, 'col': 'column of precinct ' + item.key, 'grand_col': 'grand total (small totals)', 'grand_row': 'grand total (row totals)'}[item.kind] }")
    sums = "\n".join(["Failing sum:", "  " + (_fmt_check(me) if me else "(no longer present)"),
                      "Sums that cross it:"] + [f"  {_fmt_check(c)}" for c in others]) if others or me else ""
    hist = "\n".join("  - " + h for h in item.history) or "  (nothing yet)"
    hint = hint_for(item, me, others)
    mine = {k for k, _ in me.terms} if me and not me.kind.startswith("grand") else set()
    cross = [k for k in checks.locate([c for c in chs if c.kind == "row"], [c for c in chs if c.kind == "col"])
             if k in mine]
    if cross:
        hint = (hint + "\n" if hint else "") + ("Cells where a failing row sum and a failing column sum cross (a misread "
                                                 "cell shows up at such a crossing): " +
                                                 ", ".join(f"{k[2]}/{k[3]}" for k in cross[:12]))
    ladder = list(ladder)
    return DECISION_PROMPT.format(title=title, sums=sums, hint=hint, history=hist,
                                  used=item.actions, limit=MAX_ACTIONS, ladder=", ".join(ladder),
                                  first=ladder[0])


READ_PROMPTS = {
    "cell": """This image is a crop of one cell from a ruled election canvass sheet: the cell of precinct {column},
row {row}. It holds one printed whole number. Read the digits exactly as printed; do not correct or add anything up.
Answer with strict JSON only: {{"value": <integer>}}""",
    "column": """This image is a crop of one precinct column from a ruled election canvass sheet: precinct {column}.
Top to bottom it holds the cells of rows EARLY, ABSENTEE and PRECINCT, then under them a small printed total in smaller
digits. Parts of the neighbouring columns may show at the edges; ignore them. Read the digits exactly as printed; do
not correct or add anything up.
Answer with strict JSON only: {{"EARLY": <integer>, "ABSENTEE": <integer>, "PRECINCT": <integer>, "total": <integer>}}""",
    "row_total": """This image is a crop of the printed total at the right end of row {row} of a ruled election canvass
sheet (the TOTAL column). It holds one whole number. Read the digits exactly as printed.
Answer with strict JSON only: {{"value": <integer>}}""",
    "col_total": """This image is a crop of the small printed total under precinct {column} of a ruled election canvass
sheet. It holds one whole number in small digits (a neighbouring column's total may show at the edges; read the
middle one). Read the digits exactly as printed.
Answer with strict JSON only: {{"value": <integer>}}""",
    "row_strip": """This image is a crop of part of row {row} of a ruled election canvass sheet. It holds {n} cells, one
per precinct, left to right, for precincts {columns}. Each holds one printed whole number; a solid black cell is
blacked out: use null for it. Read the digits exactly as printed; do not correct or add anything up.
Answer with strict JSON only: {{"values": [{n} integers or null, in that order]}}""",
    "grand": """This image is a crop of the grand total printed at the bottom right of a block of a ruled election
canvass sheet, under the TOTAL column. It holds one whole number. Read the digits exactly as printed.
Answer with strict JSON only: {{"value": <integer>}}""",
}


def _int(v, what):
    if isinstance(v, int) and not isinstance(v, bool):
        return v
    raise ValueError(f"{what} must be an integer, got {v!r}")


def read_validator(kind, n=None):
    def check(d):
        if not isinstance(d, dict):
            raise ValueError("answer must be an object")
        if kind == "row_strip":
            v = d.get("values")
            if not isinstance(v, list) or len(v) != n:
                raise ValueError(f"values must be a list of {n} entries")
            for x in v:
                if x is not None:
                    _int(x, "value")
        elif kind == "column":
            for k in (*ROWS, "total"):
                _int(d.get(k), k)
        else:
            _int(d.get("value"), "value")
    return check


def decision_validator(d):
    if not isinstance(d, dict) or d.get("action") not in ("reread", "cannot_verify", "done"):
        raise ValueError('"action" must be "reread", "cannot_verify" or "done"')
    if d["action"] == "cannot_verify" and not str(d.get("reason") or "").strip():
        raise ValueError('"cannot_verify" needs a "reason"')
    if d["action"] != "reread":
        return
    rr = d.get("rereads")
    if rr is None and "target" in d:
        rr = [{k: d[k] for k in ("target", "dpi", "model") if k in d}]
    if not isinstance(rr, list) or not rr:
        raise ValueError('"reread" needs a non-empty "rereads" list')
    norm = []
    for r in rr:
        t = r.get("target") if isinstance(r, dict) else None
        if not isinstance(t, dict) or t.get("kind") not in KINDS:
            raise ValueError(f"target kind must be one of {KINDS}")
        need = {"cell": ("row", "column"), "column": ("column",), "row_total": ("row",), "col_total": ("column",),
                "grand": (), "row_strip": ("row",)}[t["kind"]]
        for f in need:
            if not isinstance(t.get(f), str) or not t[f]:
                raise ValueError(f'target {t["kind"]} needs "{f}"')
        dpi = r.get("dpi", 300)
        if dpi not in DPIS:
            raise ValueError(f"dpi must be one of {DPIS}")
        model = r.get("model") or ""
        if not isinstance(model, str):
            raise ValueError("model must be a name")
        norm.append({"target": {k: t[k] for k in ("kind", *need)}, "dpi": dpi, "model": model})  # unknown names: pick_model
    d["rereads"] = norm


# ---- the loop ------------------------------------------------------------------------------------------------------

def _block_no(b):
    return -1 if b in ("reg", "cast") else int(b.rsplit("-b", 1)[1])


def describe(ch) -> str:
    """A failing sum in words, for a verdict's reason."""
    what = {"row": f"row sum {ch.key}", "col": f"column sum of precinct {ch.key}",
            "grand_col": "grand total against the small totals", "grand_row": "grand total against the row totals"}[ch.kind]
    return f"{what} (page {ch.page}, block {ch.block_id}: the cells add to {ch.computed}, printed {ch.printed})"


class Closer:
    def __init__(self, county, gw, led, geo, *, run_id="", crop_dir=None, log=print, reader=None, pair=True):
        self.county, self.gw, self.led, self.geo, self.run_id, self.log = county, gw, led, geo, run_id, log
        self.crop_dir = Path(crop_dir) if crop_dir else Path("runs") / run_id / "crops" if run_id else Path("/tmp/crossfoot-crops")
        self.reader = norm(reader or getattr(gw, "model", None) or HAIKU)
        self.ladder = ladder_for(self.reader)
        self.pair = pair
        self.reread_entities: set = set()
        self.seen: dict = {}
        self.rungs: dict = {}            # (page, block, target) -> ladder steps tried on it
        self.done_reads: set = set()     # (page, block, target, model, dpi)
        self.handled: set = set()        # entities of suspects already worked
        self.n_crops = 0

    def ev(self, kind, **payload):
        self.led.event(self.county, kind, payload)

    def checks_now(self):
        return _state(self.led, self.county)[2]

    def item_check(self, item):
        return next((c for c in self.checks_now() if _ck(c) == (item.kind, item.page, item.block, item.key)), None)

    def sync_status(self):
        ch = derive_status(self.led, self.county)
        if ch:
            self.ev("status_change", changes=ch)
        return ch

    def given_up(self) -> set:
        """Value keys (cells and printed totals) that have a final status or sit in a verdict: sums through them cannot be
        made to hold, so they are not worked again."""
        out = {_ckey(c) for c in self.led.cells(self.county) if c["status"] in FINAL}
        for v in self.led.verdicts(self.county):
            if v["entity"]:
                out.add(tuple(json.loads(v["entity"])))
        return out

    # -- one re-read
    def _target_refusal(self, item, t):
        """The reason this target may not be re-read now, else None."""
        cells, totals, chs = _state(self.led, self.county)
        page, bid = item.page, item.block
        byk = {_ckey(c): c for c in cells}
        failing = {_ck(c) for c in chs if not c.ok}
        kind = t["kind"]
        if kind == "cell":
            c = byk.get((page, bid, t["row"], t["column"]))
            if c is None:
                return f"there is no cell {t['row']} / {t['column']} in {bid}"
            if c["status"] == "accepted":
                return "that cell is accepted: every sum it sits on holds"
        elif kind == "column":
            col = [c for c in cells if c["page"] == page and c["block_id"] == bid and c["column"] == t["column"]]
            if not col:
                return f"there is no column {t['column']} in {bid}"
            if all(c["status"] == "accepted" for c in col) and ("col", page, bid, t["column"]) not in failing:
                return "every cell of that column is accepted"
        elif kind == "row_strip":
            row = [c for c in cells if c["page"] == page and c["block_id"] == bid and c["row_kind"] == t["row"]]
            if not row:
                return f"there is no row {t['row']} in {bid}"
            if all(c["status"] == "accepted" for c in row):
                return "every cell of that row is accepted"
        elif kind == "row_total":
            if ("row", page, bid, t["row"]) not in failing and ("grand_row", page, bid, "") not in failing:
                return "that row's sum and the grand total by rows hold; its printed total is not in question"
        elif kind == "col_total":
            if ("col", page, bid, t["column"]) not in failing and ("grand_col", page, bid, "") not in failing:
                return "that column's sum and the grand total hold; the small total is not in question"
        elif kind == "grand":
            if ("grand_col", page, bid, "") not in failing and ("grand_row", page, bid, "") not in failing:
                return "the grand total's sums hold"
        return None

    def _total(self, page, bid, direction, key):
        return next((x["value"] for x in self.led.totals(self.county)
                     if (x["page"], x["block_id"], x["direction"], x["key"]) == (page, bid, direction, key)), None)

    def _updates(self, item, t, ans, model):
        page, bid = item.page, item.block
        cells = {_ckey(c): c for c in self.led.cells(self.county)}
        out = []
        if t["kind"] in ("cell", "column", "row_strip"):
            if t["kind"] == "cell":
                pairs = [(t["row"], t["column"], ans["value"])]
            elif t["kind"] == "column":
                pairs = [(r, t["column"], ans[r]) for r in ROWS]
            else:
                pairs = [(t["row"], col, v) for col, v in ans["strip"].items() if v is not None]
            for r, col, v in pairs:
                c = cells.get((page, bid, r, col))
                if c is None or c["status"] == "accepted":
                    continue
                out.append({"entity": ("cell", page, bid, r, col), "old": c["value"], "new": v, "model": model,
                            "label": f"{r}/{col}"})
        if t["kind"] == "column" or t["kind"] == "col_total":
            out.append({"entity": ("total", page, bid, "col", t["column"]),
                        "old": self._total(page, bid, "col", t["column"]),
                        "new": ans["total"] if t["kind"] == "column" else ans["value"], "model": model,
                        "label": f"small total/{t['column']}"})
        if t["kind"] == "row_total":
            out.append({"entity": ("total", page, bid, "row", t["row"]), "old": self._total(page, bid, "row", t["row"]),
                        "new": ans["value"], "model": model, "label": f"row total/{t['row']}"})
        if t["kind"] == "grand":
            out.append({"entity": ("total", page, bid, "grand", ""), "old": self._total(page, bid, "grand", ""),
                        "new": ans["value"], "model": model, "label": "grand total"})
        return out

    def _refuse(self, item, t, dpi, model, why):
        self.ev("refused", item=item.id, target=t, dpi=dpi, model=model, reason=why)
        item.history.append(f"asked for {_tdesc(t)} with {model}: refused ({why})")
        self.log(f"    refused: {why}")
        return {"refused": why, "readings": {}, "ok": False}

    def reread(self, item: Item, r: dict) -> dict:
        """One action: re-read a target. Returns {refused, readings: {entity: value read}, ok: the item's sum holds}."""
        t, dpi, asked = r["target"], r["dpi"], r["model"]
        item.actions += 1
        tk = (item.page, item.block, tkey(t))
        tried = self.rungs.setdefault(tk, set())
        step, why = pick_model(asked, self.ladder, tried)
        model = self.ladder[step] if step is not None else norm(asked)
        if why is None and (*tk, model, dpi) in self.done_reads:
            why = f"{_tdesc(t)} has already been re-read with {model} at {dpi} dpi"
        why = why or self._target_refusal(item, t)
        if why:
            return self._refuse(item, t, dpi, model, why)
        self.n_crops += 1
        dest = self.crop_dir / f"reread-{self.n_crops:04d}-{item.block}.png"
        name = {"cell": "reread_cell", "column": "reread_column", "row_strip": "reread_strip"}.get(t["kind"], "reread_total")
        cell_tag = f"{t.get('row', '')}/{t.get('column', '')}".strip("/") or None
        with tracing.trace(name, kind="TOOL", run=self.run_id, county=self.county, page=item.page, block=item.block,
                           cell=cell_tag, target=t["kind"], dpi=dpi, model=model) as sp:
            try:
                if t["kind"] == "row_strip":
                    pieces = self.geo.strip_crops(item.page, item.block, t["row"], dpi, dest, STRIP_CELLS)
                else:
                    path, box = self.geo.crop(item.page, item.block, t, dpi, dest)
                    pieces = None
            except GeometryError as e:
                return self._refuse(item, t, dpi, model, f"no crop: {e}")
            tried.add(step)
            self.done_reads.add((*tk, model, dpi))
            if pieces is None:
                sp.set_attribute("crop_path", str(path))
                prompt = READ_PROMPTS[t["kind"]].format(**{"row": t.get("row"), "column": t.get("column")})
                ans = self.gw.ask_json(prompt, path, validate=read_validator(t["kind"]), model=model)
                crops = str(path)
            else:
                strip = {}
                for pth, cols, bx in pieces:
                    prompt = READ_PROMPTS["row_strip"].format(row=t["row"], n=len(cols), columns=", ".join(cols))
                    a = self.gw.ask_json(prompt, pth, validate=read_validator("row_strip", len(cols)), model=model)
                    strip.update(zip(cols, a["values"]))
                ans, crops = {"strip": strip}, [str(p_) for p_, _, _ in pieces]
                box = (min(b_[0] for _, _, b_ in pieces), min(b_[1] for _, _, b_ in pieces),
                       max(b_[2] for _, _, b_ in pieces), max(b_[3] for _, _, b_ in pieces))
        ups = self._updates(item, t, ans, model)
        settle(self.led, self.county, ups, self.seen)
        for u in ups:
            self.seen.setdefault(u["entity"], []).append(u["new"])
            self.reread_entities.add(u["entity"])
        self.sync_status()
        with tracing.trace("check_sums", kind="TOOL", run=self.run_id, county=self.county, page=item.page,
                           block=item.block):
            me = self.item_check(item)
        ok = bool(me and me.ok)
        changes = [{"what": u["label"], "entity": list(u["entity"]), "old": u["old"], "new": u["new"],
                    "kept": u["kept"], "sums_hold_old": u.get("sums_hold_old"), "sums_hold_new": u.get("sums_hold_new")}
                   for u in ups]
        self.ev("reread", item=item.id, page=item.page, block=item.block, target=t, model=model, dpi=dpi, box=list(box),
                crop=crops, ladder_step=step, changes=changes)
        self.ev("check", item=item.id, page=item.page, block=item.block, sum_kind=item.kind, key=item.key, ok=ok,
                computed=me.computed if me else None, printed=me.printed if me else None,
                failing_in_block=sum(1 for c in self.checks_now() if c.block_id == item.block and not c.ok))
        item.history.append(f"re-read {_tdesc(t)} at {dpi} dpi with {model}: " +
                            ("; ".join(f"{c['what']} {c['old']} -> {c['new']} ({'kept new' if c['kept'] == 'new' else 'kept old'})"
                                       for c in changes if c["old"] != c["new"]) or "read the same values") +
                            f"; this sum now {'holds' if ok else 'still fails'}")
        self.log(f"    {_tdesc(t)} {dpi} dpi {model}: {'holds' if ok else 'still fails'}")
        return {"refused": None, "readings": {u["entity"]: u["new"] for u in ups}, "ok": ok}

    # -- verdicts
    def give_verdict(self, sums, verdict, reason, entity=None):
        """Every sum that stays failing gets a verdict and a reason. A cell that is the located value gets the status."""
        for ch in sums:
            self.led.set_verdict(self.county, sum_id(ch), ch.page, ch.block_id, verdict, reason, list(entity) if entity else None)
        if entity and entity[2] not in ("row", "col", "grand"):
            self.led.set_status(self.county, *entity, verdict, reason)
            self.ev("status_change", changes=[{"cell": list(entity), "old": "open", "new": verdict, "reason": reason}])
        self.ev("verdict", sums=[sum_id(c) for c in sums], verdict=verdict, reason=reason,
                entity=list(entity) if entity else None)

    # -- a located value
    def work_suspect(self, s: checks.Suspect):
        first = s.sums[0]
        item = Item(first.kind, first.page, first.block_id, first.key)
        ids = [sum_id(c) for c in s.sums]
        ent, t = entity_of(s.entity), target_of(s.entity)
        self.handled.add(s.entity)
        self.ev("item_start", item=item.id, page=item.page, block=item.block)
        self.ev("suspect", item=item.id, sums=ids, entity=list(s.entity), read=s.read, would_be=s.would_be)
        self.log(f"    suspect {s.entity}: read {s.read}, the sums need {s.would_be}")
        readings, result, last = [], None, None
        for step in range(len(self.ladder)):
            if item.actions >= MAX_ACTIONS:
                break
            last = self.reread(item, {"target": t, "dpi": SUSPECT_DPI, "model": self.ladder[step]})
            if last["refused"]:
                break
            now = {_ck(c): c for c in self.checks_now()}
            if all(now.get(_ck(c)) is None or now[_ck(c)].ok for c in s.sums):
                result = "holds"
                break
            rd = last["readings"].get(ent)
            readings.append((self.ladder[step], rd))
            vals = [v for _, v in readings]
            if rd is not None and rd in vals[:-1]:
                result = "document_inconsistent"
                break
        now = {_ck(c): c for c in self.checks_now()}
        sums_now = [now[_ck(c)] for c in s.sums if _ck(c) in now]
        if result == "holds":
            self.ev("item_end", item=item.id, result="holds")
            return
        seen = ", ".join(f"{m} read {v}" for m, v in readings)
        if result == "document_inconsistent":
            why = (f"the scan shows {readings[-1][1]} there on every re-read ({seen}) while both sums it sits on still "
                   f"fail: {describe(sums_now[0])}; and {describe(sums_now[1])}. The document disagrees with itself.")
            self.give_verdict(sums_now, "document_inconsistent", why, s.entity)
            self.ev("item_end", item=item.id, result="document_inconsistent")
        else:
            why = ((f"re-reads ({seen}) did not settle it" if readings else f"no re-read was possible ({last and last['refused']})")
                   + f": {describe(sums_now[0])}; and {describe(sums_now[1])}")
            self.give_verdict(sums_now, "cannot_verify", why, s.entity)
            self.ev("item_end", item=item.id, result="cannot_verify")

    # -- one item the model decides
    def stop(self, item, reason):
        chs = self.checks_now()
        me = next((c for c in chs if _ck(c) == (item.kind, item.page, item.block, item.key)), None)
        marked = []
        if me and not me.ok:
            if not me.kind.startswith("grand"):
                cells, totals = self.led.cells(self.county), self.led.totals(self.county)
                on = checks.crossing(cells, totals)
                by = {_ckey(c): c for c in cells}
                up = self.given_up()
                vids = {v["sum_id"] for v in self.led.verdicts(self.county)}
                for k, _ in me.terms:
                    c = by.get(k)
                    if c is None or c["status"] == "accepted" or c["status"] in FINAL:
                        continue
                    others = [x for x in on.get(k, []) if _ck(x) != _ck(me)]
                    live = [x for x in others if not x.ok and sum_id(x) not in vids and
                            not any(kk in up for kk, _ in x.terms)]
                    if live:
                        self.led.set_status(self.county, *k, "cannot_verify", reason)
                        marked.append(list(k))
            self.led.set_verdict(self.county, sum_id(me), me.page, me.block_id, "cannot_verify", reason)
            self.ev("verdict", sums=[sum_id(me)], verdict="cannot_verify", reason=reason, entity=None)
        if marked:
            self.ev("status_change", changes=[{"cell": k, "old": "open", "new": "cannot_verify", "reason": reason}
                                              for k in marked])
        self.ev("stop", item=item.id, page=item.page, block=item.block, reason=reason, cells=marked)
        self.log(f"    stop: {reason}")

    def work(self, item: Item):
        with tracing.trace("work_item", kind="TOOL", run=self.run_id, county=self.county, page=item.page,
                           block=item.block, item=item.id):
            self._work(item)

    def _work(self, item: Item):
        self.ev("item_start", item=item.id, page=item.page, block=item.block)
        while True:
            me = self.item_check(item)
            if me is None or me.ok:
                self.ev("item_end", item=item.id, result="holds")
                return
            if item.actions >= MAX_ACTIONS:
                self.stop(item, "six actions used on this item and its sum still fails")
                self.ev("item_end", item=item.id, result="cannot_verify")
                return
            prompt = build_prompt(item, self.led, self.county, self.ladder)
            try:
                d = self.gw.ask_json(prompt, validate=decision_validator, model=DECIDER)
            except ValueError as e:
                self.ev("decision", item=item.id, model=DECIDER, error=str(e)[:200])
                self.stop(item, f"the model gave no usable action ({str(e)[:120]})")
                self.ev("item_end", item=item.id, result="cannot_verify")
                return
            self.ev("decision", item=item.id, model=DECIDER, answer=d)
            if d["action"] == "cannot_verify":
                self.stop(item, str(d["reason"])[:300])
                self.ev("item_end", item=item.id, result="cannot_verify")
                return
            if d["action"] == "done":
                self.stop(item, "the model ended the item while its sum still fails")
                self.ev("item_end", item=item.id, result="cannot_verify")
                return
            for r in d["rereads"]:
                if item.actions >= MAX_ACTIONS:
                    break
                self.reread(item, r)
                me = self.item_check(item)
                if me is None or me.ok:
                    break


def _tdesc(t):
    return t["kind"] + "".join(f" {t[k]}" for k in ("row", "column") if k in t)


def work_list(chs, done_ids: set, given_up: set = frozenset()) -> list[Item]:
    """Failing sums, grouped by block (page order), rows then columns then the grand totals within a block.
    A sum is left out when it was worked before (or has a verdict: `done_ids`) or a value on it is already given up on
    (`given_up`): the sum cannot be made to hold without that value."""
    items = [Item(c.kind, c.page, c.block_id, c.key) for c in chs if not c.ok and sum_id(c) not in done_ids and
             not any(k in given_up for k, _ in c.terms) and (c.printed_key not in given_up)]
    items.sort(key=lambda i: (i.page, _block_no(i.block), ORDER[i.kind], i.key))
    return items


def next_suspects(closer: Closer, chs, done_ids, given_up) -> list:
    found = checks.suspects(chs).suspects
    out = [s for s in found if s.entity not in closer.handled and s.entity not in given_up and
           not any(sum_id(c) in done_ids for c in s.sums)]
    out.sort(key=lambda s: (s.sums[0].page, _block_no(s.sums[0].block_id), ORDER[s.sums[0].kind], s.entity))
    return out


def close_county(county, gw, led, geo, *, run_id="", max_items=None, log=print, crop_dir=None, reader=None,
                 pair=True) -> dict:
    """Work every failing sum of a county's ledger. Returns the summary figures (also written as events)."""
    t0 = time.time()
    c0, p0 = gw.calls, (gw.prompt_tokens, gw.completion_tokens, gw.cost)
    cl = Closer(county, gw, led, geo, run_id=run_id, crop_dir=crop_dir, log=log, reader=reader, pair=pair)
    before = count_failing(cl.checks_now())
    first = {_ckey(c): c["value"] for c in led.cells(county)}
    first_totals = {(t["page"], t["block_id"], t["direction"], t["key"]): t["value"] for t in led.totals(county)}
    stopped = None
    done_ids = {json.loads(e["payload_json"])["item"] for e in led.events(county) if e["kind"] == "item_end"}
    for e in led.events(county):
        if e["kind"] == "suspect":
            cl.handled.add(tuple(json.loads(e["payload_json"])["entity"]))
    cl.ev("close_start", failing_before=before, reader=cl.reader, ladder=cl.ladder)
    cl.sync_status()                       # cells whose sums already hold are accepted; a resumed run keeps its own
    worked = 0
    complete = False
    try:
        with tracing.trace("close_county", kind="AGENT", run=run_id, county=county):
            tried: set = set()
            while True:
                chs = cl.checks_now()
                up = cl.given_up()
                vids = {v["sum_id"] for v in led.verdicts(county)}
                if max_items is not None and worked >= max_items:
                    break
                sus = next_suspects(cl, chs, vids, up) if pair else []
                if sus:
                    s = sus[0]
                    worked += 1
                    log(f"item {worked}: suspect {sum_id(s.sums[0])} / {sum_id(s.sums[1])}")
                    with tracing.trace("work_suspect", kind="TOOL", run=run_id, county=county, page=s.sums[0].page,
                                       block=s.sums[0].block_id):
                        cl.work_suspect(s)
                    continue
                todo = [i for i in work_list(chs, done_ids | vids, up) if i.id not in tried]
                if not todo:
                    complete = True
                    break
                item = todo[0]
                tried.add(item.id)
                worked += 1
                log(f"item {worked}: {item.id}")
                cl.work(item)
                done_ids.add(item.id)
            if complete:
                _finish(cl)
    except BudgetExceeded as e:
        stopped = str(e)
        log(f"stopped: {e}")
        cl.ev("stop", item=None, reason=stopped, cells=[])
    after = count_failing(cl.checks_now())
    cells = led.cells(county)
    totals_changed = sum(1 for t in led.totals(county)
                         if t["value"] != first_totals.get((t["page"], t["block_id"], t["direction"], t["key"])))
    vs = led.verdicts(county)
    s = {"county": county, "run_id": run_id, "reader": cl.reader, "ladder": cl.ladder, "items_worked": worked,
         "sums_failing_before": before, "sums_failing_after": after,
         "cells_reread": len({e for e in cl.reread_entities if e[0] == "cell"}),
         "values_reread": len(cl.reread_entities),
         "cells_changed": sum(1 for c in cells if c["value"] != first.get(_ckey(c))),
         "totals_changed": totals_changed,
         "cells_total": len(cells), "cells_accepted": sum(c["status"] == "accepted" for c in cells),
         "cells_cannot_verify": sum(c["status"] == "cannot_verify" for c in cells),
         "cells_document_inconsistent": sum(c["status"] == "document_inconsistent" for c in cells),
         "cells_open": sum(c["status"] not in ("accepted", "cannot_verify", "document_inconsistent") for c in cells),
         "verdicts": {k: sum(1 for v in vs if v["verdict"] == k) for k in ("document_inconsistent", "cannot_verify")},
         "model_calls": gw.calls - c0, "prompt_tokens": gw.prompt_tokens - p0[0],
         "completion_tokens": gw.completion_tokens - p0[1], "metered_cost_estimate": round(gw.cost - p0[2], 4),
         "seconds": round(time.time() - t0, 1), "stopped": stopped}
    cl.ev("close_end", summary=s)
    return s


def _finish(cl: Closer):
    """After every failing sum has been worked: a cell on no printed sum becomes cannot_verify, and a sum that still
    fails without a verdict (it shares a value that was given up on) gets one. Cells on a failing sum that is explained
    by another value are left as they are, with the sum's verdict as the reason."""
    cells, totals = cl.led.cells(cl.county), cl.led.totals(cl.county)
    on = checks.crossing(cells, totals)
    for c in cells:
        if c["status"] == "accepted" or c["status"] in FINAL or on.get(_ckey(c)):
            continue
        reason = "no printed sum covers this cell"
        cl.led.set_status(cl.county, c["page"], c["block_id"], c["row_kind"], c["column"], "cannot_verify", reason)
        cl.ev("status_change", changes=[{"cell": list(_ckey(c)), "old": c["status"], "new": "cannot_verify",
                                         "reason": reason}])
    have = {v["sum_id"] for v in cl.led.verdicts(cl.county)}
    for ch in checks.all_checks(cells, totals):
        if not ch.ok and sum_id(ch) not in have:
            why = "a value on this sum was given up on, so the sum cannot be made to hold"
            cl.led.set_verdict(cl.county, sum_id(ch), ch.page, ch.block_id, "cannot_verify", why)
            cl.ev("verdict", sums=[sum_id(ch)], verdict="cannot_verify", reason=why, entity=None)
