---
name: discover-boards
description: Auto-discover Jira boards and active sprints using Atlassian MCP tools. Suggests config additions for undiscovered boards.
---

# Board Discovery Skill

## Purpose

Use Atlassian MCP tools to discover all available Jira boards and their active sprints. Compare what's found with what's configured in `config.yaml`. Report any boards that exist in Jira but aren't yet configured.

## When to Invoke

- On `/discover-boards` or "discover boards"
- During initial system setup
- When a new board needs to be added to monitoring
- Periodically to check for new boards

## Data Dependencies (Load in This Order)

1. **Read**: `config.yaml` — current board configuration (boards section only)

## Execution

1. Use `getVisibleJiraProjects` MCP tool to list all accessible Jira projects
2. For each project of interest, use `searchJiraIssuesUsingJql` to find boards with active sprints:
   - JQL: `project = "{KEY}" AND sprint in openSprints()`
3. Compare discovered boards with `config.yaml` boards section
4. For each configured board (ALPHA, BETA, GAMMA):
   - Confirm the board exists in Jira
   - Report active sprint name, start/end dates, issue count
5. For undiscovered boards:
   - Suggest adding them to config.yaml
   - Provide the board name, project key, and sprint info

## Output

Report to the user:
- **Configured boards found**: list with active sprint details
- **Configured boards NOT found**: warnings for misconfigured boards
- **Undiscovered boards**: suggestions for new boards to monitor

## Quality Self-Evaluation

After running, verify:
- [ ] All configured boards (ALPHA, BETA, GAMMA) were checked
- [ ] Active sprint info is current (not stale)
- [ ] Suggestions include enough detail to update config.yaml
- [ ] No false positives (boards that don't need monitoring)
