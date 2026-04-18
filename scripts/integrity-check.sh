#!/usr/bin/env bash
# Integrity check for claude-code-mcp-qa-automation.
# Runs Gates 0, 4, 5 from the bulletproof publishing contract plus artifact-
# specific verification that the advertised shape is what the repo ships.
#
# Gate 0: every claim in docs/claim-evidence.md must be marked verified.
# Gate 4: zero occurrences of private identifiers from the private source repos.
# Gate 5: zero secret-like tokens outside whitelisted files.
# Artifact-specific: skill count, Python-module count, store schema, demo runs,
#                    tests pass.

set -euo pipefail

cd "$(dirname "$0")/.."

fail=0
green() { printf '\033[32m%s\033[0m\n' "$1"; }
red()   { printf '\033[31m%s\033[0m\n' "$1"; }

echo "[Gate 0] claim-evidence mapping..."
# Match only unchecked-box *table cells* — pipe-delimited — not prose explaining the rule.
if grep -Eq '^\| .* \| .* \| ☐ \|$' docs/claim-evidence.md; then
  red "FAIL: unverified claims in docs/claim-evidence.md (look for | ☐ | rows)"
  fail=1
else
  green "OK: all claim-table rows marked verified"
fi

echo "[Gate 4] identifier grep (private names / clients / domains)..."
# The targeted leak surface for this artifact: real client domains, real
# individual names, real board codes, real Atlassian/Slack IDs. The word list
# is narrow and unique — no generic English to avoid false positives. Three
# meta-files are excluded because they enumerate the banned tokens as part of
# the sanitisation policy itself, not as leaks:
#   - integrity-check.sh  (this file — the word list lives in the regex)
#   - claim-evidence.md   (references the sanitisation policy by name)
#   - tests/test_pipeline.py (regression-test asserts the forbidden list is
#     absent from fixtures — it IS the backstop for this gate)
if grep -riE \
  'sirrista|saacash|aman0101|ATATT3|xoxe|xoxp|\bOlga\b|\bArun\b|\bThinh\b|\bHudson\b|\bAnida\b|\bVladimir\b|\bSirish\b|Om Prakash|dev\.querylah|bhandari\.aman0101|taksha|daxa|querylah' \
  --exclude-dir=.git \
  --exclude-dir=.pytest_cache \
  --exclude-dir=__pycache__ \
  --exclude-dir=output \
  --exclude=integrity-check.sh \
  --exclude=claim-evidence.md \
  --exclude=test_pipeline.py \
  . ; then
  red "FAIL: identifier leak"
  fail=1
else
  green "OK: no private identifiers"
fi

echo "[Gate 5] secret grep..."
# Narrow to assignment-style and well-known secret prefixes. Prose discussion of
# 'token' / 'secret' / 'api key' in markdown documentation is allowed — only
# real credentials trip this gate.
hits=$(grep -riE \
  '(sk-[a-zA-Z0-9]{20,}|sk-ant-[a-zA-Z0-9_-]{20,}|ghp_[a-zA-Z0-9]{20,}|xoxb-[0-9a-zA-Z-]{20,}|xoxp-[0-9a-zA-Z-]{20,}|ATATT3[a-zA-Z0-9]{20,}|AKIA[A-Z0-9]{16}|[A-Z_]+_(KEY|TOKEN|SECRET|PASSWORD)=[^[:space:]]+)' \
  --exclude-dir=.git \
  --exclude-dir=.pytest_cache \
  --exclude-dir=__pycache__ \
  --exclude-dir=output \
  --exclude-dir=node_modules \
  --exclude='*.env.example' \
  --exclude=integrity-check.sh \
  . || true)
if [[ -n "$hits" ]]; then
  red "FAIL: possible secret(s) detected — review manually:"
  echo "$hits"
  fail=1
else
  green "OK: no secret patterns"
fi

echo "[Artifact-specific] skill count..."
skill_count=$(find .claude/skills -maxdepth 1 -mindepth 1 -type d | wc -l)
if [[ "$skill_count" -ne 16 ]]; then
  red "FAIL: expected 16 skill directories, found $skill_count"
  fail=1
else
  green "OK: 16 skill directories"
fi

echo "[Artifact-specific] every skill has SKILL.md..."
missing_skill=0
for d in .claude/skills/*/; do
  if [[ ! -f "$d/SKILL.md" ]]; then
    red "FAIL: $d missing SKILL.md"
    missing_skill=1
  fi
done
if [[ "$missing_skill" -eq 0 ]]; then
  green "OK: every skill has SKILL.md"
else
  fail=1
fi

echo "[Artifact-specific] Python module count..."
module_count=$(find src -maxdepth 1 -type f -name '*.py' | wc -l)
if [[ "$module_count" -ne 8 ]]; then
  red "FAIL: expected 8 Python modules in src/, found $module_count"
  fail=1
else
  green "OK: 8 Python modules in src/"
fi

echo "[Artifact-specific] store schema has 7 CREATE TABLE statements..."
create_table_count=$(grep -c 'CREATE TABLE IF NOT EXISTS' src/store.py || true)
if [[ "$create_table_count" -ne 7 ]]; then
  red "FAIL: expected 7 CREATE TABLE statements in src/store.py, found $create_table_count"
  fail=1
else
  green "OK: 7-table SQLite schema"
fi

echo "[Artifact-specific] pytest..."
if python3 -m pytest tests/ -q >/tmp/qa_pytest.log 2>&1; then
  green "OK: pytest passed"
else
  red "FAIL: pytest — see /tmp/qa_pytest.log"
  cat /tmp/qa_pytest.log
  fail=1
fi

echo "[Artifact-specific] demo runs end-to-end..."
if bash scripts/run-demo.sh >/tmp/qa_demo.log 2>&1; then
  green "OK: demo succeeded"
else
  red "FAIL: demo — see /tmp/qa_demo.log"
  cat /tmp/qa_demo.log
  fail=1
fi

echo
if [[ "$fail" -ne 0 ]]; then
  red "INTEGRITY CHECK FAILED"
  exit 1
fi
green "ALL GATES GREEN"
