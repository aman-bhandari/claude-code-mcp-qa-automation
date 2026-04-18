# Skill: Generate Retrospective

## Description

Generate an end-of-sprint scored review where **flags are the primary analytical lens**. Evaluates sprint performance across 11 sections — from scorecard to carry-over register — answering: *"What process failures caused this sprint's outcome, and who/when/where did they manifest?"*

## Delegation

This skill loads ~20K tokens (15 SQL queries + sprint.ai.json + guidelines + config). When called from the orchestrator, it MUST run in a sub-agent via the Agent tool. When invoked standalone (`/generate-retrospective`), it can run in the main thread but benefits from sub-agent isolation for large sprints.

## Usage

```
/generate-retrospective
/generate-retrospective --board ALPHA
/generate-retrospective --board ALPHA --sprint ALPHA_0.2.1
```

## Parameters

| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| `--board` | No | All enabled boards | Which board(s) to review |
| `--sprint` | No | Latest sprint | Sprint name to review |

## Prerequisites

- Pipeline must have run for the target sprint (final day data must exist)
- Best run after sprint ends (day 10 or later, or sprint state = "closed")

## Execution Steps

### 1. Resolve Parameters

- Determine target board(s): if `--board` specified use it, else use all boards from `config.yaml > scheduling > reports > retrospective > boards`
- Determine sprint: if `--sprint` specified use it, else find latest sprint from `output/`
- Find the highest day number available for the sprint (`MAX(day_number)`)

### 2. Load Data (per board)

Read these files and ONLY these files:

```
output/{sprint}/day-{N}/sprint.ai.json       # Final day snapshot
output/{sprint}/day-{N}/sprint.history.json  # Reconstructed sprint history (full Jira changelog analysis)
output/{sprint}/day-{N}/sprint.detail.json   # Granular analytics (status durations, deployments, capacity, blockers)
output/{sprint}/sprint.trends.json           # Cross-sprint trend data for historical context
config.yaml                                 # Benchmarks, severity rankings
docs/guidelines/retrospective/_main.md       # Retrospective guidelines
```

`sprint.detail.json` provides: `statusDurations[]` (Section 6b), `deploymentActivity` (Section 7b), `capacityUtilization[]` (Section 8), `carryOverWatch` (Section 10). If this file does not exist, generate the report without these enhancements.

`sprint.trends.json` provides cross-sprint metrics for historical context in the scorecard. If unavailable, skip trend references.

**When `sprint.history.json` exists**, use it to enrich all sections with full-sprint context. This file provides reconstructed daily states, Say-Do ratio data, work story transitions, and retroactive flag analysis derived from Jira changelog history.

**Query SQLite database** (`output/sprint-pulse.db`) using all 15 named queries below. Filter by `sprint_name = ?` only — **DO NOT add `AND board_name = ?`** (that column does not exist on `flag_runs`, `sprint_scores`, or `ticket_flag_history`).

