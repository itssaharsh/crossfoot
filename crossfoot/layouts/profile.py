"""Which model reads a county, decided by measurement.

A sample (the candidate blocks of page 1 until at least SAMPLE_ROW_SUMS row sums exist) is read with the cheap model.
If more than a tenth of the sample's row sums fail, the county is read with the stronger model and the sample's values
are thrown away; otherwise the cheap model keeps the county and so does the sample. The figures of the decision are
written as an event and a span and printed as one line (see `matrix.read_county`).
"""
from __future__ import annotations

SAMPLE_MODEL = "claude-haiku"
STRONG_MODEL = "claude-sonnet-4.6"
SAMPLE_ROW_SUMS = 20
FAIL_LINE = 0.10        # more than this share of the sample's row sums failing switches the reader


def decide(failing: int, total: int) -> dict:
    """The decision from the sample's figures. `total` is the number of row sums in the sample."""
    rate = failing / total if total else 1.0
    switch = total == 0 or failing * 10 > total
    return {"row_sums": total, "failing": failing, "rate": round(rate, 4), "line": FAIL_LINE,
            "sampled_with": SAMPLE_MODEL, "reader": STRONG_MODEL if switch else SAMPLE_MODEL,
            "kept_sample": not switch}


def sentence(d: dict) -> str:
    if d["kept_sample"]:
        return (f"reader: {d['reader']} (sample: {d['failing']} of {d['row_sums']} row sums fail, "
                f"{d['rate']:.1%}, not over {FAIL_LINE:.0%}; the sample's values are kept)")
    return (f"reader: {d['reader']} (sample: {d['failing']} of {d['row_sums']} row sums fail, "
            f"{d['rate']:.1%}, over {FAIL_LINE:.0%}; the sample was read with {d['sampled_with']} and is discarded)")


# ---- which layout a county uses, decided from its first page ----------------------------------------------------------

LAYOUTS = ("matrix", "report", "no_printed_totals")
REJECT_SHARE = 1 / 3        # more than this share of the first page's row sums failing rejects the decision
REPORT_COLUMNS = ("total", "absentee", "early", "election_day")

LAYOUT_PROMPT = """TASK: layout.
This image is the first page of a scanned election results document. Decide which layout it uses:
- "matrix": a landscape canvass sheet with the precincts as columns, a TOTAL column, and three ruled rows (EARLY,
  ABSENTEE, PRECINCT) for each candidate;
- "report": a report with one precinct per section, each candidate on one row with a total and a breakdown into
  absentee, early voting and election day (numbers in columns, a precinct name at the top of the section);
- "no_printed_totals": each candidate has only a vote count and a percentage; there is no breakdown and no printed total
  of a contest, so nothing on the page can be added up and checked against anything printed.
For "report", also give the order of the number columns left to right, using these names: "total", "absentee", "early",
"election_day" (ignore percentage columns). For the other two answers, columns is an empty list.
Answer with strict JSON only, no prose: {"layout": "matrix" | "report" | "no_printed_totals", "columns": [...]}"""


def layout_validator(d):
    if not isinstance(d, dict) or d.get("layout") not in LAYOUTS:
        raise ValueError(f'"layout" must be one of {LAYOUTS}')
    cols = d.get("columns")
    if not isinstance(cols, list):
        raise ValueError('"columns" must be a list')
    if d["layout"] == "report" and (sorted(cols) != sorted(REPORT_COLUMNS)):
        raise ValueError(f'for "report", "columns" must list each of {REPORT_COLUMNS} once, in printed order')


def decide_layout(gw, png) -> dict:
    """One call on the first page with the cheap model. Returns {layout, columns}."""
    d = gw.ask_json(LAYOUT_PROMPT, png, validate=layout_validator, model=SAMPLE_MODEL)
    return {"layout": d["layout"], "columns": list(d["columns"])}


def rejected(failing: int, total: int) -> bool:
    """True when the decision must be thrown away: more than a third of the first page's row sums fail (or there are
    no row sums to test it with)."""
    return total == 0 or failing * 3 > total
