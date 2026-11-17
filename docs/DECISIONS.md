# Decisions

Format: ID · date · decision · why · alternatives rejected · owner. Never edit an old entry; supersede it with a new one.

### D-001 · 8 Nov · Pick Track 3 (Path Finder)
- Why: fully objective scoring (evo), CPU-only, small deliverable, core XR problem (6DoF tracking fallback), likely fewest entrants.
- Rejected: T1 (low ceiling, ties), T4 (GPU/video heavy), T2 (crowded, ≥70% top-1 likely infeasible, needs phone power/thermal measurements).

### D-002 · 8 Nov · Final submission estimator in C++; research in Python
- Why: Python+numpy process RSS ≈ 20–30 MB, far above the 8 MB budget if they measure process peak. C++ (Eigen, header-only) fits easily and maximizes the 40 efficiency points.
- Rejected: pure-Python submission (budget risk). Revisit if organizers say memory = tracemalloc.

### D-003 · 8 Nov · Frozen data split
- Train: EuRoC MH_01, MH_02, MH_03, V1_01, V1_02, V2_01, V2_03 + TUM-VI room1–4.
- Val: MH_05, TUM-VI room5 (tuning, model selection, thresholds).
- **Held-out test: MH_04, V1_03, V2_02, TUM-VI room6.** Report only, never tune.
- Why: mixes easy/medium/hard per environment; held-out set has one sequence per scene type.

### D-004 · 8 Nov · Strategy = learned layers on a classical ESKF, with fallback
- Layers: L0 naive → L1 ESKF → L2 learned IMU correction → L3 learned velocity measurement → L4 RTS smoothing → L5 blind-5 s forecaster. Each layer must beat the previous one on held-out to be kept.
- Fallback rule: if L2/L3 don't beat L1 by Day 5 (13 Nov) EOD, ship L1+L4+L5.

### D-005 · 9 Nov · Full build; nothing cut for cost (user decision)
- Keep all of: C++ final regardless of the organizers' memory answer (confirms D-002, removes its "revisit" clause), TUM-VI in training, L2 and L3 both, GRU blind forecaster alongside the simple candidates, interactive replay demo before submission.
- Why: being ready for any organizer answer beats depending on one. Training may use Colab/Kaggle GPU.
- Rejected: conditional "build only if needed" scoping proposed on 9 Nov.

### D-006 · 9 Nov · Every selection uses val; held-out is report-only (supersedes the "held-out" wording in D-004)
- D-004's "must beat the previous one on held-out" and its Day 5 fallback test contradicted D-003 and the CLAUDE.md held-out rule: picking layers on held-out makes the reported numbers optimistic.
- Layer keep/drop, thresholds, model choice and the Day 5 fallback are all decided on val (MH_05, TUM room5). Held-out runs only through `scripts/run_heldout.sh`, for reporting.

### D-007 · 9 Nov · Anti-overfitting protocol (refines D-006)
Training data is small (11 sequences, roughly 25 min) and val is only 2 sequences, so overfitting and selection noise are the main threats to the score. Rules:
1. **Separate generators.** Nets train on `research/augment.py`, a different degradation family from `research/degrade.py` (heavy-tailed noise, step and sinusoidal bias, varied escalation curves, severity 0.3–3). Nets never import `degrade.py`; a test enforces it. Otherwise training and measurement share one generating function and the numbers flatter us.
2. **Organizer script is a one-shot unseen evaluator first.** When it arrives, run the frozen pipeline on it once and log the result before any use in tuning or training.
3. **Model selection = grouped cross-validation inside train**, 5 folds, each leaving out a whole environment: MH_01–03, V1_01–02, V2_01+03, room1–2, room3–4. Never split windows of one sequence across train and test. Val confirms the CV choice; 2 sequences cannot pick among many candidates.
4. **Keep rule, fixed before results.** A layer stays only if, across CV folds and val: median per-sequence ATE or blind error improves by ≥10%, it wins ≥2/3 of paired sequence-seed comparisons, and no sequence worsens by >25%.
5. **Cross-sensor check.** Report train-EuRoC→test-TUM and the reverse. They use different IMUs and motion, and this is our best estimate of behaviour on data we have not seen.
6. **Capacity.** ≤100k params, weight decay, random rotation augmentation, early stopping on the fold's left-out group. Final retrain on train+val uses the epoch count fixed by CV. Held-out never enters weights. Uncertainty heads must show 60–75% 1-sigma coverage on left-out folds.
7. **Classical tuning counts too.** ESKF parameters are tuned on train, confirmed on val, and swept at severity 0.5/1/2/3; a narrow optimum is rejected.
8. **Held-out budget: 3 runs per pipeline** (Day 5, after the C++ port, final). `run_heldout.sh` requires a clean git tree and appends to `docs/HELDOUT_LOG.md`. Any change motivated by a held-out result marks that run contaminated in the log.
9. **Claims.** Organizers may reuse public sequences we trained on. Deck and README quote held-out numbers only and say so.

