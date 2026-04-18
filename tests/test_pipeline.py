"""End-to-end tests for the QA automation demo."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from src import config, metrics, orchestrator, pipeline, store


REPO_ROOT = Path(__file__).resolve().parent.parent
FIXTURE_01 = REPO_ROOT / "fixtures" / "example_sprint_01.json"
FIXTURE_02 = REPO_ROOT / "fixtures" / "example_sprint_02.json"


def test_flags_load_and_board_scope_override(tmp_path: Path) -> None:
    flags_alpha = config.load_flags("ALPHA")
    flags_beta = config.load_flags("BETA")
    flags_gamma = config.load_flags("GAMMA")

    assert flags_alpha.is_on("collect_tickets")
    assert flags_alpha.get("max_report_words") == 4000
    assert flags_beta.get("max_report_words") == 1000
    assert flags_gamma.get("max_report_words") == 800
    assert flags_gamma.get("include_burndown") is False


def test_flag_count_is_reasonable() -> None:
    total = config.count_flags()
    assert total > 10, f"expected >10 total flag entries, got {total}"


def test_store_schema_has_seven_tables(tmp_path: Path) -> None:
    db = tmp_path / "test.sqlite3"
    conn = store.init_store(db)
    try:
        assert store.count_tables(conn) == 7
    finally:
        conn.close()


def test_metrics_compute_from_fixture_01() -> None:
    sprint = json.loads(FIXTURE_01.read_text(encoding="utf-8"))
    m = metrics.compute_sprint_metrics(
        sprint_id=sprint["sprint_id"], tickets=sprint["tickets"]
    )
    assert m.ticket_count == 20
    assert m.total_points > 0
    assert 0 < m.completion_ratio <= 1


def test_pipeline_end_to_end(tmp_path: Path) -> None:
    db = tmp_path / "alpha.sqlite3"
    out = tmp_path / "ALPHA" / "report.html"
    summary = pipeline.run(fixture_path=FIXTURE_01, db_path=db, output_html_path=out)

    assert out.is_file()
    html = out.read_text(encoding="utf-8")
    assert "<!doctype html>" in html
    assert "ALPHA_0.3.2" in html  # sprint_name rendered
    assert "Sprint KPIs" in html
    assert summary["tables_in_store"] == 7
    assert summary["metrics"]["ticket_count"] == 20

    # Sanity: sprint_metrics row landed
    conn = sqlite3.connect(db)
    try:
        row = conn.execute(
            "SELECT total_points, ticket_count FROM sprint_metrics WHERE sprint_id = ?",
            (sprint := summary["sprint_id"],),
        ).fetchone()
        assert row is not None
        assert row[1] == 20
    finally:
        conn.close()


def test_orchestrator_parallel_fanout(tmp_path: Path) -> None:
    fixtures = {"ALPHA": FIXTURE_01, "BETA": FIXTURE_02}
    results = orchestrator.run_boards(
        fixtures_by_board=fixtures,
        output_root=tmp_path / "out",
        db_root=tmp_path / "_db",
    )
    assert len(results) == 2
    assert all("error" not in r for r in results)
    worker_boards = {r["worker_board"] for r in results}
    assert worker_boards == {"ALPHA", "BETA"}

    # Both reports produced
    assert (tmp_path / "out" / "ALPHA" / "report.html").is_file()
    assert (tmp_path / "out" / "BETA" / "report.html").is_file()


def test_no_hardcoded_real_identifiers_in_fixtures() -> None:
    for fixture in [FIXTURE_01, FIXTURE_02]:
        text = fixture.read_text(encoding="utf-8").lower()
        for forbidden in ("sirrista", "saacash", "wl-", "sw-", "spmaster"):
            assert forbidden not in text, f"{fixture.name} contains forbidden '{forbidden}'"
