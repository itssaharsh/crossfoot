"""No command ends in a traceback when an input it needs is missing: it prints one plain line and returns 1.
Run in an empty folder, with the downloader faked to fail where a network would be needed."""
import pytest

from crossfoot import cli, sources


@pytest.fixture(autouse=True)
def empty_folder(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sources, "DATA", tmp_path / "data")
    monkeypatch.delenv("NEATLOGS_API_KEY", raising=False)

    def down(key, root=None):
        raise sources.FetchError(f"could not download https://example.invalid/{key}: offline")
    monkeypatch.setattr(sources, "fetch", down)


CASES = {
    "fetch": ["fetch", "--county", "panola"],
    "fetch-all": ["fetch", "--all"],
    "filecheck": ["filecheck", "--county", "panola"],
    "render": ["render", "--county", "panola", "--page", "1"],
    "read": ["read", "--county", "panola"],
    "read-page": ["read-page", "--county", "cottle", "--into", "nope", "--pages", "1"],
    "close-no-ledger": ["close", "--county", "panola", "--resume", "nope"],
    "close-latest": ["close", "--county", "panola", "--resume", "latest"],
    "audit-panola": ["audit", "--county", "panola"],
    "audit-panola-resume": ["audit", "--county", "panola", "--resume", "nope"],
    "audit-report": ["audit", "--county", "cottle"],
    "audit-all-resume": ["audit", "--all", "--resume", "nope"],
    "summarize": ["summarize", "--base", "nope"],
    "summarize-use": ["summarize", "--base", "nope", "--use", "panola=nope"],
    "score": ["score", "--county", "panola", "--findings", "nope.json"],
    "verify-known": ["verify-known", "--county", "panola"],
    "site-build": ["site", "build", "--run", "nope"],
    "site-build-latest": ["site", "build", "--run", "latest"],
}


@pytest.mark.parametrize("name", CASES)
def test_a_missing_input_is_one_plain_line_and_exit_1(name, capsys):
    rc = cli.main(CASES[name])
    err = capsys.readouterr().err
    assert rc == 1, err
    assert err.strip() and "Traceback" not in err


def test_render_with_the_scan_present_but_not_the_tool_is_plain_too(monkeypatch, capsys, tmp_path):
    monkeypatch.setattr(sources, "fetch", lambda key, root=None: [])
    rc = cli.main(["render", "--county", "panola", "--page", "1"])
    assert rc == 1 and "Traceback" not in capsys.readouterr().err
