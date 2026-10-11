"""The audit's rules: status of a disagreement from the printed sums, and the corrected file (AC-7). No network."""
import csv
import io
import re

from PIL import Image

from crossfoot import audit
from crossfoot.ledger import Ledger
from tests.test_agent import GOOD, make_block

HEAD = "county,precinct,office,district,party,candidate,votes,absentee,early_voting,election_day"


def sm(name, scan, file):
    return {"name": name, "holds_with_scan": scan, "holds_with_file": file}


# ---- status rules --------------------------------------------------------------------------------------------------

def test_settled_when_a_total_holds_with_the_scan_and_fails_with_the_file():
    st, why = audit.decide_status([sm("row", True, False), sm("col", True, False)])
    assert st == "settled_against_file"


def test_a_sum_that_fails_with_both_values_decides_nothing():
    st, why = audit.decide_status([sm("row", True, False), sm("grand", True, False), sm("x", False, False)])
    assert st == "settled_against_file" and "decide nothing" in why


def test_not_settled_when_a_total_holds_with_the_file_and_fails_with_the_scan():
    st, why = audit.decide_status([sm("row", True, False), sm("col", False, True)])
    assert st == "document_inconsistent"
    assert "row" in why and "col" in why            # names which totals disagree


def test_cannot_verify_when_no_total_decides():
    assert audit.decide_status([sm("a", False, False)])[0] == "cannot_verify"
    assert audit.decide_status([sm("a", True, True)])[0] == "cannot_verify"
    assert audit.decide_status([])[0] == "cannot_verify"


def test_cannot_verify_when_the_scan_value_breaks_every_sum_and_the_file_holds_one():
    st, why = audit.decide_status([sm("a", False, True), sm("b", False, False)])
    assert st == "cannot_verify" and "doubt" in why


def test_cannot_verify_when_the_scan_value_is_in_doubt():
    st, why = audit.decide_status([sm("a", True, False)], doubt="the re-read gave a third value")
    assert st == "cannot_verify" and "third value" in why


# ---- AC-7: the corrected file --------------------------------------------------------------------------------------

def file_text(rows):
    return HEAD + "\n" + "".join(",".join(r) + "\n" for r in rows)


def parse(text):
    return list(csv.DictReader(io.StringIO(text)))


def finding(row, part, new, status="settled_against_file", kind="wrong_number", scan_value=None):
    return {"file_row": row, "part": part, "file_value": 0, "scan_value": new if scan_value is None else scan_value,
            "kind": kind, "status": status}


def test_only_settled_findings_change_the_file_and_the_diff_has_exactly_those_lines():
    rows = [["X", "1", "C", "", "REP", "A", "15", "2", "10", "3"],
            ["X", "2", "C", "", "REP", "A", "31", "4", "21", "6"],
            ["X", "3", "C", "", "REP", "A", "9", "1", "4", "4"]]
    raw = file_text(rows).encode()
    fs = [finding(1, "early_voting", 20), finding(1, "votes", 30),
          finding(2, "absentee", 7, status="cannot_verify"),
          finding(2, "election_day", 5, status="document_inconsistent")]
    new, diff, applied = audit.apply_corrections(raw, fs)
    assert len(applied) == 2
    old_l, new_l = raw.decode().splitlines(True), new.decode().splitlines(True)
    assert [i for i, (a, b) in enumerate(zip(old_l, new_l)) if a != b] == [2]      # only precinct 2's line
    assert old_l[:2] + old_l[3:] == new_l[:2] + new_l[3:]                          # every other byte is kept
    assert new_l[2] == "X,2,C,,REP,A,30,4,20,6\n"
    assert diff.count("\n-X,") == 1 and diff.count("\n+X,") == 1
    assert diff.startswith("--- a/") and "@@" in diff


