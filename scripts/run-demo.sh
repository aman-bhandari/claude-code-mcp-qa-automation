#!/usr/bin/env bash
# Run the demo end-to-end against the synthetic fixtures.
#
# Produces:
#   output/<board>/report.html      one per board
#   output/summary.json             run summary
#   output/_db/<board>.sqlite3      per-board SQLite store
#
# Prerequisites: python3.10+, pip install pyyaml

set -euo pipefail
cd "$(dirname "$0")/.."

if ! python3 -c 'import yaml' 2>/dev/null; then
  echo "pyyaml not installed. Run: pip install pyyaml  (or: pip install -e .)" >&2
  exit 1
fi

# Clean stale output so the demo is reproducible from scratch.
rm -rf output

python3 -m src

# Verify artifacts landed where advertised
for path in output/ALPHA/report.html output/BETA/report.html output/summary.json; do
  if [[ ! -f "$path" ]]; then
    echo "FAIL: expected $path but it was not produced" >&2
    exit 1
  fi
done

echo
echo "Demo complete. Open output/ALPHA/report.html in a browser."
