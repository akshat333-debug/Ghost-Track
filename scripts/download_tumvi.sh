#!/usr/bin/env bash
# Streams each TUM-VI room tar (1.7+ GB) and keeps only IMU + mocap CSVs (a few MB).
set -euo pipefail
DATA="$(cd "$(dirname "$0")/.." && pwd)/research/data/tumvi"
BASE=https://cdn3.vision.in.tum.de/tumvi/exported/euroc/512_16
mkdir -p "$DATA"
for i in 1 2 3 4 5 6; do
  name="dataset-room${i}_512_16"
  [ -s "$DATA/$name/mav0/imu0/data.csv" ] && [ -s "$DATA/$name/mav0/mocap0/data.csv" ] && continue
  echo "fetching $name"
  curl -sSfL --retry 5 "$BASE/$name.tar" | tar -xf - -C "$DATA" \
    "$name/mav0/imu0/data.csv" "$name/mav0/mocap0/data.csv"
done
