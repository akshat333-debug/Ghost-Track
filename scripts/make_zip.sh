#!/usr/bin/env bash
# Builds submission/VITVellore_ZeroDrift.zip in the slide-17 layout.
# The bundled trajectory comes from a public sequence run through the organizers' script exactly as their FAQ
# describes (raw EuRoC file in, script defaults): MH_01_easy unless another clean IMU CSV is given.
# Usage: scripts/make_zip.sh [clean imu0/data.csv]
set -euo pipefail
cd "$(dirname "$0")/.."
clean="${1:-research/data/euroc/MH_01_easy/mav0/imu0/data.csv}"
name=VITVellore_ZeroDrift
work=build/bundle
rm -rf "$work" && mkdir -p "$work/sample/imu0" "$work/$name/src" submission
python3 research/official/degrade_imu.py "$clean" "$work/sample/imu0/data.csv" > "$work/degrade.log"
python3 -X tracemalloc - "$work/sample/imu0/data.csv" "$work/$name/estimated_trajectory.txt" "$clean" > "$work/$name/metadata.json" <<'PY'
import json, platform, runpy, subprocess, sys, time, tracemalloc
imu, out, clean = sys.argv[1:4]
sys.argv = ["main.py", imu, out]
runpy.run_path("src/main.py", run_name="__main__")
peak = tracemalloc.get_traced_memory()[1]
walls = []
for _ in range(3):
    t = time.perf_counter()
    subprocess.run([sys.executable, "src/main.py", imu, out], check=True)
    walls.append(time.perf_counter() - t)
rows = [ln.split()[0] for ln in open(out)]
seconds = float(rows[-1]) - float(rows[0])
print(json.dumps({
    "team": "VITVellore_ZeroDrift", "track": 3, "entrypoint": "src/main.py",
    "run": "python3 src/main.py <imu0/data.csv | folder | zip> [estimated_trajectory.txt]",
    "dependencies": "Python 3 standard library only",
    "sample_input": f"{clean} degraded with the organizers' degrade_imu.py (defaults, seed 42), raw EuRoC column order",
    "poses": len(rows), "imu_seconds": round(seconds, 3),
    "peak_heap_mb_traced_from_interpreter_start": round(peak / 1e6, 2),
    "wall_seconds_whole_process_best_of_3": round(min(walls), 3),
    "ms_per_imu_second": round(min(walls) * 1000 / seconds, 2),
    "threads": 1, "python": platform.python_version(), "machine": platform.machine(), "system": platform.system(),
    "commit": subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip(),
}, indent=2))
PY
python3 research/eval/validate_format.py "$work/$name/estimated_trajectory.txt" "$work/sample/imu0/data.csv"
cp src/main.py src/README.md "$work/$name/src/"
(cd "$work" && rm -f "../../submission/$name.zip" && zip -qr "../../submission/$name.zip" "$name")
unzip -l "submission/$name.zip"
cat "$work/$name/metadata.json"
