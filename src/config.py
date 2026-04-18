"""Flag-gated config loader.

The key pattern: no behavior toggle lives inline in code. Every "should I do X?"
decision reads a flag from flags.yaml. Board-scoped overrides are applied on
top of globals.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

import yaml


REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_FLAGS_PATH = REPO_ROOT / "config" / "flags.yaml"
DEFAULT_TEAM_PATH = REPO_ROOT / "config" / "team_config.yaml"


@dataclass(frozen=True)
class ResolvedFlags:
    """Flag values resolved for a specific board.

    Global flags + board-scoped overrides, merged. Immutable once resolved.
    """

    values: Mapping[str, Any]

    def get(self, key: str, default: Any = None) -> Any:
        return self.values.get(key, default)

    def is_on(self, key: str) -> bool:
        return bool(self.values.get(key, False))


def load_flags(board: str, path: Path = DEFAULT_FLAGS_PATH) -> ResolvedFlags:
    """Load flags.yaml, apply board-scoped overrides, return a frozen view.

    Raises FileNotFoundError if the flags file is missing. Raises KeyError if
    the board has no entry AND global is missing (indicates a malformed file).
    """
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    globals_ = dict(raw.get("global", {}))
    overrides = dict(raw.get("boards", {}).get(board, {}))
    merged = {**globals_, **overrides}
    if not merged:
        raise KeyError(f"No flags resolved for board {board!r}; check flags.yaml")
    return ResolvedFlags(values=merged)


def load_team(path: Path = DEFAULT_TEAM_PATH) -> dict:
    """Load team_config.yaml."""
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def count_flags(path: Path = DEFAULT_FLAGS_PATH) -> int:
    """Count total flag entries (global + all board scopes)."""
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    total = len(raw.get("global", {}))
    for board_flags in raw.get("boards", {}).values():
        total += len(board_flags or {})
    return total
