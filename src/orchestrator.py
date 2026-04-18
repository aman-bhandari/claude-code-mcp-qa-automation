"""Orchestrator — documents the sub-agent parallelization pattern.

In Claude Code, the Agent tool (often surfaced as the Task tool) spawns a
sub-agent in an isolated context window. Parallelizing work across boards
means spawning one sub-agent per board and awaiting their results.

This scaffold runs the pipeline in-process across boards using a thread pool
as a stand-in for that sub-agent fan-out. The shape is identical — dispatch
N jobs, gather N results — so the orchestration code reads the same whether
the workers are real sub-agents or threaded pipeline runs.

For the actual Claude Code pattern, the orchestrator would emit Task calls
rather than ThreadPoolExecutor submits. See `.claude/skills/orchestrator/`
for the skill-level documentation.
"""

from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Iterable

from . import config, pipeline


def run_boards(
    fixtures_by_board: dict[str, Path],
    output_root: Path,
    db_root: Path,
    max_parallel: int | None = None,
) -> list[dict]:
    """Run the pipeline for each (board, fixture) pair, in parallel.

    Args:
      fixtures_by_board: e.g. {"ALPHA": Path(".../example_sprint_01.json")}
      output_root: directory to write reports under (one subdir per board)
      db_root: directory to place per-board SQLite stores
      max_parallel: upper bound on concurrent workers. If None, reads
        `max_parallel_subagents` from flags (global scope).

    Returns:
      A list of pipeline summary dicts, one per board, in completion order.
    """
    if max_parallel is None:
        # Use global flag scope (pass any valid board; they share globals)
        sample_board = next(iter(fixtures_by_board), None) or "ALPHA"
        flags = config.load_flags(board=sample_board)
        max_parallel = int(flags.get("max_parallel_subagents", 3))

    results: list[dict] = []
    with ThreadPoolExecutor(max_workers=max_parallel) as pool:
        futures = {
            pool.submit(
                pipeline.run,
                fixture_path=fixture_path,
                db_path=db_root / f"{board}.sqlite3",
                output_html_path=output_root / board / "report.html",
            ): board
            for board, fixture_path in fixtures_by_board.items()
        }
        for fut in as_completed(futures):
            board = futures[fut]
            try:
                summary = fut.result()
                summary["worker_board"] = board
                results.append(summary)
            except Exception as exc:
                results.append({"worker_board": board, "error": str(exc)})
    return results


def write_summary(results: Iterable[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(list(results), indent=2), encoding="utf-8")
