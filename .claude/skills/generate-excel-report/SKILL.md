---
name: generate-excel-report
description: Generate 3-sheet Excel report (flag-wise, assignee-wise, owner-wise) from enriched pipeline data.
---

# Generate Excel Report Skill

## Purpose

Generate a structured Excel workbook with 3 sheets providing different views of sprint flag and ticket data. This is the ONLY report skill that reads full enriched data (enriched.json), not sprint.ai.json.

## When to Invoke

- On `/generate-excel-report` command
- When user asks for an Excel export of sprint data

## Data Dependencies

1. **Read**: `config.yaml` — sprint settings
2. **Read**: `flags.yaml` — flag definitions (for owner lookup)
3. **Read**: `output/{sprint}/day-{N}/enriched.json` — full enriched ticket data
4. **Read**: `output/{sprint}/day-{N}/sprint.ai.json` — flag results

## Execution

### Step 1: Determine Sprint and Day

- If user specifies sprint and day: use those
- If only sprint: find the latest `day-N` directory
- If neither: use the latest sprint from `output/`

### Step 2: Run the Tool

```bash
python tools/generate_excel.py --sprint {sprint_name} --day {day_number}
```

Or call the module directly:
```python
from sprint_pulse.export.excel import generate_excel_report
```

### Step 3: Confirm Output

- Verify the file was created at `reports/excel/{sprint}_day{N}.xlsx`
- Report file size and row counts per sheet

## Output

- Excel file at `reports/excel/{sprint}_day{N}.xlsx`
- 3 sheets: Flags, Assignees, Owners

## Sheet Descriptions

| Sheet | Rows | Purpose |
|-------|------|---------|
| Flags | One per flagged ticket | All flags with ticket details, severity color-coded |
| Assignees | One per developer | Ticket counts, points, worklogs, flag exposure |
| Owners | One per flag owner role | Flag count rollup by owner (PM, Tech Lead, etc.) |

## Return Schema (for orchestrator)

When invoked as a sub-agent by the orchestrator, return this JSON after completion:

```json
{
  "board": "ALPHA",
  "sprint": "ALPHA_0.3.2",
  "day": 5,
  "excel_path": "reports/excel/ALPHA_0.3.2_day5.xlsx",
  "sheets": ["Flags", "Assignees", "Owners"],
  "row_counts": {"Flags": 45, "Assignees": 12, "Owners": 6},
  "status": "success"
}
```

If any step fails, return: `{"board": "...", "status": "failed", "step": "...", "error": "..."}`

## Quality Self-Evaluation

After running, verify:
- [ ] File was created and is non-empty
- [ ] All 3 sheets are present
- [ ] Severity cells are color-coded
- [ ] Column widths are readable
- [ ] No empty sheets (unless genuinely no data)
