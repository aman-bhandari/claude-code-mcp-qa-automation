# Skill: Compare Sprints

## Description

Compare metrics across 2 or more sprints to identify trends, improvements, and regressions. Uses historical database data — no current pipeline run needed.

## Delegation

This skill queries historical database data across multiple sprints (~9K+ tokens, scaling with sprint count). When called from the orchestrator or when comparing 3+ sprints, it should run in a sub-agent via the Agent tool.

## Usage

```
/compare-sprints --board ALPHA --sprints ALPHA_0.2.0,ALPHA_0.2.1
/compare-sprints --board ALPHA --last 3
/compare-sprints --board ALPHA --quarter Q1-2026
```

## Parameters

| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| `--board` | Yes | — | Board to compare |
| `--sprints` | No | — | Comma-separated sprint names to compare |
| `--last` | No | 2 | Compare last N sprints for the board |
| `--quarter` | No | — | Compare all sprints in a quarter (e.g., Q1-2026) |

One of `--sprints`, `--last`, or `--quarter` must be provided.

## Prerequisites

- At least 2 sprints must have data in the database
- Pipeline must have run for each sprint being compared

## Execution Steps

### 1. Resolve Parameters

- Determine which sprints to compare:
  - `--sprints`: use the listed names directly
  - `--last N`: query DB for the N most recent sprints on this board
  - `--quarter`: query DB for all sprints within the quarter's date range

### 2. Load Data

Read these files:

```
config.yaml                                 # Benchmarks
docs/guidelines/comparison/_main.md          # Comparison guidelines
output/{sprint}/sprint.trends.json           # Cross-sprint trend data (day-matched comparisons)
```

`sprint.trends.json` provides pre-computed day-matched metrics, carry-over trends, deployment frequency, and risk score averages across sprints. Use it as the primary source for metrics comparison when available. Fall back to SQLite when unavailable.

**Query SQLite database** (`output/sprint-pulse.db`):

```sql
-- Find sprints (for --last or --quarter)
SELECT sprint_name, start_date, end_date, state
FROM sprints
WHERE board_name = '{board}'
ORDER BY start_date DESC
LIMIT {N};

-- Final-day metrics for each sprint
SELECT sprint_name, completion_rate, weighted_completion, qa_pass_rate,
       review_coverage, flow_efficiency, estimation_accuracy,
       health_score, total_flags_triggered, cycle_time_days
FROM sprint_scores
WHERE sprint_name IN ({sprint_list}) AND board_name = '{board}'
  AND day_number = (SELECT MAX(day_number) FROM sprint_scores
                    WHERE sprint_name = ss.sprint_name AND board_name = ss.board_name)
ORDER BY start_date;

-- Developer metrics per sprint
SELECT sprint_name, developer_name, total_tickets, done_tickets,
       worklog_hours, completion_rate, flag_count
FROM developer_metrics
WHERE sprint_name IN ({sprint_list}) AND board_name = '{board}'
ORDER BY sprint_name, developer_name;

-- Flag totals per sprint (aggregate)
SELECT sprint_name, flag_id, flag_name, category,
       MAX(flagged_ticket_count) as peak_tickets,
       COUNT(*) as days_active
FROM flag_runs
WHERE sprint_name IN ({sprint_list}) AND board_name = '{board}'
GROUP BY sprint_name, flag_id
ORDER BY sprint_name, days_active DESC;
```

**NEVER read enriched.json or sprint.ai.json.**

### 3. Generate Report

Follow `docs/guidelines/comparison/_main.md`. Key analysis:

**Metrics Table** — side-by-side comparison with trend arrows
**Flag Trends** — which flags are increasing/decreasing across sprints
**Team Trends** — developer performance comparison (sensitive — focus on process, not blame)
**Process Improvement** — DoR, QA rework, scope stability trends
**Takeaways** — top 3 improvements, top 3 remaining issues

### 4. Save Report

Save to: `reports/comparison/{board}/{board}_{sprint_range}_{date}.md`

Example: `reports/comparison/ALPHA/ALPHA_0.2.0_vs_0.2.1_2026-04-15.md`

### 5. Confirm

Print: board, sprints compared, key trend summary, file path.

## Context Budget

- `sprint.trends.json`: ~3K tokens (pre-computed cross-sprint trends, optional)
- SQLite results: ~5K tokens (scales with sprint count)
- Guideline: ~2K tokens
- `config.yaml`: ~2K tokens
- **Total input**: ~12K tokens max

## Error Handling

- Only 1 sprint in DB: "Need at least 2 sprints to compare. Only found {sprint_name}."
- Missing metrics for a sprint: Include sprint in comparison but mark metrics as "N/A."
- Board not found: "No data for board '{board}'. Available boards: ALPHA, BETA, GAMMA."
