---
name: query-sprint-data
description: General-purpose Jira intelligence — answer any question about sprint data using SQL queries against the local database and JQL via Jira MCP.
---

# Query Sprint Data Skill

## Purpose

Answer natural language questions about sprint data by translating them into SQL queries against the local SQLite database (`output/sprint-pulse.db`) and/or JQL queries via Jira MCP. Supports ad-hoc analysis that doesn't fit into structured reports.

## When to Invoke

- On `/query-sprint-data` command
- When user asks data questions about sprints, tickets, developers, or flags
- When user needs custom analysis not covered by standard reports

## Data Dependencies (Load in This Order)

1. **Read**: `config.yaml` — board names, workflow statuses (for context)
2. **Database**: `output/sprint-pulse.db` — 6 tables (see schema below)
3. **MCP** (optional): `searchJiraIssuesUsingJql` — for live Jira queries the DB can't answer

## Database Schema

6 tables available for querying:

| Table | Key Columns | Use For |
|-------|-------------|---------|
| `sprints` | name, board_name, start_date, end_date, state | Sprint metadata |
| `ticket_snapshots` | sprint_name, ticket_key, snapshot_date, day_number, status, assignee, issue_type, priority, cycle_time_days, total_worklog_hours, parent_key | Per-ticket daily state |
| `flag_runs` | sprint_name, run_date, day_number, flag_id, flag_name, severity, flagged_ticket_count, flagged_tickets | Flag detection results |
| `sprint_scores` | sprint_name, run_date, day_number, health_score, completion_rate, weighted_completion, qa_pass_rate, total_tickets, done_tickets, blocked_tickets | Sprint-level metrics |
| `developer_metrics` | sprint_name, developer_name, run_date, day_number, total_tickets, done_tickets, worklog_hours, flag_count | Per-developer metrics |
| `ticket_flag_history` | sprint_name, ticket_key, snapshot_date, flag_id, flag_name, severity, reason | Per-ticket flag audit |

## Execution

### Step 1: Understand the Question

- Parse the user's natural language question
- Identify: target entity (tickets, developers, flags, sprints), time range, filters, aggregation
- Determine if the question can be answered from DB or needs live Jira MCP

### Step 2: Construct Query

**For DB queries:**
- Build a SELECT query against the appropriate table(s)
- Only SELECT statements are allowed — never INSERT, UPDATE, DELETE, DROP
- Validate table and column names against the known schema
- Use parameterized queries to prevent SQL injection
- Apply reasonable LIMIT (default 50 rows)

**For Jira MCP queries:**
- Build JQL string from the question
- Use `searchJiraIssuesUsingJql` MCP tool
- Useful for: live ticket status, fields not in DB, cross-project queries

### Step 3: Execute and Format

- Run the query against `output/sprint-pulse.db`
- Format results as a readable table or summary
- If results are large, summarize with aggregates and offer to show details

### Step 4: Present Results

- Show the data in a clear format (markdown table for small results, summary for large)
- Include the query used (for transparency and reproducibility)
- Suggest follow-up questions if relevant

## Example Questions

- "Who has the most blocked tickets in ALPHA_0.2.1?"
- "Show me flag trends for the last 3 sprints"
- "What's the average cycle time by developer?"
- "Which tickets have been flagged more than 3 times?"
- "Compare completion rates across all boards"
- "Which flags triggered most frequently last sprint?"

## Output

- Formatted query results (tables, summaries, charts described in text)
- The SQL/JQL query used

## Quality Self-Evaluation

After running, verify:
- [ ] Query is SELECT-only (no mutations)
- [ ] Table and column names are valid
- [ ] Results are formatted readably
- [ ] Large result sets are summarized, not dumped raw
- [ ] Query is shown to user for transparency
