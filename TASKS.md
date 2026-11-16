# Tasks

Status: `todo` / `in progress (owner)` / `done (commit)`. Owners: A estimator+C++, B nets, C data/eval/docs.

## Next up (16 Nov replan; schedule in `docs/PLAN.md` header)
- [x] Follow-up questions: not sent, user decision 16 Nov; handled by detection and two-way tests
- [ ] One-shot baseline: frozen ESKF on official-degraded val, logged before any tuning (D-007 rule 2)
- [ ] Gate G1: `python3 -m research.eval.drag_gate` (D-019)
- [x] `src/main.py` v0 (parser, front end, attitude, CLI), budget + robustness tests, Dockerfile, `scripts/measure_budget.sh` for Python
- [ ] Backup zip 1 once v0 at least ties never-moving
- [ ] 18 Nov: node filter + RTS in pure Python; drag measurement if G1 passed; keep-rule verdict on dev variants
- [ ] 19 Nov: blind forecaster CV, val confirmation, sweeps, Docker budgets, held-out run 1
- [ ] 20 Nov: freeze; README, `scripts/make_zip.sh`, fresh-clone repro, deck, brownie (sensor-health timeline + replay)
- [ ] 21 Nov: video, self-audit, repo public, submit
- Cancelled by D-015/D-018: C++ RTS, C++ Docker build, L2 net, GRU forecaster.

## Earlier list (before the FAQ)
- [ ] Waiting on organizer reply to questions sent 9 Nov; log answers in `docs/ORGANIZER_QUESTIONS.md` (C)
- [ ] Day 0 — Download EuRoC + TUM-VI CSVs: `scripts/download_euroc.py`, `scripts/download_tumvi.sh`; each teammate runs once (in progress)
- [ ] Day 0 — Read AirIMU, AirIO, TLIO, RoNIN; summary in `docs/LITERATURE.md` (B)

## Day 1 (9 Nov)
- [x] `research/io_euroc.py` loader (IMU csv + GT) + TUM writer (A)
- [x] L0 naive strapdown baseline `research/baselines/naive.py` (A)
- [x] Training window sampler (`research/nets/data.py`)
- [x] `research/augment.py`: training degradation family, distinct from `degrade.py`
- [x] Grouped 5-fold CV folds and `research/nets/train_vel.py`
- [x] `research/degrade.py` degradation simulator (C)
- [x] `research/eval/score.py` (evo ATE/RPE + proxy 100-pt) + `validate_format.py` (C)

## Day 2–4
- [x] L1 ESKF tuned on train (tilt noise); parity with C++ held
- [ ] Dropout handling + RTS smoother (A)
- [ ] L2 IMU correction net v1 (B)
- [ ] L3 velocity net: failed keep rule (D-014); next step awaits team decision (B)
- [x] Fusion hook: `eskf.run(..., vel_fn=...)`; C++ net forward still pending
- [x] `scripts/run_heldout.sh`
- [x] `scripts/measure_budget.sh`
- [x] L5 classical blind forecast (D-012), in Python and C++
- [ ] L5 GRU forecaster; must beat D-012 on val (B)

## Day 5 checkpoint (13 Nov)
- [ ] Freeze best Python pipeline by val results (D-006). Fallback rule: if L2/L3 don't beat L1, ship L1+L4+L5.

## Day 6–9
- [x] C++ port of ESKF, with Python parity test
- [ ] C++ RTS smoother (A)
- [x] Weight export + C++ net forward (`-DPF_NET`) + parity test (≤1e-3 m, float32 net)
- [ ] Dockerfile and `src/README.md` written; build and run in Docker not yet tested, repo README and fresh-clone repro pending (C)
- [ ] Deck (`CollegeName_TeamName`), architecture diagram (C)
- [ ] Walkthrough video ≤3 min (C)
- [ ] Interactive replay demo with degradation toggles, before submission (C, D-005)
- [ ] Feature freeze 17 Nov; `scripts/make_zip.sh`; dry-run validation (all)

## Day 10 (18 Nov)
- [ ] Submit by 18:00 via Google Form. Keep backup L1 zip.

## Done
- [x] Team registered as **Zero Drift** (confirmed 9 Nov)
- [x] Repo scaffold + team docs (local commit, 8 Nov)
- [x] GitHub remote `akshat333-debug/Ghost-Track` connected, `main` pushed (9 Nov)
- [x] Full plan saved to `docs/PLAN.md` (9 Nov)

