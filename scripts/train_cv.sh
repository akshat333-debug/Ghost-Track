#!/usr/bin/env bash
# Trains one velocity net per left-out environment (D-007), then applies the keep rule.
# Usage: scripts/train_cv.sh [epochs]
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p research/results
for k in 0 1 2 3 4; do
  python3 -u -m research.nets.train_vel --fold "$k" --epochs "${1:-40}" --out "research/results/vel_fold$k.pt" | tee "research/results/vel_fold$k.log"
done
python3 -u -m research.eval.run_cv | tee research/results/cv_report.txt
