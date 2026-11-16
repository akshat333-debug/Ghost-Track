#!/usr/bin/env bash
# The only entry point allowed to touch held-out sequences (D-003, D-006, D-007, D-017).
# Report, never tune. Budget: 3 runs per pipeline. Official script, seed 42, both column orders.
# Usage: scripts/run_heldout.sh [method]   (default src/main.py)
set -euo pipefail
cd "$(dirname "$0")/.."
method="${1:-src/main.py}"
if [ -n "$(git status --porcelain)" ]; then
  echo "refusing: commit first so this run is traceable" >&2
  exit 1
fi
mkdir -p research/results
log="research/results/heldout_$(git rev-parse --short HEAD).log"
PF_HELDOUT=1 python3 -m research.eval.run_official --method "$method" --split heldout --variant official 2>/dev/null | tee "$log"
echo "| $(date +%F) | $(git rev-parse --short HEAD) | $method | $(grep '^MEAN' "$log") |" >> docs/HELDOUT_LOG.md
