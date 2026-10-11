"""The reader is chosen by measurement: a sample of page 1 with claude-haiku; over a tenth of its row sums failing
means claude-sonnet-4.6 reads the county. Fake answers on both sides of the line; no network."""
import json
from types import SimpleNamespace

from crossfoot.layouts import matrix, profile
from crossfoot.ledger import Ledger
from crossfoot.model import Gateway
from tests.test_matrix_read import header, page


class Recording:
    """A fake gateway client: answers come from `answers_for(model)`; the models asked are recorded."""
    def __init__(self, answers_for):
        self.answers_for, self.models = answers_for, []
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    def _create(self, **kw):
        self.models.append(kw["model"])
        msg = SimpleNamespace(content=self.answers_for(kw["model"], len(self.models)))
        return SimpleNamespace(choices=[SimpleNamespace(message=msg)],
                               usage=SimpleNamespace(prompt_tokens=100, completion_tokens=10))


def blk(e, a, p, off=0):
    """A one-precinct block; `off` is added to the printed EARLY total, so its row sum fails when off != 0."""
    row = lambda v, t: {"values": [v], "total": t}
    return json.dumps({"contest": "C", "candidate": "Cand",
                       "rows": {"EARLY": row(e, e + off), "ABSENTEE": row(a, a), "PRECINCT": row(p, p)},
                       "col_totals": [e + a + p], "grand": e + a + p + off})


def run(tmp_path, answers_for, model="auto"):
    page(tmp_path)
    c = Recording(answers_for)
    led = Ledger()
    lines = []
    gw = Gateway(client=c, sleep=lambda s: None, min_interval=0)
    s = matrix.read_county("x", gw, led, pages=[1], data_root=tmp_path, run_id="", log=lines.append, model=model)
    return s, c, led, lines


def test_a_sample_that_holds_keeps_haiku_and_its_values(tmp_path):
    s, c, led, lines = run(tmp_path, lambda m, n: header() if n == 1 else blk(4, 5, 6))
    assert c.models == [profile.SAMPLE_MODEL] * 3               # one call per block, none repeated
    assert s["reader"] == "claude-haiku" and s["sample"]["failing"] == 0 and s["sample"]["kept_sample"] is True
    assert s["sample"]["row_sums"] == 10 and s["sample"]["rate"] == 0.0
    ev = [json.loads(e["payload_json"]) for e in led.events("x") if e["kind"] == "choose_reader"]
    assert len(ev) == 1 and ev[0]["reader"] == "claude-haiku" and ev[0]["row_sums"] == 10
    assert any(l.startswith("reader: claude-haiku") and "0 of 10" in l for l in lines) and len(lines) == 1
    assert len(led.cells("x")) == 10


def test_a_sample_over_a_tenth_failing_switches_to_sonnet_and_reads_again(tmp_path):
    bad = lambda m, n: header() if n % 3 == 1 else blk(4, 5, 6, off=1 if m == "claude-haiku" else 0)
    s, c, led, lines = run(tmp_path, bad)
    assert c.models == ["claude-haiku"] * 3 + ["claude-sonnet-4.6"] * 3
    assert s["reader"] == "claude-sonnet-4.6" and s["sample"]["failing"] == 2 and s["sample"]["row_sums"] == 10
    assert s["sample"]["kept_sample"] is False
    assert s["row_sums_fail"] == 0 and {c_["model"] for c_ in led.cells("x")} == {"claude-sonnet-4.6"}   # the sample is gone
    assert any("over 10%" in l for l in lines)
    assert s["model_calls"] == 6


def test_exactly_a_tenth_failing_keeps_haiku(tmp_path):
    # 10 row sums, one failing: one tenth is not more than a tenth
    answers = lambda m, n: header() if n == 1 else blk(4, 5, 6, off=1 if n == 2 else 0)
    s, c, led, lines = run(tmp_path, answers)
    assert s["sample"]["failing"] == 1 and s["reader"] == "claude-haiku"


def test_decide_is_on_the_line():
    assert profile.decide(2, 20)["reader"] == "claude-haiku"
    assert profile.decide(3, 20)["reader"] == "claude-sonnet-4.6"
    assert profile.decide(0, 0)["reader"] == "claude-sonnet-4.6"


def test_a_named_model_skips_the_sample_and_says_so(tmp_path):
    s, c, led, lines = run(tmp_path, lambda m, n: header() if n == 1 else blk(4, 5, 6), model="claude-sonnet-4.6")
    assert c.models == ["claude-sonnet-4.6"] * 3 and s["reader"] == "claude-sonnet-4.6"
    assert s["sample"]["skipped"] is True and "no sample" in lines[0]