```sql
-- Q1: Flag Activity Map (Section 2)
SELECT fr.flag_id, fr.flag_name, fr.category, fr.severity,
    MIN(fr.day_number) AS first_day, MAX(fr.day_number) AS last_day,
    (MAX(fr.day_number) - MIN(fr.day_number) + 1) AS persistence_days,
    MAX(fr.flagged_ticket_count) AS peak_ticket_count,
    CASE WHEN MAX(fr.day_number) = (SELECT MAX(day_number) FROM flag_runs WHERE sprint_name = fr.sprint_name)
         THEN 0 ELSE 1 END AS was_resolved
FROM flag_runs fr WHERE fr.sprint_name = ?
GROUP BY fr.flag_id, fr.flag_name, fr.category, fr.severity
ORDER BY persistence_days DESC, peak_ticket_count DESC;

-- Q2: Category Flag Burden (Section 2 summary + Section 3 ordering)
SELECT fr.category,
    COUNT(DISTINCT fr.flag_id) AS distinct_flags,
    SUM(fr.flagged_ticket_count) AS total_flag_instances,
    COUNT(DISTINCT tfh.ticket_key) AS unique_tickets_affected
FROM flag_runs fr
JOIN ticket_flag_history tfh ON tfh.sprint_name = fr.sprint_name
    AND tfh.flag_id = fr.flag_id AND tfh.day_number = fr.day_number
WHERE fr.sprint_name = ?
GROUP BY fr.category ORDER BY total_flag_instances DESC;

-- Q3: Per-Flag Ticket Detail with Assignee + Phase (Section 3 core)
SELECT tfh.flag_id, tfh.flag_name, tfh.category, tfh.severity,
    tfh.ticket_key, tfh.day_number, tfh.reason,
    ts.assignee, ts.status, ts.summary, ts.parent_key,
    CASE WHEN tfh.day_number <= 2 THEN 'Early'
         WHEN tfh.day_number <= 7 THEN 'Mid'
         WHEN tfh.day_number <= 10 THEN 'Late'
         ELSE 'Buffer' END AS sprint_phase
FROM ticket_flag_history tfh
JOIN ticket_snapshots ts ON ts.sprint_name = tfh.sprint_name
    AND ts.ticket_key = tfh.ticket_key AND ts.day_number = tfh.day_number
WHERE tfh.sprint_name = ?
ORDER BY tfh.category, tfh.flag_id, tfh.day_number, tfh.ticket_key;

-- Q4: First/Last Flag Occurrence per Ticket (Section 3 detail)
SELECT tfh.flag_id, tfh.flag_name, tfh.ticket_key, ts.assignee,
    MIN(tfh.day_number) AS first_flagged_day,
    MAX(tfh.day_number) AS last_flagged_day,
    COUNT(*) AS days_flagged, MIN(tfh.reason) AS sample_reason
FROM ticket_flag_history tfh
JOIN ticket_snapshots ts ON ts.sprint_name = tfh.sprint_name
    AND ts.ticket_key = tfh.ticket_key
    AND ts.day_number = (SELECT MIN(t2.day_number) FROM ticket_flag_history t2
                         WHERE t2.sprint_name = tfh.sprint_name
                           AND t2.ticket_key = tfh.ticket_key
                           AND t2.flag_id = tfh.flag_id)
WHERE tfh.sprint_name = ?
GROUP BY tfh.flag_id, tfh.flag_name, tfh.ticket_key, ts.assignee
ORDER BY tfh.flag_id, first_flagged_day;

-- Q5: Flags per Epic (Section 3 epic linkage)
SELECT ts.parent_key AS epic_key, tfh.flag_id, tfh.flag_name, tfh.category,
    COUNT(DISTINCT tfh.ticket_key) AS flagged_tickets,
    MIN(tfh.day_number) AS first_day, MAX(tfh.day_number) AS last_day
FROM ticket_flag_history tfh
JOIN ticket_snapshots ts ON ts.sprint_name = tfh.sprint_name
    AND ts.ticket_key = tfh.ticket_key AND ts.day_number = tfh.day_number
WHERE tfh.sprint_name = ? AND ts.parent_key IS NOT NULL
GROUP BY ts.parent_key, tfh.flag_id, tfh.flag_name, tfh.category
ORDER BY ts.parent_key, flagged_tickets DESC;

-- Q6: Flags by Assignee with Category Breakdown (Section 8)
SELECT ts.assignee, tfh.category,
    COUNT(DISTINCT tfh.flag_id) AS distinct_flags,
    COUNT(DISTINCT tfh.ticket_key) AS tickets_affected,
    SUM(CASE WHEN tfh.severity IN ('high','critical') THEN 1 ELSE 0 END) AS high_sev_instances
FROM ticket_flag_history tfh
JOIN ticket_snapshots ts ON ts.sprint_name = tfh.sprint_name
    AND ts.ticket_key = tfh.ticket_key AND ts.day_number = tfh.day_number
WHERE tfh.sprint_name = ? AND ts.assignee IS NOT NULL
GROUP BY ts.assignee, tfh.category ORDER BY ts.assignee, tickets_affected DESC;

-- Q7: Developer Metrics Final Day (Section 8 summary table)
SELECT developer_name, total_tickets, done_tickets, worklog_hours,
    flag_count, qa_rejection_count, code_review_skipped_count,
    completion_rate, regression_count, estimation_accuracy
FROM developer_metrics
WHERE sprint_name = ?
  AND day_number = (SELECT MAX(day_number) FROM developer_metrics WHERE sprint_name = ?)
ORDER BY completion_rate DESC;

-- Q8: Phase × Flag Category Matrix (Section 9)
SELECT
    CASE WHEN tfh.day_number <= 2 THEN 'Early (Days 1-2)'
         WHEN tfh.day_number <= 7 THEN 'Mid (Days 3-7)'
         WHEN tfh.day_number <= 10 THEN 'Late (Days 8-10)'
         ELSE 'Buffer (Days 11+)' END AS sprint_phase,
    tfh.category,
    COUNT(DISTINCT tfh.flag_id) AS distinct_flags,
    COUNT(DISTINCT tfh.ticket_key) AS tickets_affected
FROM ticket_flag_history tfh WHERE tfh.sprint_name = ?
GROUP BY sprint_phase, tfh.category
ORDER BY CASE sprint_phase WHEN 'Early (Days 1-2)' THEN 1 WHEN 'Mid (Days 3-7)' THEN 2
    WHEN 'Late (Days 8-10)' THEN 3 ELSE 4 END, tickets_affected DESC;

-- Q9: Sprint Health Trajectory (Section 9)
SELECT day_number, health_score, total_flags_triggered, completion_rate,
    CASE WHEN day_number <= 2 THEN 'Early' WHEN day_number <= 7 THEN 'Mid'
         WHEN day_number <= 10 THEN 'Late' ELSE 'Buffer' END AS sprint_phase
FROM sprint_scores WHERE sprint_name = ? ORDER BY day_number;

-- Q10: Flag Escalations (Section 9)
SELECT fr1.flag_id, fr1.flag_name, fr1.category, fr1.day_number AS escalation_day,
    fr1.severity AS new_severity, fr1.flagged_ticket_count
FROM flag_runs fr1
WHERE fr1.sprint_name = ? AND fr1.severity IN ('high','critical')
  AND EXISTS (SELECT 1 FROM flag_runs fr2
              WHERE fr2.sprint_name = fr1.sprint_name AND fr2.flag_id = fr1.flag_id
                AND fr2.day_number < fr1.day_number
                AND fr2.severity NOT IN ('high','critical'))
ORDER BY fr1.day_number;

-- Q11: Carry-Over Tickets with Flag Context (Section 10)
SELECT ts.ticket_key, ts.summary, ts.status, ts.assignee,
    ts.days_in_current_status, ts.parent_key AS epic_key,
    GROUP_CONCAT(DISTINCT tfh.flag_name, ' | ') AS active_flags,
    GROUP_CONCAT(DISTINCT tfh.category, ' | ') AS flag_categories
FROM ticket_snapshots ts
LEFT JOIN ticket_flag_history tfh ON tfh.sprint_name = ts.sprint_name
    AND tfh.ticket_key = ts.ticket_key AND tfh.day_number = ts.day_number
WHERE ts.sprint_name = ?
  AND ts.day_number = (SELECT MAX(day_number) FROM ticket_snapshots WHERE sprint_name = ?)
  AND ts.status NOT IN ('Done', 'Closed')
ORDER BY ts.status, ts.assignee;

-- Q12: Commitment Drift (Section 4) — requires due_date column
SELECT ts.ticket_key, ts.summary, ts.assignee, ts.due_date,
    ts.first_ready_for_qa_date, ts.status, ts.sprint_worklog_hours,
    GROUP_CONCAT(DISTINCT tfh.flag_name, ' | ') AS flags
FROM ticket_snapshots ts
LEFT JOIN ticket_flag_history tfh ON tfh.sprint_name = ts.sprint_name
    AND tfh.ticket_key = ts.ticket_key
    AND tfh.day_number = (SELECT MAX(day_number) FROM ticket_snapshots WHERE sprint_name = ts.sprint_name)
WHERE ts.sprint_name = ?
  AND ts.day_number = (SELECT MAX(day_number) FROM ticket_snapshots WHERE sprint_name = ?)
  AND ts.due_date IS NOT NULL
ORDER BY ts.due_date;

-- Q13: QA Issue Log (Section 5)
SELECT ts.ticket_key, ts.summary, ts.assignee,
    ts.qa_failed_count, ts.regression_count, ts.code_review_skipped,
    ts.first_ready_for_qa_date, ts.first_in_test_date, ts.resolution_date,
    GROUP_CONCAT(DISTINCT tfh.reason, ' | ') AS flag_reasons,
    GROUP_CONCAT(DISTINCT tfh.flag_name, ' | ') AS qa_flags
FROM ticket_snapshots ts
LEFT JOIN ticket_flag_history tfh ON tfh.sprint_name = ts.sprint_name
    AND tfh.ticket_key = ts.ticket_key
    AND tfh.flag_id IN (7, 17, 19, 22, 32)
WHERE ts.sprint_name = ?
  AND ts.day_number = (SELECT MAX(day_number) FROM ticket_snapshots WHERE sprint_name = ?)
  AND (ts.qa_failed_count > 0 OR ts.regression_count > 0 OR ts.code_review_skipped = 1)
GROUP BY ts.ticket_key
ORDER BY ts.qa_failed_count DESC, ts.regression_count DESC;

-- Q14: Status Aging & Flow Breakdown (Section 6)
SELECT ts.ticket_key, ts.summary, ts.assignee, ts.status,
    ts.first_in_dev_date, ts.first_in_code_review_date,
    ts.first_ready_for_qa_date, ts.first_in_test_date,
    ts.resolution_date, ts.cycle_time_days,
    ts.sprint_worklog_hours, ts.days_in_current_status,
    GROUP_CONCAT(DISTINCT tfh.flag_name, ' | ') AS active_flags
FROM ticket_snapshots ts
LEFT JOIN ticket_flag_history tfh ON tfh.sprint_name = ts.sprint_name
    AND tfh.ticket_key = ts.ticket_key
    AND tfh.day_number = (SELECT MAX(day_number) FROM ticket_snapshots WHERE sprint_name = ts.sprint_name)
WHERE ts.sprint_name = ?
  AND ts.day_number = (SELECT MAX(day_number) FROM ticket_snapshots WHERE sprint_name = ?)
  AND ts.first_in_dev_date IS NOT NULL
GROUP BY ts.ticket_key
ORDER BY ts.cycle_time_days DESC;

-- Q15: Say-Do Ratio (Section 7)
SELECT 'committed' AS snapshot, COUNT(*) AS ticket_count,
    SUM(original_estimate_hours) AS total_hours
FROM ticket_snapshots WHERE sprint_name = ? AND day_number = 1
UNION ALL
SELECT 'final' AS snapshot, COUNT(*) AS ticket_count,
    SUM(original_estimate_hours) AS total_hours
FROM ticket_snapshots WHERE sprint_name = ?
  AND day_number = (SELECT MAX(day_number) FROM ticket_snapshots WHERE sprint_name = ?)
  AND status IN ('Done', 'Closed')
UNION ALL
SELECT 'added_mid_sprint' AS snapshot, COUNT(*) AS ticket_count,
    SUM(original_estimate_hours) AS total_hours
FROM ticket_snapshots WHERE sprint_name = ?
  AND day_number = (SELECT MAX(day_number) FROM ticket_snapshots WHERE sprint_name = ?)
  AND was_added_mid_sprint = 1;
```

