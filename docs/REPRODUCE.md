# Reproduce everything

Needs Python 3 and `pip install -r requirements.txt` (the submission itself needs nothing).

| Step | Command |
|---|---|
| Data (IMU and ground-truth CSVs only) | `python3 scripts/download_euroc.py && bash scripts/download_tumvi.sh` |
| Tests (35) | `python3 -m pytest tests -q` |
| Validation, organizer config | `python3 -m research.eval.run_official --method src/main.py --split val --variant official` |
| Validation, seeds 1–5 | `python3 -m research.eval.run_official --method src/main.py --split val --variant seeds --n 5` |
| Held-out report (budgeted, clean tree) | `scripts/run_heldout.sh` |
| Memory and runtime budgets | `scripts/measure_budget.sh research/data/euroc/MH_01_easy/mav0/imu0/data.csv` |
| Submission zip | `scripts/make_zip.sh` |
| Figures, hero animation, deck | `python3 -m research.demo.figures && python3 -m research.demo.figures --dark && python3 -m research.demo.hero && python3 -m research.demo.build_deck` |

## Repository layout

| Path | What it is |
|---|---|
| `src/` | The submission: `main.py` and its README |
| `submission/` | Bundle zip in the slide-17 layout |
| `presentation/` | Deck and the organizers' template |
| `demo/` | Video script, figures, hero animation |
| `research/official/` | Organizers' `degrade_imu.py`, unchanged |
| `research/eval/` | evo scorer, format validator, runner, rotor-drag gate |
| `research/explore/` | Tuning sweeps and prototypes behind each decision |
| `research/baselines/` | Plain integration and our first filter, as reference points |
| `research/demo/` | Figure, animation and deck builders |
| `scripts/` | Downloads, budgets, held-out report, zip |
| `tests/` | Format, malformed inputs, crash fallback, memory and runtime gates |
| `docs/` | Results, architecture, decisions, experiments, rules, FAQ, task log |

Earlier code (C++ port, learned velocity network, first simulator) is preserved at git tag `pre-cleanup`.
