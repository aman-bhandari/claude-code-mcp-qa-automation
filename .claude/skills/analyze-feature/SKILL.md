---
name: analyze-feature
description: Feature-level deep-dive — analyze an epic or feature across boards, sprints, and child tickets. Shows completion, risks, blockers, and timeline.
---

# Analyze Feature Skill

## Purpose

Deep-dive analysis of a single feature (epic) across boards and sprints. Shows completion status, child ticket breakdown, blockers, flag exposure, and estimated timeline. Uses both the local database (historical snapshots) and live Jira data (current state).

## Delegation

This skill fetches live Jira data via MCP + historical DB queries (~8-15K tokens depending on epic size). For large epics (50+ children), it should run in a sub-agent to avoid polluting the main thread's context.

## When to Invoke

- On `/analyze-feature` command
- When user asks about a specific epic, feature, or initiative
- When user wants to understand why a feature is delayed or blocked

## Data Dependencies (Load in This Order)

1. **Read**: `config.yaml` — board names, workflow statuses
2. **Read**: `flags.yaml` — active flag definitions (for flag exposure check)
3. **Database**: `output/sprint-pulse.db` — tables: `ticket_snapshots`, `epic_snapshots`, `flag_runs`, `ticket_flag_history`
4. **MCP**: `searchJiraIssuesUsingJql` — live epic + children state from Jira
5. **MCP** (optional): `getJiraIssue` — full epic details if needed

## Execution

### Step 1: Identify the Feature

- Accept epic key (e.g., `PROJ-123`), epic name, or feature keyword
- If ambiguous, search Jira for matching epics and ask user to confirm
- Fetch the epic via `getJiraIssue` MCP tool for full details

### Step 2: Fetch Child Tickets

- Use JQL: `"Epic Link" = {epic_key} OR parent = {epic_key}`
- Collect: key, summary, status, assignee, story points, issue type, priority
- Group by status category (to do / in progress / done)

### Step 3: Compute Feature Metrics

- **Completion %**: done children / total children (count-based and point-based)
- **Blocked tickets**: children with "blocked" status or blocker flag links
- **In-progress aging**: children in progress for 5+ days
- **Unassigned work**: children with no assignee
- **Sprint distribution**: which sprints contain children (current + past)

### Step 4: Check Flag Exposure

- Query `ticket_flag_history` for any children flagged in current/recent sprints
- Group flags by type and severity
- Highlight recurring flags (same ticket flagged in multiple runs)

### Step 5: Check Epic History (if available)

- Query `epic_snapshots` for completion % trend over time
- Show trajectory: is completion accelerating, stalling, or regressing?

### Step 6: Generate Analysis

Write a structured analysis:

```
## Feature: {epic_key} — {summary}

**Status**: {status} | **Owner**: {assignee} | **Completion**: {pct}%

### Child Ticket Breakdown
| Status | Count | Points | Assignees |
...

### Risks & Blockers
- {blocked tickets}
- {aging in-progress}
- {unassigned work}

### Flag Exposure
- {flagged children with details}

### Completion Trend
- {trajectory from epic_snapshots if available}

### Recommendation
- {actionable next steps}
```

## Output

- Feature analysis report (markdown, displayed to user)
- No file output unless user requests it

## Quality Self-Evaluation

After running, verify:
- [ ] Epic identified correctly (key matches user intent)
- [ ] All children fetched (JQL covers both Epic Link and parent)
- [ ] Metrics computed from live data, not stale cache
- [ ] Flags cross-referenced against actual flag history
- [ ] Recommendations are specific and actionable
