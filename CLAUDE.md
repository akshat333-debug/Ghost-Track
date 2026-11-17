# Path Finder — agent rules (every team member's Claude reads this first)

Samsung PRISM XR Hackathon 2026, **Track 3: Trajectory Estimation Under Sensor Degradation**.
Goal: win (top-4 prize + PPO). Final submission **22 Nov 2026 23:59**, target **21 Nov evening**. Organizer FAQ of 16 Nov: `docs/Track3_FAQ_Responses.txt`.
Full rules/specs: `docs/hackathondetails.md`. Design: `docs/ARCHITECTURE.md`. Layout: `README.md`.

## Before any work
1. `git pull --rebase` on `main`.
2. Read `docs/TASKS.md` (Next up + latest handoff note), then `docs/DECISIONS.md`. Do not redo or contradict a logged decision without adding a new decision entry.
3. Claim the task in `docs/TASKS.md` (owner + `in progress`), commit + push that claim immediately so others don't pick it.

## While working
- Small branch per task (`a/eskf-bias`, `b/velnet-v1`, ...), merge to `main` same day. Never leave work unpushed overnight.
- **Held-out rule (non-negotiable):** test split = `MH_04, V1_03, V2_02, TUM room6` (frozen in DECISIONS.md D-003). Never tune, train, pick thresholds or choose models on them. Only `scripts/run_heldout.sh` touches them, only to report.
- **Anti-overfitting (D-007, D-017, D-027):** tune only on dev variants of train sequences; keep rule is fixed in advance; held-out has a 3-run budget (1 used); no more constant tuning on the 22 cached runs.
- Never use ground truth of the evaluation input inside the estimator. If the organizers' test reuses public sequences, we still never exploit known GT.
- Every number that goes in the deck/README must have a `docs/EXPERIMENTS.md` row with a commit hash.
- Submission is **Python only**: `src/main.py`, standard library only, no numpy (D-015). Budgets: ≤8 MB heap, ≤20 ms per 1 s of IMU, single thread, offline, no network. Our gates: 3 MB while estimating, 4 MB with script compilation, 8 ms (D-028).
- Tune only on `dev_variant` degradations of train sequences; the official seed-42 config is report-only (D-017). Never assume column order (D-016). No sequence fingerprinting or ground-truth lookup (D-021).
- Output format is exact: `estimated_trajectory.txt`, 8 space-separated cols `timestamp tx ty tz qx qy qz qw`, seconds (ns × 1e-9), unit quaternion, one pose per input row (duplicated rows included, never append rows). Run the validator before claiming done.

## After every unit of work (same commit)
- Tick/update `docs/TASKS.md` + append a **handoff note** (done / next / gotchas / how to run).
- New decision → `docs/DECISIONS.md` entry. New result → `docs/EXPERIMENTS.md` row.
- Design changed → update `docs/ARCHITECTURE.md`. Any change under `src/` → `scripts/make_zip.sh` and `git add -f submission/*.zip`.
- Commit message: `<area>: <what>` (e.g. `eskf: add accel bias state`). Push.

## Ownership (avoid merge conflicts)
- **A** — estimator (`src/main.py`).
- **B** — evaluation (`research/`, `scripts/`, `tests/`).
- **C** — docs, deck (`presentation/`), video and figures (`demo/`).
Touch another owner's files only after a quick heads-up in the handoff note.
