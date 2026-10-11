"""The audit: compare a closed ledger with the published file, settle each disagreement with the scan's printed totals.

The published file is a second reading of the same scan. It tells the audit where to look, never what to write: a
value changes only because a re-read of the scan gave it, and a correction to the file is written only where a printed
total decides it.

Steps: (1) match the scan's contests and candidates to the file's, by normalised labels first, then once per county
by the model as two lists (checked in code: one-to-one, close county totals); what is left is listed. (2) Compare every
part of every row. (3) Look at each disagreeing value on the scan once more (400 dpi, claude-sonnet-4.6, up to three at
a time); if it gives the file's value and the sums hold with it, the ledger was wrong, it is corrected, and there is no
finding. (4) Classify what is left, group the findings that describe one slip, and decide each one's status from the
sums it sits on. (5) Write the corrected file, which differs from the published one only where a finding is
`settled_against_file`.

findings.json
  county, run_id, file         names; file = the published file's name
  policy                       {question_id, answer, answered_by, meaning}
  counts                       {findings, by_kind, by_status, groups, corrections}
  findings  [{id, group, county, office, district, party, candidate, precinct,
              part                  votes | absentee | early_voting | election_day
              file_value, scan_value   integers, or null (a row the file lacks, or the scan lacks)
              kind                  file_row_fails_own_total | wrong_number | wrong_column | wrong_precinct |
                                    missing_row | extra_row
              status                settled_against_file | document_inconsistent | cannot_verify
              reason                the status in words
              sums  [{name, kind, terms [{cell, value}], printed, printed_label, computed_with_scan, holds_with_scan,
                      computed_with_file, holds_with_file}]   the printed totals that decide it
              page, block, box      where the scan's cell is ([x0, y0, x1, y1] at 200 dpi), or null
              crop                  path of the group's picture, relative to the county folder
              reread                {model, dpi, value, crop} or null: the single-value re-read of the scan
              file_row, file_line   index among the file's data rows, and its line number in the file, or null
              corrected             true when the corrected file differs from the published one at this value
              confirmed_by_person   false until a person changes it}]
  groups    [{id, kind, office, district, candidate, precincts, page, block, findings [ids], statuses, crop}]
  corrections  [{finding, file_row, part, old, new}]
  unmatched    {scan: [...], file: [...], rejected: [...], model: {...}}    what could not be matched, and why
  corrected_events [...]           ledger values the re-read changed (the file was right), each with its sums
  audit        {rereads, rereads_agreed_with_ledger, rereads_agreed_with_file, ledger_corrected, seconds}
"""
from __future__ import annotations

import csv
import difflib
import io
import json
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path

from . import agent, checks
from .model import BudgetExceeded, Gateway, price
from .sources import _int

PARTS = ("votes", "absentee", "early_voting", "election_day")
SCAN_ROW = {"absentee": "ABSENTEE", "early_voting": "EARLY", "election_day": "PRECINCT"}
KINDS = ("file_row_fails_own_total", "wrong_number", "wrong_column", "wrong_precinct", "missing_row", "extra_row")
STATUSES = ("settled_against_file", "document_inconsistent", "cannot_verify")
REREAD_MODEL = agent.SONNET
REREAD_DPI = 400
PARALLEL = 3
CLOSE_ENOUGH = 0.10        # mapped pairs: county totals within this share of each other
MIN_LINK_VOTES = 10        # a row moved to another precinct is recognised by its values; small ones coincide too easily,
                           # so below this many votes only a swap (each row sits where the other belongs) counts
CORRECTABLE = ("wrong_number", "wrong_column", "wrong_precinct", "file_row_fails_own_total")


# ---- labels ------------------------------------------------------------------------------------------------------

def nk(s) -> str:
    return re.sub(r"[^a-z0-9]", "", str(s or "").lower())


_PARTY = re.compile(r"\s*[\(\[]\s*(?:[A-Za-z]{2,4}|write[\s-]*in)\s*[\)\]]\s*$", re.I)
_WORDS = re.compile(r"\b(?:district|precinct no\.?|precinct)\b", re.I)


def candidate_key(label) -> str:
    """A candidate's label as the scan prints it ("A/B (PARTY)", "Name [REP]") or the file has it, normalised."""
    return nk(_PARTY.sub("", str(label or "")).split("/")[0])


def contest_keys(label) -> list[str]:
    a, b = nk(label), nk(_WORDS.sub("", str(label or "")))
    return [a] if a == b else [a, b]


# ---- the scan, as blocks -----------------------------------------------------------------------------------------

@dataclass
class Block:
    id: str
    page: int
    contest: str            # as printed, with "Write In" replaced by the contest above it
    candidate: str | None
    cells: dict = field(default_factory=dict)      # (row_kind, column) -> cell dict
    totals: dict = field(default_factory=dict)     # (direction, key) -> value
    cols: list = field(default_factory=list)

    def total(self) -> int | None:
        g = self.totals.get(("grand", ""))
        if g is not None:
            return g
        cs = [v for (d, _), v in self.totals.items() if d == "col"]
        return sum(cs) if cs else None


def scan_blocks(cells, totals) -> list[Block]:
    out, by, cur = [], {}, None
    for c in cells:
        k = (c["page"], c["block_id"])
        if k not in by:
            label = c["contest"] or ""
            if nk(label) == "writein":
                label = cur or label
            else:
                cur = label
            by[k] = Block(c["block_id"], c["page"], label, c["candidate"])
            out.append(by[k])
        b = by[k]
        if c["value"] is not None:
            b.cells[(c["row_kind"], c["column"])] = c
        if c["column"] not in b.cols:
            b.cols.append(c["column"])
    for t in totals:
        b = by.get((t["page"], t["block_id"]))
        if b is not None:
            b.totals[(t["direction"], t["key"])] = t["value"]
    return out


# ---- the file, as contests and candidates ------------------------------------------------------------------------

@dataclass
class FileCand:
    key: str
    label: str
    rows: dict = field(default_factory=dict)       # precinct -> (index, row)


@dataclass
class FileContest:
    key: str
    label: str
    district: str
    cands: dict = field(default_factory=dict)      # candidate key -> FileCand


