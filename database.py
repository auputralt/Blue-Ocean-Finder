from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from datetime import datetime

DB_PATH = Path(__file__).parent / "blue_ocean.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS reports (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    industry        TEXT NOT NULL,
    location        TEXT NOT NULL,
    enhanced_query  TEXT,
    search_queries  TEXT,
    research_data   TEXT,
    synthesis       TEXT,
    favorite        INTEGER DEFAULT 0,
    created_at      TEXT DEFAULT (datetime('now'))
);
"""


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db() -> None:
    with _conn() as conn:
        conn.executescript(_SCHEMA)


def save_report(
    industry: str,
    location: str,
    enhanced: dict,
    research: list[dict],
    synthesis: str,
) -> int:
    with _conn() as conn:
        cur = conn.execute(
            """INSERT INTO reports
               (industry, location, enhanced_query, search_queries, research_data, synthesis)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                industry,
                location,
                enhanced.get("enhanced_query", ""),
                json.dumps(enhanced.get("search_queries", {})),
                json.dumps(research),
                synthesis,
            ),
        )
        return cur.lastrowid  # type: ignore[return-value]


def list_reports(favorites_only: bool = False, limit: int = 100) -> list[dict]:
    sql = "SELECT id, industry, location, favorite, created_at FROM reports"
    if favorites_only:
        sql += " WHERE favorite = 1"
    sql += " ORDER BY created_at DESC LIMIT ?"

    with _conn() as conn:
        rows = conn.execute(sql, (limit,)).fetchall()
    return [dict(r) for r in rows]


def get_report(report_id: int) -> dict | None:
    with _conn() as conn:
        row = conn.execute(
            "SELECT * FROM reports WHERE id = ?", (report_id,)
        ).fetchone()
    if row is None:
        return None
    d = dict(row)
    d["search_queries"] = json.loads(d.get("search_queries") or "{}")
    d["research_data"] = json.loads(d.get("research_data") or "[]")
    return d


def toggle_favorite(report_id: int) -> bool:
    with _conn() as conn:
        conn.execute(
            "UPDATE reports SET favorite = 1 - favorite WHERE id = ?",
            (report_id,),
        )
        row = conn.execute(
            "SELECT favorite FROM reports WHERE id = ?", (report_id,)
        ).fetchone()
    return bool(row["favorite"]) if row else False


def delete_report(report_id: int) -> None:
    with _conn() as conn:
        conn.execute("DELETE FROM reports WHERE id = ?", (report_id,))
