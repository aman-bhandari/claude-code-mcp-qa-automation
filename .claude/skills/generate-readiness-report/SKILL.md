# Skill: Generate Readiness Report

## Description

Generate a pre-sprint Definition of Ready (DoR) assessment. Evaluates whether tickets are properly prepared before the sprint starts or in the first days.

## Usage

```
/generate-readiness-report
/generate-readiness-report --board ALPHA
/generate-readiness-report --board ALPHA --sprint ALPHA_0.2.2
```

## Parameters

| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| `--board` | No | All enabled boards | Which board(s) to assess |
| `--sprint` | No | Latest sprint | Sprint name to assess |

## Prerequisites

- Pipeline must have run for the target sprint (day -1 or day 1 data must exist)
- Best run on day -1 (pre-sprint) or day 1

## Execution Steps

### 1. Resolve Parameters

- Determine target board(s): if `--board` specified use it, else use all boards from `config.yaml > scheduling > reports > readiness > boards`
- Determine sprint: if `--sprint` specified use it, else find latest sprint from `output/`

### 2. Load Data (per board)

Read these files and ONLY these files:

```
output/{sprint}/day-{N}/sprint.ai.json     # Sprint data (earliest available day)
output/{sprint}/day-{N}/sprint.detail.json # Secondary analytics (carry-over, capacity baseline)
team_config.yaml                            # Team capacity and roles
config.yaml                                 # Board settings
docs/guidelines/readiness/_main.md          # Readiness report guidelines
```

`sprint.detail.json` provides: `carryOverWatch` (Section 5b), `capacityUtilization[]` (Section 3 enhancement). If this file does not exist, generate the report without these enhancements.

**NEVER read `enriched.json`.**

### 3. Generate Report

Follow `docs/guidelines/readiness/_main.md`. Key analysis:

**DoR Compliance** — check flags array for DoR-related flags:
- Flag 3 / 25: Missing description
- Flag 6: No due date
- Flag 9: No acceptance criteria
- Flag 13: Missing components
- Flag 15: Missing time estimate
- Flag 40: Epic missing BRD
- Flag 41: Ticket missing Figma (FE only)
- Flag 42: Epic missing Figma

Calculate: `dor_compliance_pct = (tickets_without_DoR_flags / total_tickets) * 100`

**Capacity** — from `teamSummary` + `team_config.yaml`:
- Map each developer's ticket load against their available hours
- Flag overloads (estimated hours > available * 1.2)

**Dependencies** — from `tickets` array:
- Identify blocked tickets (isBlocked = true)
- Count tickets already overdue on day 1

### 4. Save Report

Save to: `reports/readiness/{board}/{sprint}/{sprint}_{board}_{date}.md`

### 5. Confirm

Print: board, sprint, DoR compliance %, verdict (Ready/Conditionally Ready/Not Ready), file path.

## Context Budget

- `sprint.ai.json`: ~5K tokens
- `sprint.detail.json`: ~4K tokens (carry-over and capacity analytics, optional)
- `team_config.yaml`: ~2K tokens
- Guideline: ~2K tokens
- `config.yaml`: ~2K tokens (boards + workflow sections only)
- **Total input**: ~15K tokens max

## Return Schema (for orchestrator)

When invoked as a sub-agent by the orchestrator, return this JSON after completion:

```json
{
  "board": "ALPHA",
  "sprint": "ALPHA_0.3.2",
  "report_path": "reports/readiness/ALPHA/ALPHA_0.3.2/ALPHA_0.3.2_WL_2026-04-07.md",
  "verdict": "Conditionally Ready",
  "dor_compliance_pct": 74,
  "overloaded_developers": 2,
  "blocked_tickets": 1,
  "status": "success"
}
```

If any step fails, return: `{"board": "...", "status": "failed", "step": "...", "error": "..."}`

## Error Handling

- No day -1 or day 1 data: "No early sprint data found. Run /run-pipeline for day 1 first."
- No team_config data for board: skip capacity section, note "Team configuration not available for {board}."
