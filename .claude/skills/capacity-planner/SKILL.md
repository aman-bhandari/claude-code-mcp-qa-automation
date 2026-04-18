---
name: capacity-planner
description: Analyze developer load vs available capacity. Identifies overloaded team members, underutilized capacity, and sprint completion risk based on remaining work and available hours.
---

# Capacity Planner Skill

## Purpose

Compare each developer's assigned workload against their available capacity for the remainder of the sprint. Identify overload risks, underutilization, and project whether the sprint can complete on time.

## When to Invoke

- On `/capacity-planner` command
- During mid-sprint checkpoints to assess completion risk
- When user asks about developer workload, bandwidth, or capacity

## Data Dependencies (Load in This Order)

1. **Read**: `config.yaml` — `sprint` section (business_days, buffer_days), board config
2. **Read**: `team_config.yaml` — team members, roles, `default_hours_per_day`, `leave_dates`, `daily_overrides`
3. **Read**: `output/{sprint}/day-{N}/sprint.ai.json` — `teamSummary` section for current assignments and worklogs

## Execution

### Step 1: Determine Sprint Context

- Identify current sprint and day number from sprint.ai.json metadata
- Calculate remaining business days (total - current day - buffer_days)
- Note: buffer days are deployment-focused, not regular dev capacity

### Step 2: Compute Available Capacity Per Developer

For each team member in `team_config.yaml`:
- Base hours = `default_hours_per_day` x remaining_business_days
- Subtract leave: check `leave_dates` for any dates within remaining sprint window
- Apply `daily_overrides` if any (e.g., half-day Friday)
- Result: `available_hours` per developer

### Step 3: Compute Remaining Workload Per Developer

From `sprint.ai.json > teamSummary`:
- Count assigned tickets not yet done
- Sum `estimate_hours_remaining` for those tickets
- If no estimates: use average cycle time from developer_metrics as proxy
- Include tickets in blocked/review states (they still need work)

### Step 4: Calculate Utilization and Risk

Per developer:
- `utilization_pct` = remaining_work_hours / available_hours x 100
- `overload_risk`: >100% = overloaded, 80-100% = at capacity, <80% = has bandwidth
- `completion_probability`: based on utilization and historical completion rate

Sprint-level:
- `team_utilization_avg`: average utilization across team
- `bottleneck_developers`: anyone >120% utilization
- `available_bandwidth`: developers with <60% utilization who could take on work

### Step 5: Generate Capacity Matrix

Present a table:

| Developer | Role | Tickets Remaining | Est. Hours Left | Available Hours | Utilization % | Risk |
|-----------|------|-------------------|-----------------|-----------------|---------------|------|

Plus summary:
- Sprint completion risk assessment (low/medium/high)
- Recommended load rebalancing if bottlenecks exist
- Flag developers on leave during remaining sprint

## Output

- Capacity matrix table
- Sprint completion risk assessment
- Rebalancing recommendations (if applicable)

## Quality Self-Evaluation

After running, verify:
- [ ] All team members from team_config.yaml are included
- [ ] Leave dates are correctly factored into available hours
- [ ] Utilization percentages are reasonable (not negative, not >1000%)
- [ ] Risk assessment aligns with the numbers
- [ ] Recommendations are actionable (specific developers and ticket moves)
