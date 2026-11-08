# Tasks

Status: `todo` / `in progress (owner)` / `done (commit)`. Owners: A estimator+C++, B nets, C data/eval/docs.

## Next up
- [ ] Day 0 — Send `docs/ORGANIZER_QUESTIONS.md` email to prism@samsung.com (C)
- [ ] Day 0 — Download EuRoC + TUM-VI CSVs: `scripts/download_euroc.py`, `scripts/download_tumvi.sh`; each teammate runs once (in progress)
- [ ] Day 0 — Read AirIMU, AirIO, TLIO, RoNIN; summary in `docs/LITERATURE.md` (B)

## Day 1 (9 Nov)
- [x] `research/io_euroc.py` loader (IMU csv + GT) + TUM writer (A)
- [x] L0 naive strapdown baseline `research/baselines/naive.py` (A)
- [ ] Training window sampler + dataset class (B)
- [ ] `research/augment.py`: training degradation family, distinct from `degrade.py` (B, D-007)
- [ ] Grouped 5-fold CV harness (B, D-007)
- [x] `research/degrade.py` degradation simulator (C)
- [x] `research/eval/score.py` (evo ATE/RPE + proxy 100-pt) + `validate_format.py` (C)

## Day 2–4
- [ ] L1 ESKF: p,v,q,bg,ba; gravity init; adaptive Q (A)
- [ ] Dropout handling + RTS smoother (A)
- [ ] L2 IMU correction net v1 (B)
- [ ] L3 body-frame velocity net v1 + covariance head (B)
- [ ] Fuse L3 into ESKF (A)
- [x] `scripts/run_heldout.sh`
- [ ] `scripts/measure_budget.sh` (C)
- [ ] L5 blind-5 s forecaster: constant velocity, damped acceleration, GRU; compare on val (C/B)

## Day 5 checkpoint (13 Nov)
- [ ] Freeze best Python pipeline by val results (D-006). Fallback rule: if L2/L3 don't beat L1, ship L1+L4+L5.

## Day 6–9
- [ ] C++ port ESKF + smoother (A)
- [ ] Weight export + C++ net forward + parity test ≤1e-5 (B)
- [ ] Dockerfile, README, fresh-clone repro (C)
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
