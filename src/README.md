# Path Finder submission (Team Zero Drift, VITVellore_ZeroDrift)

IMU-only 6-DoF trajectory estimation under sensor degradation. Python 3 standard library only: nothing to
install, single thread, no network, no files other than the input and the output.
Tested on Python 3.9, 3.12, 3.13, 3.14 and in Docker on Linux: the output file is byte-identical on all of them.

## Run

    python3 main.py <input> [output]

- `input`: the IMU CSV (`imu0/data.csv`), a folder that contains it, or a zip of that folder. With no
  argument the current folder is searched.
- `output`: a file or folder. Default `./estimated_trajectory.txt`.

Output is TUM format, space separated: `timestamp tx ty tz qx qy qz qw`, timestamp in seconds, unit quaternion.
Exactly one pose per input data row, in input order. Rows are never added; duplicated input rows get one pose each.

## What it does not assume

Measured from the first rows of the file instead: column order (gyro-first as in EuRoC, or accel-first as in
the organizers' script), accel unit (m/s² or g), timestamp unit (ns, µs, ms, s), sample rate, gravity magnitude,
start attitude. A header line is optional.

## How it works

1. Row cleaning: all-zero or NaN rows are a dead sensor, exact repeats are a stuck sensor, a 3-sample median
   removes one-row spikes, missing rows are covered by integrating over the real time step.
2. Pass 1: gyro integration with a weak pull toward the measured specific-force direction; sums per 0.2 s node.
3. Node filter with backward smoothing (horizontal position, velocity, acceleration error, lateral accel bias).
   It uses rotor drag as a velocity measurement: on a multirotor the accelerometer reading normal to the thrust
   axis is proportional to velocity. The measurement is gated statistically, so on data that is not rotor
   flight the filter falls back to bounded dead reckoning.
4. After the sensor dies: the path relaxes smoothly to the centre of the flown area; attitude is held.
5. Pass 2: the same attitude sweep again, writing every row. Memory does not grow with file length.

## Budgets (limits: 8 MB, 20 ms per second of IMU)

See `../metadata.json` for the numbers measured when this bundle was built: about 1 MB of Python heap while
estimating, under 3 MB counting the one-off compilation of this script, and about 2 ms per second of IMU.
If anything inside the estimator ever fails, a neutral trajectory with one pose per row is still written.
