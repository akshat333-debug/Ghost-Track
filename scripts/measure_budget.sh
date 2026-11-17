#!/usr/bin/env bash
# Python heap and compute per second of IMU against the Track 3 budgets (8 MB, 20 ms/s).
# Usage: scripts/measure_budget.sh <imu.csv>
set -euo pipefail
imu=$(cd "$(dirname "$1")" && pwd)/$(basename "$1")
cd "$(dirname "$0")/.."
mkdir -p build
out=build/budget_output.txt
echo "heap (limit 8 MB): $(python3 scripts/heap_probe.py "$imu" "$out")"
python3 - "$imu" "$out" <<'PY'
import subprocess, sys, time
imu, out = sys.argv[1:3]
walls = []
for _ in range(3):
    t = time.perf_counter()
    subprocess.run([sys.executable, "src/main.py", imu, out], check=True)
    walls.append(time.perf_counter() - t)
rows = [ln.split()[0] for ln in open(out)]
seconds = float(rows[-1]) - float(rows[0])
print(f"whole process, best of 3: imu_seconds={seconds:.3f} wall_seconds={min(walls):.3f} ms_per_imu_s={min(walls) * 1000 / seconds:.2f} (limit 20)")
PY
python3 research/eval/validate_format.py "$out" "$imu"
