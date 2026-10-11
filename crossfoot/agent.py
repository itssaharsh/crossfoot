"""The investigation loop: a model chooses what to look at again for each failing sum; code holds it to the rules.

For each failing sum (an item) `claude-haiku` is shown the item as text and answers with one JSON action:
`reread` (one or more targets, each with a dpi and a model), `cannot_verify` (a reason) or `done`. Code carries the
action out, checks the rules, writes an event and answers with the checks' new result. A model never sets a status:
a cell is accepted when every printed sum it sits on holds, and only then.

Rules that code enforces whatever the model says:
- at most MAX_ACTIONS actions per item (a refused request counts as one);
- the stronger model only after two re-reads of that item with the weak model have failed;
- a cell that is already accepted is never re-read; a total is re-read only while a sum it sits on fails;
- a re-read value replaces the old one only if more of that value's sums hold with it; both readings are kept in the event;
- cells still on failing sums when an item stops become cannot_verify, with the reason.
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path

from . import checks, tracing
from .layouts.matrix import ROWS, GeometryError, digit_px, scale_for  # noqa: F401  (re-exported for callers)
from .model import BudgetExceeded

WEAK = "claude-haiku"
STRONG = "claude-sonnet-4.6"
MAX_ACTIONS = 6
STRONG_AFTER = 2          # failed re-reads with the weak model before the strong one may be asked for
DPIS = (300, 400)
KINDS = ("cell", "column", "row_total", "col_total", "grand")
ORDER = {"row": 0, "col": 1, "grand": 2}


class StrongModelRefused(Exception):
    pass


@dataclass
class Item:
    kind: str                 # 'row' | 'col' | 'grand': the kind of failing sum
    page: int
    block: str
    key: str
    actions: int = 0
    weak_failures: int = 0
    history: list = field(default_factory=list)

    @property
    def id(self) -> str:
        return f"{self.kind}:{self.page}:{self.block}:{self.key}"


def check_model(item: Item, model: str):
    """The model rule. Raises StrongModelRefused (the reason is the message) or ValueError for an unknown model."""
    if model == WEAK:
        return
    if model != STRONG:
        raise ValueError(f"unknown model {model!r}; use {WEAK} or {STRONG}")
    if item.weak_failures < STRONG_AFTER:
        raise StrongModelRefused(f"{STRONG} is allowed only after two re-reads with {WEAK} have failed on this item; "
                                 f"{item.weak_failures} have so far")


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
    cannot_verify is final. Returns the changes [{cell, old, new}]."""
    cells, totals = led.cells(county), led.totals(county)
    on = checks.crossing(cells, totals)
    out = []
    for c in cells:
        if c["status"] == "cannot_verify":
            continue
        cs = on.get(_ckey(c), [])
        new = "accepted" if cs and all(x.ok for x in cs) else ("failed" if c["status"] == "failed" else "first_read")
        if new != c["status"]:
            led.set_status(county, c["page"], c["block_id"], c["row_kind"], c["column"], new)
            out.append({"cell": list(_ckey(c)), "old": c["status"], "new": new})
    return out


def count_failing(chs) -> dict:
    out = {"row": 0, "col": 0, "grand": 0}
    for ch in chs:
        out[ch.kind] += not ch.ok
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
        (direction == "col" and ((ch.kind == "col" and ch.key == key) or ch.kind == "grand")) or
        (direction == "grand" and ch.kind == "grand")))


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
shows a crop of it to a model and returns what it reads.

ITEM: {title}
{sums}
{hint}
Tried so far on this block:
{history}

Actions used on this item: {used} of {limit}. A re-read that does not make the sums hold counts as an action. The
stronger model {strong} is allowed only after two re-reads with {weak} have failed on this item ({fails} so far).

