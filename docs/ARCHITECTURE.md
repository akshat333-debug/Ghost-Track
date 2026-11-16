# Architecture

## Design as shipped (D-015, D-016, D-024, D-025, D-026). Sections below are the 9 Nov design, kept for history.
`src/main.py`, standard library only, two streaming passes so memory does not grow with file length.
1. Probe (first 1000 rows): column layout by gravity magnitude, accel and timestamp units, sample period, gravity magnitude, start attitude from mean specific force, gyro-bias seed from the median rate (trusted below 0.2 rad/s), node step from the file size (0.2 s, at most 2000 nodes).
2. Row cleaning, identical in both passes: NaN or all-zero rows are a dead sensor; an exact repeat of all six channels is a stuck sensor; a duplicated timestamp reuses the previous pose; a 3-sample median per channel removes one-row spikes; integration uses the real time step, so missing rows need no special case; gaps over 0.1 s are coasted.
3. Pass 1: quaternion gyro integration with a weak Mahony-style pull toward the specific-force direction; per node, sums of body specific force, quaternion and world velocity increment.
4. Node filter, 8 states (horizontal position, velocity, world-acceleration error, accel bias in the plane normal to thrust). Input: world velocity increments. Measurement: rotor drag, lateral specific force = -0.177 /s x body velocity, accepted only inside a chi-square gate. Zero-velocity and stay-near-origin priors, loosened only while most recent drag measurements are accepted. States-only RTS backward pass.
5. Blind window: horizontal path relaxes to the centre of the flown path (velocity decay 0.5 s, pull 1 s); attitude held.
6. Pass 2: the same attitude sweep, vertical position by leaky double integration, horizontal position interpolated from the nodes, one row written per input row. A 0.5 mm circle is added so evo's alignment never sees a degenerate path.
Not built, on purpose: 15-state filter (D-024), learned nets (D-018), C++ (D-015).

## Problem
Input: degraded IMU (200 Hz gyro + accel incl. gravity, EuRoC CSV, ns timestamps). Degradation escalates over time: noise ↑, bias drift ↑, ~2 s dropouts, unknown gravity alignment, then total IMU failure → predict 5 s blind.
Output: 6-DoF pose per IMU frame (TUM format). Budget: ≤8 MB RAM, ≤20 ms per 1 s of IMU, 1 thread, offline.

## Layers (each kept only if it beats the previous one on val; D-006)
| layer | what | owner |
|---|---|---|
| L0 | naive strapdown, gravity from first ~1 s mean accel | A |
| L1 | error-state Kalman filter (ESKF), state `p, v, q, b_g, b_a`; adaptive process noise for escalating jamming; zero-velocity/hover pseudo-measurements | A |
| L2 | learned IMU correction (AirIMU-style): small 1D CNN/TCN → gyro/accel residual + uncertainty | B |
| L3 | learned velocity from ~1 s of gravity-aligned IMU with random-yaw training (D-009) → ESKF velocity measurement with learned covariance | B |
| L4 | offline forward ESKF + backward RTS smoother (legal: processing is offline) | A |
| L5 | blind-5 s forecaster: const-velocity / damped const-accel / small GRU on last 2–3 s of states; chosen on val | C/B |

## Status (9 Nov)
L0 and L1 implemented; L4 smoother in Python only; classical L5 in Python and C++. L3 is implemented but failed the keep rule (D-014) and is off by default. L2 and the GRU forecaster are not built.

## Zero-effort reference
IMU alone has no absolute correction, so in a small room "never move" is a strong baseline. Every result is compared with `null_ate` / `null_blind` from `research/eval/score.py`. Pure classical IMU-only filtering may not beat it; a learned velocity measurement (L3) is what is expected to.

## Dropout handling
Propagate with motion prior through the gap; RTS smoother uses post-gap data to bend the gap trajectory back. Output still has one pose per input IMU timestamp (pending organizer answer on whether missing rows need poses).

## Budgets
Nets ≤ ~100k params, FP16/INT8 weights compiled into `weights.hpp` (≪1 MB). Net inference at 10–20 Hz windows. C++ target: < 4 MB RSS, < 5 ms per 1 s of IMU.
Measured so far (ESKF only, no nets, room1 on macOS): 1.38 MB peak RSS, 3.2 ms per 1 s of IMU.
With the velocity net (float32, 10 Hz, room1 on macOS while training ran on the same machine): 1.77 MB peak RSS, 8.8 ms per 1 s of IMU.

## Open questions (see docs/ORGANIZER_QUESTIONS.md)
Memory measurement method; C++ allowed; test data source; checkpoint definition; blind-window timestamps; dropout representation; evo alignment mode.
