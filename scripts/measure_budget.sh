#!/usr/bin/env bash
# Peak RSS and compute per second of IMU against the Track 3 budgets (8 MB, 20 ms/s).
# Usage: scripts/measure_budget.sh <imu.csv>
set -euo pipefail
imu=$(cd "$(dirname "$1")" && pwd)/$(basename "$1")
cd "$(dirname "$0")/.."
mkdir -p build
g++ -O2 -std=c++17 -o build/pathfinder src/main.cpp
out=build/budget_output.txt
if [ "$(uname)" = Darwin ]; then
  stats=$(/usr/bin/time -l build/pathfinder "$imu" "$out" 2>&1)
  rss_mb=$(awk '/maximum resident set size/{printf "%.2f", $1/1048576}' <<<"$stats")
  secs=$(awk '/ real /{print $1}' <<<"$stats")
else
  stats=$(/usr/bin/time -f '%M %e' build/pathfinder "$imu" "$out" 2>&1)
  rss_mb=$(awk '{printf "%.2f", $1/1024}' <<<"$stats")
  secs=$(awk '{print $2}' <<<"$stats")
fi
duration=$(awk -F, '!/^#/{if(!f)f=$1; l=$1} END{printf "%.3f", (l-f)*1e-9}' "$imu")
echo "peak_rss_mb=$rss_mb budget=8"
echo "imu_seconds=$duration wall_seconds=$secs ms_per_imu_s=$(awk -v s="$secs" -v d="$duration" 'BEGIN{printf "%.3f", s*1000/d}') budget=20"
python3 research/eval/validate_format.py "$out" "$imu"