def file_contests(rows: list[dict]) -> dict:
    out: dict = {}
    for i, r in enumerate(rows):
        k = nk((r.get("office") or "") + " " + (r.get("district") or ""))
        fc = out.setdefault(k, FileContest(k, r.get("office") or "", r.get("district") or ""))
        ck = candidate_key(r.get("candidate"))
        cand = fc.cands.setdefault(ck, FileCand(ck, r.get("candidate") or ""))
        cand.rows.setdefault(str(r.get("precinct")), (i, r))
    return out


def file_votes(cand: FileCand) -> int:
    return sum(_int(r.get("votes")) or 0 for _, r in cand.rows.values())


# ---- matching ----------------------------------------------------------------------------------------------------

MATCH_PROMPT = """Two lists of election contests and candidates describe the same election. One list is read from a
scanned canvass, the other from a published spreadsheet. Spelling and wording differ ("United States Senator" and
"U.S. Senate" are the same contest). Pair only the entries that are certainly the same; leave out any you are not sure of.
{lists}
Answer with strict JSON only: {{"contests": [[scan number, file number], ...], "candidates": [[scan number, file number], ...]}}.
Each number may appear at most once."""


def match_validator(ns):
    def check(d):
        if not isinstance(d, dict):
            raise ValueError("answer must be an object")
        for name, (a, b) in ns.items():
            pairs = d.get(name)
            if not isinstance(pairs, list):
                raise ValueError(f'"{name}" must be a list of pairs')
            for p in pairs:
                if not (isinstance(p, list) and len(p) == 2 and all(isinstance(x, int) and not isinstance(x, bool)
                                                                     for x in p)):
                    raise ValueError(f'"{name}" holds pairs of whole numbers')
    return check


def _close(a, b) -> bool:
    if a is None or b is None:
        return False
    return abs(a - b) <= CLOSE_ENOUGH * max(a, b, 1)


@dataclass
class Matching:
    block_map: dict = field(default_factory=dict)       # block id -> (file contest key, file candidate key)
    unmatched_scan: list = field(default_factory=list)
    unmatched_file: list = field(default_factory=list)
    rejected: list = field(default_factory=list)
    model: dict = field(default_factory=dict)


def match(blocks: list[Block], fcs: dict, gw=None, log=print) -> Matching:
    """Scan block -> file candidate. Normalised labels first; what is left goes to the model once, as two lists."""
    m = Matching()
    fkeys = set(fcs)
    cmap: dict = {}                                   # scan contest label -> file contest key
    for label in dict.fromkeys(b.contest for b in blocks):
        k = next((k for k in contest_keys(label) if k in fkeys), None)
        if k is not None and k not in cmap.values():
            cmap[label] = k

    def by_names(bs, label_map):
        used = set()
        for b in bs:
            fk = label_map.get(b.contest)
            ck = candidate_key(b.candidate)
            if fk is not None and ck in fcs[fk].cands and (fk, ck) not in used and b.id not in m.block_map:
                m.block_map[b.id] = (fk, ck)
                used.add((fk, ck))
        used.update(m.block_map.values())
        return used

    by_names(blocks, cmap)

    def leftovers():
        used = set(m.block_map.values())
        sc = [b for b in blocks if b.id not in m.block_map]
        fc = [(fk, ck) for fk, c in fcs.items() for ck in c.cands if (fk, ck) not in used]
        return sc, fc

    sc, fc = leftovers()
    s_con = [l for l in dict.fromkeys(b.contest for b in sc) if l not in cmap]
    f_con = [fcs[k] for k in fcs if k not in cmap.values() and any((k, ck) in set(fc) for ck in fcs[k].cands)]
    if gw is not None and sc and fc:
        s_can = sc
        f_can = fc
        lists = ("SCAN CONTESTS:\n" + "\n".join(f"{i}: {l}" for i, l in enumerate(s_con)) +
                 "\nFILE CONTESTS:\n" + "\n".join(f"{j}: {c.label}{' district ' + c.district if c.district else ''}"
                                                   for j, c in enumerate(f_con)) +
                 "\nSCAN CANDIDATES:\n" + "\n".join(f"{i}: {b.contest} :: {b.candidate}" for i, b in enumerate(s_can)) +
                 "\nFILE CANDIDATES:\n" + "\n".join(
                     f"{j}: {fcs[fk].label}{' district ' + fcs[fk].district if fcs[fk].district else ''} :: "
                     f"{fcs[fk].cands[ck].label}" for j, (fk, ck) in enumerate(f_can)))
        ns = {"contests": (len(s_con), len(f_con)), "candidates": (len(s_can), len(f_can))}
        try:
            ans = gw.ask_json(MATCH_PROMPT.format(lists=lists), validate=match_validator(ns), model=agent.SONNET)
        except BudgetExceeded:
            raise
        except ValueError as e:
            ans = {"contests": [], "candidates": []}
            m.rejected.append({"what": "the model's answer", "why": f"not usable: {str(e)[:150]}"})
        m.model = {"asked": {"scan_contests": s_con, "file_contests": [c.label for c in f_con],
                             "scan_candidates": [f"{b.contest} :: {b.candidate}" for b in s_can],
                             "file_candidates": [f"{fcs[fk].label} :: {fcs[fk].cands[ck].label}" for fk, ck in f_can]},
                   "answer": ans}
        # contests: one-to-one, and the blocks of the scan contest add up close to the file's rows
        seen_s, seen_f = set(), set()
        for i, j in ans.get("contests", []):
            if not (0 <= i < len(s_con) and 0 <= j < len(f_con)) or i in seen_s or j in seen_f:
                m.rejected.append({"what": f"contest pair {i}/{j}", "why": "not one-to-one, or not in the list"})
                continue
            seen_s.add(i); seen_f.add(j)
            sa = sum(b.total() or 0 for b in blocks if b.contest == s_con[i])
            fb = sum(file_votes(c) for c in f_con[j].cands.values())
            if not _close(sa, fb):
                m.rejected.append({"what": f"{s_con[i]} = {f_con[j].label}",
                                   "why": f"county totals are not close (scan {sa}, file {fb})"})
                continue
            cmap[s_con[i]] = f_con[j].key
        by_names(blocks, cmap)
        sc, fc = leftovers()
        fset = set(fc)
        seen_s, seen_f = set(), set()
        for i, j in ans.get("candidates", []):
            if not (0 <= i < len(s_can) and 0 <= j < len(f_can)) or i in seen_s or j in seen_f:
                m.rejected.append({"what": f"candidate pair {i}/{j}", "why": "not one-to-one, or not in the list"})
                continue
            seen_s.add(i); seen_f.add(j)
            b, (fk, ck) = s_can[i], f_can[j]
            if b.id in m.block_map or (fk, ck) not in fset:
                continue                                  # already matched by name inside a mapped contest
            if cmap.get(b.contest) != fk:
                m.rejected.append({"what": f"{b.candidate} = {fcs[fk].cands[ck].label}",
                                   "why": "their contests are not paired"})
                continue
            if not _close(b.total(), file_votes(fcs[fk].cands[ck])):
                m.rejected.append({"what": f"{b.candidate} = {fcs[fk].cands[ck].label}",
                                   "why": f"county totals are not close (scan {b.total()}, "
                                          f"file {file_votes(fcs[fk].cands[ck])})"})
                continue
            m.block_map[b.id] = (fk, ck)
    sc, fc = leftovers()
    m.unmatched_scan = [{"block": b.id, "page": b.page, "contest": b.contest, "candidate": b.candidate} for b in sc]
    m.unmatched_file = [{"contest": fcs[fk].label, "district": fcs[fk].district, "candidate": fcs[fk].cands[ck].label,
                         "rows": len(fcs[fk].cands[ck].rows)} for fk, ck in fc]
    return m


