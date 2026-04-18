# Skill: Generate Daily Report

## Description

Generate a daily sprint analytics report for one or all boards. Report sections and verbosity are controlled per-board via `config.yaml`.

## Usage

```
/generate-daily-report
/generate-daily-report --board ALPHA
/generate-daily-report --board BETA --sprint ALPHA_0.2.1 --day 5
```

## Parameters

| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| `--board` | No | All enabled boards | Which board(s) to report on |
| `--sprint` | No | Latest sprint | Sprint name to report on |
| `--day` | No | Auto-detect | Sprint day number to report for |

## Prerequisites

- Pipeline must have run for the target sprint/day (`sprint.ai.json` must exist)
- Run `/run-pipeline` first if no data exists

## Execution Steps

### 1. Resolve Parameters

- Determine target board(s): if `--board` specified use it, else use all boards from `config.yaml > scheduling > reports > daily > boards`
- Determine sprint: if `--sprint` specified use it, else find latest sprint from `output/` directory
- Determine day: if `--day` specified use it, else use `config.yaml > sprint > report_day` or auto-calculate from dates

### 2. Load Data (per board)

Read these files and ONLY these files:

```
output/{sprint}/day-{N}/sprint.ai.json          # PRIMARY data source (~5K tokens, includes delta)
output/{sprint}/day-{N}/sprint.detail.json      # SECONDARY data source (~4K tokens, granular analytics)
config.yaml                                       # Board settings, workflow meanings, benchmarks
```

Delta data is inside `sprint.ai.json` under the `"delta"` key (may be `null` on first run).

`sprint.detail.json` provides: `statusDurations[]`, `commentAnalysis`, `carryOverWatch`, `blockerSummary`, `deploymentActivity`, `capacityUtilization[]`. If this file does not exist, generate the report without these enhancements.

**Load the daily report guideline:** read `docs/guidelines/daily/_main.md`

**Read per-board report config from `config.yaml > boards > {board}`:**
- `report_sections` — which sections to include (in order)
- `verbosity.daily` — detail level: "detailed" | "balanced" | "summary"
- `max_report_words.daily` — approximate word limit

**NEVER read `enriched.json`. NEVER read all guidelines at once.**

### 3. Generate Report

Follow the loaded guideline to write the report. Key inputs from `sprint.ai.json`:

- `metrics` object → Status Summary, Timeline, Quality sections
- `flags` array → Flag Alert section (group by severity, include ticket keys and reasons)
- `tickets` array → Risk & Blockers (filter by isBlocked, isOverdue, high flagCount)
- `teamSummary` array → Capacity section (per-developer metrics)
- `delta` section (inside sprint.ai.json) → Delta emphasis ("Since yesterday: ...")

Use `config.yaml > workflow > status_meaning` to explain ambiguous statuses.
Use `config.yaml > benchmarks` to contextualize metrics against expected ranges.

### 4. Save Report

Save to: `reports/daily/{board}/{sprint}/{sprint}_{board}_day{N}_{date}.md`

Example: `reports/daily/ALPHA/ALPHA_0.3.2/ALPHA_0.3.2_WL_day5_2026-04-07.md`

### 5. Confirm

Print summary: board, sprint, day, file path, key metrics (completion rate, health score, flag count).

## Context Budget

- `sprint.ai.json`: ~7K tokens (includes delta section)
- `sprint.detail.json`: ~4K tokens (granular analytics, optional)
- Guideline: ~2K tokens
- `config.yaml`: ~3K tokens (read only boards + workflow + benchmarks sections)
- **Total input**: ~16K tokens max
- **Report output**: up to max_report_words (ALPHA: 4000, BETA: 1000, GAMMA: 800)

## Return Schema (for orchestrator)

When invoked as a sub-agent by the orchestrator, return this JSON after completion:

```json
{
  "board": "ALPHA",
  "sprint": "ALPHA_0.3.2",
  "day": 5,
  "report_path": "reports/daily/ALPHA/ALPHA_0.3.2/ALPHA_0.3.2_WL_day5_2026-04-07.md",
  "word_count": 3200,
  "health_score": 72,
  "completion_rate": 0.33,
  "flag_count": 8,
  "status": "success"
}
```

If any step fails, return: `{"board": "...", "status": "failed", "step": "...", "error": "..."}`

## Error Handling

- Missing `sprint.ai.json`: "No pipeline data found. Run /run-pipeline first."
- `delta` is `null`: Generate without delta section. Note: "Day-over-day comparison not available."
- Empty flags array: "No flags triggered on day {N}."
- **Day 1**: Set expectations appropriately — low completion is normal.
- **Buffer days (11-13)**: Focus on deployment flags only, skip capacity/quality sections.
- **Multiple boards**: Generate separate reports for each board.

## Example Output Structure (ALPHA Full)

```markdown
# ALPHA Daily Report — ALPHA_0.2.1 | Day 5/10

**Date**: 2026-04-07 | **Health**: 72/100 (on_track)

---

## 1. Status Summary
Sprint ALPHA_0.2.1 is at day 5 of 10. 8 of 24 tickets are Done (33%).
Weighted completion: 52%. Health score: 72/100 (on track per day-5 benchmark).

Since yesterday: 2 tickets moved to Done, 1 new blocker (ALPHA-145).

## 2. Flag Alert

### Critical
(none)

### High
- **Bulk Closure Without Verification** (Flag 2) — 1 ticket
  - ALPHA-112 (Bob Kumar): 3 tickets closed within 8 minutes

### Medium
- **Status Stale More Than 3 Days** (Flag 16) — 3 tickets
  - ALPHA-98 (Grace James): In Development for 4 days
  - ALPHA-103 (Bob Kumar): In Code Review for 3 days
  - ALPHA-115 (Bob Kumar): QA Failed for 3 days

...
```
