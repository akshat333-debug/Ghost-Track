# Experiments

One row per run. Held-out numbers only from `scripts/run_heldout.sh`. Val numbers for tuning.

| date | commit | layer/config | split | ATE RMSE (m) | RPE (m/s) | blind-5s err (m) | dropout err (m) | peak RAM (MB) | ms per 1 s IMU | notes |
|---|---|---|---|---|---|---|---|---|---|---|
| 9 Nov | ee3517d | C++ ESKF (no nets), budget only | train: room1 seed 0 | — | — | — | — | 1.38 | 3.2 | macOS, not Linux Docker. Accuracy not measured here. |
| 9 Nov | 1b30092 | L0 naive | val (MH_05, room5), seeds 0–2, severity 1 | 8471 | 404 | 19839 | 6412 | — | — | mean. Never-moving reference: ATE 4.06, blind 4.56 |
| 9 Nov | 1b30092 | L1 ESKF (classical) | val (MH_05, room5), seeds 0–2, severity 1 | 3.99 | 1.03 | 5.67 | 3.11 | 1.38 (room1) | 3.2 (room1) | mean. ATE ties never-moving (4.06), blind worse than it (4.56). Tuned on train only. |
