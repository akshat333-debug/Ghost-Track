# Experiments

One row per run. Held-out numbers only from `scripts/run_heldout.sh`. Val numbers for tuning.

| date | commit | layer/config | split | ATE RMSE (m) | RPE (m/s) | blind-5s err (m) | dropout err (m) | peak RAM (MB) | ms per 1 s IMU | notes |
|---|---|---|---|---|---|---|---|---|---|---|
| 9 Nov | ee3517d | C++ ESKF (no nets), budget only | train: room1 seed 0 | — | — | — | — | 1.38 | 3.2 | macOS, not Linux Docker. Accuracy not measured here. |
| 9 Nov | 1b30092 | L0 naive | val (MH_05, room5), seeds 0–2, severity 1 | 8471 | 404 | 19839 | 6412 | — | — | mean. Never-moving reference: ATE 4.06, blind 4.56 |
| 9 Nov | 1b30092 | L1 ESKF (classical) | val (MH_05, room5), seeds 0–2, severity 1 | 3.99 | 1.03 | 5.67 | 3.11 | 1.38 (room1) | 3.2 (room1) | mean. ATE ties never-moving (4.06), blind worse than it (4.56). Tuned on train only. |
| 9 Nov | 362090d | L1 ESKF (reference for row below) | CV fold 0 (MH_01–03), seeds 0–1 | 4.30 | 0.87 | 3.11 | 3.85 | — | — | mean of 6 runs. Never-moving: ATE 4.37, blind 2.51 |
| 9 Nov | 362090d | L1 + L3 velocity net with tilt channel | CV fold 0 (MH_01–03, environment unseen in training), seeds 0–1 | 3.73 | 0.77 | 3.44 | 3.77 | — | — | mean of 6 runs. ATE beats never-moving; MH_03 worse than ESKF; blind worse. One fold only. |
| 9 Nov | fd5a31b | L1 ESKF + recent-area blind forecast (D-012) | val (MH_05, room5), seeds 0–2, severity 1 | 3.96 | 1.04 | 4.71 | 3.11 | — | — | mean. Never-moving: ATE 4.06, blind 4.56. |
| 9 Nov | c43a58d | C++ ESKF + velocity net (float32), budget only | train: room1 seed 0 | — | — | — | — | 1.77 | 8.8 | macOS, under concurrent training load. |
| 9 Nov | 863cde3 | L1 ESKF, reference for row below | 5-fold CV (all 11 train sequences), seeds 0–2 | 1.75 | — | 1.51 | 1.82 | — | — | median across runs |
| 9 Nov | 863cde3 | L1 + L3 velocity net, each fold scored on its unseen environment | 5-fold CV, seeds 0–2 | 2.60 | — | above 1.51, see notes | above 1.82, see notes | — | — | **Fails D-007 keep rule on ATE, waypoint, blind and dropout.** ATE gain −36%, wins 33%, worst sequence 165% worse. Helps MH_01, MH_02, V1_02, V2_01; hurts rooms, MH_03, V2_03. Full report: `research/results/cv_report.txt` (not committed). |
