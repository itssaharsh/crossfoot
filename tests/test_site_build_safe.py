"""The page build: it fetches a scan that is missing, says one plain line when it cannot, and never leaves site/data/ half
written. No network, no model: fakes stand in for the downloader and the renderer."""
import json

import pytest

from crossfoot import cli, sitebuild, sources

FAIL = {}


def raw(county):
    return {"county": county, "run_id": "r1", "layout": "matrix", "pages": [{"number": 1, "width": 100, "height": 100}],
            "blocks": [], "cells": [], "totals": [], "checks": [], "events": [], "summary": {}}


@pytest.fixture
def runs(tmp_path):
    root = tmp_path / "runs"
    for c in ("alpha", "beta"):
        (root / "r1" / c).mkdir(parents=True)
        (root / "r1" / c / "county.json").write_text(json.dumps(raw(c)))
    (root / "r1" / "summary.json").write_text(json.dumps({
        "run_id": "r1", "counties": [{"county": "alpha", "status": "audited"}, {"county": "beta", "status": "audited"}],
        "totals": {}}))
    return root


@pytest.fixture
def fake_render(monkeypatch):
    def pages(county, numbers, out_dir, data_root=None, max_width=1600):
        if county == "beta" and FAIL.get("beta"):
            raise RuntimeError("renderer broke half way")
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / f"{county}-p1.webp").write_bytes(b"new-" + county.encode())
        return {1: (100, 100, 100, 100)}
    FAIL.clear()
    monkeypatch.setattr(sitebuild, "render_pages", pages)
    monkeypatch.setattr(sitebuild, "render_blocks", lambda raw, sizes, out_dir, data_root=None: ({}, {}))


def tree(root):
    return {p.relative_to(root).as_posix(): p.read_bytes() for p in sorted(root.rglob("*")) if p.is_file()}


def old_site(tmp_path):
    out = tmp_path / "site" / "data"
    (out / "pages").mkdir(parents=True)
    (out / "blocks").mkdir()
    (out / "index.json").write_text('{"run":"old"}')
    (out / "pages" / "alpha-p1.webp").write_bytes(b"old image")
    (out / "blocks" / "alpha-b1.webp").write_bytes(b"old block")
    return out


def test_a_build_that_fails_half_way_leaves_the_old_files(tmp_path, runs, fake_render):
    out = old_site(tmp_path)
    before = tree(out)
    FAIL["beta"] = True
    with pytest.raises(RuntimeError):
        sitebuild.build("r1", str(runs), str(out), data_root=tmp_path / "data", fetch=lambda key, root=None: [],
                        log=lambda s: None)
    assert tree(out) == before
    assert [p.name for p in (tmp_path / "site").iterdir()] == ["data"], "no staging folder is left beside site/data"


def test_a_good_build_replaces_site_data_whole(tmp_path, runs, fake_render):
    out = old_site(tmp_path)
    keys = sitebuild.build("r1", str(runs), str(out), data_root=tmp_path / "data", fetch=lambda key, root=None: [],
                           log=lambda s: None)
    assert keys == ["alpha", "beta"]
    t = tree(out)
    assert t["pages/alpha-p1.webp"] == b"new-alpha" and "blocks/alpha-b1.webp" not in t
    assert json.loads(t["index.json"])["run"] == "r1"


def test_a_scan_that_is_not_in_data_is_fetched_once_per_county(tmp_path, runs, fake_render):
    asked = []

    def fetch(key, root=None):
        asked.append(key)
        return ["scan"]
    lines = []
    sitebuild.build("r1", str(runs), str(tmp_path / "out"), data_root=tmp_path / "data", fetch=fetch, log=lines.append)
    assert asked == ["alpha", "beta"]
    assert len(lines) == 2 and "alpha" in lines[0] and "beta" in lines[1]


def test_a_scan_already_there_is_not_fetched(tmp_path, runs, fake_render):
    for c in ("alpha", "beta"):
        p = sources.scan_path(c, tmp_path / "data")
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(b"%PDF")
    asked = []
    sitebuild.build("r1", str(runs), str(tmp_path / "out"), data_root=tmp_path / "data",
                    fetch=lambda key, root=None: asked.append(key), log=lambda s: None)
    assert asked == []


def test_a_failed_download_is_one_plain_line_and_exit_1(tmp_path, runs, fake_render, monkeypatch, capsys):
    out = old_site(tmp_path)
    before = tree(out)
    monkeypatch.chdir(tmp_path)

    def fetch(key, root=None):
        raise sources.FetchError(f"could not download https://example.invalid/{key}.pdf: offline")
    monkeypatch.setattr(sources, "fetch", fetch)
    monkeypatch.setattr(sources, "COUNTIES", {**sources.COUNTIES, "alpha": "Alpha", "beta": "Beta"})
    rc = cli.main(["site", "build", "--run", "r1", "--runs-dir", str(runs), "--out", str(out)])
    err = capsys.readouterr().err.strip().splitlines()
    assert rc == 1 and len(err) == 1
    assert "alpha" in err[0] and "https://example.invalid/alpha.pdf" in err[0] and "Traceback" not in err[0]
    assert tree(out) == before


def test_a_partial_build_keeps_the_other_counties_of_the_same_run(tmp_path, runs, fake_render):
    out = tmp_path / "out"
    kw = dict(data_root=tmp_path / "data", fetch=lambda key, root=None: [], log=lambda s: None)
    sitebuild.build("r1", str(runs), str(out), **kw)
    sitebuild.build("r1", str(runs), str(out), counties=["beta"], **kw)
    t = tree(out)
    assert "pages/alpha-p1.webp" in t and "pages/beta-p1.webp" in t
    assert [c["key"] for c in json.loads(t["index.json"])["counties"]] == ["alpha", "beta"]