ACTIONS. Answer with one JSON object and nothing else:
{{"action": "reread", "rereads": [{{"target": TARGET, "dpi": 300 or 400, "model": "{weak}"}}, ...]}}
{{"action": "cannot_verify", "reason": "<why this cannot be settled from the scan>"}}
{{"action": "done"}}
TARGET is one of:
{{"kind": "cell", "row": "EARLY" | "ABSENTEE" | "PRECINCT", "column": "<precinct>"}}
{{"kind": "column", "column": "<precinct>"}}   the three cells of one precinct and the small total under them
{{"kind": "row_total", "row": "EARLY" | "ABSENTEE" | "PRECINCT" | "REGISTERED"}}   the row's printed total
{{"kind": "col_total", "column": "<precinct>"}}   the small total under one precinct
{{"kind": "grand"}}   the block's grand total
Several re-reads in one answer must be for this block. A printed total can be the misread value, not only a cell."""


def _fmt_terms(ch) -> str:
    return ", ".join(f"{k[2] if ch.kind == 'col' else k[3]}={v}" for k, v in ch.terms)


def _fmt_check(ch) -> str:
    what = {"row": f"row sum {ch.key}", "col": f"column sum, precinct {ch.key}", "grand": "grand total"}[ch.kind]
    comp = "unread term" if ch.computed is None else ch.computed
    diff = "" if ch.computed is None else f", off by {ch.computed - ch.printed:+d}"
    return f"{what}: {'HOLDS' if ch.ok else 'FAILS'}; terms {_fmt_terms(ch)}; they add to {comp}; printed {ch.printed}{diff}"


def _crossing_checks(item: Item, chs) -> list:
    """The checks that cross the item's sum at its cells (other row/column sums through its terms)."""
    me = next((c for c in chs if _ck(c) == (item.kind, item.page, item.block, item.key)), None)
    if me is None or me.kind == "grand":
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
    if me.kind == "grand":
        return "Note: the small totals do not add to the grand total; either a small total or the grand total is misread."
    return ""


def build_prompt(item: Item, led, county) -> str:
    cells, totals, chs = _state(led, county)
    me = next((c for c in chs if _ck(c) == (item.kind, item.page, item.block, item.key)), None)
    others = _crossing_checks(item, chs)
    who = next((c for c in cells if c["block_id"] == item.block and c["page"] == item.page), None)
    title = (f"page {item.page}, block {item.block}"
             f"{', ' + str(who['contest']) if who and who.get('contest') else ''}"
             f"{', ' + str(who['candidate']) if who and who.get('candidate') else ''}; failing sum: "
             f"{ {'row': 'row ' + item.key, 'col': 'column of precinct ' + item.key, 'grand': 'grand total'}[item.kind] }")
    sums = "\n".join(["Failing sum:", "  " + (_fmt_check(me) if me else "(no longer present)"),
                      "Sums that cross it:"] + [f"  {_fmt_check(c)}" for c in others]) if others or me else ""
    hist = "\n".join("  - " + h for h in item.history) or "  (nothing yet)"
    hint = hint_for(item, me, others)
    mine = {k for k, _ in me.terms} if me and me.kind != "grand" else set()
    cross = [k for k in checks.locate([c for c in chs if c.kind == "row"], [c for c in chs if c.kind == "col"])
             if k in mine]
    if cross:
        hint = (hint + "\n" if hint else "") + ("Cells where a failing row sum and a failing column sum cross (a misread "
                                                 "cell shows up at such a crossing): " +
                                                 ", ".join(f"{k[2]}/{k[3]}" for k in cross[:12]))
    return DECISION_PROMPT.format(title=title, sums=sums, hint=hint, history=hist,
                                  used=item.actions, limit=MAX_ACTIONS, strong=STRONG, weak=WEAK,
                                  fails=item.weak_failures)


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
    "grand": """This image is a crop of the grand total printed at the bottom right of a block of a ruled election
canvass sheet, under the TOTAL column. It holds one whole number. Read the digits exactly as printed.
Answer with strict JSON only: {{"value": <integer>}}""",
}


def _int(v, what):
    if isinstance(v, int) and not isinstance(v, bool):
        return v
    raise ValueError(f"{what} must be an integer, got {v!r}")