def test_a_correction_needs_a_scan_value_and_a_settled_finding():
    raw = file_text([["X", "1", "C", "", "REP", "A", "15", "2", "10", "3"]]).encode()
    fs = [finding(0, "votes", None, scan_value=None, kind="extra_row"),
          finding(0, "absentee", 9, kind="missing_row", status="cannot_verify")]
    fs[0]["scan_value"] = None
    new, diff, applied = audit.apply_corrections(raw, fs)
    assert new == raw and diff == "" and applied == []


def test_a_quoted_field_and_crlf_lines_are_kept():
    line = 'X,2,"Justice, Place 2",,REP,A,31,4,21,6\r\n'
    raw = (HEAD + "\r\n" + line).encode()
    new, diff, applied = audit.apply_corrections(raw, [finding(0, "votes", 30)])
    assert new.decode() == HEAD + "\r\n" + 'X,2,"Justice, Place 2",,REP,A,30,4,21,6\r\n'
    assert len(applied) == 1


def test_end_to_end_small_file_and_ledger(tmp_path):
    led = Ledger()
    make_block(led, 1, "p1-b1")                       # precincts 1 and 2; EARLY row total 30, small totals 15 and 30
    rows = [["X", "1", "C", "", "", "cand p1-b1", "15", "2", "10", "3"],
            ["X", "2", "C", "", "", "cand p1-b1", "30", "4", "21", "6"]]    # precinct 2 early_voting 21, should be 20
    raw = file_text(rows).encode()
    res = audit.audit_county("x", led, Geo(), Gw(led), parse(raw.decode()), run_dir=tmp_path, make_crops=False,
                             log=lambda *a: None)
    fs = res["findings"]
    assert [(f["precinct"], f["part"], f["file_value"], f["scan_value"], f["kind"], f["status"],
             f["confirmed_by_person"]) for f in fs] == [
        ("2", "early_voting", 21, 20, "wrong_number", "settled_against_file", False),
        ("2", "votes", 30, 30, "file_row_fails_own_total", "cannot_verify", False)]   # 4 + 21 + 6 is not 30
    sums = {s["name"]: s for s in fs[0]["sums"]}
    assert all(s["holds_with_scan"] and not s["holds_with_file"] for s in sums.values()) and len(sums) == 2
    new, diff, applied = audit.apply_corrections(raw, fs)
    assert len(applied) == 1
    assert new.decode().splitlines(True)[2] == "X,2,C,,,cand p1-b1,30,4,20,6\n"
    assert new.decode().splitlines(True)[:2] == raw.decode().splitlines(True)[:2]


class Geo:
    def crop(self, page, bid, target, dpi, dest):
        dest.parent.mkdir(parents=True, exist_ok=True)
        Image.new("L", (10, 10), 255).save(dest)
        return dest, (0, 0, 10, 10)

    def cell_box(self, page, bid, row, col):
        return None

    def total_box(self, page, bid, direction, key):
        return None

    def block_box(self, page, bid):
        return None


class Gw:
    """Answers a single-value re-read with what the ledger holds (the scan shows what the first read said)."""
    model = "claude-sonnet-4.6"
    calls = prompt_tokens = completion_tokens = 0
    cost = 0.0

    def __init__(self, led, says=None):
        self.cells = {(c["row_kind"], c["column"]): c["value"] for c in led.cells("x")}      # read here: sqlite is
        self.totals = {t["key"]: t["value"] for t in led.totals("x") if t["direction"] == "col"}   # per thread
        self.says, self.asked = says, []

    def ask_json(self, prompt, image=None, *, validate=None, model=None):
        self.asked.append((prompt, model))
        m = re.search(r"cell of precinct (\S+),\s*row (\w+)", prompt, re.S)
        if m:
            col, row = m.group(1).rstrip(","), m.group(2)
            v = self.cells[(row, col)]
        else:
            col = re.search(r"under precinct (\S+?)[ .]", prompt).group(1)
            v = self.totals[col]
        if self.says:
            v = self.says(row if m else "votes", col, v)
        ans = {"value": v}
        if validate:
            validate(ans)
        return ans


# ---- matching, groups, re-reads, the rest -------------------------------------------------------------------------

