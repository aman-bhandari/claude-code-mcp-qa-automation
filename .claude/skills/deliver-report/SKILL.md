---
name: deliver-report
description: Publish generated reports to Slack channels and Confluence pages via MCP tools. Supports daily, readiness, retrospective, and comparison reports.
---

# Deliver Report Skill

## Purpose

Publish sprint-pulse reports from `reports/` to external channels — Slack and/or Confluence — using MCP tools. Handles formatting differences between targets (Slack truncation, Confluence full markdown).

## When to Invoke

- On `/deliver-report` command
- After any report generation skill completes (if delivery is enabled)
- As part of orchestrated end-to-end workflows

## Data Dependencies (Load in This Order)

1. **Read**: `config.yaml` — `delivery` section (Slack channels, Confluence spaces, enabled flags)
2. **Read**: `reports/` — find the target report file(s)
3. **Read**: The report file content to deliver

## Parameters

- `--report-type {daily|readiness|retrospective|comparison}` — which report to deliver
- `--board {ALPHA|BETA|GAMMA}` — board context for channel selection
- `--target {slack|confluence|both|local}` — delivery destination (default: from config)
- `--report-path {path}` — explicit path to report file (overrides auto-discovery)
- `--dry-run` — show what would be sent without actually sending

## Execution

### Step 1: Resolve Report File

- If `--report-path` provided: use it directly
- Otherwise: scan `reports/{report_type}/{board}/` for the most recent file matching the board
- If no report found: error with suggestion to run the generation skill first

### Step 2: Check Delivery Config

- Read `config.yaml > delivery` section
- Verify target channel is enabled (slack.enabled, confluence.enabled)
- If target is disabled in config: warn user and suggest enabling it first
- Resolve channel/space names from config:
  - Slack: `delivery.slack.channels.{report_type}`
  - Confluence: `delivery.confluence.spaces.reports`

### Step 3: Format for Target

**Slack formatting:**
- Truncate to key sections (Executive Summary, Flags, Action Items)
- Max ~3000 characters per message (Slack limit)
- If report exceeds limit: split into threaded messages
- Strip complex markdown tables — convert to simple lists
- Add header: `Sprint Pulse — {Report Type} — {Board} — {Date}`

**Confluence formatting:**
- Full markdown report (Confluence renders markdown natively)
- Add page title: `{Board} {Report Type} — {Sprint} Day {N}`
- Set parent page based on config space
- If `update_existing: true`: find and update existing page for same sprint/day

### Step 4: Deliver

**Slack:**
- Use MCP tool `slack_send_message` with resolved channel
- If threaded: send header first, then sections as thread replies

**Confluence:**
- If updating: use MCP tool `getConfluencePage` to find existing, then `updateConfluencePage`
- If creating: use MCP tool `createConfluencePage` with space key and title

### Step 5: Confirm

- Report delivery status to user (success/failure per target)
- Include links to delivered content (Slack permalink, Confluence page URL)

## Output

- Report delivered to configured Slack channel(s) and/or Confluence space
- No local file changes

## Return Schema (for orchestrator)

When invoked as a sub-agent by the orchestrator, return this JSON after completion:

```json
{
  "board": "ALPHA",
  "report_type": "daily",
  "targets": {
    "slack": {"status": "success", "channel": "#sprint-pulse-wl"},
    "confluence": {"status": "skipped", "reason": "disabled in config"}
  },
  "status": "success"
}
```

If any step fails, return: `{"board": "...", "status": "failed", "step": "...", "error": "..."}`

## Quality Self-Evaluation

After running, verify:
- [ ] Report file was found and read successfully
- [ ] Delivery config was checked before sending
- [ ] Slack message respects character limits
- [ ] Confluence page has correct title and space
- [ ] User received confirmation with delivery status
- [ ] Dry-run mode did not actually send anything
