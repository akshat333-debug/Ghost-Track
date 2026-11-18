# Results in full

Every number here has a row in [EXPERIMENTS.md](EXPERIMENTS.md) with the commit that produced it.
Scoring is the organizers': evo ATE (RMSE) after SE(3) Umeyama alignment, on files degraded with their
`degrade_imu.py`. The reference everywhere is a tracker that **never moves** (it sits at the centre of the flown
path), which is a hard bar indoors: plain double integration misses it by kilometres.

## 1. Held-out: 8 of 8 runs beat never-moving

Four sequences frozen on day one and never used for any choice, organizers' defaults and seed (42), both column
orders the brief allows (A: accel-first as the script's docstring; B: raw EuRoC gyro-first).

| Sequence | Ours, order A / B (m) | Never moving (m) | Gain |
|---|---|---|---|
| MH_04, machine hall, drone | 6.63 / 6.65 | 6.81 | 3% |
| V1_03, Vicon room, drone | 1.47 / 1.47 | 1.58 | 7% |
| V2_02, Vicon room, drone | 1.70 / 1.73 | 2.12 | 19% |
| room6, handheld | 0.84 / 0.87 | 0.99 | 14% |
| **Mean of 8 runs** | **2.67** | **2.87** | **7%** |

Blind 5 s: 1.92 m against 2.13 m. Relative error over 1 s: 0.59 m. Relative rotation over 1 s: 2.2°.

## 2. Any seed: 20 of 20 validation runs beat never-moving

A judge may degrade with a different seed. Organizer defaults with seeds 1–5 (not 42), both column orders, on
the validation sequences (D-030, report only, nothing tuned):

| Sequence | Ours, mean of 10 runs (m) | Never moving (m) | Gain range across seeds |
|---|---|---|---|
| MH_05, machine hall, drone | 6.42 | 6.87 | 3–9% |
| room5, handheld | 0.67 | 0.93 | 17–45% |
| **All 20 runs** | **3.55** | **3.90** | **20 of 20 wins** |

Column order makes almost no difference (A 3.49 m, B 3.60 m). Blind 5 s ties never-moving on average
(2.37 m against 2.34 m; 13 of 20 runs better).

## 3. Efficiency (40 of the 100 points)

| 184 s flight | macOS arm64, Python 3.13 | Linux aarch64, Docker `python:3.12-slim` | Limit |
|---|---|---|---|
| Heap while estimating | 1.12 MB | 0.84 MB | 8 MB |
| Heap including one-off compilation of the script | 2.87 MB | 2.58 MB | 8 MB |
| Whole process, per second of IMU | 1.5 ms | 1.6 ms | 20 ms |

- A 15-minute file needs 2.07 MB: node records are capped at 2000, so memory does not grow with length.
- 1.5 ms per IMU-second means one second of data is processed about 650 times faster than real time.
- Heap is measured with `tracemalloc` started before the script is compiled ([`scripts/heap_probe.py`](../scripts/heap_probe.py)).
  From the interpreter's first instruction (`python -X tracemalloc`), Python's own start-up adds 3 MB on macOS and
  about 6 MB on the Linux image before any of our code runs; the FAQ puts the limit on the algorithm.
- Output is byte-identical on Python 3.9, 3.12, 3.13, 3.14 (macOS) and 3.12 (Linux Docker).

## 4. How the numbers were kept honest

- **Frozen split:** train 11 sequences, validation 2, held-out 4. Held-out is report-only, budget of three runs, one used.
- **Tuned on variants, reported on the real thing:** constants were chosen only on randomised variants of the
  organizers' degradation (other seeds, severities, dropout lengths, both orders) applied to training sequences.
- **Keep rule fixed in advance:** a component ships only with ≥10% median gain, two thirds of paired wins, and no
  sequence worse by more than 25%.
- **Failures logged:** a learned velocity network, a 15-state Kalman filter, a C++ port and a looser drag gate were
  built, measured and dropped ([DECISIONS.md](DECISIONS.md)).
- **No shortcuts:** the estimator never learns which sequence it reads and never sees ground truth.

## 5. Limits

- An IMU alone cannot hold an absolute position for minutes. Gains over never-moving are 3–19% on drones and
  14–45% handheld; what the method recovers best is attitude and local motion.
- The blind 5 s forecast relaxes toward the centre of the flown path; coasting on the last velocity was tested and
  was worse (D-026).
- The rotor-drag measurement gains 6% on drone flights, below our own 10% bar; it ships as a recorded exception (D-025).

## Reproduce

    python3 scripts/download_euroc.py && bash scripts/download_tumvi.sh
    python3 -m research.eval.run_official --method src/main.py --split val --variant official
    python3 -m research.eval.run_official --method src/main.py --split val --variant seeds --n 5
    scripts/run_heldout.sh                     # budgeted, clean tree only
    scripts/measure_budget.sh research/data/euroc/MH_01_easy/mav0/imu0/data.csv
