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

## How to run (fills in as scripts land)
| step | command | status |
|---|---|---|
| download data | `scripts/download_data.sh` | todo |
| degrade a sequence | `python research/degrade.py --seq MH_01 --seed 0` | todo |
| run estimator (py) | `python research/baselines/eskf.py <imu.csv> <out.txt>` | todo |
| score | `python research/eval/score.py <est.txt> <gt>` | todo |
| held-out report | `scripts/run_heldout.sh` | todo |
| budgets | `scripts/measure_budget.sh` | todo |
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