def read_validator(kind):
    def check(d):
        if not isinstance(d, dict):
            raise ValueError("answer must be an object")
        if kind == "column":
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
                "grand": ()}[t["kind"]]
        for f in need:
            if not isinstance(t.get(f), str) or not t[f]:
                raise ValueError(f'target {t["kind"]} needs "{f}"')
        dpi = r.get("dpi", 300)
        if dpi not in DPIS:
            raise ValueError(f"dpi must be one of {DPIS}")
        model = r.get("model", WEAK)
        if model not in (WEAK, STRONG):
            raise ValueError(f"model must be {WEAK} or {STRONG}")
        norm.append({"target": {k: t[k] for k in ("kind", *need)}, "dpi": dpi, "model": model})
    d["rereads"] = norm


# ---- the loop ------------------------------------------------------------------------------------------------------

class Closer:
    def __init__(self, county, gw, led, geo, *, run_id="", crop_dir=None, log=print):
        self.county, self.gw, self.led, self.geo, self.run_id, self.log = county, gw, led, geo, run_id, log
        self.crop_dir = Path(crop_dir) if crop_dir else Path("runs") / run_id / "crops" if run_id else Path("/tmp/crossfoot-crops")
        self.reread_cells: set = set()
        self.seen: dict = {}
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

    # -- one re-read
    def _refusal(self, item, t, model):
        """Return the reason a re-read of this target with this model is not allowed, else None."""
        try:
            check_model(item, model)
        except (StrongModelRefused, ValueError) as e:
            return str(e)
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
        elif kind == "row_total":
            if ("row", page, bid, t["row"]) not in failing:
                return "that row's sum holds; its printed total is not in question"
        elif kind == "col_total":
            if ("col", page, bid, t["column"]) not in failing and ("grand", page, bid, "") not in failing:
                return "that column's sum and the grand total hold; the small total is not in question"
        elif kind == "grand":
            if ("grand", page, bid, "") not in failing:
                return "the grand total's sum holds"
        return None

    def _updates(self, item, t, ans, model):
        page, bid = item.page, item.block
        cells = {_ckey(c): c for c in self.led.cells(self.county)}
        out = []
        if t["kind"] in ("cell", "column"):
            pairs = [(t["row"], ans["value"])] if t["kind"] == "cell" else [(r, ans[r]) for r in ROWS]
            col = t["column"]
            for r, v in pairs:
                c = cells.get((page, bid, r, col))
                if c is None or c["status"] == "accepted":
                    continue
                out.append({"entity": ("cell", page, bid, r, col), "old": c["value"], "new": v, "model": model,
                            "label": f"{r}/{col}"})
        if t["kind"] == "column" or t["kind"] == "col_total":
            old = next((x["value"] for x in self.led.totals(self.county)
                        if (x["page"], x["block_id"], x["direction"], x["key"]) == (page, bid, "col", t["column"])), None)
            out.append({"entity": ("total", page, bid, "col", t["column"]), "old": old,
                        "new": ans["total"] if t["kind"] == "column" else ans["value"], "model": model,
                        "label": f"small total/{t['column']}"})
        if t["kind"] == "row_total":
            old = next((x["value"] for x in self.led.totals(self.county)
                        if (x["page"], x["block_id"], x["direction"], x["key"]) == (page, bid, "row", t["row"])), None)
            out.append({"entity": ("total", page, bid, "row", t["row"]), "old": old, "new": ans["value"],
                        "model": model, "label": f"row total/{t['row']}"})
        if t["kind"] == "grand":
            old = next((x["value"] for x in self.led.totals(self.county)
                        if (x["page"], x["block_id"], x["direction"], x["key"]) == (page, bid, "grand", "")), None)
            out.append({"entity": ("total", page, bid, "grand", ""), "old": old, "new": ans["value"], "model": model,
                        "label": "grand total"})
        return out

    def reread(self, item: Item, r: dict):
        t, dpi, model = r["target"], r["dpi"], r["model"]
        item.actions += 1
        why = self._refusal(item, t, model)
        if why:
            self.ev("refused", item=item.id, target=t, dpi=dpi, model=model, reason=why)
            item.history.append(f"asked for {_tdesc(t)} with {model}: refused ({why})")
            self.log(f"    refused: {why}")
            return
        self.n_crops += 1
        dest = self.crop_dir / f"reread-{self.n_crops:04d}-{item.block}.png"
        name = {"cell": "reread_cell", "column": "reread_column"}.get(t["kind"], "reread_total")
        cell_tag = f"{t.get('row', '')}/{t.get('column', '')}".strip("/") or None
        with tracing.trace(name, kind="TOOL", run=self.run_id, county=self.county, page=item.page, block=item.block,
                           cell=cell_tag, target=t["kind"], dpi=dpi, model=model) as sp:
            try:
                path, box = self.geo.crop(item.page, item.block, t, dpi, dest)
            except GeometryError as e:
                self.ev("refused", item=item.id, target=t, dpi=dpi, model=model, reason=f"no crop: {e}")
                item.history.append(f"asked for {_tdesc(t)}: no crop could be cut ({e})")
                return
            sp.set_attribute("crop_path", str(path))
            prompt = READ_PROMPTS[t["kind"]].format(**{"row": t.get("row"), "column": t.get("column")})
            ans = self.gw.ask_json(prompt, path, validate=read_validator(t["kind"]), model=model)
        ups = self._updates(item, t, ans, model)
        settle(self.led, self.county, ups, self.seen)
        for u in ups:
            self.seen.setdefault(u["entity"], []).append(u["new"])
        for u in ups:
            if u["entity"][0] == "cell":
                self.reread_cells.add(tuple(u["entity"][1:]))
        self.sync_status()
        with tracing.trace("check_sums", kind="TOOL", run=self.run_id, county=self.county, page=item.page,
                           block=item.block):
            me = self.item_check(item)
        ok = bool(me and me.ok)
        if model == WEAK and not ok:
            item.weak_failures += 1
        changes = [{"what": u["label"], "entity": list(u["entity"]), "old": u["old"], "new": u["new"],
                    "kept": u["kept"], "sums_hold_old": u.get("sums_hold_old"), "sums_hold_new": u.get("sums_hold_new")}
                   for u in ups]
        self.ev("reread", item=item.id, page=item.page, block=item.block, target=t, model=model, dpi=dpi, box=list(box),
                crop=str(path), changes=changes)
        self.ev("check", item=item.id, page=item.page, block=item.block, sum_kind=item.kind, key=item.key, ok=ok,
                computed=me.computed if me else None, printed=me.printed if me else None,
                failing_in_block=sum(1 for c in self.checks_now() if c.block_id == item.block and not c.ok))
        item.history.append(f"re-read {_tdesc(t)} at {dpi} dpi with {model}: " +
                            ("; ".join(f"{c['what']} {c['old']} -> {c['new']} ({'kept new' if c['kept'] == 'new' else 'kept old'})"
                                       for c in changes if c["old"] != c["new"]) or "read the same values") +
                            f"; this sum now {'holds' if ok else 'still fails'}")
        self.log(f"    {_tdesc(t)} {dpi} dpi {model}: {'holds' if ok else 'still fails'}")

    # -- one item
    def stop(self, item, reason):
        me = self.item_check(item)
        marked = []
        if me and not me.ok and me.kind != "grand":
            by = {_ckey(c): c for c in self.led.cells(self.county)}
            for k, _ in me.terms:
                c = by.get(k)
                if c and c["status"] != "accepted":
                    self.led.set_status(self.county, *[c[f] for f in ("page", "block_id", "row_kind", "column")],
                                        "cannot_verify", reason)
                    marked.append(list(k))
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
                self.stop(item, f"six actions used on this item and its sum still fails")
                self.ev("item_end", item=item.id, result="cannot_verify")
                return
            prompt = build_prompt(item, self.led, self.county)
            try:
                d = self.gw.ask_json(prompt, validate=decision_validator, model=WEAK)
            except ValueError as e:
                self.ev("decision", item=item.id, model=WEAK, error=str(e)[:200])
                self.stop(item, f"the model gave no usable action ({str(e)[:120]})")
                self.ev("item_end", item=item.id, result="cannot_verify")
                return
            self.ev("decision", item=item.id, model=WEAK, answer=d)
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
    """Failing sums, grouped by block (page order), rows then columns then the grand total within a block.
    A sum is left out when it was worked before or a cell on it is already cannot_verify (`given_up`): the sum
    cannot be made to hold without that cell, and the cells left on it are closed at the end."""
    items = [Item(c.kind, c.page, c.block_id, c.key) for c in chs if not c.ok and
             f"{c.kind}:{c.page}:{c.block_id}:{c.key}" not in done_ids and
             not (c.kind != "grand" and any(k in given_up for k, _ in c.terms))]

    def block_no(b):
        return -1 if b in ("reg", "cast") else int(b.rsplit("-b", 1)[1])
    items.sort(key=lambda i: (i.page, block_no(i.block), ORDER[i.kind], i.key))
    return items