def test_labels_are_normalised():
    assert audit.candidate_key("Jill Stein/Rudolph Ware (GRN)") == audit.candidate_key("Jill Stein")
    assert audit.candidate_key("Jeff Rambin [REP]") == "jefframbin"
    assert audit.candidate_key("R.C. (Cutter) Clinton (REP)") == audit.candidate_key("R.C. (Cutter) Clinton")
    assert "countycommissioner3" in audit.contest_keys("County Commissioner, Precinct No. 3")
    assert audit.nk("Rail-road Commissioner") == audit.nk("Railroad Commissioner")


class FakeFileGw:
    def __init__(self, answer):
        self.answer, self.prompts = answer, []

    def ask_json(self, prompt, image=None, *, validate=None, model=None):
        self.prompts.append(prompt)
        validate(self.answer)
        return self.answer


def _blocks_and_file():
    led = Ledger()
    make_block(led, 1, "p1-b1")
    cells, totals = led.cells("x"), led.totals("x")
    blocks = audit.scan_blocks(cells, totals)
    rows = [{"office": "Senate", "district": "", "candidate": "cand p1-b1", "precinct": "1", "votes": "15"},
            {"office": "Senate", "district": "", "candidate": "cand p1-b1", "precinct": "2", "votes": "30"}]
    return blocks, audit.file_contests(rows)


def test_what_is_left_goes_to_the_model_once_and_is_checked_in_code():
    blocks, fcs = _blocks_and_file()
    gw = FakeFileGw({"contests": [[0, 0]], "candidates": [[0, 0]]})
    m = audit.match(blocks, fcs, gw)
    assert len(gw.prompts) == 1 and m.block_map == {"p1-b1": ("senate", "candp1b1")} and not m.unmatched_scan


def test_a_model_pairing_with_far_totals_is_rejected_and_listed():
    blocks, fcs = _blocks_and_file()
    for r in fcs["senate"].cands["candp1b1"].rows.values():
        r[1]["votes"] = "900"
    m = audit.match(blocks, fcs, FakeFileGw({"contests": [[0, 0]], "candidates": [[0, 0]]}))
    assert m.block_map == {} and m.rejected and m.unmatched_scan and m.unmatched_file


def test_a_model_pairing_that_is_not_one_to_one_is_rejected():
    blocks, fcs = _blocks_and_file()
    m = audit.match(blocks, fcs, FakeFileGw({"contests": [[0, 0], [0, 0]], "candidates": []}))
    assert any("one-to-one" in r["why"] for r in m.rejected)


def test_names_that_match_never_reach_the_model():
    blocks, fcs = _blocks_and_file()
    for b in blocks:
        b.contest = "Senate"
    m = audit.match(blocks, fcs, FakeFileGw({"contests": [], "candidates": []}))
    assert m.block_map and not m.model


def _row(prec, file, scan, bid="b"):
    blk = audit.Block(bid, 1, "C", "A")
    return audit.Row(blk, prec, dict(zip(audit.PARTS, file)) if file else None, 0, {}, dict(zip(audit.PARTS, scan)) if scan else None)


def kinds(rows):
    return sorted((s.row.precinct, s.part, s.kind) for s in audit.classify(rows))


def test_a_value_in_the_wrong_part_of_one_precinct_is_one_wrong_column_group():
    sl = audit.classify([_row("18", (1, 0, 0, 1), (1, 0, 1, 0))])
    assert {s.kind for s in sl} == {"wrong_column"} and len({s.group for s in sl}) == 1 and len(sl) == 2


def test_the_same_row_under_other_precincts_is_one_wrong_precinct_group():
    big = [_row("1", (320, 14, 168, 138), (181, 5, 102, 74)), _row("2", (181, 5, 102, 74), (311, 3, 195, 113)),
           _row("3", (311, 3, 195, 113), (320, 14, 168, 138))]
    sl = audit.classify(big)
    assert {s.kind for s in sl} == {"wrong_precinct"} and len({s.group for s in sl}) == 1