# ---- rows --------------------------------------------------------------------------------------------------------

@dataclass
class Row:
    block: Block | None
    precinct: str
    file: dict | None             # part -> int | None
    file_idx: int | None
    file_row: dict | None
    scan: dict | None             # part -> int | None
    office: str = ""
    district: str = ""
    party: str = ""
    candidate: str = ""

    @property
    def page(self):
        return self.block.page if self.block else None


def _file_parts(r: dict) -> dict:
    return {p: _int(r.get(p)) for p in PARTS}


def _scan_parts(b: Block, col: str) -> dict | None:
    if b.id == "reg":
        c = b.cells.get(("REGISTERED", col))
        return {"votes": c["value"], "absentee": None, "early_voting": None, "election_day": None} if c else None
    got = {p: (b.cells[(SCAN_ROW[p], col)]["value"] if (SCAN_ROW[p], col) in b.cells else None)
           for p in PARTS if p != "votes"}
    if all(v is None for v in got.values()):
        return None
    return {"votes": b.totals.get(("col", col)), **got}


def build_rows(blocks, matching, fcs, file_rows) -> list[Row]:
    out, seen = [], set()
    for b in blocks:
        if b.id not in matching.block_map:
            continue
        fk, ck = matching.block_map[b.id]
        fc, cand = fcs[fk], fcs[fk].cands[ck]
        order = list(b.cols) + [p for p in cand.rows if p not in b.cols]
        for p in order:
            sp = _scan_parts(b, p) if p in b.cols else None
            fr = cand.rows.get(p)
            if sp is None and fr is None:
                continue
            if fr:
                seen.add(fr[0])
            r = fr[1] if fr else {}
            out.append(Row(b, p, _file_parts(r) if fr else None, fr[0] if fr else None, r or None, sp,
                           fc.label, fc.district, (r.get("party") if fr else "") or "", cand.label))
    for i, r in enumerate(file_rows):      # file rows with no scan block: only their own sum can be tested
        if i not in seen:
            out.append(Row(None, str(r.get("precinct")), _file_parts(r), i, r, None, r.get("office") or "",
                           r.get("district") or "", r.get("party") or "", r.get("candidate") or ""))
    return out


def row_fails_own_total(r: Row) -> bool:
    f = r.file
    if not f or any(f[p] is None for p in PARTS):
        return False
    return f["votes"] != f["absentee"] + f["early_voting"] + f["election_day"]


def diff_parts(r: Row) -> list[str]:
    if not r.file or not r.scan:
        return []
    return [p for p in PARTS if r.file[p] is not None and r.scan[p] is not None and r.file[p] != r.scan[p]]


# ---- the sums that decide ----------------------------------------------------------------------------------------

def decide_status(sums: list[dict], doubt: str | None = None) -> tuple[str, str]:
    """The status of a disagreement from the printed sums it sits on. Each sum: {name, holds_with_scan, holds_with_file}.

    settled_against_file: at least one printed total holds with the scan's value and fails with the file's, and none holds
      with the file's and fails with the scan's, and the scan's totals do not disagree with each other at the cell.
    document_inconsistent: the scan's own printed totals disagree with each other at the cell: some hold with the
      scan's value and some do not (the reason names which).
    cannot_verify: no printed total decides (a sum that fails with both values decides nothing), or the scan's value
      is itself in doubt."""
    if doubt:
        return "cannot_verify", doubt
    for_scan = [s for s in sums if s["holds_with_scan"] and not s["holds_with_file"]]
    for_file = [s for s in sums if not s["holds_with_scan"] and s["holds_with_file"]]
    both_fail = [s for s in sums if not s["holds_with_scan"] and not s["holds_with_file"]]
    if for_scan and for_file:
        return ("document_inconsistent",
                "the scan's own printed totals disagree with each other at this cell: " +
                "; ".join(s["name"] for s in for_scan) + " hold(s) with the scan's value and fail(s) with the file's, but " +
                "; ".join(s["name"] for s in for_file) + " hold(s) with the file's value and fail(s) with the scan's")
    if for_scan:
        note = (" (" + "; ".join(s["name"] for s in both_fail) + " fail with either value and decide nothing)"
                if both_fail else "")
        return ("settled_against_file",
                "; ".join(s["name"] for s in for_scan) + " hold(s) with the scan's value and fail(s) with the file's, "
                "and no printed total holds with the file's value and fails with the scan's" + note)
    if for_file:
        return ("cannot_verify",
                "the scan's value is in doubt: " + "; ".join(s["name"] for s in for_file) +
                " holds with the file's value and fails with the scan's, and no printed total supports the scan's")
    return "cannot_verify", ("no printed total decides: " + ("; ".join(s["name"] for s in sums) +
                                                              " give the same answer with either value"
                                                              if sums else "no printed total covers this value"))