---
## Handoff notes (newest on top)
### 16 Nov — `src/main.py` v0
- Done: pure-stdlib streaming `src/main.py` (layout/unit/rate detection, duplicate and stuck rows, 3-sample median against spikes, real-`dt` integration, coast through gaps and the dead tail, half-millimetre circle so evo can always align). `tests/test_main.py`: both column orders, 13 robustness cases, byte determinism, folder/zip input, memory and runtime gates. Dockerfile and `scripts/measure_budget.sh` now run Python. Measured on room1 (Mac, machine under download load): 5.15 MB traced from interpreter start, 2 to 4 ms per IMU-second.
- Organizer follow-up email will not be sent (user, 16 Nov: no time). Every open question is covered by detection or by testing both readings.
- Not good yet: v0 position is a leaky integrator, ATE about 4 m on room1 against 1.0 m for never-moving, and tilt error reaches 10 to 15 degrees in bursts. EuRoC gyro bias is about 0.08 rad/s (plain integration drifts 4.6 deg/s on MH_05), so the bias state matters. The node filter + RTS of 18 Nov replaces the position and attitude core; do not tune v0 constants.
- Next: when downloads finish, one-shot baseline row, gate G1, then the node filter.
- Gotchas: timing tests are noisy while downloads run (load average was 48); the runtime test takes best of three.
### 16 Nov — FAQ pivot
- Done: FAQ and official script read and vendored; D-015 to D-021; C++ moved to `legacy/cpp/`; `research/official_degrade.py`, `research/eval/run_official.py`, `research/eval/drag_gate.py`; scorer reports full-alignment tiers and tolerates duplicated rows; 17 tests pass.
- Next: baseline row, G1, then `src/main.py`.
- Gotchas: `Dockerfile` and `scripts/measure_budget.sh` still build the C++ and are broken until `main.py` lands. Never tune on `--variant official`. Order B noise depends on the sequence because of the script's unit auto-detect (D-016).
- How to run: `python3 -m pytest tests -q`
### 9 Nov — 5-fold verdict
- Done: L3 failed the D-007 keep rule (D-014). Do not relax thresholds to pass it.
- Next: choose between calibrating fusion (no retraining) and a drone-focused rebuild. Candidate pipeline meanwhile is classical ESKF + D-012.
- Gotchas: any calibration chosen on CV must then be confirmed once on val.
### 9 Nov — C++ net forward
- Done: `research/nets/export_weights.py`, `src/vel_net.hpp`, `-DPF_NET` build. Parity with Python within 1e-3 m on a degraded flight. Net build on room1: 1.77 MB, 8.8 ms per 1 s of IMU, measured under training load.
- Next: `src/weights.hpp` is generated from the final model, not committed yet. A build without `-DPF_NET` remains the classical fallback.
### 9 Nov — window test closed
- Done: D-013, window stays 1 s; `PF_WINDOW` and the pooling layer removed. Early stopping skips warmup epochs.
- Next: `scripts/train_cv.sh` running, result in `research/results/cv_report.txt`.
### 9 Nov — blind forecast
- Done: D-012 in `eskf.py` and `src/main.cpp`, parity test passes. Val blind 5.67 to 4.71 m (never-moving 4.56).
- In progress: window-length test on fold 0. `PF_WINDOW` env override stays until a length is chosen; default 200 is unchanged.
### 9 Nov — tilt test result
- Done: D-011. Tilt channel barely helps. Velocity accuracy equals clean-input accuracy, so more denoising will not help. ATE on the unseen hall improves over ESKF and never-moving on MH_01 and MH_02, worse on MH_03.
- Next: test a longer input window (2–3 s) on fold 0 before running all folds. Fusion should be disabled in the blind window planning: it does not help there.
### 9 Nov — tilt channel, CV paused
- Done: stopped the D-009 CV run after fold 0 stalled near 0.44 m/s (0.49 for zero). Added the tilt channel (D-010). RTS smoother added (`research/baselines/eskf_rts.py`): on train, RPE 0.90 to 0.72 and dropout 2.35 to 2.14, ATE unchanged; classical only.
- Next: compare `research/results/fold0_tilt.log` with `fold0_no_tilt.log`, then decide whether to run `scripts/train_cv.sh`.
- Gotchas: C++ RTS and net forward are not ported yet.
### 9 Nov — val confirmation, all data in
- Done: all 17 sequences downloaded; GT frames pass on train and val. Val: L0 ATE 8471 m, L1 ATE 3.99 m, never-moving 4.06 m. L1 blind 5.67 m is worse than never-moving 4.56 m.
- Next: `scripts/train_cv.sh` is running locally (40 epochs, 5 folds); result in `research/results/cv_report.txt`. Do not start another MPS job until it finishes.
### 9 Nov — ESKF tuning and CV runner
- Done: tilt noise set to 4 m/s^2 (flat optimum at severity 0.5–3), median tilt error now about 1°. Gap attitude uncertainty raised. Net fusion hook added. `scripts/train_cv.sh` trains all folds and applies the D-007 keep rule via `research/eval/run_cv.py`. Tried and removed: holding the last angular rate through gaps (no gain).
- Finding: tightening velocity or position priors drives ATE to the never-moving value (about 1.27 m median on 6 train sequences). Classical IMU-only cannot beat it; do not tune further for ATE.
- Next: when all sequences land, `scripts/train_cv.sh`.
- Gotchas: sweeps used train sequences only.
### 9 Nov — velocity net code
- Done: `augment.py`, grouped folds, `VelNet` (84,246 params), trainer with early stopping and coverage reporting; runs on Apple MPS, and Colab/Kaggle should need no change. 15 tests pass.
- Smoke only (train room1, test room2, 6 epochs): test RMSE 0.47 m/s per axis vs 0.59 for predicting zero, train 0.33 and widening, coverage 0.51 (target 60–75%). One training sequence, so this proves the pipeline runs, not accuracy. Not an experiment row.
- Next: when all data lands, run folds 0–4, then fuse into the ESKF. Replace the assumed 5° tilt error in `data.py` with the ESKF's measured tilt error.
- Gotchas: nets must never import the evaluation simulator (test enforces). Early-stop epoch from CV becomes `--epochs` for `--fold final`.
### 9 Nov — C++ port and budgets
- Done: `src/main.cpp` matches `eskf.py` within 1e-5 m on a degraded flight; 12 tests pass. Budget on room1: 1.38 MB, 3.2 ms per 1 s of IMU. Dockerfile and `src/README.md` added.
- Next: Docker build test (Docker Desktop must be running); data, then ESKF tuning.
- Gotchas: any change to `eskf.py` or its PARAMS must be mirrored in `src/main.cpp`, or the parity test fails. Budget numbers are macOS; re-measure in Linux Docker before quoting.
- Run: `scripts/measure_budget.sh research/data/degraded/room1_s0/mav0/imu0/data.csv`
### 9 Nov — first ESKF, zero-effort reference
- Done: L1 ESKF with tilt, stillness, bounded-velocity and bounded-position pseudo-measurements. Scorer now reports `null_ate` and `null_blind`: error of a tracker that stays at the flown centroid.
- Finding (room1, 3 seeds, train split, not tuned): ESKF ATE 1.74–2.11 m vs null 1.04 m; blind 2.6–6.8 m vs null 0.8–1.1 m. Better than L0 by three orders of magnitude, but worse than not moving. Small rooms reward doing nothing, so a method is only credible if it beats `null_*`.
- Next: when data lands, compare against null on every train sequence. Do not simply tighten `pos_sigma` to room size: that collapses to null and would fail in the larger Machine Hall.
- Run: `python3 -c` smoke as in the Run section of PROJECT_FLOW, or `python3 -m research.eval.run_split --method research.baselines.eskf --split train`.
### 9 Nov — real-data check on room1
- Done: GT frame confirmed on room1 (gyro vs GT-derived rate correlation ≥0.99); L0 attitude drift 2.5° over 130 s on clean data, so the integrator is right. Scorer fixed for 120 Hz mocap: match count and the 1 s RPE delta no longer assume 200 Hz.
- Next: when downloads finish, `python3 -m research.eval.check_gt train val`, then L0 on val, then L1 ESKF.
- Gotchas: `ate_rot_deg` is meaningless when position has diverged, because SE(3) alignment comes from positions; judge attitude by relative rotation error. Don't hardcode gravity: room1 world-z specific force averages 9.77 m/s², so L1 should estimate magnitude and accel bias. TUM-VI starts handheld and moving, so a static-start assumption fails.
### 9 Nov — anti-overfitting protocol
- Done: D-007 logged; held-out runs now need a clean tree, use seeds 100–102, and append to `docs/HELDOUT_LOG.md`; test blocks nets from importing `degrade.py`.
- Next: real-data L0, then L1 ESKF. Team B must build `augment.py` and the CV harness before the first training run.
- Gotchas: read D-007 before tuning anything. Team is Zero Drift; organizer email still needs the college name.
### 9 Nov — eval harness + L0
- Done: loader, TUM writer, degradation simulator, evo scorer with per-tier errors, format validator, L0, held-out guard, 7 self-checks passing on synthetic flights.
- Next: real-data run of L0 on val, ground-truth frame check, then L1 ESKF.
- Gotchas: `degrade` cuts each sequence at failure + 5 s so the blind window is mid-flight. Sensor mounting is randomized, so nets need rotation handling or augmentation. `proxy60` uses our own scales: rank our methods with it, never quote it. Blind and dropout rows are NaN until organizers answer Q6/Q7.
- Run: `python3 -m pytest tests -q`
### 9 Nov — remote + plan
- Done: remote connected; plan saved to `docs/PLAN.md`; D-005 (full build) and D-006 (select on val only) logged.
- Next: data download, then loader, degrade, scorer, validator, L0.
- Gotchas: D-004 said "beat on held-out", which contradicted D-003. D-006 fixes that. Use val for every choice.
### 8 Nov — scaffold
- Done: git repo, folder layout, CLAUDE.md, TASKS/DECISIONS/EXPERIMENTS, docs (flow, architecture, workflow, organizer questions).
- Next: GitHub remote + push; register; send organizer email; data download.
- Gotchas: Python RSS likely > 8 MB → final submission planned in C++ (D-002). Waiting on organizer answers for memory measurement, test data, blind-window timestamps.
