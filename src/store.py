"""SQLite trending store.

A seven-table schema holds sprint snapshots, ticket states, and cross-sprint
trend rollups. The point of the store is not to be a production database — it
is to give the pipeline a queryable substrate where "what changed since last
sprint?" answers in a single SELECT rather than a re-scan of raw Jira data.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Iterable, Mapping


SCHEMA_STATEMENTS: list[str] = [
    """
    CREATE TABLE IF NOT EXISTS sprints (
      sprint_id   TEXT PRIMARY KEY,
      sprint_name TEXT NOT NULL,
      board       TEXT NOT NULL,
      start_date  TEXT NOT NULL,
      end_date    TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS tickets (
      sprint_id    TEXT NOT NULL,
      key          TEXT NOT NULL,
      title        TEXT NOT NULL,
      status       TEXT NOT NULL,
      story_points INTEGER,
      assignee     TEXT,
      story_type   TEXT,
      PRIMARY KEY (sprint_id, key),
      FOREIGN KEY (sprint_id) REFERENCES sprints(sprint_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS sprint_metrics (
      sprint_id                TEXT PRIMARY KEY,
      total_points             INTEGER NOT NULL,
      completed_points         INTEGER NOT NULL,
      in_progress_points       INTEGER NOT NULL,
      to_do_points             INTEGER NOT NULL,
      completion_ratio         REAL    NOT NULL,
      ticket_count             INTEGER NOT NULL,
      completed_ticket_count   INTEGER NOT NULL,
      FOREIGN KEY (sprint_id)  REFERENCES sprints(sprint_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS assignee_load (
      sprint_id TEXT NOT NULL,
      assignee  TEXT NOT NULL,
      points    INTEGER NOT NULL,
      tickets   INTEGER NOT NULL,
      PRIMARY KEY (sprint_id, assignee),
      FOREIGN KEY (sprint_id) REFERENCES sprints(sprint_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS story_type_breakdown (
      sprint_id  TEXT NOT NULL,
      story_type TEXT NOT NULL,
      points     INTEGER NOT NULL,
      tickets    INTEGER NOT NULL,
      PRIMARY KEY (sprint_id, story_type),
      FOREIGN KEY (sprint_id) REFERENCES sprints(sprint_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS run_log (
      run_id     INTEGER PRIMARY KEY AUTOINCREMENT,
      sprint_id  TEXT NOT NULL,
      run_at     TEXT NOT NULL,
      skill      TEXT NOT NULL,
      status     TEXT NOT NULL,
      FOREIGN KEY (sprint_id) REFERENCES sprints(sprint_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS flag_snapshots (
      sprint_id TEXT NOT NULL,
      flag_name TEXT NOT NULL,
      flag_value TEXT NOT NULL,
      PRIMARY KEY (sprint_id, flag_name),
      FOREIGN KEY (sprint_id) REFERENCES sprints(sprint_id)
    )
    """,
]


def init_store(db_path: Path) -> sqlite3.Connection:
    """Open (or create) the SQLite file and ensure schema is present."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    for stmt in SCHEMA_STATEMENTS:
        conn.execute(stmt)
    conn.commit()
    return conn


def count_tables(conn: sqlite3.Connection) -> int:
    cursor = conn.execute(
        "SELECT COUNT(*) FROM sqlite_master WHERE type='table' "
        "AND name NOT LIKE 'sqlite_%'"
    )
    return int(cursor.fetchone()[0])


def upsert_sprint(conn: sqlite3.Connection, sprint: Mapping[str, object]) -> None:
    conn.execute(
        "INSERT OR REPLACE INTO sprints "
        "(sprint_id, sprint_name, board, start_date, end_date) "
        "VALUES (?, ?, ?, ?, ?)",
        (
            sprint["sprint_id"],
            sprint["sprint_name"],
            sprint["board"],
            sprint["start_date"],
            sprint["end_date"],
        ),
    )


def upsert_tickets(
    conn: sqlite3.Connection, sprint_id: str, tickets: Iterable[Mapping[str, object]]
) -> None:
    rows = [
        (
            sprint_id,
            t["key"],
            t["title"],
            t["status"],
            t.get("story_points"),
            t.get("assignee"),
            t.get("story_type"),
        )
        for t in tickets
    ]
    conn.executemany(
        "INSERT OR REPLACE INTO tickets "
        "(sprint_id, key, title, status, story_points, assignee, story_type) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        rows,
    )
