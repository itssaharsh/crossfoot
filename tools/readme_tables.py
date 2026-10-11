"""Write the README's tables from the final run's files, so no figure in them is typed by hand.

    python3 tools/readme_tables.py            rewrite the blocks between <!-- name:start --> and <!-- name:end --> in README.md
    python3 tools/readme_tables.py --check    exit 1 if README.md differs from what the files give

Reads runs/<run>/summary.json (the newest run with one, or --run) and, for the picture, the findings.json and crop of the
run that the summary names for Panola."""
import argparse, json, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FULL_RUN = "20261011-120008"          # the one full run of Panola from nothing, named in the README
PICTURE = ("panola", "f005")          # a settled finding whose crop shows the cell and the row sum


def latest_summary() -> str:
    ids = sorted(p.parent.name for p in (ROOT / "runs").glob("*/summary.json"))
    return ids[-1]


def n(v) -> str:
    return f"{v:,}"


def findings_table(s: dict) -> str:
    head = ("| County | Layout | Published rows compared | Disagreements | Settled by the printed totals | Cannot be verified "
            "| Printed sums in all | Holding with the published file | Holding with the corrected file |\n"
            "|---|---|---|---|---|---|---|---|---|")
    rows = []
    for c in s["counties"]:
        name = c["county"].replace("_", " ").title()
        if c["status"] != "audited":
            rows.append(f"| {name} | {c['layout']} | not checked: nothing printed on the scan can be summed | | | | | | |")
            continue
        sc, st = c["sums_check"], c["findings_by_status"]
        rows.append(f"| {name} | {c['layout']} | {n(c['rows_compared'])} of {n(c['rows_published'])} | {n(sum(st.values()))} "
                    f"| {n(st.get('settled_against_file', 0))} | {n(st.get('cannot_verify', 0))} | {n(sc['in_all'])} "
                    f"| {n(sc['holding_with_published'])} | {n(sc['holding_with_corrected'])} |")
    t = s["totals"]
    st, sc = t["findings_by_status"], t["sums_check"]
    rows.append(f"| **All** | | {n(t['rows_compared'])} of {n(t['rows_published'])} | {n(sum(st.values()))} "
                f"| {n(st.get('settled_against_file', 0))} | {n(st.get('cannot_verify', 0))} | {n(sc['in_all'])} "
                f"| {n(sc['holding_with_published'])} | {n(sc['holding_with_corrected'])} |")
    return "\n".join([head, *rows])


def cost_table(s: dict) -> str:
    head = "| County | Pages | Model calls | Metered cost (estimate) | Seconds |\n|---|---|---|---|---|"
    rows = [f"| {c['county'].replace('_', ' ').title()} | {c['pages']} | {c['model_calls']} | ${c['metered_cost']:.4f} | {c['seconds']} |"
            for c in s["counties"]]
    t = s["totals"]
    rows.append(f"| **All** | {sum(c['pages'] for c in s['counties'])} | {t['model_calls']} | ${t['metered_cost']:.4f} | {t['seconds']} |")
    full = json.loads((ROOT / "runs" / FULL_RUN / "run.json").read_text())
    note = (f"These are the figures of the audit that `summary.json` lists for each county; a county audited again from an "
            f"earlier run's ledger counts the new calls only, not the reading that was paid for in that earlier run. The one "
            f"full run of Panola from nothing, [`runs/{FULL_RUN}/run.json`](runs/{FULL_RUN}/run.json), took "
            f"{full['seconds']} seconds, {full['model_calls']} model calls and ${full['metered_cost_estimate']:.2f} (metered estimate).")
    return "\n".join([head, *rows, "", note])


def picture(s: dict) -> str:
    county, fid = PICTURE
    run = next(c["from_run"] for c in s["counties"] if c["county"] == county)
    base = f"runs/{run}/{county}"
    doc = json.loads((ROOT / base / "findings.json").read_text())
    f = next(x for x in doc["findings"] if x["id"] == fid)
    row = next(x for x in f["sums"] if x["kind"] == "row")
    part = f["part"].replace("_", " ")
    return (f"![crop of the scan: {f['candidate']}, precinct {f['precinct']}, the cell outlined]({base}/{f['crop']})\n\n"
            f"*Panola County, page {f['page']}, {f['candidate']}, precinct {f['precinct']}, {part}. The published file has "
            f"{f['file_value']}; the scan has {f['scan_value']}. The row's printed total is {row['printed']}: the cells add to "
            f"{row['computed_with_scan']} with the scan's value and to {row['computed_with_file']} with the file's, so the printed "
            f"total decides (finding {fid} in [{base}/findings.json]({base}/findings.json); not confirmed by a person).*")


def blocks(run: str) -> dict:
    s = json.loads((ROOT / "runs" / run / "summary.json").read_text())
    return {"table": findings_table(s), "cost": cost_table(s), "picture": picture(s), "run": f"`runs/{run}`"}


def apply(text: str, b: dict) -> str:
    for name, body in b.items():
        text = re.sub(rf"(<!-- {name}:start -->\n).*?(<!-- {name}:end -->)", lambda m: m.group(1) + body + "\n" + m.group(2), text, flags=re.S)
    return text


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", default=None)
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args(argv)
    run = a.run or latest_summary()
    path = ROOT / "README.md"
    old = path.read_text()
    new = apply(old, blocks(run))
    if a.check:
        print("README figures match the files" if new == old else "README figures differ from the files")
        return 0 if new == old else 1
    path.write_text(new)
    print(f"README.md blocks written from runs/{run}/summary.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