**NEVER read `enriched.json`.**

### 3. Generate Report

Follow `docs/guidelines/retrospective/_main.md`. Generate all 11 sections:

1. **Sprint Scorecard** — final metrics table + benchmark comparison + letter grade + 2-sentence headline naming the dominant flag category
2. **Flag Activity Map** — Q1 table (every flag that fired: persistence days, peak count, resolved?) + Q2 category burden summary
3. **Process Category Breakdown** — one subsection per flag category ordered by Q2 burden; each subsection: affected tickets (Q3), first/last occurrence (Q4), epic linkage (Q5)
4. **Commitment Drift Register** — Q12 table: due date vs first-ready-for-QA date, compute drift in days, list associated flags
5. **QA Issue Log** — Q13 table: QA failures, regressions, skipped code reviews per ticket with flag reasons
6. **Status Aging & Flow Breakdown** — Q14 table per ticket with milestone dates + flow efficiency % computed as `(sprint_worklog_hours / (cycle_time_days * 8)) * 100`
7. **Say-Do Ratio & Estimation Health** — Q15: committed vs delivered ticket count + hours; scope creep (added_mid_sprint) quantified
8. **Team Lens: Flags by Assignee** — Q6 category breakdown per person + Q7 developer metrics table; frame as process patterns, no blame
9. **Sprint Phase Analysis** — Q8 phase × category matrix + Q9 health trajectory narrative + Q10 escalation events
10. **Carry-Over Register** — Q11 table: each incomplete ticket with status, days stuck, and the flag that explains the stall
11. **Recommendations** — max 5; each must cite a specific flag ID + the measurable impact from the data above

