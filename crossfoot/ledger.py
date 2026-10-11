"""SQLite ledger: cells, printed totals and events for one run. Resume keeps accepted cells."""
from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS cells(
  id INTEGER PRIMARY KEY, county TEXT, page INTEGER, block_id TEXT, contest TEXT, candidate TEXT,
  row_kind TEXT, column TEXT, value INTEGER, first_read INTEGER, status TEXT DEFAULT 'first_read',
  tries INTEGER DEFAULT 0, model TEXT, x0 INTEGER, y0 INTEGER, x1 INTEGER, y1 INTEGER, reason TEXT,
  UNIQUE(county, page, block_id, row_kind, column));
CREATE TABLE IF NOT EXISTS totals(
  county TEXT, page INTEGER, block_id TEXT, direction TEXT, key TEXT, value INTEGER,
  UNIQUE(county, page, block_id, direction, key));
CREATE TABLE IF NOT EXISTS events(
  id INTEGER PRIMARY KEY, ts REAL, county TEXT, kind TEXT, payload_json TEXT);
"""
STATUSES = ("first_read", "accepted", "failed", "cannot_verify")


class Ledger:
    """One SQLite file. Cells are keyed by (county, page, block_id, row_kind, column)."""

    def __init__(self, path: str | Path = ":memory:"):
        self.db = sqlite3.connect(str(path))
        self.db.row_factory = sqlite3.Row
        self.db.executescript(SCHEMA)
        if "reason" not in {r["name"] for r in self.db.execute("PRAGMA table_info(cells)")}:
            self.db.execute("ALTER TABLE cells ADD COLUMN reason TEXT")  # ledgers made before the loop existed

    def close(self):
        self.db.close()

    def put_cell(self, county, page, block_id, row_kind, column, value, *, contest=None, candidate=None,
                 model=None, box=(None, None, None, None)):
        """Insert a first read, or re-read an open cell. An accepted cell is never overwritten (resume)."""
        self.db.execute(
            "INSERT INTO cells(county,page,block_id,contest,candidate,row_kind,column,value,first_read,model,x0,y0,x1,y1)"
            " VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)"
            " ON CONFLICT(county,page,block_id,row_kind,column) DO UPDATE SET value=excluded.value,"
            " tries=tries+1, model=excluded.model WHERE status!='accepted'",
            (county, page, block_id, contest, candidate, row_kind, column, value, value, model, *box))
        self.db.commit()

    def set_status(self, county, page, block_id, row_kind, column, status, reason=None):
        if status not in STATUSES:
            raise ValueError(f"unknown status {status!r}")
        self.db.execute("UPDATE cells SET status=?, reason=? WHERE county=? AND page=? AND block_id=? AND row_kind=? "
                        "AND column=?", (status, reason, county, page, block_id, row_kind, column))
        self.db.commit()

    def reread_cell(self, county, page, block_id, row_kind, column, value, model=None):
        """Record one re-read of a cell: tries goes up by one, the value is the one kept, the model only if it changed it."""
        self.db.execute("UPDATE cells SET value=?, tries=tries+1, model=COALESCE(?, model) WHERE county=? AND page=? "
                        "AND block_id=? AND row_kind=? AND column=? AND status!='accepted'",
                        (value, model, county, page, block_id, row_kind, column))
        self.db.commit()

    def put_total(self, county, page, block_id, direction, key, value):
        self.db.execute("INSERT OR REPLACE INTO totals VALUES(?,?,?,?,?,?)",
                        (county, page, block_id, direction, key, value))
        self.db.commit()

    def event(self, county, kind, payload=None):
        self.db.execute("INSERT INTO events(ts,county,kind,payload_json) VALUES(?,?,?,?)",
                        (time.time(), county, kind, json.dumps(payload or {})))
        self.db.commit()

    def cells(self, county=None, status=None) -> list[dict]:
        q, a = "SELECT * FROM cells WHERE 1=1", []
        if county:
            q += " AND county=?"; a.append(county)
        if status:
            q += " AND status=?"; a.append(status)
        return [dict(r) for r in self.db.execute(q + " ORDER BY id", a)]

    def totals(self, county=None) -> list[dict]:
        q, a = "SELECT * FROM totals", []
        if county:
            q += " WHERE county=?"; a.append(county)
        return [dict(r) for r in self.db.execute(q, a)]

    def events(self, county=None) -> list[dict]:
        q, a = "SELECT * FROM events", []
        if county:
            q += " WHERE county=?"; a.append(county)
        return [dict(r) for r in self.db.execute(q + " ORDER BY id", a)]

    def open_cells(self, county=None) -> list[dict]:
        """Cells that still need work: first_read or failed."""
        return [c for c in self.cells(county) if c["status"] in ("first_read", "failed")]
