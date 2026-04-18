# CLAUDE.md — QA Automation Scaffold Entry Point

Behavioral contract for a Claude Code project that orchestrates QA-automation workflows via skills, sub-agents, and a flag-gated pipeline.

## What this file does

Every line exists because Claude Code's defaults get it wrong without the instruction. When a line stops earning its presence, cut it.

## Role

Claude Code operates as the **Coordinator** — it reads skill contracts from `.claude/skills/`, invokes the pipeline via `python3 -m src`, spawns sub-agents for per-board fan-out, and aggregates results. It does not bypass the skill contracts; skills are the source of truth for what each step does.

## Entry points

- Run the demo end-to-end: `bash scripts/run-demo.sh`
- Run the pipeline directly: `python3 -m src`
- Run tests: `python3 -m pytest tests/ -q`
- Pre-push integrity check: `bash scripts/integrity-check.sh`

## Architecture

Full writeup in [`docs/architecture.md`](docs/architecture.md). Summary:

- `.claude/skills/` — 16 skill contracts, markdown-only. Describe inputs, behaviour, and failure modes per skill.
- `src/` — 8 Python modules: `config.py` (flag loader), `metrics.py` (aggregations), `orchestrator.py` (fan-out), `pipeline.py` (single-board run), `report.py` (HTML render), `store.py` (SQLite schema), `__main__.py` (demo entry), `__init__.py`.
- `config/flags.yaml` — 16 global flags + 6 board-scoped overrides = 22 entries total.
- `config/team_config.yaml` — 3 boards (ALPHA, BETA, GAMMA), 8 synthetic members.
- `fixtures/` — 2 synthetic sprint JSON files (30 tickets total).
- `tests/test_pipeline.py` — 7 end-to-end tests.

## The 16 skills

| Skill | What it does |
|-------|--------------|
| `orchestrator` | Fans out per-board workflows in parallel via the Agent tool |
| `run-pipeline` | Runs the pipeline for one board (fixture → store → metrics → HTML) |
| `discover-boards` | Lists the boards configured in `team_config.yaml` |
| `system-check` | Pre-flight diagnostic before a run |
| `flag-control` | Lists and flips flags in `config/flags.yaml` |
| `query-sprint-data` | Reads from the SQLite trending store |
| `audit-requirements` | Checks ticket frontmatter against a requirements spec |
| `analyze-feature` | Feature-level analysis across tickets in a sprint |
| `capacity-planner` | Estimates per-assignee capacity from historical load |
| `compare-sprints` | Side-by-side trend comparison across sprints |
| `generate-daily-report` | Daily status report for one board |
| `generate-readiness-report` | Sprint readiness report |
| `generate-retrospective` | End-of-sprint retrospective report |
| `generate-excel-report` | Tabular Excel export |
| `deliver-report` | Slack / email delivery contract (scaffold ships dry-run only) |
| `apply-feedback` | Self-healing feedback pass after the main workflow |

## Key invariants

- **Skills own the contract.** If a skill's behaviour needs to change, edit the `SKILL.md`, not the Python. The Python is a *realisation* of the contract, not the contract itself.
- **Flags own the toggles.** No `if FEATURE_X` booleans in Python. Every toggle is an entry in `config/flags.yaml`.
- **Deterministic output.** Reports are self-contained HTML with inline CSS and no JavaScript. Same input + same flags = byte-identical output.
- **Board independence.** If one board's run fails, others continue. The orchestrator surfaces per-board status; it does not roll the whole run back.

## Honest scope

This scaffold is a reference shape. It is not a drop-in replacement for a production Jira/Slack/Playwright pipeline. The source-system client, delivery layer, and browser-automation bridge are out of scope — see `docs/architecture.md` → "What the scaffold is NOT".
