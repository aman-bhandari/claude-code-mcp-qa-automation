---
name: system-check
description: Validate system configuration, database connectivity, Jira authentication, and overall health. Regenerates STATE.md.
---

# System Check Skill

## Purpose

Run a comprehensive health check of the sprint-pulse system. Validates that all configuration files are valid, the database is accessible, and Jira credentials are configured. Updates STATE.md with the current system status.

## When to Invoke

- On `/system-check` or "system check"
- Before the first pipeline run in a new session
- After editing config.yaml, team_config.yaml, or flags.yaml
- When troubleshooting system issues

## Data Dependencies (Load in This Order)

1. **Read**: `config.yaml` — main system configuration
2. **Read**: `team_config.yaml` — team members and ticket categories
3. **Read**: `flags.yaml` — flag definitions (check count and validity)
4. **Read**: `known_issues.yaml` — any known workarounds to report
5. **Read**: `.env` — check that credentials are set (do NOT read values into output)
6. **Check**: `output/sprint-pulse.db` — database exists and tables are created

## Execution

1. Run `python -m sprint_pulse check` and capture the output
2. Interpret the results:
   - **HEALTHY**: All checks passed. Report success.
   - **DEGRADED**: Missing credentials but config is valid. Report what's missing.
   - **UNHEALTHY**: Config errors or database issues. Report specific failures.
3. Update `STATE.md` with:
   - Current date and health status
   - Capability checklist (what's working, what's not)
   - Configuration summary (boards, statuses, flags, team size)
   - Any known issues from `known_issues.yaml`

## Output

Update `STATE.md` at the project root with the current system health status.

## Quality Self-Evaluation

After running, verify:
- [ ] All 3 YAML config files parsed without errors
- [ ] flags.yaml has exactly 43 flags
- [ ] Database has 6 tables + _migrations table
- [ ] STATE.md reflects actual current state (not stale data)
- [ ] No sensitive data (API tokens, passwords) appears in output

## Error Handling

- **Missing .env**: Report as DEGRADED, not UNHEALTHY (system works for config validation)
- **Corrupted database**: Delete and recreate (migrations will rebuild schema)
- **Invalid YAML syntax**: Report exact line/column of error with fix suggestion
- **Unknown board in flags.yaml**: Warn but don't fail (board may be added later)
