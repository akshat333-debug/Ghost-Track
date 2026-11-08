# Track 3 "Path Finder" — Full Win Plan (Samsung PRISM XR Hackathon 2026)

> **Amended 9 Nov.** Binding changes on top of the original 8 Nov plan:
> - **Full build, nothing cut (D-005):** C++ port regardless of the organizers' memory answer; TUM-VI in training; L2 *and* L3 both built; GRU forecaster built and compared against constant velocity / damped acceleration; interactive replay demo built before submission.
> - **Selection happens on val, never held-out (D-006):** wherever this plan originally said "beat X on held-out", it now says val. Held-out is report-only.
> - **Split:** D-003 in `DECISIONS.md` is authoritative (MH_05 is val).
> - **Compute:** Colab/Kaggle free GPU for training, per D-005.

## Context
Goal: win Track 3 (top-4 prize + PPO). Task: degraded IMU CSV (EuRoC format) → 6-DoF trajectory, one pose per IMU frame, plus 5 s dead-reckoning after the IMU dies. Limits: ≤8 MB peak RAM, ≤20 ms compute per 1 s of IMU, single CPU thread, offline. Scored by evo (ATE/RPE) against hidden ground truth. Points: 40 efficiency (memory 20, runtime 20) and 60 accuracy (waypoints 30, blind 5 s 20, dropout 10).
Team: 3 all-rounders, each driving a Claude agent, handing work off via git. Hardware: 8 GB CPU laptops plus free Colab/Kaggle. Hard deadline 18 Nov 23:59, no extension. Today is 8 Nov, so 10 days.
Strategy: learned correction (AirIMU/AirIO-style) fused in an EKF, with a classical ESKF as the always-working fallback. Final inference in C++, because Python's own RSS (~20–30 MB with numpy) likely breaks 8 MB if they measure process peak.

## Day 0 (today, 8 Nov) — must do
1. **Register** via the form before 23:59 (CollegeName_TeamName, all 3 members, Theme = Track 3).
2. **Email prism@samsung.com** (draft in `docs/ORGANIZER_QUESTIONS.md`):
   - How is peak RAM measured (process RSS or tracemalloc)? Is C++ allowed? Docker or bare machine?
   - Test data: held-out sequences, or degraded public EuRoC/TUM-VI? When is the degradation script released?
   - Waypoints/checkpoints: are they given as input? How are they scored (position at timestamps)?
   - Blind 5 s: are timestamps for the 5 s provided as rows, or do we generate them at IMU rate?
   - Dropouts: rows missing, or NaN rows? Must we output poses for the missing timestamps?
   - evo alignment mode (none / SE3 / Sim3, origin alignment)? This decides how much the initial yaw matters.
3. Create a private GitHub repo, add all 3 members, scaffold the docs (below), first commit + push.

## Repo layout
```
pathfinder/
├── CLAUDE.md               # rules every member's agent follows (below)
├── README.md               # quickstart
├── TASKS.md                # live checklist, owner + status, "Next up" + handoff notes
├── DECISIONS.md            # ADR log: date, decision, why, alternatives, owner
├── EXPERIMENTS.md          # every run: commit, config, held-out ATE/RPE/blind/dropout, RAM, ms
├── docs/
│   ├── hackathondetails.md # moved from root
│   ├── PROJECT_FLOW.md     # end-to-end pipeline + how to run everything
│   ├── ARCHITECTURE.md     # estimator design, state vector, nets, data flow diagram
│   ├── WORKFLOW.md         # branching, commit/push, handoff protocol
│   └── ORGANIZER_QUESTIONS.md # questions + answers received
├── research/               # Python: training + experiments (not submitted as-is)
│   ├── data/ (gitignored)  # EuRoC/TUM-VI downloads
│   ├── io_euroc.py  degrade.py  split.py
│   ├── baselines/ naive.py  eskf.py
│   ├── nets/ imu_correct.py  vel_net.py  forecaster.py  train.py  export_weights.py
│   └── eval/ score.py (evo wrapper + proxy 100-pt scorer)  validate_format.py
├── src/                    # SUBMISSION code
│   ├── main.cpp  eskf.hpp  nets.hpp  weights.hpp (generated)  CMakeLists.txt
│   ├── main.py             # thin fallback entrypoint
│   └── README.md
├── tests/                  # format, timestamp, py-vs-cpp parity, memory/runtime budget
├── scripts/ download_data.sh  run_heldout.sh  measure_budget.sh  make_zip.sh
├── Dockerfile
└── submission/ (gitignored build output → team_name.zip)
```