### D-008 · 9 Nov · C++ estimator has no external dependencies (refines D-002)
- `src/main.cpp` hand-writes the fixed-size matrix math instead of using Eigen, so `g++ main.cpp` builds anywhere and the bundle stays one file. Reads the input twice and streams output, so memory does not grow with sequence length.
- Why safe: `tests/test_cpp_parity.py` holds the port to the Python estimator within 1e-5 m.
- Fact check of D-002: measured Python RSS on room1 is 68 MB (scipy + numpy), far past the 8 MB budget. C++ measures 1.38 MB.
- Rejected: Eigen (a vendored dependency for a handful of operations).

### D-009 · 9 Nov · Velocity net works in a gravity-aligned frame with random yaw (TLIO-style)
- Input: 1 s of gyro and gravity-removed accel rotated into the world frame by the estimator's attitude, plus a validity mask. Output: world velocity and log-variance. Training rotates input and target together by a random yaw.
- Why: sensor mounting is unknown (`degrade.py` randomizes it, and the brief says gravity alignment is unknown), so body-frame features could break on data with a different mount. In this frame the mount cancels out, and heading drift does not change the prediction problem.
- Trade-off accepted: AirIO reports gains from body-frame features, and random yaw also discards any "drones fly forward" prior. Revisit only if organizers confirm a fixed mount; compare by grouped CV under D-007.
- Rejected: body-frame input with rotation augmentation (needs the net to learn invariance from about 25 min of data).

### D-010 · 9 Nov · Add a mount-independent tilt channel to the velocity net (amends D-009)
- Evidence: fold 0 of the D-009 net (train V1, V2, rooms; test Machine Hall) reached 0.44 m/s per axis against 0.49 for predicting zero, about 10% better after 15 of 40 epochs.
- Cause: gravity-removed world-frame specific force is nearly vertical in steady flight, so it hides body tilt. Tilt is what predicts drone velocity, which matches AirIO's body-frame finding that D-009 had set aside.
- Change: add 3 channels, the sensor's running-mean specific-force direction rotated to world. It estimates the body-up axis without knowing the mount, and stays causal.
- Test: compare fold 0 with and without it before running all folds.

### D-011 · 9 Nov · Result of the D-010 test: tilt channel is not the fix (no change to code)
- Fold 0 test RMSE 0.437 m/s with tilt vs 0.445 without, against 0.49 for zero. The hypothesis behind D-010 was mostly wrong. The channel stays because it costs nothing, but it earned no credit.
- Same model on clean input: 0.424 m/s. So sensor corruption is not the limit; the limit is how much velocity information a 1 s window holds, and generalization to an unseen environment (train 0.255, test 0.437).
- Fused into the ESKF on the unseen Machine Hall: mean ATE 4.30 to 3.73 m, never-moving 4.37 m. Blind gets worse (3.11 to 3.44 m).

### D-012 · 9 Nov · Blind 5 s: decaying coast pulled toward the last 20 s of flown positions (L5 classical candidate)
- Chosen on train (11 sequences, 3 seeds) from: hold, damped velocity at 3 time constants, pull toward all-flight, 20 s, 10 s and 5 s centroids. 20 s had the best balance: mean 2.72 to 2.16 m, median 1.85 to 1.52 m.
- Val confirmation: blind 5.67 to 4.71 m, 5 of 6 runs better. Never-moving reference is 4.56 m, so this nearly closes the gap and does not beat it.
- GRU forecaster (D-005) still to be built and must beat this on val.
- Why this is honest and not leakage: it uses only our own estimated positions before failure.

### D-013 · 9 Nov · Velocity-net input stays at 1 s
- Fold 0 final test RMSE: 1 s 0.437, 2.56 s 0.439, 3.84 s 0.435 m/s; train error fell to 0.212 at 3.84 s, so longer windows mostly widen the generalization gap. Criterion set before the test (clearly beat 0.437) is not met. 1 s also costs the least compute.
- Fused ATE at 2.56 s was 3.58 m vs 3.73 m at 1 s, within run-to-run spread on 6 runs. The 3.84 s fused numbers are not comparable: its best checkpoint came from epoch 6, before uncertainty training.
- Bug fixed: early stopping now ignores warmup epochs, whose uncertainty output is untrained and makes the filter nearly ignore the net.

