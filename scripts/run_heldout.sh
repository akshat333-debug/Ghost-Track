#!/usr/bin/env bash
# The only entry point allowed to touch held-out sequences (D-003, D-006). Report, never tune.
# Usage: scripts/run_heldout.sh research.baselines.eskf
set -euo pipefail
cd "$(dirname "$0")/.."
PF_HELDOUT=1 python3 -m research.eval.run_split --method "$1" --split heldout --seeds 0 1 2
