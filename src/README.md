# Path Finder submission (Team Zero Drift)

IMU-only 6-DoF trajectory estimation. Python 3 standard library only: no packages to install, single thread, no network.

Run:

    python3 main.py <imu0/data.csv> estimated_trajectory.txt

(`main.py` lands on 17 Nov; see `TASKS.md`.)

Output is TUM format: `timestamp tx ty tz qx qy qz qw`, one pose per input IMU row.
Rows with missing or non-numeric values are treated as dropped frames and still get a pose.
