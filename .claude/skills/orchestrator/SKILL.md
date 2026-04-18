# Skill: Orchestrator

## Description

Chain existing skills into end-to-end workflows by spawning sub-agents via the Agent tool. The orchestrator is a **lightweight coordinator** that sequences pipeline → report → deliver → feedback for one or all boards. It does NOT execute Python directly, read sprint data, or generate reports — it delegates all heavy work to sub-agents with isolated context windows.

## Usage

```
/orchestrator --daily --board ALPHA
/orchestrator --daily --all-boards
/orchestrator --readiness --board ALPHA
/orchestrator --retro --board ALPHA
/orchestrator --full --board ALPHA
/orchestrator --daily --all-boards --dry-run
```

## Parameters

| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| `--daily` | One of daily/readiness/retro/full required | — | Run daily workflow: pipeline → daily-report → deliver → feedback |
| `--readiness` | — | — | Run readiness workflow: pipeline → readiness-report → deliver |
| `--retro` | — | — | Run retrospective workflow: pipeline → retrospective → deliver → feedback |
| `--full` | — | — | Run full cycle: pipeline → daily-report → excel-report → deliver → feedback |
| `--board` | No | All boards | Which board to process (ALPHA, BETA, GAMMA) |
| `--all-boards` | No | false | Process all boards from `config.yaml > scheduling > reports > {type} > boards` |
| `--dry-run` | No | false | Print the execution chain without spawning any agents |
| `--skip-pipeline` | No | false | Skip pipeline step (use existing data) |
| `--skip-deliver` | No | false | Skip delivery step (generate report only) |
| `--skip-feedback` | No | false | Skip feedback/self-healing step |

## Workflow Chains

| Workflow | Sub-Agent Chain | Feedback? |
|----------|----------------|-----------|
| `--daily` | pipeline → daily-report → deliver | Yes |
| `--readiness` | pipeline → readiness-report → deliver | No |
| `--retro` | pipeline → retrospective → deliver | Yes |
| `--full` | pipeline → daily-report + excel-report → deliver | Yes |

## Prerequisites

- System must be healthy (`STATE.md` shows no critical errors)
- Config files must be valid (`config.yaml`, `team_config.yaml`, `flags.yaml`)
- For delivery: delivery targets must be enabled in `config.yaml > delivery`

## Execution Steps

### 1. Resolve Parameters

- Read ONLY `config.yaml` (scheduling section) and `STATE.md`
- Determine workflow type from flags (`--daily`, `--readiness`, `--retro`, `--full`)
- Determine board list:
  - If `--board` specified: use that single board
  - If `--all-boards`: read board list from `config.yaml > scheduling > reports > {type} > boards`
  - Default: all boards from config
- Build the skill chain based on workflow type (see Workflow Chains table)
- Apply skip flags: remove steps matching `--skip-pipeline`, `--skip-deliver`, `--skip-feedback`

### 2. Dry-Run Check

If `--dry-run` is set:
- Print the resolved chain for each board
- Print the agent prompt that WOULD be sent
- Exit without spawning any agents

Example dry-run output:
```
Orchestrator: --daily --all-boards (dry-run)

Board 1/3: ALPHA
  Agent prompt: "Execute daily workflow for board ALPHA: pipeline → report → deliver"

Board 2/3: BETA
  Agent prompt: "Execute daily workflow for board BETA: pipeline → report → deliver"

Board 3/3: GAMMA
  Agent prompt: "Execute daily workflow for board GAMMA: pipeline → report → deliver"

Phase 2: Apply feedback (after all boards complete)
```

### 3. Phase 1 — Spawn Board Agents (PARALLEL)

Use the Agent tool to spawn one sub-agent per board. **For `--all-boards`, issue ALL Agent tool calls in a single message** (this is how Claude Code runs them in parallel).

Each agent's prompt follows this pattern (adapt for workflow type):

