#!/usr/bin/env bash
# Traced heap peak and compute per second of IMU against the Track 3 budgets (8 MB, 20 ms/s).
# Memory is traced from interpreter start, imports included: the strictest reading of the FAQ (D-015, D-020).
# Usage: scripts/measure_budget.sh <imu.csv>
set -euo pipefail
imu=$(cd "$(dirname "$1")" && pwd)/$(basename "$1")
cd "$(dirname "$0")/.."
mkdir -p build
out=build/budget_output.txt
python3 -X tracemalloc - "$imu" "$out" <<'PY'
import runpy, sys, time, tracemalloc
imu, out = sys.argv[1:3]
sys.argv = ["main.py", imu, out]
start = time.perf_counter()
runpy.run_path("src/main.py", run_name="__main__")
wall = time.perf_counter() - start
peak = tracemalloc.get_traced_memory()[1]  # read before this harness allocates anything of its own
rows = [ln.split()[0] for ln in open(out)]
seconds = float(rows[-1]) - float(rows[0])
print(f"peak_traced_mb={peak / 1e6:.2f} budget=8")
print(f"imu_seconds={seconds:.3f} wall_seconds={wall:.3f} ms_per_imu_s={wall * 1000 / seconds:.3f} budget=20 (tracing on, so an upper bound)")
PY
start=$(python3 -c 'import time; print(time.time())')
python3 src/main.py "$imu" "$out"
python3 - "$start" "$out" <<'PY'
import sys, time
wall = time.time() - float(sys.argv[1])
rows = [ln.split()[0] for ln in open(sys.argv[2])]
seconds = float(rows[-1]) - float(rows[0])
print(f"untraced whole process: wall_seconds={wall:.3f} ms_per_imu_s={wall * 1000 / seconds:.3f} budget=20")
PY
python3 research/eval/validate_format.py "$out" "$imu"
