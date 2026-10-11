"""Score a claimed list of disagreements against the audit's findings, with the audit's own label matching.

A claim is {office, candidate, precinct, part, file_value, scan_value}. Labels are matched as the audit matches them
(`audit.nk` for offices and precincts, `audit.candidate_key` for candidates). Each claim goes in one group:

  settled             the audit has a finding at that value, reads the same scan value, and printed totals settle it
                      against the file (status settled_against_file)
  same_but_undecided  the audit reads the same scan value and no printed total decides (cannot_verify or
                      document_inconsistent)
  contradicted        the audit compared that row and its accepted value is the file's value: the claim is a misreading
  other_value         the audit has a finding there but reads neither the claim's scan value (a third value)
  not_matched         the label is not in the audit's findings or in the published file (or is ambiguous)

`missed_settled` lists the audit's settled findings that no claim names. Nothing here calls a model.
"""
from __future__ import annotations

import json
from pathlib import Path

from .audit import PARTS, candidate_key, nk
from .sources import _int

GROUPS = ("settled", "same_but_undecided", "contradicted", "other_value", "not_matched")


def _key(office, candidate, precinct, part) -> tuple:
    return (nk(office), candidate_key(candidate), nk(precinct), part)


def score(claims: list[dict], findings: list[dict], published: list[dict], not_compared=()) -> dict:
    by_slot: dict = {}
    for f in findings:
        by_slot.setdefault(_key(f["office"], f["candidate"], f["precinct"], f["part"]), []).append(f)
    skipped = {n if isinstance(n, int) else n.get("file_row") for n in not_compared}
    rows: dict = {}
    for i, r in enumerate(published):
        rows.setdefault(_key(r.get("office"), r.get("candidate"), r.get("precinct"), None)[:3], []).append((i, r))

    groups = {g: [] for g in GROUPS}
    named = set()
    for c in claims:
        key = _key(c["office"], c["candidate"], c["precinct"], c["part"])
        fs = by_slot.get(key, [])
        out = {"claim": c}
        if len(fs) > 1:
            out["why"] = "more than one finding has this label (different districts)"
            groups["not_matched"].append(out)
            continue
        if fs:
            f = fs[0]
            named.add(key)
            out["finding"] = {k: f[k] for k in ("id", "kind", "status", "file_value", "scan_value") if k in f}
            out["claim_file_value_is_published"] = c.get("file_value") == f["file_value"]
            if c.get("scan_value") != f["scan_value"]:
                out["why"] = f"the audit reads {f['scan_value']}, the claim {c.get('scan_value')}"
                groups["other_value"].append(out)
            elif f["status"] == "settled_against_file":
                groups["settled"].append(out)
            else:
                out["why"] = f["status"]
                groups["same_but_undecided"].append(out)
            continue
        hits = rows.get(key[:3], [])
        if len(hits) != 1:
            out["why"] = "no published row with this label" if not hits else "more than one published row has this label"
            groups["not_matched"].append(out)
            continue
        i, r = hits[0]
        if i in skipped:
            out["why"] = "the audit did not compare this row"
            groups["not_matched"].append(out)
            continue
        out["accepted_value"] = _int(r.get(c["part"])) if c["part"] in PARTS else None
        out["claim_file_value_is_published"] = c.get("file_value") == out["accepted_value"]
        out["why"] = "the audit compared this row and found no disagreement: its accepted value is the file's"
        groups["contradicted"].append(out)
    settled = [f for f in findings if f["status"] == "settled_against_file"]
    missed = [f for f in settled if _key(f["office"], f["candidate"], f["precinct"], f["part"]) not in named]
    return {"counts": {"claims": len(claims), **{g: len(groups[g]) for g in GROUPS}}, "groups": groups,
            "audit_findings": len(findings), "audit_settled": len(settled),
            "missed_settled": [{k: f.get(k) for k in ("id", "office", "candidate", "precinct", "part", "file_value",
                                                      "scan_value", "kind")} for f in missed]}


def audit_side(run_id: str, county: str, runs: Path = Path("runs")) -> dict:
    """What the audit's own run chain for one county spent, from the run files: a run's summary.json entry for the county
    when it has one, else its run.json. Follows `resumed_from` back to the run that read the scan."""
    chain, r = [], run_id
    while r:
        d = json.loads((runs / r / "run.json").read_text())
        s = runs / r / "summary.json"
        e = next((c for c in json.loads(s.read_text())["counties"] if c["county"] == county), None) if s.exists() else None
        chain.append({"run_id": r, "command": d.get("command"),
                      "model_calls": (e or d).get("model_calls"),
                      "metered_cost": (e or {}).get("metered_cost", d.get("metered_cost_estimate")),
                      "seconds": (e or {}).get("seconds", d.get("seconds")),
                      "models": sorted(((e or d).get("model_calls_by_model") or {}))})
        r = d.get("resumed_from")
    return {"runs": chain, "model_calls": sum(c["model_calls"] or 0 for c in chain),
            "metered_cost": round(sum(c["metered_cost"] or 0 for c in chain), 4),
            "seconds": round(sum(c["seconds"] or 0 for c in chain), 1),
            "models": sorted({m for c in chain for m in c["models"]})}