def sums_decide(sums: list[dict]) -> bool:
    """True when every printed sum through a value holds with the ledger's value and fails with the file's (two sums
    for a cell or a printed total, one for a value that sits on one sum). No single-value look at the scan outweighs it."""
    return bool(sums) and all(s["holds_with_scan"] and not s["holds_with_file"] for s in sums)


def finding_status(sums: list[dict], rd: dict | None, sv, fv) -> tuple[str, str, bool]:
    """(status, reason, reread_disagrees). The printed sums decide; the single-value re-read is only a note.
    settled_against_file   every sum through the value holds with the ledger's value and fails with the file's
    document_inconsistent  some sums hold with the ledger's value and fail with the file's, others the other way round
    cannot_verify          anything else (a sum that fails with both values, or holds with both, decides nothing)
    reread_disagrees is true when a re-read was made, gave a number, and it differs from the ledger's value."""
    got = rd.get("value") if rd else None
    disagrees = got is not None and got != sv
    note = f" (a single-value re-read of the scan gave {got}; the printed sums decide regardless)" if disagrees else ""
    if sums_decide(sums):
        return "settled_against_file", decide_status(sums)[1] + note, disagrees
    st, why = decide_status(sums)
    if st == "settled_against_file":                  # some sum fails with both values or holds with both: no decision
        und = [x["name"] for x in sums if not (x["holds_with_scan"] and not x["holds_with_file"])]
        why = ("the sums do not decide: " + "; ".join(und) + " fail(s) with either value or hold(s) with both, "
               "although others hold with the scan's value and fail with the file's")
        st = "cannot_verify"
    if st == "cannot_verify" and rd is not None and rd.get("value") is None and rd.get("error"):
        why += f"; the re-read of the scan could not be made ({rd['error']})"
    return st, why + (note if st == "cannot_verify" else ""), disagrees


def describe_sum(ch) -> tuple[str, str]:
    """(name, label of the printed total) of a check, in words."""
    if ch.kind == "row":
        if ch.key == "REGISTERED":
            return ("the registered-voters row (its cells add to the printed total of the row; this row has no other sum)",
                    "printed total at the right end of the row")
        return (f"the {ch.key} cells across the page add to the row total printed at the right end of the row",
                "printed total at the right end of the row")
    if ch.kind == "col":
        return (f"the three cells of precinct {ch.key} add to the small total printed under the column",
                "small total printed under the column")
    if ch.kind == "grand_col":
        return "the small totals under the columns add to the grand total", "grand total"
    return "the row totals add to the grand total", "grand total"


def entity_key(row: Row, part: str) -> tuple | None:
    """The scan value a part of a row is: ('cell', page, block, row_kind, column) or ('total', page, block, 'col', column)."""
    b = row.block
    if b is None:
        return None
    if part == "votes":
        return ("cell", b.page, b.id, "REGISTERED", row.precinct) if b.id == "reg" else \
            ("total", b.page, b.id, "col", row.precinct)
    return ("cell", b.page, b.id, SCAN_ROW[part], row.precinct)


def _variant(cells, totals, ent, value):
    cs, ts = [dict(c) for c in cells], [dict(t) for t in totals]
    if ent[0] == "cell":
        key = tuple(ent[1:])
        hit = [c for c in cs if checks.cell_key(c) == key]
        for c in hit:
            c["value"] = value
        if not hit and value is not None:
            cs.append({"page": ent[1], "block_id": ent[2], "row_kind": ent[3], "column": ent[4], "value": value})
    else:
        key = tuple(ent[1:])
        hit = [t for t in ts if (t["page"], t["block_id"], t["direction"], t["key"]) == key]
        for t in hit:
            t["value"] = value
        if not hit and value is not None:
            ts.append({"page": ent[1], "block_id": ent[2], "direction": ent[3], "key": ent[4], "value": value})
    return checks.all_checks(cs, ts)


def _ck(c):
    return (c.kind, c.page, c.block_id, c.key)


def _touches(ch, ent) -> bool:
    key = tuple(ent[1:])
    if ent[0] == "cell":
        return any(k == key for k, _ in ch.terms)
    return ch.printed_key == key or any(k == key for k, _ in ch.terms)


def sums_for(ent, scan_value, file_value, cells, totals) -> list[dict]:
    """The printed sums the scan value sits on, each tested with the scan's value and with the file's (a value the file
    lacks counts as 0; one the scan lacks counts as absent). `cells`/`totals` are the ledger's rows of the one block."""
    with_scan = {_ck(c): c for c in _variant(cells, totals, ent, scan_value)}
    with_file = {_ck(c): c for c in _variant(cells, totals, ent, 0 if file_value is None else file_value)}
    out = []
    for k, fch in with_file.items():
        sch = with_scan.get(k)
        if sch is None or not (_touches(fch, ent) or _touches(sch, ent)):
            continue
        name, label = describe_sum(sch)
        out.append({"name": name, "kind": sch.kind, "page": sch.page, "block": sch.block_id,
                    "terms": [{"cell": list(kk), "value": v} for kk, v in sch.terms], "printed": sch.printed,
                    "printed_label": label, "computed_with_scan": sch.computed, "holds_with_scan": sch.ok,
                    "computed_with_file": fch.computed, "holds_with_file": fch.ok})
    order = {"row": 0, "col": 1, "grand_col": 2, "grand_row": 3}
    out.sort(key=lambda s: order[s["kind"]])
    return out


# ---- classification and groups -----------------------------------------------------------------------------------

@dataclass
class Slot:
    row: Row
    part: str
    kind: str
    group: tuple


def _tuple(d):
    return tuple(d[p] for p in PARTS) if d and all(d[p] is not None for p in PARTS) else None


