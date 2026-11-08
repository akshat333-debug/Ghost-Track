#!/usr/bin/env bash
# The only entry point allowed to touch held-out sequences (D-003, D-006, D-007).
# Report, never tune. Budget: 3 runs per pipeline. Usage: scripts/run_heldout.sh research.baselines.eskf
set -euo pipefail
cd "$(dirname "$0")/.."
if [ -n "$(git status --porcelain)" ]; then
  echo "refusing: commit first so this run is traceable" >&2
  exit 1
fi
mean=$(PF_HELDOUT=1 python3 -m research.eval.run_split --method "$1" --split heldout --seeds 100 101 102 | tee /dev/stderr | grep '^MEAN')
echo "| $(date +%F) | $(git rev-parse --short HEAD) | $1 | $mean |" >> docs/HELDOUT_LOG.md