### D-014 · 9 Nov · Velocity net as built does not ship: it failed the keep rule
- 5-fold CV, each net on its unseen environment: median ATE 1.75 to 2.60 m, 33% of runs better, worst sequence 165% worse. Waypoint, blind and dropout fail too. Thresholds were fixed in D-007 and are not being changed.
- Mean ATE improves on MH_01 (4.29 to 3.33), MH_02 (4.70 to 3.13), V1_02 (2.70 to 2.26), V2_01 (1.77 to 1.61). It worsens on all rooms (room1 1.11 to 3.12), MH_03 and V2_03 (1.97 to 3.13). The earlier fold 0 result overstated it.
- Likely causes, not yet tested: over-confident uncertainty (1-sigma coverage 0.46–0.73, three of five folds below the required 0.60), and the bounded velocity prior being switched off when the net is active.
- Current submission candidate: classical ESKF + D-012 blind forecast. The `-DPF_NET` code stays but is not the default.


### D-015 · 16 Nov · Submission is one pure-standard-library `src/main.py` (supersedes D-002, D-005 C++ clause, D-008)
- Organizer FAQ (16 Nov, `docs/Track3_FAQ_Responses.txt`): Python only, `main.cpp` not accepted; 8 MB is measured at algorithm/heap level, not process RSS.
- Measured: `import numpy` alone is 9.9 MB under `python -X tracemalloc` (bare interpreter 3.0 MB, pandas 39.5 MB). If imports are traced, numpy breaks the limit by itself, so the submission imports only `sys, os, math, array, zipfile`.
- Measured: pure-Python parse + quaternion integration + rotation + formatting costs 4 µs per row, 0.8 ms per IMU-second at 200 Hz (budget 20 ms).
- One estimator: the research harness runs `src/main.py` through the file interface, so there is no second implementation and no parity test. C++ moved to `legacy/cpp/`.
- Rejected: numpy in the submission (memory risk under one plausible measurement), keeping a numpy reference next to `main.py` (two implementations to keep equal).

### D-016 · 16 Nov · Official `degrade_imu.py` adopted; column order is detected, never assumed
- Vendored unchanged at `research/official/degrade_imu.py`, sha256 `cc7398db47efe8cefb581c13501f43687db2a5a13e7ed89697dc98afcd4b2f31`.
- Conflict: the script indexes columns 1–3 as accel; slide 15 and EuRoC put gyro there. Run on a raw EuRoC file ("order B"), gyro columns get the accel corruption and accel columns the gyro corruption. The script's unit auto-detect then depends on the sequence: median gyro norm inside 0.5–2 rad/s is read as "g" and the noise is divided by 9.81.
- `main.py` finds the accel triplet by gravity magnitude and estimates noise levels from the data. The harness scores both orders. Question sent to organizers.
- Facts read from the script: invalid rows are exact zeros on the last 5 s (only if the file is longer than 7 s); dropouts are missing rows (single ≤6%, bursts 5–50 rows); rows can be duplicated with the same timestamp; stuck runs repeat a row 2–10 times; spikes hit all six channels of one row; first 2 s are protected; seed is fixed at 42.

### D-017 · 16 Nov · Generator roles and scorer (extends D-007, relaxes nothing)
- Tuning uses only `official_degrade.dev_variant`: seeds ≠ 42, `max_level` 0.5–2, `gamma` 1–2.5, both column orders, bursts up to 400 rows (slide 13 says 2 s dropouts, the script says ≤50 rows). Train sequences only. Old `research/degrade.py` and `augment.py` stay as stress cases.
- The official config (seed 42, defaults) is report-only: val for confirmation, held-out for the quoted numbers. `run_official.py` refuses it on train.
- Primary metric: evo translation ATE RMSE after one SE(3) alignment over all poses (FAQ §4). Tier proxies `waypoint20`, `blind_full`, `dropout_full` use the same alignment; the flown-only-alignment versions stay because the organizers' tier method is unknown. Duplicated rows are scored once.
- evo raises on a constant or collinear estimate, so the output must span two dimensions.

