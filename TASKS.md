# Tasks

Status: `todo` / `in progress (owner)` / `done (commit)`. Owners: A estimator+C++, B nets, C data/eval/docs.

## Next up
- [ ] Day 0 — Register team on Google Form before 8 Nov 23:59 (any member)
- [ ] Day 0 — Send `docs/ORGANIZER_QUESTIONS.md` email to prism@samsung.com (C)
- [ ] Day 0 — Create private GitHub repo, add all 3 members, push `main` (A)
- [ ] Day 0 — Download EuRoC (IMU + GT) + TUM-VI room1–6 via `scripts/download_data.sh` (C)
- [ ] Day 0 — Read AirIMU, AirIO, TLIO, RoNIN; summary in `docs/LITERATURE.md` (B)

## Day 1 (9 Nov)
- [ ] `research/io_euroc.py` loader (IMU csv + GT) + TUM writer (A)
- [ ] L0 naive strapdown baseline `research/baselines/naive.py` (A)
- [ ] Training window sampler + dataset class (B)
- [ ] `research/degrade.py` degradation simulator (C)
- [ ] `research/eval/score.py` (evo ATE/RPE + proxy 100-pt) + `validate_format.py` (C)

## Day 2–4
- [ ] L1 ESKF: p,v,q,bg,ba; gravity init; adaptive Q (A)
- [ ] Dropout handling + RTS smoother (A)
- [ ] L2 IMU correction net v1 (B)
- [ ] L3 body-frame velocity net v1 + covariance head (B)
- [ ] Fuse L3 into ESKF (A)
- [ ] `scripts/run_heldout.sh`, `scripts/measure_budget.sh` (C)
- [ ] L5 blind-5 s forecaster candidates (C)

## Day 5 checkpoint (13 Nov)
- [ ] Freeze best Python pipeline by held-out results. Fallback rule: if L2/L3 don't beat L1, ship L1+L4+L5.

## Day 6–9
- [ ] C++ port ESKF + smoother (A)
- [ ] Weight export + C++ net forward + parity test ≤1e-5 (B)
- [ ] Dockerfile, README, fresh-clone repro (C)
- [ ] Deck (`CollegeName_TeamName`), architecture diagram (C)
- [ ] Walkthrough video ≤3 min (C)
- [ ] Feature freeze 17 Nov; `scripts/make_zip.sh`; dry-run validation (all)

## Day 10 (18 Nov)
- [ ] Submit by 18:00 via Google Form. Keep backup L1 zip.

## Done
- [x] Repo scaffold + team docs (local commit, 8 Nov)

---
## Handoff notes (newest on top)
### 8 Nov — scaffold
- Done: git repo, folder layout, CLAUDE.md, TASKS/DECISIONS/EXPERIMENTS, docs (flow, architecture, workflow, organizer questions).
- Next: GitHub remote + push; register; send organizer email; data download.
- Gotchas: Python RSS likely > 8 MB → final submission planned in C++ (D-002). Waiting on organizer answers for memory measurement, test data, blind-window timestamps.