def close_county(county, gw, led, geo, *, run_id="", max_items=None, log=print, crop_dir=None) -> dict:
    """Work every failing sum of a county's ledger. Returns the summary figures (also written as events)."""
    t0 = time.time()
    c0, p0 = gw.calls, (gw.prompt_tokens, gw.completion_tokens, gw.cost)
    cl = Closer(county, gw, led, geo, run_id=run_id, crop_dir=crop_dir, log=log)
    before = count_failing(cl.checks_now())
    first = {_ckey(c): c["value"] for c in led.cells(county)}
    stopped = None
    done_ids = {json.loads(e["payload_json"])["item"] for e in led.events(county) if e["kind"] == "item_end"}
    cl.ev("close_start", failing_before=before)
    cl.sync_status()                       # cells whose sums already hold are accepted; a resumed run keeps its own
    worked = 0
    try:
        with tracing.trace("close_county", kind="AGENT", run=run_id, county=county):
            tried: set = set()
            while True:
                given_up = {_ckey(c) for c in led.cells(county) if c["status"] == "cannot_verify"}
                todo = [i for i in work_list(cl.checks_now(), done_ids, given_up) if i.id not in tried]
                if not todo:
                    _finish_open_cells(cl)
                    break
                if max_items is not None and worked >= max_items:
                    break
                item = todo[0]
                tried.add(item.id)
                worked += 1
                log(f"item {worked}: {item.id}")
                cl.work(item)
                done_ids.add(item.id)
    except BudgetExceeded as e:
        stopped = str(e)
        log(f"stopped: {e}")
        cl.ev("stop", item=None, reason=stopped, cells=[])
    after = count_failing(cl.checks_now())
    cells = led.cells(county)
    s = {"county": county, "run_id": run_id, "items_worked": worked,
         "sums_failing_before": before, "sums_failing_after": after,
         "cells_reread": len(cl.reread_cells),
         "cells_changed": sum(1 for c in cells if c["value"] != first.get(_ckey(c))),
         "cells_total": len(cells), "cells_accepted": sum(c["status"] == "accepted" for c in cells),
         "cells_cannot_verify": sum(c["status"] == "cannot_verify" for c in cells),
         "cells_open": sum(c["status"] not in ("accepted", "cannot_verify") for c in cells),
         "model_calls": gw.calls - c0, "prompt_tokens": gw.prompt_tokens - p0[0],
         "completion_tokens": gw.completion_tokens - p0[1], "metered_cost_estimate": round(gw.cost - p0[2], 4),
         "seconds": round(time.time() - t0, 1), "stopped": stopped}
    cl.ev("close_end", summary=s)
    return s


def _finish_open_cells(cl: Closer):
    """After every failing sum has been worked: a cell still not accepted is on no failing sum that can be worked
    (it sits on no printed sum, or its sums were already given up on). It becomes cannot_verify."""
    cells, totals = cl.led.cells(cl.county), cl.led.totals(cl.county)
    on = checks.crossing(cells, totals)
    for c in cells:
        if c["status"] in ("accepted", "cannot_verify"):
            continue
        cs = on.get(_ckey(c), [])
        reason = "no printed sum covers this cell" if not cs else "a sum it sits on still fails and was given up on"
        cl.led.set_status(cl.county, c["page"], c["block_id"], c["row_kind"], c["column"], "cannot_verify", reason)
        cl.ev("status_change", changes=[{"cell": list(_ckey(c)), "old": c["status"], "new": "cannot_verify",
                                         "reason": reason}])