### D-018 · 16 Nov · Learned nets retired
- D-014 already failed the keep rule. Now they also cannot ship: no torch or numpy (D-015), and an 84k-parameter conv net in pure Python is far above 20 ms per IMU-second. `research/nets/` stays for the record, unused. GRU forecaster (D-005) cancelled.

### D-019 · 16 Nov · Hypothesis: rotor-drag velocity measurement, behind gate G1
- Physics (Leishman, Macdonald, Beard, McLain 2014): a multirotor's accelerometer reads −k·v in the plane normal to thrust. That is a velocity measurement from the IMU alone, the thing D-011/D-014 could not learn from 1 s windows with random per-window bias.
- Gate G1, thresholds fixed before the first run (`research/eval/drag_gate.py`): on clean train data, median R² ≥ 0.3 on EuRoC train and k spread < 30% across sequences, at a 0.5 s averaging window. Fail → dropped, thresholds not revisited.
- If it passes it still has to pass the D-007 keep rule on dev variants, and must not hurt TUM-VI rooms (handheld, no rotors): innovation-based noise inflation has to switch it off there.
- Fallback that always ships: attitude + bounded-motion filter + RTS smoother + blind forecast.

### D-020 · 16 Nov · Budget gates
- Whole-process traced peak (`python -X tracemalloc`) ≤ 6 MB on a 3-minute and a 15-minute file; wall time including interpreter start ≤ 6 ms per IMU-second on the dev Mac, re-measured in Linux Docker. Tests enforce both. Two streaming passes over the file keep memory independent of length.

### D-021 · 16 Nov · Integrity line
- No sequence fingerprinting, no ground-truth lookup, no constant fitted to a named sequence. `main.py` is never told which dataset it reads. The evaluation file may be a public sequence with a fixed seed; that is not used.

### D-022 · 16 Nov · Gate G1 as written fails on its first sequence; gate redefined before the rest of the data arrived
- MH_02 (only EuRoC train sequence downloaded at the time), whole-sequence fit as D-019 specified: k = 0.15 /s, R² = 0.004. By the letter of D-019 the drag idea is dead.
- Diagnosis from 15 s segments of the same sequence: the first 40 s are the vehicle being shaken by hand (lateral specific-force std 0.4–1.9 m/s²), which swamps the fit. In rotor flight, lateral std is 0.05–0.20 m/s², k is 0.15–0.24 /s and R² is 0.2–0.8 (median about 0.5). The D-019 test measured the wrong thing: it asked for one linear law over a file that mixes handling and flight.
- This is a change of a pre-registered test after seeing data, so it is stated plainly rather than patched quietly. What keeps it honest: (1) the new test G1b is fixed now, while MH_01, MH_03 and all V1/V2 sequences are still not on disk; (2) MH_02 is excluded from the verdict; (3) only segments that pass an IMU-only flight test count (lateral specific-force rms < 0.25 m/s² over the segment), since the estimator must recognise flight without ground truth; (4) thresholds stay R² ≥ 0.3 and k spread < 30%; (5) the D-007 keep rule on dev variants still decides whether it ships.
- Caveat already visible: the drag signal is about 0.1 m/s² rms, the same size as the accel bias walk the official script reaches late in a file. Expect the gain to concentrate in the first two thirds of a flight.
- Also decided 16 Nov (user): no follow-up email to the organizers. Every open point is handled by detection or by testing both readings: column order (D-016), run command (file, folder or zip input, default output name), memory tool (traced from interpreter start, D-020), duplicated rows (one pose each), dropout length (dev variants span 50 to 400 rows), bundle trajectory (generated from a documented public sequence).

### D-023 · 16 Nov · Gate G1b passes; drag measurement goes into the estimator
- All seven EuRoC train sequences on disk. Six counted (MH_02 excluded, D-022): median segment R² 0.472 (need ≥ 0.3), drag coefficient mean 0.177 /s, spread across sequences 10% (need < 30%). Per sequence: MH_01 0.192 /s R² 0.56; MH_03 0.187, 0.82; V1_01 0.157, 0.36; V1_02 0.183, 0.64; V2_01 0.150, 0.22; V2_03 0.195, 0.53.
- TUM-VI rooms 1–4: 0 of 34 segments pass the flight test, so handheld data is not mistaken for rotor flight.
- Weak spots to carry into the design: slow sequences (V1_01, V2_01) have little velocity to explain, hence low R²; the fixed flight threshold rejects 6 of 8 segments of MH_03, so the filter must gate on innovation consistency instead of that threshold.
- Still to earn: the D-007 keep rule on dev variants, and no harm on TUM-VI rooms.
- Fact check closed: the slide 15 sample timestamp 1403636579758555392 is the first IMU row of MH_01_easy.

