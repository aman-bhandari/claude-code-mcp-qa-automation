# Architecture

A reference scaffold for QA-automation pipelines built on Claude Code skills + MCP patterns. This document explains what each layer does and why the boundaries are where they are.

## Layers, from top down

```
┌────────────────────────────────────────────────────────────────────────┐
│  Claude Code skills (.claude/skills/)                                  │
│  16 invokable skills — orchestrator, pipeline, report, deliver, etc.   │
│  Each skill is a markdown contract describing inputs, behaviour, and   │
│  failure modes. Skills delegate heavy work to Python or to sub-agents. │
└───────────────────────────────┬────────────────────────────────────────┘
                                │ invokes
                                ▼
┌────────────────────────────────────────────────────────────────────────┐
│  Orchestrator (src/orchestrator.py)                                    │
│  Fans out pipeline runs across boards via sub-agent parallelism.       │
│  In Claude Code, the fan-out is the Agent tool spawning sub-agents in  │
│  isolated context windows. The scaffold uses ThreadPoolExecutor as a   │
│  structurally-identical stand-in.                                      │
└───────────────────────────────┬────────────────────────────────────────┘
                                │ dispatches
                                ▼
┌────────────────────────────────────────────────────────────────────────┐
│  Pipeline (src/pipeline.py)                                            │
│  Single-board run: fixture → flag resolution → store writes →          │
│  metrics computation → HTML render.                                    │
└───────┬────────────┬────────────────┬────────────────┬─────────────────┘
        │            │                │                │
        ▼            ▼                ▼                ▼
┌─────────────┐ ┌──────────┐ ┌──────────────┐ ┌────────────────────┐
│  config.py  │ │ store.py │ │  metrics.py  │ │     report.py      │
│  flags +    │ │ 7-table  │ │  sprint,     │ │  inline CSS, no    │
│  team_cfg   │ │ SQLite   │ │  assignee,   │ │  JS — self-        │
│  loaders    │ │ schema   │ │  story-type  │ │  contained HTML    │
└─────────────┘ └──────────┘ └──────────────┘ └────────────────────┘
```

## Skills (the human-facing surface)

The 16 skill files under `.claude/skills/` are the layer a human operator interacts with. Each skill is a markdown contract — no code. Claude Code reads the `SKILL.md` on invocation and acts accordingly. Examples:

- `run-pipeline` — runs the pipeline for one board
- `orchestrator` — fans out pipeline runs across boards
- `generate-daily-report` — produces a daily status report
- `flag-control` — lists / flips flags in `config/flags.yaml`
- `system-check` — pre-flight diagnostic before a run
- `audit-requirements` — checks ticket frontmatter against a requirements spec

Skills do not contain Python. They tell Claude Code what command to run, which files to read, and how to interpret success or failure. Swapping the Python implementation does not require touching the skills — the skill contract is deliberately implementation-agnostic.

## Sub-agent parallelism

In Claude Code, the `Task` tool (aliased as the Agent tool in some clients) spawns a sub-agent in its own context window. The parent agent dispatches the sub-agent with a prompt; the sub-agent returns a result. The parent continues without paying the context cost of the sub-agent's work.

The orchestrator's fan-out shape mirrors this:

```
parent             sub-agent 1          sub-agent 2          sub-agent 3
  │                     │                    │                    │
  │─ spawn(ALPHA) ─────▶│                    │                    │
  │─ spawn(BETA)  ─────────────────────────▶ │                    │
  │─ spawn(GAMMA) ────────────────────────────────────────────────▶│
  │                     │                    │                    │
  │                     │ ─ result ─┐        │                    │
  │                     │           │        │ ─ result ─┐        │
  │ ◀───────────────────│           │        │           │        │
  │                                 │        │           │        │ ─ result
  │ ◀──────────────────────────────▶│        │           │        │
  │                                          │           │        │
  │ ◀────────────────────────────────────────│           │        │
  │                                                                │
  │ ◀──────────────────────────────────────────────────────────────│
  │
  ▼
  aggregate
```

The scaffold's ThreadPoolExecutor is a structural stand-in. Swapping it for real Agent calls does not change the caller's shape — `run_boards()` still dispatches N jobs, still gathers N results in completion order. That replaceability is the whole point.

## Flags — every toggle is config

Every behavior that could be on or off is a flag in `config/flags.yaml`, not an inline boolean in Python. The cost is an extra layer of indirection. The benefit: when a regression hits, the first diagnostic step is to run the same pipeline with the flag flipped and see whether the regression stays. Without that step, debugging devolves into a code-archaeology expedition.

Flags have two scopes: global (apply to all boards) and board-scoped (override globals for one board). The resolver in `src/config.py` merges them.

## SQLite trending store

A seven-table schema holds sprint snapshots, ticket states, computed metrics, assignee loads, story-type breakdowns, run logs, and flag snapshots. See `src/store.py` for the schema.

The store is not a production database. Its value is:

1. **Trend queries.** "Completion ratio across the last 6 sprints for ALPHA" is one SELECT.
2. **Reproducibility.** The flag-snapshots table records which flag values produced which metrics, so a regression can be re-run against the exact config that was live.
3. **Audit.** The run_log table records every skill invocation with a status.

The store lives per-board under `output/_db/<board>.sqlite3`. A production deployment would centralise to a shared trending store; the per-board layout keeps the demo reproducible from scratch.

## Deterministic reports

The report renderer (`src/report.py`) emits a self-contained HTML file with inline CSS and no JavaScript. Given the same fixture and the same flags, the rendered HTML is byte-identical. That property makes the output reviewable in git diffs and cacheable across re-runs.

## What the scaffold is NOT

- Not a production Jira integration. The real source-system client is out of scope; the fixtures simulate what the client would emit.
- Not a Slack/email delivery system. The `deliver-report` skill documents the contract but the scaffold ships dry-run only.
- Not a Chrome DevTools MCP → Playwright pipeline. The skills reference that integration pattern; the scaffold does not ship a runnable browser-automation layer.
- Not a drop-in replacement for a sprint-pulse deployment. The scaffold is a reference architecture — skill contracts, orchestration shape, flag-driven config, deterministic pipeline — that a real deployment can adapt.

## Adopting this architecture

1. Copy `.claude/skills/` into your project. Edit each SKILL.md to match your stack.
2. Replace the fixture loader in `src/pipeline.py` with a real source-system client (Jira, Linear, GitHub Projects, whatever).
3. Extend `config/flags.yaml` to cover the behaviors your pipeline needs to toggle.
4. Extend `src/store.py` with whatever additional tables your metrics require.
5. Run `bash scripts/run-demo.sh` to verify the adapted pipeline still produces a clean report from end to end.
