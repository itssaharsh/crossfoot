"""`crossfoot audit --all`: order, resume, budget stop, one county failing, the summary files. A fake model throughout."""
import json
import threading
import time
from types import SimpleNamespace

import pytest

from crossfoot import allrun, audit
from crossfoot.ledger import Ledger
from crossfoot.model import BudgetExceeded
from crossfoot.layouts import report


class FakeClient:
    def __init__(self, tokens=(100_000, 10_000), delay=0.0):
        self.tokens, self.delay, self.calls = tokens, delay, 0
        self.live = self.peak = 0
        self.starts = []
        self._l = threading.Lock()
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    def _create(self, **kw):
        with self._l:
            self.calls += 1
            self.live += 1
            self.peak = max(self.peak, self.live)
            self.starts.append(time.monotonic())
        time.sleep(self.delay)
        with self._l:
            self.live -= 1
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content='{"a": 1}'))],
                               usage=SimpleNamespace(prompt_tokens=self.tokens[0], completion_tokens=self.tokens[1]))


def make_gw(budget=9.0, **kw):
    return audit.AuditGateway(client=FakeClient(**kw), budget=budget, min_interval=0)


def result(**kw):
    d = {"outcome": "audited", "layout": "report", "pages": 3, "cells_read": 10, "sums_first_read": {"passing": 8, "failing": 2},
         "cells_reread": 2, "cells_accepted": 10, "cannot_verify": 1, "findings_by_kind": {"wrong_number": 1},
         "findings_by_status": {"cannot_verify": 1}, "second_sum_exists": False,
         "sums_check": {"in_all": 8, "holding_with_published": 7, "holding_with_corrected": 8}}
    d.update(kw)
    return d


def run(tmp_path, fn, gw=None, counties=None, resume=False, log=None, led=None):
    gw = gw or make_gw()
    led = led or Ledger(tmp_path / "ledger.sqlite")
    return allrun.run_all(tmp_path, "RID", gw, led, fn, counties=counties or allrun.ORDER, resume=resume,
                          log=log or (lambda *a: None))


def test_fixed_order_one_line_per_start_and_end_and_no_input(tmp_path, monkeypatch):
    monkeypatch.setattr("builtins.input", lambda *a: pytest.fail("asked for input"))
    seen, lines = [], []
    run(tmp_path, lambda c, ctx: seen.append(c) or result(), log=lines.append)
    assert seen == ["panola", "san_saba", "cottle", "jones", "lynn", "scurry", "foard", "limestone"]
    starts = [l for l in lines if " start" in l]
    ends = [l for l in lines if " end" in l]
    assert len(starts) == len(ends) == 8
    assert starts[0].startswith("panola") and ends[-1].startswith("limestone")


def test_summary_files_and_fields(tmp_path):
    def fn(c, ctx):
        ctx.gw.ask_json("p", model="claude-haiku")
        return result()
    s = run(tmp_path, fn, counties=("panola", "san_saba"))
    d = json.loads((tmp_path / "summary.json").read_text())
    assert d == json.loads(json.dumps(s))
    row = d["counties"][0]
    for k in ("county", "status", "layout", "pages", "cells_read", "sums_first_read", "cells_reread", "cells_accepted",
              "cannot_verify", "findings_by_kind", "findings_by_status", "second_sum_exists", "sums_check", "model_calls",
              "model_calls_by_model", "prompt_tokens", "completion_tokens", "metered_cost", "seconds"):
        assert k in row, k
    assert row["model_calls"] == 1 and row["model_calls_by_model"]["claude-haiku"]["calls"] == 1
    assert d["totals"]["model_calls"] == 2 and d["totals"]["sums_check"]["in_all"] == 16
    md = (tmp_path / "summary.md").read_text()
    assert "| panola " in md and "| san_saba " in md


def test_one_county_failing_is_recorded_and_the_run_goes_on(tmp_path):
    def fn(c, ctx):
        if c == "san_saba":
            raise RuntimeError("download failed: boom")
        return result()
    s = run(tmp_path, fn)
    rows = {r["county"]: r for r in s["counties"]}
    assert rows["san_saba"]["status"] == "failed" and "boom" in rows["san_saba"]["reason"]
    assert all(rows[c]["status"] == "audited" for c in rows if c != "san_saba")
    assert "san_saba" in (tmp_path / "summary.md").read_text() and "boom" in (tmp_path / "summary.md").read_text()


def test_budget_stop_writes_what_it_has_and_lists_counties_not_reached(tmp_path):
    gw = make_gw(budget=0.30)          # a call here costs about $0.165

    def fn(c, ctx):
        for _ in range(3):
            ctx.gw.ask_json("p")
        return result()
    called = []
    s = run(tmp_path, lambda c, ctx: called.append(c) or fn(c, ctx), gw=gw)
    assert called == ["panola"]
    rows = {r["county"]: r for r in s["counties"]}
    assert rows["panola"]["status"] == "stopped" and "budget" in rows["panola"]["reason"].lower()
    assert s["not_reached"] == list(allrun.ORDER[1:])
    assert all(rows[c]["status"] == "not_reached" for c in allrun.ORDER[1:])
    assert (tmp_path / "summary.json").exists() and "not reached" in (tmp_path / "summary.md").read_text().lower()