### D-024 · 16 Nov · Estimator core is a streaming attitude filter plus short-leak dead reckoning, not a 15-state filter; drag is not in the submission yet
- Bound test (`research/explore/drag_bound2.py`, clean train data, ground-truth attitude): velocity taken straight from drag, with accel bias solved by least squares, has horizontal error 0.43–0.82 m/s against 0.33–1.13 m/s for assuming zero velocity. ATE beats never-moving on 3 of 7 sequences and loses on 4. The segment R² of D-023 measures velocity changes after local centering; the absolute velocity is not recoverable at that quality. Drag alone is not a position sensor here.
- The old numpy ESKF cannot serve as a test bench for drag: on dev variants it has no defence against spikes and reaches 40 deg/s rotation error (V1_02), ATE 2.9 m against 1.78 m never-moving. Adding the drag update to it changed nothing measurable (`research/baselines/eskf_drag.py`, kept as a prototype).
- Shipped core instead (`src/main.py`): 3-sample median, gyro integration with a weak pull toward the specific-force direction, gyro bias seeded from the median rate of the first 1000 rows (trusted only below 0.2 rad/s), leaky double integration. Constants swept on 22 cached dev-variant runs of the 11 train sequences (`research/explore/tune.py`): velocity leak 0.3 s, position leak 1 s, tilt gain 0.2 /s, bias gain 0.001 /s². Neighbouring settings give 0.96–0.99, so the optimum is flat.
- Train dev variants: ATE / never-moving median 0.964 (drones 0.968, rooms 0.959), worst run 1.05; blind 0.75 of never-moving; rotation error 1.1 deg/s (was 2.2 before the bias seed).
- Honest reading: this is a controlled shrink toward never-moving that keeps the fast part of the motion. It does not track the slow path. Whether drag fused jointly with attitude can add to it is open and is the next experiment; it ships only through the keep rule.
- Rejected for now: 15-state node filter + RTS in pure Python (about 2 ms per node, and the bound test gives no evidence it would beat this core without a working velocity measurement).

### D-025 · 16 Nov · Drag filter ported into `src/main.py` as an explicit exception to the keep rule (user decision)
- Prototype `research/explore/drag_kf.py` on 22 train dev-variant runs, against the D-024 core: median ATE ratio 0.940, wins 95% of runs, worst run 1.01. Ablation: filter + smoother without drag 0.962 (drones 0.997, rooms 0.940); with drag, drones 0.934. So drag is worth about 6% on drones and the smoother about 5% on rooms.
- D-007 rule 4 asks for a median gain of at least 10%. This is 6%: the rule's first clause fails, the other two (≥2/3 wins, no sequence worse by >25%) pass. The user chose to ship it anyway on 16 Nov. Recorded as an exception, not as a pass; the threshold is not changed.
- Port: two streaming passes; pass 1 collects per-node sums (0.2 s nodes, at most 2000, widened on long files), then an 8-state horizontal filter (position, velocity, acceleration error, lateral accel bias) with a states-only backward pass, then pass 2 writes rows. Priors loosen only while more than half of recent drag measurements pass a chi-square gate, so handheld data keeps the leaky behaviour. Vertical stays bounded dead reckoning.
- Bugs found in the port: covariance lost positive definiteness from round-off (now symmetrised each node, updates skipped when the innovation covariance is not positive definite).
- Ported result, same 22 runs: ATE / never-moving median 0.921 (drones 0.910, rooms 0.933), worst 0.99; 1 s relative position error 0.63 of never-moving (was 0.98). Selection bias: constants were chosen on these runs.
- Blind window is not solved: about equal to never-moving on train; on val it is good on MH_05 and bad on room5. Blind selection by grouped CV is the next task. Current setting (pure decaying coast, 0.5 s) is provisional.
- Budgets after the port (MH_01, machine load average about 50): 6.4 MB traced from interpreter start, of which 3.0 MB is the bare interpreter and 2.7 MB is the transient cost of compiling the script; 3.7 ms per IMU-second. Own gates moved from 6 to 7 MB and 6 to 8 ms (D-020 amended); organizer limits are 8 MB and 20 ms.

