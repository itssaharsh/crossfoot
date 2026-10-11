"""Write the README's tables from the final run's files, so no figure in them is typed by hand.

    python3 tools/readme_tables.py            rewrite the blocks between <!-- name:start --> and <!-- name:end --> in README.md
    python3 tools/readme_tables.py --check    exit 1 if README.md differs from what the files give

Reads runs/<run>/summary.json (the newest run with one, or --run) and, for the picture, the findings.json and crop of the
run that the summary names for Panola."""
import argparse, json, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
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
    """Per county: the pages, then what the run that read it cost and took, then what the audits made again from its ledger
    added. The row for all counties is the reading run's own totals (`totals.read_run`)."""
    head = ("| County | Pages | Model calls | Metered cost (estimate) | Seconds | Added by later audits from the ledger |\n"
            "|---|---|---|---|---|---|")
    again = lambda g: f"{g['model_calls']} calls, ${g['metered_cost']:.4f}, {g['seconds']} s" if g else "none"
    rows = [f"| {c['county'].replace('_', ' ').title()} | {c['pages']} | {c['read_run']['model_calls']} "
            f"| ${c['read_run']['metered_cost']:.4f} | {c['read_run']['seconds']} | {again(c.get('audit_again'))} |"
            for c in s["counties"]]
    t = s["totals"]
    r = t["read_run"]
    rows.append(f"| **All** | {sum(c['pages'] for c in s['counties'])} | {r['model_calls']} | ${r['metered_cost']:.4f} "
                f"| {r['seconds']} | {again(t.get('audit_again'))} |")
    run = s["counties"][0]["read_run"]["run_id"]
    checked = [c for c in s["counties"] if c["status"] != "unchecked"]
    dear = max(checked, key=lambda c: c["read_run"]["metered_cost"])
    cheap = min(checked, key=lambda c: c["read_run"]["metered_cost"])
    name = lambda c: c["county"].replace("_", " ").title()
    fig = lambda c: (f"{name(c)} ({c['read_run']['model_calls']} model calls, ${c['read_run']['metered_cost']:.4f}, "
                     f"{c['read_run']['seconds']} seconds)")
    note = (f"Calls, cost and seconds are those of the run that read each county, [`runs/{run}/summary.json`](runs/{run}/summary.json) "
            f"(one unattended `audit --all` run). The last column is what the audits made again from the same ledgers added "
            f"(`summary.json` keeps both under `read_run` and `audit_again`). An audit from nothing costs, for the dearest "
            f"checked county, {fig(dear)}, and for the cheapest, {fig(cheap)}; Limestone, which prints nothing to add up, took "
            f"{next(c for c in s['counties'] if c['county'] == 'limestone')['read_run']['model_calls']} call to be listed as not checked.")
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
