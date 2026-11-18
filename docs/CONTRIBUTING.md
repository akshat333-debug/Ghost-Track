# Team workflow

Rules every teammate follows. Full brief: [hackathondetails.md](hackathondetails.md). Organizer FAQ: [Track3_FAQ_Responses.txt](Track3_FAQ_Responses.txt).

## Before work
1. `git pull --rebase` on `main`.
2. Read [TASKS.md](TASKS.md) and [DECISIONS.md](DECISIONS.md). Do not contradict a logged decision without a new entry.
3. Claim the task in TASKS.md, push the claim.

## Non-negotiables
- **Held-out split frozen** (D-003): `MH_04, V1_03, V2_02, room6`. Never tune, train or choose on it. Only `scripts/run_heldout.sh` touches it, 3-run budget.
- **Tune only on `dev_variant`** degradations of train sequences (D-017). The organizers' seed-42 config is report-only.
- **Never use ground truth** inside the estimator; no sequence fingerprinting (D-021).
- **Submission = `src/main.py`, standard library only** (D-015). Gates: 3 MB heap while estimating, 4 MB with compilation, 8 ms per IMU-second (D-028).
- **Exact output:** TUM, 8 columns, seconds, unit quaternion, one pose per input row. Run the validator.
- **Every published number** has a row in [EXPERIMENTS.md](EXPERIMENTS.md) with its commit.

## After work (same commit)
- Update TASKS.md with a handoff note; new decision in DECISIONS.md; new result in EXPERIMENTS.md.
- Change under `src/`: run `scripts/make_zip.sh`, `git add -f submission/*.zip`.
- Commit message `<area>: <what>`; push.

## Ownership
A estimator (`src/`) · B evaluation (`research/`, `scripts/`, `tests/`) · C docs, deck, video (`docs/`, `presentation/`, `demo/`).