## Team workflow (CLAUDE.md content — every agent obeys)
- Before work: `git pull`, read TASKS.md "Next up" + the latest handoff note + DECISIONS.md.
- One task = one small branch → PR or fast-forward to `main` same day. Never leave unpushed work overnight.
- After every unit of work, in the same commit: tick TASKS.md, add a handoff note (what was done, what's next, gotchas), log any decision in DECISIONS.md, log any result in EXPERIMENTS.md, and update PROJECT_FLOW/ARCHITECTURE if the flow changed.
- **Held-out rule:** never tune on test-split sequences. Only `run_heldout.sh` touches them, and only to report.
- Every number in the deck must trace to an EXPERIMENTS.md row with a commit hash.
- Ownership to avoid conflicts: A = estimator + C++; B = learned nets (Colab/Kaggle); C = data, degradation, eval harness, docs, video, deck. Rotate pairs for review.

## Evaluation methodology (built FIRST, before any tuning)
- **Data:** EuRoC (11 seqs, 200 Hz IMU, Vicon/Leica GT) + TUM-VI room1–6 (full mocap GT). Optional Blackbird for extra drone dynamics.
- **Split (frozen in DECISIONS.md on Day 1):** train = MH_01/02/03, V1_01/02, V2_01/03 + TUM rooms 1–4; val = TUM room5, MH_05; **held-out test = MH_04, V1_03, V2_02, TUM room6**. Test numbers get reported, never tuned on.
- **Degradation simulator `degrade.py`** mirrors the slide: escalating white noise, escalating bias random walk, 2 s dropouts, unknown initial attitude (random rotation of gravity), then total failure followed by a 5 s blind window. Randomized severity. Swapped for/validated against the organizer script once it arrives.
- **Scorer `score.py`:** evo ATE RMSE + RPE in both alignment modes, plus a proxy for their 100 pts: checkpoint error, blind-5 s endpoint/ATE, error inside dropout windows, peak RSS, ms per 1 s of IMU.
- **Format validator:** 8 columns, float seconds (ns×1e-9), unit quaternion, exactly one row per input IMU timestamp (+ blind rows per organizer answer), monotonic timestamps.

## Technical approach (layers, each must beat the previous on val)
- **L0 Naive strapdown:** gravity from the first ~1 s average accel, plain integration. Floor reference.
- **L1 Classical ESKF (fallback submission):**
  - State: p, v, q, b_g, b_a. Gravity alignment from the initial window plus online refinement.
  - Bias random walk with adaptive process noise (inflate Q when the noise estimate rises, to model escalating jamming).
  - Pseudo-measurements: zero-velocity/hover detection; velocity damping prior (bounded indoor flight).
  - Dropouts: propagate with the motion prior; interpolate pose across the gap if post-gap data allows (offline = smoothing is legal → RTS smoother pass).
- **L2 Learned IMU correction (AirIMU-style):**
  - Small 1D CNN/TCN predicts gyro/accel corrections + uncertainty from windows.
  - Trained on Colab with degradation augmentation; leave-sequence-out.
- **L3 Learned velocity measurement (AirIO-style):**
  - Net regresses body-frame velocity from ~1 s windows of body-frame IMU + attitude encoding.
  - Fused into the ESKF as a measurement with learned covariance. This is the main drift killer.
- **L4 Offline smoothing:** forward ESKF + backward RTS smoother. Offline processing is allowed and cuts ATE a lot.
- **L5 Blind 5 s forecaster:**
  - Candidates: constant velocity, damped constant acceleration, a small GRU/TCN forecasting from the last 2–3 s of estimated states.
  - Pick by val blind-5 s error; possibly blend by uncertainty.
- **Budget:** nets ≤ ~100k params, stored FP16/INT8 as a C array (≪1 MB). Inference runs at ~10–20 Hz windows, not per sample. Target well under 20 ms/s and under 4 MB RSS in C++.
- **C++ port:** Eigen (header-only) plus a hand-written conv/GRU forward pass. Weights exported to `weights.hpp`. Parity test vs Python ≤1e-5. Single thread enforced (`OMP_NUM_THREADS=1`, no threading in code).

## 10-day schedule
| Day | Date | A (estimator/C++) | B (learned nets) | C (data/eval/docs) |
|---|---|---|---|---|
| 0 | 8 Nov | repo scaffold, CLAUDE.md, docs | literature read: AirIMU, AirIO, TLIO, RoNIN | register, email organizers, download data |
| 1 | 9 | L0 naive + output writer | dataset loaders for training, window sampler | degrade.py, split frozen, score.py, validator |
| 2 | 10 | L1 ESKF + gravity init + bias | L2 correction net v1 trained (Colab) | held-out runner, EXPERIMENTS table, baseline numbers |
| 3 | 11 | dropout handling + RTS smoother | L3 velocity net v1 | memory/runtime harness (`/usr/bin/time`, Docker) |
| 4 | 12 | fuse L3 measurements into ESKF | augmentation sweep, uncertainty head | blind-5 s baselines + L5 forecaster v1 |
| 5 | 13 | **checkpoint: freeze best Python pipeline** on val | ablations (each layer on/off) | robustness sweep across degradation severities |
| 6 | 14 | C++ port ESKF + smoother | export weights, C++ net forward + parity tests | Dockerfile, README, reproducibility from fresh clone |
| 7 | 15 | C++ integration, budget tuning | final retrain (train+val), lock weights | deck draft + architecture diagram |
| 8 | 16 | full pipeline on all held-out + organizer script if out | stress tests, failure cases | video script + record walkthrough (2–3 min, ≤3 min total) |
| 9 | 17 | **feature freeze**, bug fixes only | final EXPERIMENTS numbers | zip via `make_zip.sh`, dry-run validation |
| 10 | 18 | — | — | **submit by 18:00**, not 23:59; keep a backup zip of the L1 fallback |
Fallback rule: if L2/L3 isn't beating L1 on val by Day 5 EOD, ship L1+L4+L5 in C++ and use the remaining days on robustness and efficiency.

## Jury and deck (for the top-15 cut and the 27 Nov demo)
- Framing: "IMU-only failover tracking for XR headsets/glasses when cameras lose tracking (dark, occlusion, fast motion)". That's Samsung's XR Perception group's own problem, not just a drone story.
- Show: an ablation table (L0→L5 on held-out), trajectory plots, error-vs-time across dropout and blind windows, RAM/ms vs budget, and an honest limitations slide (yaw unobservable, overfit risk).
- Innovation hooks for PRISM's patent/IP angle: degradation-aware adaptive noise + learned velocity measurement + uncertainty-gated blind forecasting.
- Live demo 27 Nov: interactive plot replaying the trajectory with degradation toggles.

## Verification
- `scripts/run_heldout.sh` → evo ATE/RPE + proxy 100-pt score on the frozen held-out sequences. Every layer logged in EXPERIMENTS.md.
- `tests/`: format validator, timestamp ns→s, row-count equality with input, quaternion norms, Python↔C++ parity.
- `scripts/measure_budget.sh`: peak RSS + ms per 1 s of IMU on Mac (`/usr/bin/time -l`) and in Linux Docker (`-v`), single thread.
- Final gate: fresh clone in Docker → build → run on a held-out degraded CSV → validator passes → zip structure matches slide 17 exactly.

## Risks
- The 8 MB RAM limit is likely to break with Python. Mitigation: C++ final; confirm the measurement method with the organizers.
- Organizer degradation may differ from ours. Mitigation: randomized augmentation; rerun as soon as their script lands.
- Test may reuse public EuRoC sequences. Never exploit known GT; held-out discipline keeps the claims defensible.
- Learned nets may overfit or blow the budget. Mitigation: L1 fallback always shippable, decided at the Day 5 checkpoint.