### 3b. History-Enriched Sections

When `sprint.history.json` is available (it always is after pipeline v4+), use it to enrich these sections:

1. **Section 1 (Scorecard)**: If `pipelineStartDay > 1`, add a note in the header: "Pipeline started on day {N}; earlier data reconstructed from Jira history." Use `dailySummary` to show completion trajectory from day 1.

2. **Section 2 (Flag Activity Map)**: Retroactive flags from `retroactiveFlags.byPhase` are now backfilled into the DB. The SQL queries (Q1, Q2) will include them. When writing about flags that appeared before the pipeline started, use the framing: "Jira history indicates Flag X conditions were present from day N" (not "Flag X fired"). Annotate with "(reconstructed)" where clarity helps.

3. **Section 3 (Process Category Breakdown)**: Use `workStory.keyTransitions` to provide narrative arc — what actually happened each day (e.g., "Day 3 saw 12 tickets move into development; by day 7 the first tickets reached code review").

4. **Section 7 (Say-Do Ratio)**: When Q15 returns 0 for the 'committed' row (no day-1 pipeline snapshot), use `sayDo` from sprint.history.json:
   - `committedDay1` = committed ticket count
   - `committedHoursDay1` = committed hours
   - Say-Do ratio = `deliveredFinal / committedDay1`
   - Note: "Day 1 commitment reconstructed from Jira sprint membership history."

