"""The cost meter and the budget guard, with a fake client (no network, no model)."""
from types import SimpleNamespace

import pytest

from crossfoot.model import BudgetExceeded, Gateway, parse_json


class FakeClient:
    def __init__(self, answers, prompt_tokens=1000, completion_tokens=100):
        self.answers = list(answers)
        self.calls = 0
        self.usage = (prompt_tokens, completion_tokens)
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    def _create(self, **kw):
        self.calls += 1
        msg = SimpleNamespace(content=self.answers.pop(0))
        return SimpleNamespace(choices=[SimpleNamespace(message=msg)],
                               usage=SimpleNamespace(prompt_tokens=self.usage[0], completion_tokens=self.usage[1]))


def gw(client, **kw):
    return Gateway(client=client, sleep=lambda s: None, min_interval=0, **kw)


def test_meter_adds_up_tokens_and_cost():
    c = FakeClient(['{"a": 1}', '{"a": 2}'])
    g = gw(c, budget=2.0)
    assert g.ask_json("p") == {"a": 1}
    g.ask_json("p")
    assert g.calls == 2 and g.prompt_tokens == 2000 and g.completion_tokens == 200
    assert g.cost > 0


def test_guard_refuses_a_call_past_the_limit_without_calling():
    c = FakeClient(['{"a": 1}'] * 5)
    g = gw(c, budget=0.0)
    with pytest.raises(BudgetExceeded) as e:
        g.ask_json("p")
    assert c.calls == 0 and "budget" in str(e.value).lower()


def test_guard_stops_after_the_limit_is_reached():
    c = FakeClient(['{"a": 1}'] * 50, prompt_tokens=100_000, completion_tokens=10_000)
    g = gw(c, budget=0.05)
    with pytest.raises(BudgetExceeded):
        for _ in range(50):
            g.ask_json("p")
    assert 0 < c.calls < 50


def test_bad_json_gets_one_repair_then_fails():
    c = FakeClient(["not json", '{"ok": true}'])
    assert gw(c).ask_json("p") == {"ok": True}
    assert c.calls == 2
    c = FakeClient(["nope", "still nope", '{"x": 1}'])
    with pytest.raises(ValueError):
        gw(c).ask_json("p")
    assert c.calls == 2


def test_validator_failure_asks_for_one_repair():
    def need_three(d):
        if len(d["v"]) != 3:
            raise ValueError("need 3 values")
    c = FakeClient(['{"v": [1]}', '{"v": [1,2,3]}'])
    assert gw(c).ask_json("p", validate=need_three) == {"v": [1, 2, 3]}
    assert c.calls == 2


def test_parse_json_strips_fences():
    assert parse_json('```json\n{"a": [1, 2]}\n```') == {"a": [1, 2]}
