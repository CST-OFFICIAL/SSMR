from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path
from typing import Any

DEFAULT_DB = Path(__file__).resolve().parents[1] / "data" / "soil_scans.sqlite3"


def database_path() -> Path:
    return Path(os.getenv("SSMR_DATABASE_PATH", str(DEFAULT_DB))).expanduser()


def connect() -> sqlite3.Connection:
    path = database_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path, timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def init_db() -> None:
    with connect() as conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS soil_scans (
            id TEXT PRIMARY KEY,
            timestamp TEXT NOT NULL,
            received_at TEXT NOT NULL,
            source TEXT NOT NULL CHECK(source IN ('simulated', 'physical')),
            payload_json TEXT NOT NULL
        )""")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_soil_scans_timestamp ON soil_scans(timestamp DESC)")


def insert_scan(scan_id: str, timestamp: str, received_at: str, source: str, payload: dict[str, Any]) -> None:
    insert_scans([{
        "id": scan_id,
        "timestamp": timestamp,
        "received_at": received_at,
        "source": source,
        "payload": payload,
    }])


def insert_scans(scans: list[dict[str, Any]]) -> None:
    """Persist a batch atomically: either every scan is inserted or none are."""
    rows = [
        (
            scan["id"],
            scan["timestamp"],
            scan["received_at"],
            scan["source"],
            json.dumps(scan["payload"], separators=(",", ":")),
        )
        for scan in scans
    ]
    with connect() as conn:
        conn.executemany(
            "INSERT INTO soil_scans(id, timestamp, received_at, source, payload_json) VALUES (?, ?, ?, ?, ?)",
            rows,
        )


def get_scan(scan_id: str) -> dict[str, Any] | None:
    with connect() as conn:
        row = conn.execute("SELECT payload_json FROM soil_scans WHERE id = ?", (scan_id,)).fetchone()
    return json.loads(row["payload_json"]) if row else None


def list_scans(limit: int = 50, offset: int = 0) -> tuple[list[dict[str, Any]], int]:
    with connect() as conn:
        total = conn.execute("SELECT COUNT(*) AS n FROM soil_scans").fetchone()["n"]
        rows = conn.execute(
            "SELECT payload_json FROM soil_scans ORDER BY timestamp DESC, received_at DESC LIMIT ? OFFSET ?",
            (limit, offset),
        ).fetchall()
    return [json.loads(row["payload_json"]) for row in rows], total
