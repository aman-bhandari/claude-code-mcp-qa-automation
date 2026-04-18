---
name: apply-feedback
description: Evaluate pipeline run quality and apply self-healing fixes for recurring issues. Processes feedback log, auto-tunes flag thresholds, and logs doubts for human review.
---

# Apply Feedback Skill

## Purpose

Run the self-healing feedback loop: evaluate the latest pipeline run for flag accuracy and metric quality, then apply auto-fixes for issues that recur past the configured threshold (default: 3).

## When to Invoke

- After a pipeline run completes (post `/run-pipeline`)
- On `/apply-feedback` command
- As part of orchestrated end-to-end workflows
- Manually to review accumulated doubts

## Data Dependencies (Load in This Order)

1. **Read**: `config.yaml` — `self_healing` section (thresholds, paths)
2. **Read**: `feedback/feedback_log.json` — accumulated observations
3. **Read**: `feedback/doubts.json` — items needing human review
4. **Read**: `feedback/quality_history.json` — quality trend over time
5. **Read**: `known_issues.yaml` — active workarounds

## Execution

### Step 1: Evaluate Latest Run

Run: `python tools/evaluate_run.py --board {board}`

- Auto-detects latest sprint and day from the database
- Override with `--sprint {name} --day {N}` if needed
- Computes: flag precision, flag stability, metric consistency
- Appends results to all three feedback JSON files
- Updates known_issues.yaml occurrence counts if matches found

### Step 2: Review Evaluation Results

- Check stdout for quality scores summary
- Read updated `feedback/feedback_log.json` for new entries
- Note any new doubts in `feedback/doubts.json`

### Step 3: Apply Fixes (if pending entries exceed threshold)

First preview: `python tools/apply_feedback.py --dry-run`

If changes look correct: `python tools/apply_feedback.py`

- Groups pending entries by suggestion target (flag_id + fix type)
- Applies fix only when group size >= `auto_fix_threshold` (config.yaml)
- Fix types: threshold adjustment (+1 step), flag disable (2x threshold)
- Verified flags are NEVER auto-adjusted — routed to doubts instead
- All applied fixes logged to CHANGELOG.md

### Step 4: Report to User

- Summarize what was evaluated (sprint, day, board)
- Show quality scores (precision, stability, consistency, overall)
- List any fixes applied or previewed
- Present pending doubts that need human review
- Show quality trend from quality_history.json (improving/declining)

### Step 5: Human Review of Doubts (if any)

- Present each pending doubt from doubts.json with evidence
- Ask human to confirm or dismiss each doubt
- Confirmed doubts: update confidence to 1.0, status to "pending" in feedback_log
- Dismissed doubts: mark resolved in doubts.json

## Output

- Updated `feedback/feedback_log.json`, `feedback/doubts.json`, `feedback/quality_history.json`
- Potentially modified `flags.yaml` (threshold adjustments or flag disabling)
- Updated `CHANGELOG.md` (if fixes applied)
- Updated `known_issues.yaml` (if new patterns detected)

## Return Schema (for orchestrator)

When invoked as a sub-agent by the orchestrator, return this JSON after completion:

```json
{
  "quality_scores": {
    "precision": 0.85,
    "stability": 0.92,
    "consistency": 0.88,
    "overall": 0.88
  },
  "fixes_applied": 1,
  "fixes_preview": ["Flag 16 threshold adjusted: 3 days -> 4 days"],
  "doubts_pending": 2,
  "status": "success"
}
```

If any step fails, return: `{"status": "failed", "step": "...", "error": "..."}`

### Sub-Agent Mode

When running as a sub-agent (invoked by orchestrator), skip Step 5 (Human Review of Doubts). Instead:
- Include pending doubts in the return JSON under `doubts_pending` count
- The orchestrator's main thread will present doubts to the user after all agents complete
- Only execute Steps 1-4 automatically

## Quality Self-Evaluation

After running, verify:
- [ ] evaluate_run.py completed without errors
- [ ] feedback_log.json entries have valid confidence scores (0.0-1.0)
- [ ] No verified flags were disabled without human confirmation
- [ ] CHANGELOG.md documents any auto-fixes applied
- [ ] quality_history.json shows the new run entry
- [ ] Doubts presented to user if confidence < doubt_threshold (0.7)
