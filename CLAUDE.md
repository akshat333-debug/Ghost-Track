# Path Finder — agent rules (every team member's Claude reads this first)

Samsung PRISM XR Hackathon 2026, **Track 3: Trajectory Estimation Under Sensor Degradation**.
Goal: win (top-4 prize + PPO). Final submission **22 Nov 2026 23:59**, target **21 Nov evening**. Organizer FAQ of 16 Nov: `docs/Track3_FAQ_Responses.txt`.
Full rules/specs: `docs/hackathondetails.md`. Plan: `docs/PROJECT_FLOW.md`, `docs/ARCHITECTURE.md`.

## Before any work
1. `git pull --rebase` on `main`.
2. Read `TASKS.md` (Next up + latest handoff note), then `DECISIONS.md`. Do not redo or contradict a logged decision without adding a new decision entry.
3. Claim the task in `TASKS.md` (owner + `in progress`), commit + push that claim immediately so others don't pick it.

## While working
- Small branch per task (`a/eskf-bias`, `b/velnet-v1`, ...), merge to `main` same day. Never leave work unpushed overnight.
- **Held-out rule (non-negotiable):** test split = `MH_04, V1_03, V2_02, TUM room6` (frozen in DECISIONS.md D-003). Never tune, train, pick thresholds or choose models on them. Only `scripts/run_heldout.sh` touches them, only to report.
- **Anti-overfitting (D-007, read it before any tuning or training):** nets train on `augment.py`, never `degrade.py`; choose models by grouped CV; keep rule is fixed in advance; held-out has a 3-run budget.
- Never use ground truth of the evaluation input inside the estimator. If the organizers' test reuses public sequences, we still never exploit known GT.
- Every number that goes in the deck/README must have an `EXPERIMENTS.md` row with a commit hash.
- Submission is **Python only**: `src/main.py`, standard library only, no numpy (D-015). Budgets: ≤8 MB heap, ≤20 ms per 1 s of IMU, single thread, offline, no network. Our gates are 7 MB and 8 ms (D-020, D-025).
- Tune only on `dev_variant` degradations of train sequences; the official seed-42 config is report-only (D-017). Never assume column order (D-016). No sequence fingerprinting or ground-truth lookup (D-021).
- Output format is exact: `estimated_trajectory.txt`, 8 space-separated cols `timestamp tx ty tz qx qy qz qw`, seconds (ns × 1e-9), unit quaternion, one pose per input row (duplicated rows included, never append rows). Run the validator before claiming done.

## After every unit of work (same commit)
- Tick/update `TASKS.md` + append a **handoff note** (done / next / gotchas / how to run).
- New decision → `DECISIONS.md` entry. New result → `EXPERIMENTS.md` row.
- Flow or design changed → update `docs/PROJECT_FLOW.md` / `docs/ARCHITECTURE.md`.
- Commit message: `<area>: <what>` (e.g. `eskf: add accel bias state`). Push.

## Ownership (avoid merge conflicts)
- **A** — estimator (`src/main.py`, `research/baselines/`).
- **B** — learned nets (`research/nets/`, Colab/Kaggle notebooks).
- **C** — data, degradation, eval (`research/io_euroc.py`, `degrade.py`, `split.py`, `research/eval/`, `scripts/`), docs, video, deck.
Touch another owner's files only after a quick heads-up in the handoff note.