def classify(rows: list[Row]) -> list[Slot]:
    """Every disagreement as a slot with a kind and a group key. A group is one slip:
    wrong_precinct  the same row of values sits under another precinct of the same candidate (unique matches only)
    wrong_column    the same values sit in other parts of the same precinct
    wrong_number    anything else that differs
    missing_row / extra_row    the scan has a row the file lacks, or the other way round
    file_row_fails_own_total   the file's votes differ from its three parts (whether or not the scan differs)"""
    slots: list[Slot] = []
    by_block: dict = {}
    for r in rows:
        by_block.setdefault(r.block.id if r.block else None, []).append(r)
    for bid, rs in by_block.items():
        if bid is None:
            continue
        d = [r for r in rs if (r.file is None) != (r.scan is None) or diff_parts(r)]
        tf = {id(r): _tuple(r.file) for r in d}
        ts = {id(r): _tuple(r.scan) for r in d}
        parent = {id(r): id(r) for r in d}

        def find(x):
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x
        linked, edge = set(), {}
        for p in d:
            v = tf[id(p)]
            if v is None or not any(v):
                continue
            src = [x for x in d if tf[id(x)] == v]
            dst = [x for x in d if ts[id(x)] == v and x is not p]
            if len(src) == 1 and len(dst) == 1:
                edge[id(p)] = dst[0]
        for pid, q in edge.items():
            p = next(x for x in d if id(x) == pid)
            swap = tf[id(q)] is not None and tf[id(q)] == ts[id(p)]
            if swap or tf[pid][0] >= MIN_LINK_VOTES:
                parent[find(pid)] = find(id(q))
                linked.update((pid, id(q)))
        comps: dict = {}
        for r in d:
            if id(r) in linked:
                comps.setdefault(find(id(r)), []).append(r)
        for ci, members in enumerate(comps.values()):
            key = ("wrong_precinct", bid, ci)
            for r in members:
                if r.file and r.scan:
                    slots += [Slot(r, p, "wrong_precinct", key) for p in diff_parts(r)]
                else:
                    slots.append(Slot(r, "votes", "wrong_precinct", key))
        for r in d:
            if id(r) in linked:
                continue
            key = (None, bid, r.precinct)
            if r.file is None:
                slots.append(Slot(r, "votes", "missing_row", ("missing_row", *key[1:])))
            elif r.scan is None:
                slots.append(Slot(r, "votes", "extra_row", ("extra_row", *key[1:])))
            else:
                dp = diff_parts(r)
                cols = [p for p in dp if p != "votes"]
                if (len(cols) >= 2 and "votes" not in dp and
                        sorted(r.file[p] for p in cols) == sorted(r.scan[p] for p in cols)):
                    slots += [Slot(r, p, "wrong_column", ("wrong_column", *key[1:])) for p in cols]
                else:
                    slots += [Slot(r, p, "wrong_number", ("wrong_number", *key[1:])) for p in dp]
    for r in rows:                                    # the file's own sum, whatever the scan says
        if row_fails_own_total(r):
            slots = [s for s in slots if not (s.row is r and s.part == "votes")]
            slots.append(Slot(r, "votes", "file_row_fails_own_total",
                              ("file_row_fails_own_total", r.block.id if r.block else None, r.precinct, r.file_idx)))
    return slots


# ---- re-reads ----------------------------------------------------------------------------------------------------

def target_for(ent) -> dict:
    return {"kind": "cell", "row": ent[3], "column": ent[4]} if ent[0] == "cell" else \
        {"kind": "col_total", "column": ent[4]}


def _reread_one(gw, path, t, model):
    prompt = agent.READ_PROMPTS[t["kind"]].format(row=t.get("row"), column=t.get("column"))
    return gw.ask_json(prompt, path, validate=agent.read_validator(t["kind"]), model=model)["value"]


def reread_slots(slots, geo, gw, crop_dir: Path, *, log=print, only=None) -> dict:
    """Look at each disagreeing value on the scan once more: 400 dpi crop, claude-sonnet-4.6, up to three at a time.
    Only the entities in `only` are read (the values the printed sums do not decide). Returns
    {entity: {value, model, dpi, crop, error}}."""
    todo: dict = {}
    for s in slots:
        if s.row.file and s.row.scan and s.part in diff_parts(s.row):
            ent = entity_key(s.row, s.part)
            if ent is not None and (only is None or ent in only):
                todo.setdefault(ent, None)
    jobs, out = [], {}
    for n, ent in enumerate(todo, 1):
        t = target_for(ent)
        try:
            path, _ = geo.crop(ent[1], ent[2], t, REREAD_DPI, crop_dir / f"audit-reread-{n:04d}-{ent[2]}.png")
        except Exception as e:                        # no crop for it: the re-read cannot be made
            out[ent] = {"value": None, "model": REREAD_MODEL, "dpi": REREAD_DPI, "crop": None,
                        "error": f"no crop: {str(e)[:120]}"}
            continue
        jobs.append((ent, t, path))
    stop = threading.Event()

    def run(job):
        ent, t, path = job
        if stop.is_set():
            return ent, {"value": None, "model": REREAD_MODEL, "dpi": REREAD_DPI, "crop": str(path),
                         "error": "not made: the run's budget was reached"}
        try:
            v = _reread_one(gw, path, t, REREAD_MODEL)
            return ent, {"value": v, "model": REREAD_MODEL, "dpi": REREAD_DPI, "crop": str(path), "error": None}
        except BudgetExceeded as e:
            stop.set()
            return ent, {"value": None, "model": REREAD_MODEL, "dpi": REREAD_DPI, "crop": str(path), "error": str(e)[:120]}
        except Exception as e:
            return ent, {"value": None, "model": REREAD_MODEL, "dpi": REREAD_DPI, "crop": str(path),
                         "error": f"no usable answer: {str(e)[:120]}"}
    with ThreadPoolExecutor(PARALLEL) as ex:
        for ent, res in ex.map(run, jobs):
            out[ent] = res
    log(f"  re-read {len(jobs)} values on the scan")
    return out


# ---- the audit ---------------------------------------------------------------------------------------------------

def _block_rows(cells, totals, page, bid):
    return ([c for c in cells if c["page"] == page and c["block_id"] == bid],
            [t for t in totals if t["page"] == page and t["block_id"] == bid])


def _state(led, county, file_rows, gw, log):
    cells, totals = led.cells(county), led.totals(county)
    blocks = scan_blocks(cells, totals)
    fcs = file_contests(file_rows)
    return cells, totals, blocks, fcs


