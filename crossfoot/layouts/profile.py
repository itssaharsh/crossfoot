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
