# Project flow (end to end)

```
EuRoC / TUM-VI (IMU + GT)
        │  scripts/download_data.sh
        ▼
research/io_euroc.py ──► research/degrade.py (noise ↑, bias drift ↑, 2 s dropouts, unknown gravity, IMU death + 5 s blind)
        │                         │
        │                         ▼
        │                 degraded imu0/data.csv  (same format as organizer input)
        ▼                         │
training (research/nets, Colab)   ▼
  L2 IMU correction net ──► estimator (research/baselines/eskf.py → src/main.cpp)
  L3 velocity net       ──►   L1 ESKF + L2/L3 fusion + L4 RTS smoother + L5 blind forecaster
  L5 forecaster         ──►           │
                                      ▼
                         estimated_trajectory.txt (TUM, one pose per IMU frame)
                                      │
                                      ▼
            research/eval/validate_format.py + score.py (evo ATE/RPE, proxy 100-pt, RAM, ms)
                                      │
                                      ▼
                         EXPERIMENTS.md → deck / video / README
```

## Since 16 Nov (D-015 to D-017)
The estimator is `src/main.py` (pure standard library). Degradation for scoring is the organizers' script through
`research/official_degrade.py`; `research/degrade.py` is a stress case only.

| step | command | status |
|---|---|---|
| score on tuning variants | `python3 -m research.eval.run_official --method src/main.py --split train --variant dev --n 4` | runner done, `main.py` todo |
| report on official config | `python3 -m research.eval.run_official --method src/main.py --split val --variant official` | runner done |
| gate G1 | `python3 -m research.eval.drag_gate` | done |
| run the submission | `python3 src/main.py <imu0/data.csv> estimated_trajectory.txt` | todo |

## How to run (before 16 Nov; C++ rows are historical, code in `legacy/cpp/`)
| step | command | status |
|---|---|---|
| download data | `python3 scripts/download_euroc.py` and `scripts/download_tumvi.sh` (CSV only, about 30 min, resumes) | done |
| degrade a sequence | `python3 -m research.degrade --seq MH_01 --seed 0` | done |
| run estimator (py) | `python research/baselines/eskf.py <imu.csv> <out.txt>` | todo |
| evaluate a method | `python3 -m research.eval.run_split --method research.baselines.naive --split val` | done |
| self-checks | `python3 -m pytest tests -q` | done |
| validate a file | `python3 research/eval/validate_format.py <est.txt> <imu.csv>` | done |
| held-out report | `scripts/run_heldout.sh <method module>` | done |
| train velocity net (one CV fold, 0–4) | `python3 -m research.nets.train_vel --fold 0 --out vel0.pt` | done |
| budgets | `scripts/measure_budget.sh <imu.csv>` | done |
| run C++ | `g++ -O2 -std=c++17 -o pathfinder src/main.cpp && ./pathfinder <imu.csv> <out.txt>` | done |
| export weights and build with net | `python3 -m research.nets.export_weights vel.pt src/weights.hpp && g++ -O2 -std=c++17 -DPF_NET -Isrc -o pathfinder src/main.cpp` | done |
| build submission | `scripts/make_zip.sh` | todo |

## Submission bundle (slide 17, exact)
```
team_name.zip
├── estimated_trajectory.txt
├── metadata.json        # optional: runtime perf, compute specs
└── src/
    ├── main.py / main.cpp
    └── README.md
```
Plus: GitHub repo link, ≤3 min demo video, deck `CollegeName_TeamName` (PPT/PDF), Docker files per general rules.
