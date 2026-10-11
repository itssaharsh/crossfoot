"""The one question the audit asks a person: what to do where the scan disagrees with itself.

question `document_disagrees_with_itself`: at some cell the scan's own printed totals do not agree with each other.
  cells   (the default) follow the cells as printed, and list the printed total as inconsistent
  totals  follow the printed totals

The default is marked as not confirmed. `crossfoot policy set --answer cells|totals` stores a person's answer in
runs/policy.json, and later runs read it. Neither answer lets the audit change a value: a correction is only ever
written where a printed total decides it (see audit.py), so the answer is recorded with the findings and the report.
"""
from __future__ import annotations

import json
from pathlib import Path

QUESTION_ID = "document_disagrees_with_itself"
ANSWERS = ("cells", "totals")
DEFAULT_BY = "default, not yet confirmed by a person"
PERSON_BY = "a person, with `crossfoot policy set`"
STORE = Path("runs") / "policy.json"
TEXT = {"cells": "follow the cells as printed and list the printed total as inconsistent",
        "totals": "follow the printed totals"}


def current(store: Path | str | None = None) -> dict:
    """The stored person's answer if there is one, else the default."""
    p = Path(store) if store else STORE
    try:
        d = json.loads(p.read_text())
        if d.get("question_id") == QUESTION_ID and d.get("answer") in ANSWERS:
            return {"question_id": QUESTION_ID, "answer": d["answer"], "answered_by": d.get("answered_by") or PERSON_BY}
    except (OSError, ValueError):
        pass
    return {"question_id": QUESTION_ID, "answer": "cells", "answered_by": DEFAULT_BY}


def set_answer(answer: str, store: Path | str | None = None) -> dict:
    if answer not in ANSWERS:
        raise ValueError(f"answer must be one of {ANSWERS}")
    p = Path(store) if store else STORE
    p.parent.mkdir(parents=True, exist_ok=True)
    d = {"question_id": QUESTION_ID, "answer": answer, "answered_by": PERSON_BY}
    p.write_text(json.dumps(d, indent=1))
    return d


def write_for_run(run_dir: Path | str, store: Path | str | None = None) -> dict:
    """Write runs/<run_id>/policy.json with the answer this run used."""
    d = {**current(store), "meaning": TEXT[current(store)["answer"]]}
    Path(run_dir).mkdir(parents=True, exist_ok=True)
    (Path(run_dir) / "policy.json").write_text(json.dumps(d, indent=1))
    return d
