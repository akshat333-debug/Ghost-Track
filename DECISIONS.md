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