def audit_county(county, led, geo, gw, file_rows, *, run_dir, make_crops=True, log=print, data_root=None,
                 file_name=None, policy=None, run_id="") -> dict:
    """Run the audit on a closed ledger. Re-reads go through `gw`; the ledger is changed only where a re-read gave the
    file's value and every sum holds with it. Returns the findings, groups, corrections and what could not be matched."""
    t0 = time.time()
    run_dir = Path(run_dir)
    crop_dir = run_dir / county / "crops"              # one picture per group
    reread_dir = run_dir / "crops"                     # the re-read crops, not committed
    cells, totals, blocks, fcs = _state(led, county, file_rows, gw, log)
    matching = match(blocks, fcs, gw, log)
    rows = build_rows(blocks, matching, fcs, file_rows)
    slots = classify(rows)
    n0 = len(slots)
    log(f"  {len(rows)} rows compared; {n0} disagreements to look at on the scan")
    decided: dict = {}                               # entity -> do the printed sums decide it (then no re-read is made)
    for sl in slots:
        if sl.row.file and sl.row.scan and sl.part in diff_parts(sl.row):
            ent = entity_key(sl.row, sl.part)
            if ent is not None and ent not in decided:
                cs, ts = _block_rows(cells, totals, ent[1], ent[2])
                decided[ent] = sums_decide(sums_for(ent, sl.row.scan[sl.part], sl.row.file[sl.part], cs, ts))
    need = {e for e, d in decided.items() if not d}
    reads = reread_slots(slots, geo, gw, reread_dir, log=log, only=need) if need else {}
    # a re-read that gives the file's value, with every sum holding with it, shows the ledger was wrong
    corrected_events, agreed_ledger = [], 0
    where = {entity_key(s.row, s.part): (s.row, s.part) for s in slots}
    for ent, rd in reads.items():
        if rd["value"] is None:
            continue
        row, part = where[ent]
        fv, old = row.file[part], row.scan[part]
        if rd["value"] == old:
            agreed_ledger += 1
        elif rd["value"] == fv:
            cs, ts = _block_rows(cells, totals, ent[1], ent[2])
            sums = sums_for(ent, old, fv, cs, ts)
            if sums and all(x["holds_with_file"] for x in sums):
                if ent[0] == "cell":
                    led.set_value(county, ent[1], ent[2], ent[3], ent[4], fv, REREAD_MODEL)
                    led.set_status(county, ent[1], ent[2], ent[3], ent[4], "first_read")
                else:
                    led.put_total(county, ent[1], ent[2], ent[3], ent[4], fv)
                led.event(county, "audit_ledger_corrected", {"entity": list(ent), "old": old, "new": fv,
                                                             "model": REREAD_MODEL, "dpi": REREAD_DPI, "sums": sums})
                corrected_events.append({"entity": list(ent), "old": old, "new": fv, "sums": sums})
                cells, totals = led.cells(county), led.totals(county)
    if corrected_events:
        agent.derive_status(led, county)
        cells, totals, blocks, fcs = _state(led, county, file_rows, gw, log)
        rows = build_rows(blocks, matching, fcs, file_rows)
        slots = classify(rows)
    findings, groups = _findings(county, slots, reads, cells, totals, geo, file_rows)
    res = {"findings": findings, "groups": groups, "matching": matching, "rows": len(rows), "crop_dir": crop_dir,
           "row_objs": rows, "cells": cells, "totals": totals,
           "corrected_events": corrected_events, "reads": reads,
           "audit": {"disagreements_found": n0, "rereads": len(reads),
                     "rereads_skipped_sums_decide": len(decided) - len(need), "rereads_agreed_with_ledger": agreed_ledger,
                     "rereads_agreed_with_file": sum(1 for r in reads.values() if r["value"] is not None) - agreed_ledger -
                     sum(1 for ent, r in reads.items() if r["value"] is not None and r["value"] != where[ent][0].file[where[ent][1]]
                         and r["value"] != where[ent][0].scan[where[ent][1]]),
                     "ledger_corrected": len(corrected_events), "seconds": round(time.time() - t0, 1)}}
    res["file_name"] = file_name
    return res


def _findings(county, slots, reads, cells, totals, geo, file_rows):
    order = {}
    for s in slots:
        order.setdefault(s.group, len(order))
    gnames = {g: f"g{n + 1:03d}" for g, n in order.items()}
    slots = sorted(slots, key=lambda s: (order[s.group], PARTS.index(s.part)))
    findings, counter = [], 0
    for s in slots:
        r = s.row
        ent = entity_key(r, s.part)
        sv = r.scan[s.part] if r.scan else None
        fv = r.file[s.part] if r.file else None
        page, bid = (r.block.page, r.block.id) if r.block else (None, None)
        sums = []
        if ent is not None and (fv is not None or sv is not None):
            cs, ts = _block_rows(cells, totals, page, bid)
            sums = sums_for(ent, sv, fv, cs, ts)
        rd = reads.get(ent) if ent else None
        if ent is None:
            status, why, dis = "cannot_verify", "this file row has no matching contest on the scan, so no printed total covers it", False
        else:
            status, why, dis = finding_status(sums, rd, sv, fv)
        if s.kind == "file_row_fails_own_total":
            f = r.file
            own = f"the file's votes {f['votes']} differ from its parts {f['absentee']} + {f['early_voting']} + " \
                  f"{f['election_day']} = {f['absentee'] + f['early_voting'] + f['election_day']}; "
            why = own + why
        counter += 1
        box = None
        if ent is not None and ent[0] == "cell" and r.scan:
            c = next((c for c in cells if checks.cell_key(c) == tuple(ent[1:])), None)
            box = [c[k] for k in ("x0", "y0", "x1", "y1")] if c and c["x0"] is not None else None
        elif ent is not None and ent[0] == "total":
            tb = geo.total_box(page, bid, "col", r.precinct) if hasattr(geo, "total_box") else None
            box = list(tb) if tb else None
        if box is None and ent is not None and r.block is not None:
            try:
                cb = geo.cell_box(page, bid, SCAN_ROW.get(s.part, "EARLY") if s.part != "votes" else "EARLY", r.precinct)
                box = list(cb) if cb else None
            except Exception:
                box = None
        findings.append({
            "id": f"f{counter:03d}", "group": gnames[s.group], "county": county, "office": r.office,
            "district": r.district, "party": r.party, "candidate": r.candidate, "precinct": r.precinct,
            "part": s.part, "file_value": fv, "scan_value": sv, "kind": s.kind, "status": status, "reason": why,
            "sums": sums, "page": page, "block": bid, "box": box, "crop": None,
            "reread": ({k: rd[k] for k in ("model", "dpi", "value", "crop", "error")} if rd else None),
            "reread_disagrees": dis, "row_not_corrected": None,
            "row_values": ({"file": r.file, "scan": r.scan} if s.kind in ("missing_row", "extra_row") else None),
            "file_row": r.file_idx, "file_line": (r.file_idx + 2) if r.file_idx is not None else None,
            "corrected": False, "confirmed_by_person": False})
    groups = []
    for g, name in gnames.items():
        fs = [f for f in findings if f["group"] == name]
        f0 = fs[0]
        groups.append({"id": name, "kind": f0["kind"], "office": f0["office"], "district": f0["district"],
                       "candidate": f0["candidate"], "precincts": sorted({f["precinct"] for f in fs}, key=_pk),
                       "page": f0["page"], "block": f0["block"], "findings": [f["id"] for f in fs],
                       "statuses": {st: sum(1 for f in fs if f["status"] == st) for st in STATUSES
                                    if any(f["status"] == st for f in fs)},
                       "what_to_do": what_to_do(g, slots) if f0["kind"] == "wrong_precinct" else None, "crop": None})
    return findings, groups


