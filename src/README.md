# Path Finder submission (Team Zero Drift)

IMU-only 6-DoF trajectory estimation. No dependencies beyond a C++17 compiler; single thread, no network.

Build and run:

    g++ -O2 -std=c++17 -o pathfinder main.cpp
    ./pathfinder <imu0/data.csv> estimated_trajectory.txt

Output is TUM format: `timestamp tx ty tz qx qy qz qw`, one pose per input IMU row.
Rows with missing or non-numeric values are treated as dropped frames and still get a pose.
