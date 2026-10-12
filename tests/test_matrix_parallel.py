"""The matrix read with several model calls in flight: same ledger and events as one at a time. Fake model, no network."""
import json
import random
import threading
import time

import pytest
from PIL import Image, ImageDraw

from crossfoot.layouts import matrix
from crossfoot.ledger import Ledger
from crossfoot.model import BudgetExceeded, Gateway
from tests.test_budget import FakeClient
from tests.test_matrix_read import block, header
from tests.test_segment import ruled

N_BLOCKS = 8        # the header and seven more


def page(tmp_path):
    d = tmp_path / "pages" / "x"
    d.mkdir(parents=True)
    im = Image.new("L", (1000, 60 + 160 * N_BLOCKS), 255)
    dr = ImageDraw.Draw(im)
    for k in range(N_BLOCKS):
        ruled(dr, 60 + 160 * k, ncols=7, x0=100)
    im.save(d / "p01-200.png")


class FakeGw:
    """Answers by block (the crop's file name), after a random pause so the answers finish out of order."""
    def __init__(self, answers, fail=(), budget_at=None):
        self.model, self.answers, self.fail, self.budget_at = "fake", answers, set(fail), budget_at
        self.calls, self.prompt_tokens, self.completion_tokens, self.cost = 0, 0, 0, 0.0
        self.started, self.late, self.raised = [], [], False
        self.lock, self.rng = threading.Lock(), random.Random(1)

    def ask_json(self, prompt, image=None, *, validate=None, model=None):
        bid = image.stem
        with self.lock:
            self.started.append(bid)
            self.calls += 1
            pause = self.rng.random() * 0.03
            if self.raised:
                self.late.append(bid)       # a call that started after the budget error was raised
        time.sleep(pause)
        if bid == self.budget_at:
            self.raised = True
            raise BudgetExceeded("run budget reached")
        if bid in self.fail:
            raise ValueError("bad answer twice")
        d = json.loads(self.answers[bid])
        if validate:
            validate(d)
        return d


def answers():
    out = {"p1-b0": header()}
    for k in range(1, N_BLOCKS):
        out[f"p1-b{k}"] = block("Pres" if k in (1, 5) else (None if k != 3 else "Gov"), k, k + 1, k + 2,
                                7 if k == 4 else 3 * k + 3)
    return out


def read(tmp_path, workers, **kw):
    led = Ledger()
    gw = FakeGw(answers(), **kw)
    s = matrix.read_county("x", gw, led, pages=[1], data_root=tmp_path, run_id="", model="m", workers=workers)
    return s, led, gw


def events(led):
    return [(e["kind"], e["payload_json"]) for e in led.events("x")]


def rows(led):
    cells = [{k: v for k, v in c.items() if k not in ("ts", "created", "updated")} for c in led.cells("x")]
    return cells, led.totals("x")


def test_workers_1_and_4_give_the_same_ledger_and_events(tmp_path):
    page(tmp_path)
    s1, l1, _ = read(tmp_path, 1)
    s4, l4, g4 = read(tmp_path, 4)
    assert rows(l1) == rows(l4) and len(rows(l1)[0]) > 20
    assert events(l1) == events(l4)
    assert [b["block"] for b in s1["blocks"]] == [b["block"] for b in s4["blocks"]]
    assert {k: s1[k] for k in ("cells_read", "row_sums_pass", "grand_sums_fail", "blocks_failed")} == \
           {k: s4[k] for k in ("cells_read", "row_sums_pass", "grand_sums_fail", "blocks_failed")}
    assert g4.calls == N_BLOCKS


def test_the_contest_name_is_carried_the_same(tmp_path):
    page(tmp_path)
    contests = []
    for w in (1, 4):
        _, led, _ = read(tmp_path, w)
        contests.append({c["block_id"]: c["contest"] for c in led.cells("x")})
    assert contests[0] == contests[1]
    assert contests[0]["p1-b2"] == "Pres" and contests[0]["p1-b3"] == "Gov" and contests[0]["p1-b4"] == "Gov"
    assert contests[0]["p1-b6"] == "Pres"


@pytest.mark.parametrize("w", [1, 4])
def test_a_failing_block_is_marked_failed_and_the_rest_is_read(tmp_path, w):
    page(tmp_path)
    s, led, _ = read(tmp_path, w, fail={"p1-b2"})
    assert s["blocks_failed"] == 1 and s["stopped"] is None
    assert {c["block_id"] for c in led.cells("x") if c["status"] == "failed"} == {"p1-b2"}
    assert {b["block"] for b in s["blocks"] if b["status"] == "read"} == {f"p1-b{k}" for k in (0, 1, 3, 4, 5, 6, 7)}
    assert [e["kind"] for e in led.events("x")].count("block_failed") == 1


def test_failure_is_the_same_with_one_and_four(tmp_path):
    page(tmp_path)
    a, b = read(tmp_path, 1, fail={"p1-b2", "p1-b5"}), read(tmp_path, 4, fail={"p1-b2", "p1-b5"})
    assert rows(a[1]) == rows(b[1]) and events(a[1]) == events(b[1])


@pytest.mark.parametrize("w", [1, 4])
def test_no_call_starts_after_the_budget_error(tmp_path, w):
    page(tmp_path)
    s, led, gw = read(tmp_path, w, budget_at="p1-b3")
    assert s["stopped"] and "budget" in s["stopped"]
    assert "p1-b3" in gw.started and gw.late == []
    assert not any(c["block_id"] == "p1-b3" for c in led.cells("x"))
    assert {b["block"] for b in s["blocks"]} == {"p1-b0", "p1-b1", "p1-b2"}


def test_the_real_gateway_guard_stops_a_parallel_read(tmp_path):
    page(tmp_path)
    c = FakeClient([header()] + [block("P", 1, 1, 1, 3)] * 7, prompt_tokens=100_000, completion_tokens=10_000)
    gw = Gateway(client=c, sleep=lambda s_: None, min_interval=0, budget=0.2)
    s = matrix.read_county("x", gw, Ledger(), pages=[1], data_root=tmp_path, run_id="", model="m", workers=4)
    assert s["stopped"] and c.calls < 8
    assert gw.calls == c.calls


def test_the_gateway_spaces_calls_across_threads():
    starts, lock = [], threading.Lock()

    class C(FakeClient):
        def _create(self, **kw):
            with lock:
                starts.append(time.monotonic())
            return super()._create(**kw)
    c = C(['{"a": 1}'] * 6)
    gw = Gateway(client=c, min_interval=0.05, budget=5.0)
    ts = [threading.Thread(target=gw.ask_json, args=("p",)) for _ in range(6)]
    [t.start() for t in ts]
    [t.join() for t in ts]
    starts.sort()
    assert all(b - a >= 0.04 for a, b in zip(starts, starts[1:]))