def test_small_coincidences_are_not_a_wrong_precinct_group():
    sl = audit.classify([_row("18", (1, 0, 0, 1), (1, 0, 1, 0)), _row("29", (0, 0, 0, 0), (1, 0, 0, 1))])
    assert "wrong_precinct" not in {s.kind for s in sl}


def test_missing_extra_and_own_total_kinds():
    sl = audit.classify([_row("1", None, (5, 1, 2, 2)), _row("2", (5, 1, 2, 2), None), _row("3", (9, 1, 2, 3), (6, 1, 2, 3))])
    assert kinds([_row("1", None, (5, 1, 2, 2)), _row("2", (5, 1, 2, 2), None)]) == [
        ("1", "votes", "missing_row"), ("2", "votes", "extra_row")]
    assert [(s.row.precinct, s.kind) for s in sl if s.row.precinct == "3"] == [("3", "file_row_fails_own_total")]


def test_a_reread_that_gives_the_files_value_with_the_sums_holding_corrects_the_ledger_and_leaves_no_finding(tmp_path):
    led = Ledger()
    make_block(led, 1, "p1-b1", wrong={("EARLY", "2"): 19})          # first read 19; the sums need 20
    rows = [["X", "1", "C", "", "", "cand p1-b1", "15", "2", "10", "3"],
            ["X", "2", "C", "", "", "cand p1-b1", "30", "4", "20", "6"]]
    gw = Gw(led, says=lambda row, col, v: 20)
    res = audit.audit_county("x", led, Geo(), gw, parse(file_text(rows)), run_dir=tmp_path, log=lambda *a: None)
    assert res["findings"] == [] and len(res["corrected_events"]) == 1
    assert next(c for c in led.cells("x") if c["column"] == "2" and c["row_kind"] == "EARLY")["value"] == 20
    assert gw.asked[0][1] == "claude-sonnet-4.6"


def test_no_module_but_the_verify_known_command_names_the_answer_key():
    from pathlib import Path
    for p in Path("crossfoot").rglob("*.py"):
        if p.name != "cli.py":
            assert "known_" not in p.read_text(), p


def test_policy_default_and_stored_answer(tmp_path):
    from crossfoot import policy
    store = tmp_path / "policy.json"
    d = policy.current(store)
    assert d["question_id"] == "document_disagrees_with_itself" and d["answer"] == "cells"
    assert d["answered_by"] == "default, not yet confirmed by a person"
    policy.set_answer("totals", store)
    assert policy.current(store)["answer"] == "totals" and "default" not in policy.current(store)["answered_by"]
    policy.write_for_run(tmp_path / "run", store)
    assert (tmp_path / "run" / "policy.json").exists()


def test_call_starts_are_spaced_when_three_threads_ask_at_once():
    import threading
    import time
    from types import SimpleNamespace as NS

    starts = []

    class Comp:
        def create(self, **kw):
            starts.append(time.monotonic())
            return NS(usage=NS(prompt_tokens=1, completion_tokens=1),
                      choices=[NS(message=NS(content='{"value": 1}'))])
    client = NS(chat=NS(completions=Comp()))
    gw = audit.AuditGateway(client, min_interval=0.2)
    ts = [threading.Thread(target=lambda: gw.ask_json("p")) for _ in range(3)]
    [t.start() for t in ts]
    [t.join() for t in ts]
    starts.sort()
    assert all(b - a >= 0.19 for a, b in zip(starts, starts[1:])), starts
    assert gw.calls == 3
    assert list(gw.calls_by_model().values())[0]["calls"] == 3


def test_open_cells_take_the_verdict_of_their_sum():
    from crossfoot import agent
    led = Ledger()
    make_block(led, 1, "p1-b1", wrong={("EARLY", "2"): 19})
    led.set_verdict("x", "row:1:p1-b1:EARLY", 1, "p1-b1", "cannot_verify", "could not be settled")
    agent.finalize_open(led, "x")
    st = {(c["row_kind"], c["column"]): c["status"] for c in led.cells("x")}
    assert st[("EARLY", "1")] == "cannot_verify" and st[("EARLY", "2")] == "cannot_verify"