def what_to_do(group, slots) -> str:
    """One sentence for a wrong_precinct group: what a person would have to do to the file's rows."""
    rows = list({id(s.row): s.row for s in slots if s.group == group}.values())
    pairs = {}
    for p in rows:
        v = _tuple(p.file)
        if v is None or not any(v):
            continue
        dst = [q for q in rows if q is not p and _tuple(q.scan) == v]
        if len(dst) == 1:
            pairs[p.precinct] = dst[0].precinct
    cols = list(rows[0].block.cols) if rows and rows[0].block else []
    off = {cols.index(q) - cols.index(p) for p, q in pairs.items() if p in cols and q in cols}
    rest = len(rows) - len(pairs)
    tail = f", and {rest} more row(s) of the group have no counterpart (see the missing and extra rows)" if rest > 0 else ""
    n = len(pairs)
    if n and len(off) == 1 and len(pairs) == sum(1 for p, q in pairs.items() if p in cols and q in cols):
        k = abs(next(iter(off)))
        way = "later" if next(iter(off)) < 0 else "earlier"
        return (f"Move the same {n} rows of values, each labelled {k} precinct{'s' if k != 1 else ''} {way} than where "
                f"the scan has it, back to the precinct the scan puts them under{tail}.")
    shown = ", ".join(f"{p} to {q}" for p, q in list(pairs.items())[:8]) + (" and more" if n > 8 else "")
    return f"Move the same {n} rows of values to the precinct where the scan has them ({shown}){tail}."


def _pk(p):
    return (0, int(p), "") if str(p).isdigit() else (1, 0, str(p))


# ---- the corrected file ------------------------------------------------------------------------------------------

def _spans(line: str) -> list[tuple[int, int]]:
    """Character spans of the fields of one csv line (quotes respected), without the line ending."""
    spans, start, i, q = [], 0, 0, False
    body = line.rstrip("\r\n")
    while i < len(body):
        ch = body[i]
        if ch == '"':
            q = not q
        elif ch == "," and not q:
            spans.append((start, i))
            start = i + 1
        i += 1
    spans.append((start, len(body)))
    return spans


def _correctable(f, header) -> bool:
    return (f.get("status") == "settled_against_file" and f.get("kind") in CORRECTABLE and f.get("file_row") is not None
            and isinstance(f.get("scan_value"), int) and f["part"] in header)


def whole_rows(raw: bytes, findings: list[dict]) -> tuple[list[dict], list[dict]]:
    """Keep a row's corrections only if the row is consistent afterwards: its corrected `votes` equals its corrected
    parts. Returns (findings that may be applied, rows that could not be corrected as a whole, each with its reason).
    Findings that would not be applied anyway pass through unchanged."""
    lines = raw.decode("utf-8").splitlines(True)
    header = next(csv.reader(io.StringIO(lines[0])))
    by_row: dict = {}
    for f in findings:
        if _correctable(f, header) and f["file_row"] + 1 < len(lines):
            by_row.setdefault(f["file_row"], []).append(f)
    bad, could = set(), []
    for i, fs in sorted(by_row.items()):
        cells = next(csv.reader(io.StringIO(lines[i + 1])))
        d = {h: (cells[k] if k < len(cells) else "") for k, h in enumerate(header)}
        val = {p: _int(d.get(p)) for p in PARTS}
        for f in fs:
            val[f["part"]] = f["scan_value"]
        parts = [val["absentee"], val["early_voting"], val["election_day"]]
        if val["votes"] is None or any(v is None for v in parts):
            why = "a number of the row is empty in the file, so the corrected row's total cannot be checked"
        elif val["votes"] != sum(parts):
            why = (f"the corrected votes {val['votes']} would not equal the corrected parts {parts[0]} + {parts[1]} + "
                   f"{parts[2]} = {sum(parts)}")
        else:
            continue
        bad.add(i)
        could.append({"file_row": i, "file_line": i + 2, "office": d.get("office"), "candidate": d.get("candidate"),
                      "precinct": d.get("precinct"), "findings": [f.get("id") for f in fs], "reason": why})
    return [f for f in findings if f.get("file_row") not in bad or not _correctable(f, header)], could


def apply_corrections(raw: bytes, findings: list[dict]) -> tuple[bytes, str, list[dict]]:
    """Change only the cells whose finding is settled_against_file (and whose scan value is a number and whose file row
    exists); keep every other byte. Returns (new bytes, unified diff of exactly the changed lines, what was applied).
    Each finding needs {file_row, part, file_value, scan_value, kind, status}; file_row is the index among the data rows."""
    text = raw.decode("utf-8")
    lines = text.splitlines(True)
    header = next(csv.reader(io.StringIO(lines[0])))
    new, applied = list(lines), []
    for f in findings:
        if not _correctable(f, header):
            continue
        i = f["file_row"] + 1
        if i >= len(new):
            continue
        sp = _spans(new[i])
        a, b = sp[header.index(f["part"])]
        new[i] = new[i][:a] + str(f["scan_value"]) + new[i][b:]
        applied.append({"finding": f.get("id"), "file_row": f["file_row"], "part": f["part"],
                        "old": f.get("file_value"), "new": f["scan_value"]})
    out = "".join(new)
    name = "published file"
    diff = "".join(difflib.unified_diff(lines, new, fromfile=f"a/{name}", tofile=f"b/{name}", n=0))
    return out.encode("utf-8"), diff, applied


