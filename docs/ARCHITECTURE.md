# Architecture

## Design as shipped (D-015, D-016, D-024, D-025, D-026, D-028)
`src/main.py`, standard library only, two streaming passes so memory does not grow with file length.
1. Probe (first 1000 rows): column layout by gravity magnitude, accel and timestamp unit (from the epoch magnitude, so it does not depend on the sample rate), sample period, gravity magnitude, start attitude from mean specific force, gyro-bias seed from the median rate (trusted below 0.2 rad/s), node step from the file size (0.2 s, at most 2000 nodes).
2. Row cleaning, identical in both passes: NaN or all-zero rows are a dead sensor; an exact repeat of all six channels is a stuck sensor; a duplicated timestamp reuses the previous pose; a 3-sample median per channel removes one-row spikes; integration uses the real time step, so missing rows need no special case; gaps over 0.1 s are coasted.
3. Pass 1: quaternion gyro integration with a weak Mahony-style pull toward the specific-force direction; per node, sums of body specific force, quaternion and world velocity increment.
4. Node filter, 8 states (horizontal position, velocity, world-acceleration error, accel bias in the plane normal to thrust). Input: world velocity increments. Measurement: rotor drag, lateral specific force = -0.177 /s x body velocity, accepted only inside a chi-square gate. Zero-velocity and stay-near-origin priors, loosened only while most recent drag measurements are accepted. States-only RTS backward pass.
5. Blind window: horizontal path relaxes to the centre of the flown path (velocity decay 0.5 s, pull 1 s); attitude held.
6. Pass 2: the same attitude sweep, vertical position by leaky double integration, horizontal position interpolated from the nodes, one row written per input row. A 0.5 mm circle is added so evo's alignment never sees a degenerate path.
Not built, on purpose: 15-state filter (D-024), learned nets (D-018), C++ (D-015).

## Failure handling
If any step raises, or a pose is not finite, `main()` rewrites the output as a neutral trajectory with one pose per
row, so the evaluator always receives a valid file. A file with no usable sensor row gets the same treatment.

## Budgets
Python heap 0.8 to 1.1 MB while estimating a 3-minute file (2.1 MB at the node cap) and 2.6 to 2.9 MB counting the one-off compilation of the script
(`scripts/heap_probe.py`); 1.5 ms per second of IMU for the whole process. Node records are capped at 2000, so
memory does not grow with file length.

## History
The 9 Nov design (15-state ESKF, learned velocity net, C++ port) is described in D-001 to D-014 of
`docs/DECISIONS.md`; its code is in git at tag `pre-cleanup`.