### D-026 · 17 Nov · Blind 5 s: relax to the centre of the flown path; no forecast has skill beyond that
- Swept on the 22 train dev-variant runs: velocity decay 0.01 / 0.5 / 1.5 s crossed with pull toward the estimated path centre at 1 s / 3 s / never. Blind error as a ratio to never-moving (rms over runs): pull 1 s gives 1.00 (drones 1.00, rooms 0.97–1.01) at every decay; pull 3 s 1.03–1.05; no pull 1.10–1.17, and up to 1.83 on rooms.
- Chosen: decay 0.5 s, pull 1 s. It replaces the pure coast of D-025, which was 4x worse than never-moving on room5.
- Stated plainly for the deck: with IMU-only input our velocity at the moment of failure is too noisy to extrapolate 5 s; the honest best guess is the centre of where the vehicle has been, approached smoothly so the path has no jump. D-012 reached the same conclusion on the old simulator.
- Val, official config: ATE 3.51 m (never-moving 3.90), blind 2.39 m (never-moving 2.34), RPE 0.67 m.

### D-027 · 17 Nov · Tested and rejected: a drag gate that ignores the zero-velocity prior
- Suspicion: in Machine Hall the drag measurement is accepted on only 3–18% of nodes, perhaps because the tight zero-velocity prior makes fast real flight look inconsistent, so the gate should not inherit it.
- Test on the 22 train dev-variant runs: add a variance (0.25, 1, 4 (m/s)²) to the innovation covariance for the gate only, at gate 9 and 30. Best drone result 0.893 of never-moving against 0.908 now, a 1.5-point gain, while rooms go from 0.93 to 1.14–2.11 and the worst run to 1.5–2.5 as handheld data starts passing the gate. The one setting that hurts nothing (0.25 at gate 9) scores 0.913 overall against 0.918: inside the noise.
- Conclusion: acceptance is not what limits drone accuracy; the drag velocity itself is too noisy to integrate over a long path. Not adopted, code reverted. Constants stay as in D-025.
- Stopping rule: no further constant tuning on these 22 runs. The remaining ideas are within their noise, and more passes over the same runs only fit them.

### D-028 · 17 Nov · Audit, Docker check, repository clean-up
- Docker (`python:3.12-slim`, Linux aarch64): image builds, output byte-identical to macOS, 1.6 ms per IMU-second.
- Memory, corrected. Earlier entries quote "traced from interpreter start" (D-020, D-025). On Linux that reading is 8.0–8.3 MB, of which 5.8–6.1 MB is the interpreter's own start-up peak before our script exists; on macOS that start-up is 3.0 MB. It measures the platform, not the estimator. New yardstick, `scripts/heap_probe.py`, starts `tracemalloc` before compiling the script: 0.84 MB (Linux) / 1.12 MB (macOS) while estimating; 2.58 / 2.87 MB counting the one-off compilation. A 15-minute file reaches 2.07 MB while estimating (2000 node records, the cap). Test gates are now 3 MB and 4 MB (replacing the 7 MB whole-process gate, which could not pass on Linux for reasons outside our code). The `-X tracemalloc` totals stay in the README for anyone who measures that way.
- Considered and rejected: cutting the compilation transient by splitting `main.py` into two files or compiling part of it lazily. A second file breaks if only `main.py` is copied; lazy `exec` makes the source worse to read. The transient is under 3 MB.
- Audit fixes in `src/main.py`: (1) timestamp unit is taken from the epoch magnitude; the step-based rule read nanosecond files above 1 kHz as microseconds; (2) any exception or non-finite pose now falls back to a neutral one-pose-per-row trajectory instead of leaving no file; (3) the output folder is created if missing; (4) a one- or zero-row file defaults to nanoseconds. Output on the bundled sample is byte-identical before and after, so held-out run 1 still describes the shipped code.
- Removed (all recoverable at git tag `pre-cleanup`): `legacy/cpp/` (D-015), `research/nets/`, `research/augment.py`, `research/baselines/eskf_net.py`, `eskf_rts.py`, `eskf_drag.py`, `research/eval/run_cv.py` (D-018); `research/degrade.py` and `research/eval/run_split.py` (our old simulator, superseded by the organizers' script, D-016); `scripts/train_cv.sh`; `docs/PLAN.md`, `docs/WORKFLOW.md`, `docs/PROJECT_FLOW.md` (stale; the README carries the commands). `research/baselines/eskf.py` is restored to its 9 Nov content, so the frozen baseline row is reproducible exactly.
- Layout: `src/` submission, `submission/` zip, `presentation/` deck, `demo/` video script and figures, `docs/` records (DECISIONS, EXPERIMENTS and TASKS moved here), `research/` evaluation harness.
