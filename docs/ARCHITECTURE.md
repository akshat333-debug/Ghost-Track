# Architecture

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

## Zero-effort reference
IMU alone has no absolute correction, so in a small room "never move" is a strong baseline. Every result is compared with `null_ate` / `null_blind` from `research/eval/score.py`. Pure classical IMU-only filtering may not beat it; a learned velocity measurement (L3) is what is expected to.

## Dropout handling
Propagate with motion prior through the gap; RTS smoother uses post-gap data to bend the gap trajectory back. Output still has one pose per input IMU timestamp (pending organizer answer on whether missing rows need poses).

## Budgets
Nets ≤ ~100k params, FP16/INT8 weights compiled into `weights.hpp` (≪1 MB). Net inference at 10–20 Hz windows. C++ target: < 4 MB RSS, < 5 ms per 1 s of IMU.
Measured so far (ESKF only, no nets, room1 on macOS): 1.38 MB peak RSS, 3.2 ms per 1 s of IMU.

## Open questions (see docs/ORGANIZER_QUESTIONS.md)
Memory measurement method; C++ allowed; test data source; checkpoint definition; blind-window timestamps; dropout representation; evo alignment mode.
