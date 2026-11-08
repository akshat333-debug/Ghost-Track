# Organizer questions — Track 3

Send to prism@samsung.com. Log answers below with date.

---
**Subject:** XR Hackathon 2026 – Track 3 (Path Finder) clarification questions – VITVellore_ZeroDrift

Hello PRISM team,

We are registered for Track 3 (Path Finder: Trajectory Estimation Under Sensor Degradation) and have a few clarifications so our submission matches your evaluation pipeline exactly:

1. **Memory budget (≤8 MB peak RAM):** how is it measured — peak process RSS (e.g. `/usr/bin/time`) or Python heap only (e.g. `tracemalloc`)? Does the interpreter/runtime count?
2. **Language:** the bundle lists `main.py / main.cpp`. Is a C++ submission accepted? Which compiler/OS/Docker image do you use to build and run it?
3. **Runtime budget (≤20 ms per 1 s of IMU):** measured on which CPU? Does it include file I/O and process start-up?
4. **Test data:** will evaluation sequences be held-out/unseen, or degraded versions of public EuRoC MAV / TUM-VI sequences? When will the degradation script be shared?
5. **Mission checkpoints / waypoints:** are checkpoint timestamps or positions given as input? How is the 30-pt waypoint score computed?
6. **Blind 5 s after IMU failure:** will the input contain rows (timestamps) for those 5 s, or should we generate poses at the IMU rate for 5 s after the last sample?
7. **Dropouts:** are dropped frames missing rows or rows with NaN/zero values? Should the output include poses for the missing timestamps?
8. **evo settings:** which alignment is used for ATE/RPE (none, SE(3), Sim(3), origin-only), and what RPE delta?
9. **Initial state:** is the initial pose/velocity given or should we assume identity at rest?
10. **Demo video length:** general rules say max 3 min, the timeline says 5 min, Track 3 says 2–3 min. Which applies?

Thank you,
Team Zero Drift (VITVellore_ZeroDrift), Vellore Institute of Technology, Vellore

---
## Answers received
| date | Q# | answer |
|---|---|---|
