"""Sprint-level metrics — deterministic aggregations from ticket state."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Iterable, Mapping


@dataclass
class SprintMetrics:
    sprint_id: str
    total_points: int
    completed_points: int
    in_progress_points: int
    to_do_points: int
    completion_ratio: float
    ticket_count: int
    completed_ticket_count: int


@dataclass
class AssigneeLoad:
    sprint_id: str
    assignee: str
    points: int
    tickets: int


@dataclass
class StoryTypeBreakdown:
    sprint_id: str
    story_type: str
    points: int
    tickets: int


def compute_sprint_metrics(
    sprint_id: str, tickets: Iterable[Mapping[str, object]]
) -> SprintMetrics:
    total = completed = in_progress = to_do = 0
    ticket_count = completed_tickets = 0
    for t in tickets:
        pts = int(t.get("story_points") or 0)
        status = str(t.get("status", "")).lower()
        total += pts
        ticket_count += 1
        if "done" in status:
            completed += pts
            completed_tickets += 1
        elif "progress" in status:
            in_progress += pts
        else:
            to_do += pts
    ratio = (completed / total) if total else 0.0
    return SprintMetrics(
        sprint_id=sprint_id,
        total_points=total,
        completed_points=completed,
        in_progress_points=in_progress,
        to_do_points=to_do,
        completion_ratio=round(ratio, 4),
        ticket_count=ticket_count,
        completed_ticket_count=completed_tickets,
    )


def compute_assignee_load(
    sprint_id: str, tickets: Iterable[Mapping[str, object]]
) -> list[AssigneeLoad]:
    points_by: dict[str, int] = defaultdict(int)
    tickets_by: dict[str, int] = defaultdict(int)
    for t in tickets:
        name = str(t.get("assignee") or "Unassigned")
        points_by[name] += int(t.get("story_points") or 0)
        tickets_by[name] += 1
    return [
        AssigneeLoad(sprint_id=sprint_id, assignee=name, points=points_by[name], tickets=tickets_by[name])
        for name in sorted(points_by)
    ]


def compute_story_type_breakdown(
    sprint_id: str, tickets: Iterable[Mapping[str, object]]
) -> list[StoryTypeBreakdown]:
    points_by: dict[str, int] = defaultdict(int)
    tickets_by: dict[str, int] = defaultdict(int)
    for t in tickets:
        story_type = str(t.get("story_type") or "unknown")
        points_by[story_type] += int(t.get("story_points") or 0)
        tickets_by[story_type] += 1
    return [
        StoryTypeBreakdown(sprint_id=sprint_id, story_type=st, points=points_by[st], tickets=tickets_by[st])
        for st in sorted(points_by)
    ]