# ---- every printed sum, with the published file and with the corrected file ---------------------------------------------

def _with_values(cells, totals, vals):
    """Copies of the ledger's cells and totals with the values of `vals` ({entity: value}) put in."""
    cs, ts = [dict(c) for c in cells], [dict(t) for t in totals]
    cmap = {checks.cell_key(c): c for c in cs}
    tmap = {(t["page"], t["block_id"], t["direction"], t["key"]): t for t in ts}
    for ent, v in vals.items():
        d = cmap if ent[0] == "cell" else tmap
        if tuple(ent[1:]) in d:
            d[tuple(ent[1:])]["value"] = v
    return cs, ts


def sums_check(cells, totals, rows, findings, applied, matching) -> dict:
    """Every printed sum of the county, tested three ways: with the ledger (the scan), with the published file's values in
    place of the ledger's, and with the corrected file's. Only matched rows (file row and scan row both there) take the
    file's values. Returns {in_all, holding_with_ledger, holding_with_published, holding_with_corrected, still_failing,
    rows_failing_own_total}; each still failing sum has its reasons."""
    new = {(a["file_row"], a["part"]): a["new"] for a in applied}
    pub, cor = {}, {}
    own = {"published": 0, "corrected": 0}
    for r in rows:
        if r.file is None:
            continue
        own["published"] += row_fails_own_total(r)
        parts = {p: new.get((r.file_idx, p), r.file[p]) for p in PARTS}
        if all(v is not None for v in parts.values()) and parts["votes"] != parts["absentee"] + parts["early_voting"] + parts["election_day"]:
            own["corrected"] += 1
        if r.block is None or r.scan is None:
            continue
        for p in PARTS:
            ent = entity_key(r, p)
            if ent is not None and r.file[p] is not None and r.scan[p] is not None:
                pub[ent], cor[ent] = r.file[p], parts[p]
    base = checks.all_checks(cells, totals)
    with_pub = checks.all_checks(*_with_values(cells, totals, pub))
    with_cor = checks.all_checks(*_with_values(cells, totals, cor))
    missing = {(r.block.page, r.block.id, r.precinct) for r in rows if r.file is None and r.scan is not None and r.block}
    unmatched = {(u["page"], u["block"]) for u in matching.unmatched_scan}
    at: dict = {}
    for f in findings:
        if f.get("block") is None or f["kind"] == "missing_row":
            continue
        e = ("cell", f["page"], f["block"], "REGISTERED", f["precinct"]) if f["block"] == "reg" and f["part"] == "votes" else \
            ("total", f["page"], f["block"], "col", f["precinct"]) if f["part"] == "votes" else \
            ("cell", f["page"], f["block"], SCAN_ROW[f["part"]], f["precinct"])
        at.setdefault(tuple(e[1:]), []).append(f)
    failing = []
    for ch in with_cor:
        if ch.ok:
            continue
        reasons = []
        keys = [k for k, _ in ch.terms] + ([ch.printed_key] if ch.printed_key else [])
        for k in keys:
            if (k[0], k[1], k[3]) in missing:
                reasons.append(f"a row missing from the file (precinct {k[3]}, page {k[0]}, block {k[1]})")
            for f in at.get(tuple(k), []):
                if f.get("row_not_corrected"):
                    reasons.append(f"a row that could not be corrected as a whole ({f['id']})")
                elif f["status"] == "cannot_verify":
                    reasons.append(f"a value that could not be verified ({f['id']}: {f['candidate'] or f['office']}, "
                                   f"precinct {f['precinct']}, {f['part']})")
                elif f["status"] == "document_inconsistent":
                    reasons.append(f"the document's own inconsistency ({f['id']})")
        if (ch.page, ch.block_id) in unmatched:
            reasons.append("a block of the scan with no counterpart in the file")
        if not reasons:
            reasons.append("the scan's own cells and its printed total disagree, and no difference from the file is involved")
        name, _ = describe_sum(ch)
        failing.append({"name": name, "kind": ch.kind, "page": ch.page, "block": ch.block_id, "key": ch.key,
                        "printed": ch.printed, "computed": ch.computed, "reasons": list(dict.fromkeys(reasons))})
    return {"in_all": len(base), "holding_with_ledger": sum(c.ok for c in base),
            "holding_with_published": sum(c.ok for c in with_pub), "holding_with_corrected": sum(c.ok for c in with_cor),
            "still_failing": failing, "rows_failing_own_total": own}


# ---- the model gateway the audit runs through --------------------------------------------------------------------

class _CountingCompletions:
    def __init__(self, inner, owner):
        self.inner, self.owner = inner, owner

    def create(self, **kw):
        self.owner._space()
        r = self.inner.create(**kw)
        self.owner._count(kw.get("model"), r.usage)
        return r


class _Counting:
    def __init__(self, client, owner):
        self.chat = type("Chat", (), {})()
        self.chat.completions = _CountingCompletions(client.chat.completions, owner)


class AuditGateway(Gateway):
    """The Gateway, with two additions the audit needs: call starts at least `min_interval` seconds apart even when
    several threads ask at once, and calls, tokens and cost counted by model."""

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.by_model: dict = {}
        self._lock = threading.Lock()
        self._start = threading.Lock()
        self._next = 0.0
        self.client = _Counting(self.client, self)

    def _count(self, model, usage):
        with self._lock:
            m = self.by_model.setdefault(model, {"calls": 0, "prompt_tokens": 0, "completion_tokens": 0, "cost": 0.0})
            m["calls"] += 1
            m["prompt_tokens"] += usage.prompt_tokens
            m["completion_tokens"] += usage.completion_tokens
            m["cost"] += price(model, usage.prompt_tokens, usage.completion_tokens)

    def _space(self):
        """Called just before a request is sent: wait until `min_interval` has passed since the last one was sent."""
        with self._start:
            wait = self._next - time.monotonic()
            if wait > 0:
                time.sleep(wait)
            self._next = time.monotonic() + self.min_interval

    def calls_by_model(self) -> dict:
        return {k: {**v, "cost": round(v["cost"], 4)} for k, v in sorted(self.by_model.items())}
