# Skill: Run Pipeline

## Description

Execute the sprint analytics pipeline for a board: fetch Jira data, enrich tickets, detect flags, compute metrics, save to database, export sprint.ai.json.

## Usage

```
/run-pipeline --board ALPHA
/run-pipeline --board ALPHA --sprint ALPHA_0.2.1 --fresh
```

## Parameters

| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| `--board` | Yes | — | Board to run pipeline for (ALPHA, BETA, GAMMA) |
| `--sprint` | No | Active sprint | Sprint name to target |
| `--day` | No | Auto-detect | Sprint day number |
| `--fresh` | No | false | Re-fetch from Jira, overwrite today's cache |
| `--format` | No | json | Output format |

## Prerequisites

- System must be healthy (run `/system-check` first if unsure)
- Jira credentials configured in `.env`
- Config files valid: `config.yaml`, `team_config.yaml`, `flags.yaml`

## Execution Steps

### 1. Load Configuration

- Read `config.yaml`, `team_config.yaml`, `flags.yaml`
- Determine target board and sprint
- Calculate current sprint day number

### 2. Determine Sprint

- If sprint name provided via `--sprint`: use it
- If not: find the active sprint for the board
- Record sprint metadata (start date, end date, state)

### 3. Fetch Data

- **MCP-first**: When running as a Claude skill, use Atlassian MCP tools
- **API fallback**: When running from CLI, use `sprint_pulse/jira/client.py`
- Fetch all sprint issues with changelogs, comments, and worklogs
- Batch enrichment (5 concurrent requests)

### 3b. Fetch Epics

- `fetch_sprint_epics()` — fetches epics linked to sprint tickets
- Gets ALL children per epic via JQL (not just sprint children)
- Returns raw epic data for enrichment

### 4. Enrich Tickets

- `TicketEnricher(config, sprint_info).enrich_all(detailed_issues)` → list[EnrichedTicket]
- Computes 80+ fields: status history, lifecycle dates, worklogs, quality metrics, DoR compliance
- Lifecycle status names read from `config.lifecycle_statuses` (zero hardcoded strings)
- Reference date clamped to sprint end for closed sprints
- `DayCache` stores enriched data at `output/{sprint}/day-{N}/enriched.json`
- Skip re-enrichment if cache exists (use `--fresh` to re-fetch from Jira and overwrite today's cache)

### 4b. Enrich Epics

- `enrich_epics()` — computes completion %, child rollups, status categories
- Uses ALL children (not just sprint-scoped) for accurate completion metrics

### 5. Detect Flags

- Load active flags for the current board
- Filter by tracking window (track_from_day ≤ current_day ≤ stop_at_day)
- Run each flag detector against enriched tickets
- `FlagEngine.run()` accepts `epics` parameter for Flag 11 (epic_children_done)
- Collect FlagResult objects with flagged tickets and evidence

### 6. Compute Metrics

- Sprint-level: completion rate, QA pass rate, velocity, etc.
- Per-developer: tickets, worklogs, cycle time, flags
- Benchmarks: compare against day-by-day expected progress

### 7. Save to Database

- Upsert sprint record
- Save ticket snapshots for today
- Save flag run results
- Save sprint scores
- Save developer metrics
- Save ticket flag history
- Save epic snapshots

### 8. Export

- Generate `sprint.ai.json` — compact AI-optimized output (~7K tokens), includes `epics` array and `delta` section
- Delta is computed by comparing today's enriched data against the previous day's snapshot and merged inline

The core command:
```bash
python -m sprint_pulse run --board {BOARD} [--sprint {SPRINT}] [--fresh]
```

## Outputs

- `output/{sprint}/day-{N}/sprint.ai.json` (includes delta)
- `output/{sprint}/day-{N}/enriched.json` (cache + Excel input)
- Updated `output/sprint-pulse.db`

## Context Budget

~12K tokens (config.yaml + team_config.yaml + flags.yaml + CLI output)

## Return Schema (for orchestrator)

When invoked as a sub-agent by the orchestrator, return this JSON after completion:

```json
{
  "board": "ALPHA",
  "sprint": "ALPHA_0.3.2",
  "day": 5,
  "tickets_enriched": 24,
  "flags_detected": 12,
  "output_path": "output/ALPHA_0.3.2/day-5/",
  "status": "success"
}
```

If any step fails, return: `{"board": "...", "status": "failed", "step": "...", "error": "..."}`

## Error Handling

- **Empty sprint**: No issues found — generate a "no data" report, don't error
- **Jira timeout**: Retry with backoff (3 attempts), then fail gracefully
- **Missing credentials**: Fail fast with clear error message pointing to `.env`
- **Sprint not found**: Show recent sprints and ask user to specify

## Quality Self-Evaluation

After execution, verify:
- [ ] Pipeline ran to completion without errors
- [ ] `sprint.ai.json` was generated and is non-empty
- [ ] Flag count is reasonable (not zero unless sprint just started)
- [ ] Database was updated with today's snapshot
- [ ] Delta section present (except on first run)
