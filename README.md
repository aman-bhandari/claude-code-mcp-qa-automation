# claude-code-mcp-qa-automation

[![CI](https://github.com/aman-bhandari/claude-code-mcp-qa-automation/actions/workflows/ci.yml/badge.svg)](https://github.com/aman-bhandari/claude-code-mcp-qa-automation/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)
[![Claude Code](https://img.shields.io/badge/Claude%20Code-skills%20%2B%20MCP-orange.svg)](https://claude.com/claude-code)

A QA-automation pipeline built on Claude Code skills + MCP patterns. Sub-agent orchestration, flag-gated config-driven execution, a 7-table SQLite trending store, and a runnable end-to-end demo.

## What this is

A Claude-Code-first QA automation pipeline. The four things encoded here that most `.claude/` QA setups miss:

1. **Skills as invocation contracts, not code.** The 16 skill files under `.claude/skills/` are pure markdown. Each one names its inputs, the work it delegates, and the failure modes it distinguishes. Swapping the Python implementation does not require touching the skill contracts.
2. **Sub-agent orchestration.** The `orchestrator` skill fans out per-board workflows in parallel via the Claude Code `Agent` tool. The Python module `src/orchestrator.py` uses `ThreadPoolExecutor` as a structurally-identical stand-in so the demo runs without needing a live Claude Code session.
3. **Flag-gated, config-driven execution.** Every behavior that could be on or off lives in `config/flags.yaml` with global + board-scoped overrides. No inline `if FEATURE_FOO:` toggles in Python. Regression debugging starts with flipping a flag and re-running, not a code spelunk.
4. **Deterministic, reviewable output.** Reports are self-contained HTML with inline CSS and zero JavaScript. Given the same fixture and flags, the rendered HTML is byte-identical. Diffs are reviewable; re-runs are cacheable.

## Tech stack

- Claude Code `.claude/skills/` (v2 format with frontmatter) for the invokable-skill surface
- Python 3.10+ for the pipeline scaffold (stdlib + `pyyaml` only; no framework dependencies)
- SQLite for the trending store (`src/store.py`, 7-table schema)
- `ThreadPoolExecutor` as a structural stand-in for Claude Code sub-agent fan-out
- `pytest` for end-to-end verification (7 tests)
- Bash integrity-check script + GitHub Actions CI for pre-push gate enforcement

## Architecture

Full writeup in [`docs/architecture.md`](docs/architecture.md). Short version:

```
claude-code-mcp-qa-automation/
├── .claude/
│   └── skills/                # 16 invokable skill contracts (markdown, no code)
│       ├── analyze-feature/
│       ├── apply-feedback/
│       ├── audit-requirements/
│       ├── capacity-planner/
│       ├── compare-sprints/
│       ├── deliver-report/
│       ├── discover-boards/
│       ├── flag-control/
│       ├── generate-daily-report/
│       ├── generate-excel-report/
│       ├── generate-readiness-report/
│       ├── generate-retrospective/
│       ├── orchestrator/            # sub-agent fan-out coordinator
│       ├── query-sprint-data/
│       ├── run-pipeline/
│       └── system-check/
├── src/                       # 8 Python modules — the implementation that realises the skill contracts
│   ├── __main__.py                  # demo entry point
│   ├── config.py                    # flag loader with board-scoped overrides
│   ├── metrics.py                   # sprint / assignee / story-type aggregations
│   ├── orchestrator.py              # ThreadPoolExecutor stand-in for sub-agent fan-out
│   ├── pipeline.py                  # single-board run: fixture → store → metrics → HTML
│   ├── report.py                    # inline-CSS self-contained HTML render
│   └── store.py                     # 7-table SQLite schema
├── config/
│   ├── flags.yaml                   # 16 global + 6 board-scoped overrides = 22 entries
│   └── team_config.yaml             # 3 synthetic boards, 8 synthetic members
├── fixtures/
│   ├── example_sprint_01.json       # 20 synthetic tickets, board ALPHA
│   └── example_sprint_02.json       # 10 synthetic tickets, board BETA
├── tests/
│   └── test_pipeline.py             # 7 end-to-end tests
├── scripts/
│   ├── run-demo.sh                  # produces output/<board>/report.html + summary.json
│   └── integrity-check.sh           # pre-push gates (claim-evidence, identifier grep, schema, counts)
├── docs/
│   ├── architecture.md              # full architecture writeup
│   └── claim-evidence.md            # Gate 0: every README claim evidenced
└── .github/workflows/ci.yml         # CI runs tests + demo + integrity check
```

## Setup

Requires Python 3.10+.

```bash
git clone https://github.com/aman-bhandari/claude-code-mcp-qa-automation.git
cd claude-code-mcp-qa-automation

# Option A — editable install
pip install -e '.[dev]'

# Option B — minimal install (no dev extras)
pip install pyyaml
```

## Usage

End-to-end demo (runs the full pipeline for both fixture boards):

```bash
bash scripts/run-demo.sh
```

Expected output:

```
Dispatching 2 board(s) in parallel...
  OK     BETA — 15/30 pts (50.0%) -> output/BETA/report.html
  OK    ALPHA — 33/69 pts (47.8%) -> output/ALPHA/report.html

Demo complete. Open output/ALPHA/report.html in a browser.
```

Artifacts produced:
- `output/ALPHA/report.html` — self-contained HTML report for board ALPHA
- `output/BETA/report.html` — self-contained HTML report for board BETA
- `output/summary.json` — run summary across boards
- `output/_db/<board>.sqlite3` — per-board SQLite trending store

Run tests:

```bash
python3 -m pytest tests/ -q
# 7 passed
```

Adopt the skills in your own project: copy `.claude/skills/` into your repo and edit each `SKILL.md` to point at your pipeline. The skill contracts do not assume a specific Python implementation.

## Integrity check

```bash
bash scripts/integrity-check.sh
```

Runs:
- **Gate 0** — every claim in `docs/claim-evidence.md` marked verified (✅)
- **Gate 4** — zero private identifiers in the repo (project-internal names, client domains, real individuals)
- **Gate 5** — no secret patterns (API keys, tokens, passwords) outside whitelisted examples
- **Artifact-specific** — skill count = 16, every skill has `SKILL.md`, Python module count = 8, store schema has 7 tables, `bash scripts/run-demo.sh` succeeds, `pytest tests/` passes

CI runs the same gates on every push via `.github/workflows/ci.yml`.

## Related artifacts

- [`claude-code-agent-skills-framework`](https://github.com/aman-bhandari/claude-code-agent-skills-framework) — `.claude/` framework for AI-engineering workflows (15 rule files, 21 skills, concentric-loop pedagogy)
- [`llm-rag-knowledge-graph`](https://github.com/aman-bhandari/llm-rag-knowledge-graph) — chronicle editorial format + wiki-as-RAG graph shape
- [`nextjs-16-mdx-research-publisher`](https://github.com/aman-bhandari/nextjs-16-mdx-research-publisher) — Next.js 16 + React 19 + TS strict + MDX + JSON-LD static publisher
- [`claude-multi-agent-protocol`](https://github.com/aman-bhandari/claude-multi-agent-protocol) — HANDOVER + SYNC inter-repo protocol

## License

MIT © 2026 Aman Bhandari. See `LICENSE`.
