# Experiments

One row per run. Held-out numbers only from `scripts/run_heldout.sh`. Val numbers for tuning.

| date | commit | layer/config | split | ATE RMSE (m) | RPE (m/s) | blind-5s err (m) | dropout err (m) | peak RAM (MB) | ms per 1 s IMU | notes |
|---|---|---|---|---|---|---|---|---|---|---|
| 9 Nov | ee3517d | C++ ESKF (no nets), budget only | train: room1 seed 0 | — | — | — | — | 1.38 | 3.2 | macOS, not Linux Docker. Accuracy not measured here. |
