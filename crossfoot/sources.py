"""The eight benchmark counties: where their scan and published file live, and the local cache under data/."""
from __future__ import annotations

import csv
import os
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import quote

DATA = Path("data")

COUNTIES = {
    "cottle": "Cottle",
    "foard": "Foard",
    "jones": "Jones",
    "limestone": "Limestone",
    "lynn": "Lynn",
    "panola": "Panola",
    "san_saba": "San Saba",
    "scurry": "Scurry",
}

_SCAN = ("https://raw.githubusercontent.com/openelections/openelections-sources-tx/master/2024/general/"
         "2024%20{name}%20County%2C%20TX%20precinct-level%20results.pdf")
_FILE = ("https://raw.githubusercontent.com/openelections/openelections-data-tx/master/2024/counties/"
         "20241105__tx__general__{key}__precinct.csv")


class FetchError(Exception):
    """A download failed; the message carries the URL."""


def scan_url(key: str) -> str:
    return _SCAN.format(name=quote(COUNTIES[key]))


def file_url(key: str) -> str:
    return _FILE.format(key=key)


def scan_path(key: str, root: Path = DATA) -> Path:
    return root / "scans" / f"{key}.pdf"


def file_path(key: str, root: Path = DATA) -> Path:
    return root / "files" / f"{key}.csv"


def _download(url: str, dest: Path) -> bool:
    """Download url to dest unless dest exists. Returns True if a download happened."""
    if dest.exists() and dest.stat().st_size > 0:
        return False
    dest.parent.mkdir(parents=True, exist_ok=True)
    part = dest.with_suffix(dest.suffix + ".part")
    try:
        with urllib.request.urlopen(url, timeout=60) as r, open(part, "wb") as f:
            while chunk := r.read(1 << 16):
                f.write(chunk)
    except (urllib.error.URLError, OSError, TimeoutError) as e:
        part.unlink(missing_ok=True)
        raise FetchError(f"could not download {url}: {e}") from e
    os.replace(part, dest)
    return True


def fetch(key: str, root: Path = DATA) -> list[str]:
    """Make sure the scan and the published file of one county are cached. Returns the names downloaded now."""
    got = []
    if _download(scan_url(key), scan_path(key, root)):
        got.append("scan")
    if _download(file_url(key), file_path(key, root)):
        got.append("file")
    return got


def read_published(key: str, root: Path = DATA) -> list[dict]:
    with open(file_path(key, root), newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _int(s: str | None) -> int | None:
    s = (s or "").strip().replace(",", "")
    try:
        return int(s)
    except ValueError:
        return None


def file_mismatches(rows: list[dict]) -> tuple[list[dict], int, int]:
    """Rows whose votes differ from absentee + early_voting + election_day.

    Returns (bad rows, rows checked, rows skipped because votes or a part is blank or not a number).
    Each bad row is the original dict plus a `parts_sum` key.
    """
    bad, checked, skipped = [], 0, 0
    for r in rows:
        vals = [_int(r.get(c)) for c in ("votes", "absentee", "early_voting", "election_day")]
        if any(v is None for v in vals):
            skipped += 1
            continue
        checked += 1
        total = vals[1] + vals[2] + vals[3]
        if vals[0] != total:
            bad.append({**r, "parts_sum": total})
    return bad, checked, skipped
