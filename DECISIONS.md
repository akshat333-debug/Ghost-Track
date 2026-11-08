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

