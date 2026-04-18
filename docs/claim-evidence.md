# Claim-Evidence Mapping

Every claim this repo makes — in its GitHub description, its README, and any resume line pointing at it — must map to a file or command that evidences the claim.

**Rule:** every row must be verified (✅) before push. An unverified row (☐) fails the integrity check and blocks CI.

## Claims

| Claim | Evidence (file / command) | Verified |
|-------|---------------------------|----------|
| "16 Claude Code skills" | `find .claude/skills -maxdepth 1 -mindepth 1 -type d \| wc -l` returns 16 | ✅ |
| "every skill has SKILL.md" | every directory under `.claude/skills/` contains `SKILL.md`; verified by `integrity-check.sh` | ✅ |
| "sub-agent orchestration pattern" | `.claude/skills/orchestrator/SKILL.md` documents the Agent-tool fan-out contract; `src/orchestrator.py` implements `ThreadPoolExecutor` as a structural stand-in; `docs/architecture.md` → "Sub-agent parallelism" explains the mapping | ✅ |
| "flag-gated, config-driven execution" | `src/config.py` (flag loader with board-scoped overrides) + `config/flags.yaml` (16 global + 6 board-scoped = 22 entries); `src.config.count_flags()` returns 22 | ✅ |
| "7-table SQLite trending store" | `src/store.py` defines `SCHEMA_STATEMENTS` with 7 `CREATE TABLE` statements; `tests/test_pipeline.py::test_store_schema_has_seven_tables` asserts `store.count_tables(conn) == 7` and passes | ✅ |
| "8 Python modules" | `ls src/*.py \| wc -l` returns 8: `__init__.py`, `__main__.py`, `config.py`, `metrics.py`, `orchestrator.py`, `pipeline.py`, `report.py`, `store.py` | ✅ |
| "runnable end-to-end demo on synthetic fixtures" | `bash scripts/run-demo.sh` produces `output/ALPHA/report.html`, `output/BETA/report.html`, `output/summary.json`; script asserts each file landed | ✅ |
| "7 pytest tests, all passing" | `python3 -m pytest tests/ -q` returns `7 passed` | ✅ |
| "2 synthetic fixtures, 30 tickets total" | `fixtures/example_sprint_01.json` holds 20 tickets on board ALPHA; `fixtures/example_sprint_02.json` holds 10 tickets on board BETA; test `test_metrics_compute_from_fixture_01` asserts `ticket_count == 20` and passes | ✅ |
| "3 synthetic boards (ALPHA, BETA, GAMMA)" | `config/team_config.yaml` lists boards ALPHA, BETA, GAMMA; `config/flags.yaml` `boards:` section has the same three keys | ✅ |
| "deterministic sprint metrics (sprint / assignee / story-type)" | `src/metrics.py` defines `compute_sprint_metrics`, `compute_assignee_load`, `compute_story_type_breakdown` — 3 metric computations with `@dataclass` result types | ✅ |
| "deterministic, self-contained HTML output (inline CSS, no JavaScript)" | `src/report.py` renders the HTML; `test_pipeline_end_to_end` asserts `"<!doctype html>"` and `"Sprint KPIs"` appear in the rendered file | ✅ |
| "zero private identifiers in the repo (sanitised extract)" | `scripts/integrity-check.sh` Gate 4 greps for the sanitisation exclusion list and returns zero hits; `test_no_hardcoded_real_identifiers_in_fixtures` asserts the fixtures contain none of the banned substrings | ✅ |

## What this file is NOT

- Not a spec. The spec is the skill contracts + `docs/architecture.md`.
- Not a changelog. Claims that no longer hold get removed here the same commit they get removed from the README.
- Not a promise of completeness. It is the Gate-0 surface — if a number in any public doc is not mapped here, it does not ship.

## How this file is enforced

`scripts/integrity-check.sh` (run locally) and `.github/workflows/ci.yml` (run on every push) both fail if any row in this file carries `☐` instead of `✅`. This applies Gate 0 of the bulletproof publishing contract.

## Adding a new claim

When the README gains a new claim — or a resume line starts pointing at this repo with a new number:

1. Add a row here with the claim text (verbatim) and the evidencing command or file path.
2. Mark as `☐` until verified.
3. Run `bash scripts/integrity-check.sh`. It fails while any row carries `☐`.
4. Verify the evidence, flip to `✅`, re-run.
5. Push only after all rows are `✅`.
