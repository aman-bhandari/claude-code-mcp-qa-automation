"""Demo entry point — run the pipeline across all fixtures in parallel.

Usage:
    python -m src

Reads every fixtures/*.json file, dispatches pipeline runs via the
orchestrator's sub-agent fan-out pattern, writes per-board reports to
output/<board>/report.html and a run summary to output/summary.json.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from . import orchestrator

REPO_ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    fixtures_dir = REPO_ROOT / "fixtures"
    output_root = REPO_ROOT / "output"
    db_root = output_root / "_db"

    fixtures_by_board: dict[str, Path] = {}
    for fixture in sorted(fixtures_dir.glob("example_sprint_*.json")):
        payload = json.loads(fixture.read_text(encoding="utf-8"))
        board = str(payload["board"])
        fixtures_by_board[board] = fixture

    if not fixtures_by_board:
        print("No fixtures found under fixtures/", file=sys.stderr)
        return 1

    print(f"Dispatching {len(fixtures_by_board)} board(s) in parallel...")
    results = orchestrator.run_boards(
        fixtures_by_board=fixtures_by_board,
        output_root=output_root,
        db_root=db_root,
    )
    orchestrator.write_summary(results, output_root / "summary.json")

    for r in results:
        if "error" in r:
            print(f"  FAIL {r['worker_board']}: {r['error']}")
        else:
            pct = r["metrics"]["completion_ratio"] * 100
            print(
                f"  OK   {r['worker_board']:>6} — "
                f"{r['metrics']['completed_points']}/{r['metrics']['total_points']} pts "
                f"({pct:.1f}%) -> {r['report_path']}"
            )

    failed = sum(1 for r in results if "error" in r)
    return 0 if failed == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
