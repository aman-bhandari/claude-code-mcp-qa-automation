---
name: audit-requirements
description: Trace Confluence requirements to Jira tickets. Identifies coverage gaps, unlinked requirements, and tickets without requirement backing.
---

# Audit Requirements Skill

## Purpose

Build a traceability matrix between Confluence requirement documents and Jira tickets. Identify requirements with no implementation tickets, tickets with no requirement backing, and coverage gaps.

## When to Invoke

- On `/audit-requirements` command
- When user asks about requirement coverage or traceability
- During readiness assessments to verify DoR compliance at the requirement level

## Data Dependencies (Load in This Order)

1. **Read**: `config.yaml` — board names, Confluence space config
2. **MCP**: `getConfluencePage` — fetch requirement document content
3. **MCP**: `searchJiraIssuesUsingJql` — find matching Jira tickets

## Parameters

- `--confluence-page {url_or_id}` — Confluence page containing requirements (required)
- `--board {ALPHA|BETA|GAMMA}` — limit Jira search to a specific board's project (optional)
- `--labels {label1,label2}` — filter Jira tickets by label (optional)

## Execution

### Step 1: Fetch Confluence Page

- Use MCP tool `getConfluencePage` with the provided page ID or URL
- Extract the page content (body)
- Parse requirements: look for numbered items, bullet points, user stories, acceptance criteria
- Each requirement gets an ID: `REQ-{page_id}-{sequence_number}`

### Step 2: Extract Requirements

- Identify individual requirements from the page content
- For each requirement, extract:
  - Short description (first line or sentence)
  - Keywords (nouns, verbs, domain terms)
  - Priority if specified
  - Any explicit ticket references (e.g., "PROJ-123")

### Step 3: Search Jira for Matches

For each requirement:
- If explicit ticket reference exists: fetch that ticket directly
- Otherwise: build JQL from keywords:
  - `project = {project} AND (summary ~ "keyword1" OR description ~ "keyword2")`
  - Optionally filter by board, labels, epic
- Match quality: exact reference > keyword match in summary > keyword match in description

### Step 4: Build Traceability Matrix

| Req ID | Requirement | Jira Tickets | Status | Coverage |
|--------|-------------|--------------|--------|----------|
| REQ-1  | User can... | PROJ-123     | Done   | Covered  |
| REQ-2  | System sh...| (none)       | -      | Gap      |

Coverage categories:
- **Covered**: at least one ticket found with matching scope
- **Partial**: ticket found but scope doesn't fully match
- **Gap**: no matching ticket found
- **Uncertain**: keyword match only, low confidence

### Step 5: Identify Orphan Tickets

- Search for tickets in the project that reference the Confluence page but aren't in the matrix
- These may be implementation tickets that don't map to a specific requirement

### Step 6: Report

Present:
- Traceability matrix with coverage status
- Summary stats: X/Y requirements covered, Z gaps, W uncertain
- List of gaps (requirements needing tickets)
- List of orphan tickets (tickets needing requirement links)
- Low-confidence matches logged to `feedback/doubts.json` for human review

## Output

- Traceability matrix (displayed to user)
- Gap analysis with recommendations
- Uncertain matches logged to `feedback/doubts.json`

## Quality Self-Evaluation

After running, verify:
- [ ] Confluence page was fetched and parsed successfully
- [ ] Requirements were extracted with clear descriptions
- [ ] JQL queries were well-formed and returned relevant results
- [ ] Coverage categories are justified (not all marked "covered" without evidence)
- [ ] Gaps are clearly identified with actionable suggestions
- [ ] Low-confidence matches routed to doubts.json, not presented as certain
