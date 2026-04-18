---
name: flag-control
description: Enable, disable, or adjust flag thresholds and tracking windows. Interactive flag management with comment-preserving YAML edits.
---

# Flag Control Skill

## Purpose

Manage the 43 productivity flags in `flags.yaml`: enable/disable flags, adjust thresholds, modify tracking windows, and review flag status. All edits preserve YAML comments and formatting via `ruamel.yaml`.

## When to Invoke

- On `/flag-control` command
- When user asks to enable, disable, or adjust a specific flag
- When reviewing which flags are active/disabled for a board
- After feedback loop identifies flags needing manual adjustment

## Data Dependencies (Load in This Order)

1. **Read**: `flags.yaml` — all 43 flag definitions
2. **Read**: `config.yaml` — board list, self_healing section
3. **Read**: `CHANGELOG.md` — recent changes (last 20 lines) for context

## Supported Operations

### List Flags

- `list` — show all flags with id, name, enabled, severity, category
- `list --disabled` — show only disabled flags with reason
- `list --board {ALPHA|BETA|GAMMA}` — show flags active for a specific board
- `list --category {category}` — filter by category (DoR Compliance, Sprint Execution, etc.)

### Enable / Disable

- `enable {flag_id}` — set `enabled: true` for the flag
- `disable {flag_id}` — set `enabled: false` for the flag
- Always confirm the action with the user before writing, showing flag name and current state
- Log the change to `CHANGELOG.md`

### Adjust Thresholds

- `adjust {flag_id} {threshold_key} {value}` — modify a specific threshold parameter
- Show current value and proposed new value before applying
- Validate: numeric thresholds must be positive, day values must be within sprint range
- Log the change to `CHANGELOG.md`

### Adjust Tracking Window

- `window {flag_id} {track_from_day} {stop_at_day}` — modify the tracking window
- Validate: track_from_day < stop_at_day, both within [-1, sprint_length]
- Log the change to `CHANGELOG.md`

### Show Flag Detail

- `show {flag_id}` — display full flag definition including all thresholds, boards, detection type

## Execution

### Step 1: Parse User Request

- Identify operation (list, enable, disable, adjust, window, show)
- Extract flag_id and parameters
- If ambiguous, ask user to clarify

### Step 2: Validate

- Confirm flag_id exists in flags.yaml
- For threshold adjustments: validate the threshold key exists for the flag's detection_type
- For window changes: validate day range is valid

### Step 3: Confirm with User

- Display: flag name, current state, proposed change
- Wait for user confirmation before writing
- Exception: `list` and `show` operations need no confirmation

### Step 4: Apply Change

- Use `ruamel.yaml` round-trip load/dump to preserve all comments and formatting
- Write updated `flags.yaml`
- Append change entry to `CHANGELOG.md` with format:
  ```
  ### YYYY-MM-DD — Flag Control
  - Flag {id} ({name}): {description of change}
  ```

### Step 5: Verify

- Re-read `flags.yaml` to confirm the change was applied correctly
- Report success to user

## Output

- Modified `flags.yaml` (comment-preserving)
- Updated `CHANGELOG.md`

## Quality Self-Evaluation

After running, verify:
- [ ] flags.yaml is valid YAML (no parse errors)
- [ ] YAML comments and formatting preserved
- [ ] CHANGELOG.md entry documents the change with date and flag details
- [ ] Only the targeted flag was modified — no collateral changes
- [ ] User confirmed before any write operation