def test_no_call_is_made_once_the_budget_is_reached_between_counties(tmp_path):
    gw = make_gw(budget=0.10)
    gw.cost = 0.10
    called = []
    s = run(tmp_path, lambda c, ctx: called.append(c) or result(), gw=gw)
    assert called == [] and s["not_reached"] == list(allrun.ORDER)


def test_resume_skips_closed_counties_and_retries_the_rest(tmp_path):
    calls = []

    def first(c, ctx):
        calls.append(c)
        if c == "cottle":
            raise RuntimeError("layout not decided")
        if c == "jones":
            raise BudgetExceeded("run budget reached")
        return result()
    s1 = run(tmp_path, first, gw=make_gw())
    assert "cottle" in [r["county"] for r in s1["counties"] if r["status"] == "failed"]
    calls.clear()
    s2 = run(tmp_path, lambda c, ctx: calls.append(c) or result(), resume=True)
    assert calls == ["cottle", "jones", "lynn", "scurry", "foard", "limestone"]
    assert all(r["status"] == "audited" for r in s2["counties"])
    assert [r["county"] for r in s2["counties"]] == list(allrun.ORDER)


def test_resume_counts_what_was_spent_before_against_the_budget(tmp_path):
    def first(c, ctx):
        ctx.gw.ask_json("p")
        return result()
    run(tmp_path, first, counties=("panola",), gw=make_gw())
    gw = make_gw(budget=0.17)           # the first run spent about $0.165
    s = run(tmp_path, lambda c, ctx: (ctx.gw.ask_json("p"), result())[1], gw=gw, resume=True,
            counties=("panola", "san_saba"))
    assert s["counties"][0]["status"] == "audited"       # kept, not run again
    assert s["counties"][1]["status"] in ("not_reached", "stopped")


def test_unchecked_county_is_final_and_listed_as_skipped(tmp_path):
    s = run(tmp_path, lambda c, ctx: result(outcome="unchecked", note="nothing can be cross-checked"), counties=("limestone",))
    assert s["counties"][0]["status"] == "unchecked"
    assert s["skipped"][0]["county"] == "limestone"
    assert "cross-checked" in (tmp_path / "summary.md").read_text()


def test_each_county_is_a_workflow_span_named_for_it(tmp_path, monkeypatch):
    spans = []
    import contextlib
    from crossfoot import tracing

    @contextlib.contextmanager
    def fake(name, kind="TOOL", **attrs):
        spans.append((name, kind, attrs))
        yield tracing._NoSpan()
    monkeypatch.setattr(tracing, "trace", fake)
    run(tmp_path, lambda c, ctx: result(), counties=("panola", "cottle"))
    assert [(n, k) for n, k, _ in spans] == [("panola", "WORKFLOW"), ("cottle", "WORKFLOW")]
    assert all(a.get("run") == "RID" for _, _, a in spans)


def test_gateway_keeps_three_in_flight_and_starts_apart():
    gw = audit.AuditGateway(client=FakeClient(delay=0.15), budget=9.0, min_interval=0.05)
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(3) as ex:
        list(ex.map(lambda i: gw.ask_json("p"), range(6)))
    c = gw.client.chat.completions.inner.create.__self__
    assert gw.calls == 6 and gw.prompt_tokens == 600_000
    gaps = [b - a for a, b in zip(c.starts, c.starts[1:])]
    assert min(gaps) >= 0.045 and c.peak <= 3


# ---- the report read overlaps page calls but writes the ledger from one thread ------------------------------------

def test_report_close_makes_no_call_for_accepted_cells_and_a_resume_none_either():
    led = Ledger()
    for col, v in (("total", 10), ("absentee", 1), ("early", 4), ("election_day", 5)):
        led.put_cell("x", 1, "p|1", "Jane Roe", col, v, contest="Mayor", candidate="Jane Roe", model="claude-haiku")

    class NoCalls:
        calls, prompt_tokens, completion_tokens, cost, model = 0, 0, 0, 0.0, "claude-haiku"

        def ask_json(self, *a, **k):
            raise AssertionError("a model call was made")
    for _ in range(2):                  # the run, then the resume
        s = report.close_county("x", NoCalls(), led, None, reader="claude-haiku")
        assert s["model_calls"] == 0 and s["cells_accepted"] == 4


def test_a_printed_total_row_with_a_colon_is_still_the_contest_total():
    """Foard prints "Cast Votes:" and "Over Votes:"; the colon must not hide the row from the contest sum."""
    from crossfoot import checks
    led = Ledger()
    ans = {"precinct": "101", "contests": [{"name": "US Senator", "continued": False, "rows": [
        {"label": "Ted Cruz", "total": 92, "absentee": 0, "early": 83, "election_day": 9, "y": 100},
        {"label": "Colin Allred", "total": 27, "absentee": 1, "early": 20, "election_day": 6, "y": 120},
        {"label": "Cast Votes:", "total": 119, "absentee": 1, "early": 103, "election_day": 15, "y": 140},
        {"label": "Over Votes:", "total": 0, "absentee": 0, "early": 0, "election_day": 0, "y": 160}]}]}
    report.store_page(led, "x", 1, ans, report.State(), model="claude-haiku", size=(1000, 1000), x_right=900)
    cs = checks.report_contest_checks(led.cells("x"))
    assert len(cs) == 4 and all(c.ok for c in cs)
    assert {c["row_kind"] for c in led.cells("x")} == {"Ted Cruz", "Colin Allred", "Cast Votes", "Over Votes"}
