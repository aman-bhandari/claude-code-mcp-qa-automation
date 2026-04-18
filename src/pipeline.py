"""End-to-end pipeline: fixture → store → metrics → report.

The pipeline is deterministic. Given the same fixture input and the same
flags.yaml, it produces byte-identical output. This is the property that
makes the run cacheable and the report reviewable.
"""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path
from typing import Mapping

from . import config, metrics, report, store


def load_fixture(path: Path) -> Mapping[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def run(
    fixture_path: Path,
    db_path: Path,
    output_html_path: Path,
) -> dict:
    """Run the full pipeline against one fixture file. Returns a summary dict."""
    sprint = load_fixture(fixture_path)
    flags = config.load_flags(board=str(sprint["board"]))
    conn = store.init_store(db_path)

    try:
        store.upsert_sprint(conn, sprint)
        tickets = list(sprint.get("tickets", []))
        if flags.is_on("collect_tickets"):
            store.upsert_tickets(conn, str(sprint["sprint_id"]), tickets)

        m = metrics.compute_sprint_metrics(str(sprint["sprint_id"]), tickets)
        loads = metrics.compute_assignee_load(str(sprint["sprint_id"]), tickets)
        breakdown = metrics.compute_story_type_breakdown(str(sprint["sprint_id"]), tickets)

        # Log the run
        conn.execute(
            "INSERT INTO run_log (sprint_id, run_at, skill, status) VALUES (?, ?, ?, ?)",
            (str(sprint["sprint_id"]), dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "pipeline", "ok"),
        )

        # Persist metrics
        conn.execute(
            "INSERT OR REPLACE INTO sprint_metrics "
            "(sprint_id, total_points, completed_points, in_progress_points, "
            "to_do_points, completion_ratio, ticket_count, completed_ticket_count) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                m.sprint_id, m.total_points, m.completed_points, m.in_progress_points,
                m.to_do_points, m.completion_ratio, m.ticket_count, m.completed_ticket_count,
            ),
        )
        conn.commit()

        # Render report
        html = report.render_report(dict(sprint), m, loads, breakdown)
        report.write_report(output_html_path, html)

        return {
            "sprint_id": sprint["sprint_id"],
            "board": sprint["board"],
            "report_path": str(output_html_path),
            "metrics": {
                "completion_ratio": m.completion_ratio,
                "total_points": m.total_points,
                "completed_points": m.completed_points,
                "ticket_count": m.ticket_count,
            },
            "tables_in_store": store.count_tables(conn),
        }
    finally:
        conn.close()
