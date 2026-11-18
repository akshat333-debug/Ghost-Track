# Tasks

Status: `todo` / `in progress (owner)` / `done (commit)`. Owners: A estimator, B evaluation, C docs, deck, video (see CLAUDE.md).

## Status (18 Nov)
- [x] `src/main.py`: pure standard library, two streaming passes, rotor-drag node filter, blind forecast (D-024 to D-026)
- [x] Held-out run 1 of 3: 8 of 8 runs beat never-moving, ATE 2.67 m vs 2.87 m
- [x] Budgets: 0.84–1.12 MB heap while estimating, 1.5 ms per IMU-second; Docker verified (D-028)
- [x] Final audit: timestamp unit made rate-driven, team added, README rewritten, CI added (D-029)
- [x] Submission zip, deck with team members, figures, video script
- [ ] Record the 2–3 min video; set `VIDEO_URL` in `research/demo/build_deck.py`, rebuild the deck
- [ ] Make the repository public
- [ ] Submit the Google Form (deadline 22 Nov 23:59)

Older items and handoff notes below are history: files they mention may only exist at git tag `pre-cleanup`.

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
