import pytest

from crossfoot import sources
from crossfoot.ledger import Ledger


def row(votes, a, e, d):
    return dict(precinct="1", office="O", candidate="C", votes=votes, absentee=a, early_voting=e, election_day=d)


def test_file_mismatches():
    rows = [row("6", "1", "2", "3"), row("7", "1", "2", "3"), row("6", "", "2", "3"), row("1,006", "1", "2", "1,003")]
    bad, checked, skipped = sources.file_mismatches(rows)
    assert len(bad) == 1 and bad[0]["votes"] == "7" and bad[0]["parts_sum"] == 6
    assert (checked, skipped) == (3, 1)


def test_urls():
    assert sources.scan_url("san_saba").endswith("2024%20San%20Saba%20County%2C%20TX%20precinct-level%20results.pdf")
    assert sources.file_url("panola").endswith("20241105__tx__general__panola__precinct.csv")


def test_failed_download_names_url(tmp_path):
    with pytest.raises(sources.FetchError) as e:
        sources._download("file:///nonexistent/x.pdf", tmp_path / "x.pdf")
    assert "file:///nonexistent/x.pdf" in str(e.value)
    assert not (tmp_path / "x.pdf").exists()


def test_cached_download_is_skipped(tmp_path):
    src = tmp_path / "src.txt"; src.write_text("hi")
    dest = tmp_path / "out" / "d.txt"
    assert sources._download(src.as_uri(), dest) is True
    assert sources._download(src.as_uri(), dest) is False


def test_ledger_resume_keeps_accepted():
    L = Ledger()
    L.put_cell("p", 1, "b", "A", "c1", 5)
    L.set_status("p", 1, "b", "A", "c1", "accepted")
    L.put_cell("p", 1, "b", "A", "c1", 9)
    assert L.cells("p")[0]["value"] == 5
    L.put_cell("p", 1, "b", "A", "c2", 1)
    L.put_cell("p", 1, "b", "A", "c2", 2)
    c2 = [c for c in L.cells("p") if c["column"] == "c2"][0]
    assert c2["value"] == 2 and c2["first_read"] == 1 and c2["tries"] == 1
    assert [c["column"] for c in L.open_cells("p")] == ["c2"]
    L.put_total("p", 1, "b", "row", "A", 6)
    L.event("p", "x", {"a": 1})
    assert L.totals("p")[0]["value"] == 6 and L.events("p")[0]["kind"] == "x"