#### Daily Workflow Agent Prompt:
```
Execute the daily workflow for board {BOARD}. Follow these steps exactly:

1. Run the pipeline:
   python -m sprint_pulse run --board {BOARD}
   If this fails, STOP and return: {"board": "{BOARD}", "status": "failed", "step": "pipeline", "error": "<message>"}

2. Generate the daily report:
   - Read .claude/skills/generate-daily-report/SKILL.md and follow its execution steps
   - The board is {BOARD}
   - Save the report to reports/daily/{BOARD}/{SPRINT}/ (create dirs if needed)

3. Deliver the report:
   - Read .claude/skills/deliver-report/SKILL.md and follow its execution steps
   - Report type: daily, board: {BOARD}
   - If delivery fails, log warning but continue

4. Return JSON summary:
   {"board": "{BOARD}", "status": "success", "pipeline": {"sprint": "...", "day": N, "tickets": N, "flags": N}, "report_path": "...", "delivery": {"target": "...", "status": "..."}}
```

#### Readiness Workflow Agent Prompt:
Same pattern but step 2 uses `generate-readiness-report/SKILL.md`, no step 4 feedback.

#### Retrospective Workflow Agent Prompt:
Same pattern but step 2 uses `generate-retrospective/SKILL.md`.

#### Full Workflow Agent Prompt:
Same pattern but step 2 runs both `generate-daily-report/SKILL.md` AND `generate-excel-report/SKILL.md`.

**If `--skip-pipeline`**: omit step 1 from the prompt. Agent starts at report generation.
**If `--skip-deliver`**: omit step 3 from the prompt. Agent returns after report generation.

### 4. Phase 2 — Feedback Agent (SEQUENTIAL)

After ALL Phase 1 board agents complete (regardless of individual success/failure):

- Only for workflows that include feedback: `--daily`, `--retro`, `--full`
- Unless `--skip-feedback` is set
- Spawn a single Agent:

```
Execute the apply-feedback skill in sub-agent mode.
Read .claude/skills/apply-feedback/SKILL.md and follow its execution steps.
Skip Step 5 (Human Review) — include pending doubts count in return JSON.
Return: {"quality_scores": {...}, "fixes_applied": N, "doubts_pending": N, "status": "success"}
```

### 5. Collect Results and Print Summary

Collect the JSON returned by each agent and print a summary table:

```
Orchestrator Complete: --daily --all-boards

Board    | Pipeline | Report | Deliver | Status
---------|----------|--------|---------|-------
ALPHA       | OK       | OK     | OK      | SUCCESS
BETA       | OK       | OK     | OK      | SUCCESS
GAMMA | FAILED   | -      | -       | pipeline error: Jira timeout

2/3 boards succeeded. Feedback: 1 fix applied, 0 doubts pending.
Reports: reports/daily/
```

## Key Design Rules

1. **The orchestrator NEVER reads**: sprint.ai.json, enriched.json, guidelines, reports, or feedback files
2. **Each sub-agent is self-contained**: reads its own SKILL.md, loads its own data
3. **Board independence**: if one board's agent fails, others continue
4. **Feedback is Phase 2**: runs AFTER all board agents complete (shared state in feedback files)
5. **Return format**: structured JSON, never raw data
6. **Parallel agents**: for `--all-boards`, ALL Agent tool calls go in a single message

## Error Handling

| Error | Action |
|-------|--------|
| Pipeline fails for a board | Agent returns failure JSON. Orchestrator notes it, continues to next board. |
| Report generation fails | Agent returns failure JSON. Board is aborted. |
| Delivery fails | Agent logs warning, returns partial success. Non-fatal. |
| Feedback fails | Orchestrator logs warning. Non-fatal. |
| Invalid board name | Orchestrator aborts with error listing valid boards (no agents spawned). |
| No workflow flag specified | Orchestrator aborts with usage help. |
| Config file missing/invalid | Orchestrator aborts entirely — run `/system-check` first. |

## Context Budget

The orchestrator is lightweight by design:
- config.yaml (scheduling section only): ~500 tokens
- STATE.md: ~500 tokens
- Agent return values: ~200 tokens per agent
- Total main thread: ~2-5K tokens (regardless of how many boards)

Each sub-agent manages its own context budget per its SKILL.md.

## Quality Self-Evaluation

After execution, verify:
- [ ] Each board in the chain was processed or has a clear error logged
- [ ] No reports were generated from stale/failed pipeline data
- [ ] Delivery was attempted for all successfully generated reports
- [ ] Summary accurately reflects success/failure of each step
- [ ] Failed boards did not block other boards from processing