5. **Section 9 (Sprint Phase Analysis)**: The phase x category matrix (Q8) now includes retroactive flags in Early/Mid/Late phases. Use `dailySummary` from sprint.history.json to narrate the health trajectory across ALL phases. Don't say "No flags fired during Early/Mid/Late" — there is now data for those phases.

6. **Section 11 (Recommendations)**: Recommendations can now cite patterns from the full sprint, not just the tracked days.

### 4. Save Report

Save to: `reports/retrospective/{board}/{sprint}/{sprint}_{board}_{date}.md`

### 5. Confirm

Print: board, sprint, grade, completion rate, flag count, carry-over count, file path.

## Context Budget

- `sprint.ai.json`: ~5K tokens
- `sprint.history.json`: ~3-5K tokens
- `sprint.detail.json`: ~4K tokens (granular analytics, optional)
- `sprint.trends.json`: ~2K tokens (cross-sprint trends, optional)
- SQLite results (15 queries + flag_feedback): ~12K tokens
- Guideline: ~3K tokens
- `config.yaml`: ~2K tokens
- **Total input**: ~31K tokens max

## Return Schema (for orchestrator)

When invoked as a sub-agent by the orchestrator, return this JSON after completion:

```json
{
  "board": "ALPHA",
  "sprint": "ALPHA_0.3.2",
  "report_path": "reports/retrospective/ALPHA/ALPHA_0.3.2/ALPHA_0.3.2_retro_2026-04-07.md",
  "grade": "B",
  "completion_rate": 0.78,
  "weighted_completion": 0.82,
  "total_flags": 45,
  "carry_over_count": 3,
  "say_do_ratio": 0.85,
  "status": "success"
}
```

If any step fails, return: `{"board": "...", "status": "failed", "step": "...", "error": "..."}`

## Error Handling

- Only 1-2 days of data: "Limited data available. Trend analysis requires 3+ days."
- No sprint_scores in DB: Generate without trend analysis, note "Historical data not available."
- Sprint still active: Warn "Sprint is still active (day {N}). Retrospective is most accurate after sprint closes."
- Q12 returns no rows: Section 4 shows "No due dates recorded for this sprint."
- `sprint.history.json` missing: Generate without history enrichment, note "History reconstruction not available — report covers pipeline-tracked days only."
- `pipelineStartDay > 1`: Full history is reconstructed from Jira changelog. Include reconstruction note in report header.
