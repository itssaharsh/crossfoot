"""A summary keeps, per county, what the run that read it cost and what the later audits added; the totals do the same."""
import json

from crossfoot import allrun


def row(county, calls, cost, secs, **kw):
    return {"county": county, "status": "audited", "layout": "matrix", "model_calls": calls, "metered_cost": cost,
            "seconds": secs, "model_calls_by_model": {"m": {"calls": calls, "prompt_tokens": 0, "completion_tokens": 0,
                                                           "cost": cost}}, **kw}


def write(root, run_id, rows, **kw):
    d = root / run_id
    d.mkdir(parents=True)
    t = allrun.totals(rows)
    (d / "summary.json").write_text(json.dumps({"run_id": run_id, "budget": 9.0, "counties": rows, "totals": t,
                                                "not_reached": [], "skipped": [], **kw}))


def test_the_reading_run_and_the_audits_made_again_are_kept_apart(tmp_path):
    write(tmp_path, "r0", [row("a", 100, 1.0, 100.0), row("b", 10, 0.5, 20.0)])
    write(tmp_path, "r1", [row("a", 4, 0.01, 5.0, from_run="x1"), row("b", 10, 0.5, 20.0, from_run="r0")],
          made_from={"base": "r0", "use": {"a": "x1"}})
    write(tmp_path, "r2", [row("a", 1, 0.002, 2.0, from_run="x2"), row("b", 10, 0.5, 20.0, from_run="r0")],
          made_from={"base": "r1", "use": {"a": "x2"}})
    s = allrun.combine(tmp_path / "r3", "r2", {}, command="t")
    a, b = s["counties"]
    assert a["read_run"]["run_id"] == "r0" and a["read_run"]["model_calls"] == 100 and a["read_run"]["seconds"] == 100.0
    assert a["audit_again"]["run_ids"] == ["x1", "x2"] and a["audit_again"]["model_calls"] == 5
    assert a["audit_again"]["metered_cost"] == 0.012 and a["audit_again"]["seconds"] == 7.0
    assert a["model_calls"] == 105 and a["seconds"] == 107.0           # the row's own figures add both
    assert b["read_run"]["model_calls"] == 10 and "audit_again" not in b
    t = s["totals"]
    assert t["read_run"]["model_calls"] == 110 and t["audit_again"]["model_calls"] == 5
    md = (tmp_path / "r3" / "summary.md").read_text()
    assert md.index("read: calls") < md.index("audit again: calls")


def test_a_second_summary_of_a_summary_adds_nothing_twice(tmp_path):
    write(tmp_path, "r0", [row("a", 100, 1.0, 100.0)])
    write(tmp_path, "r1", [row("a", 4, 0.01, 5.0, from_run="x1")], made_from={"base": "r0", "use": {"a": "x1"}})
    s1 = allrun.combine(tmp_path / "r2", "r1", {}, command="t")
    s2 = allrun.combine(tmp_path / "r3", "r2", {}, command="t")
    assert s1["counties"][0]["audit_again"] == s2["counties"][0]["audit_again"]
    assert s2["counties"][0]["model_calls"] == 104
