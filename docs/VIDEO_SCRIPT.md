# Walkthrough video script (target 2:30, hard limit 3:00)

Screen recording with voice-over. Times are cumulative. Numbers are the held-out run 1 row of `EXPERIMENTS.md`.

| Time | On screen | Say |
|---|---|---|
| 0:00–0:15 | Deck slide 1, then slide 2 | "Track 3, Path Finder, Team Zero Drift. We get one sensor, an IMU. It degrades through the mission, then dies, and we still have to output the path, including five blind seconds." |
| 0:15–0:35 | `docs/figures/health_MH_05.png` full screen | "This is what the organizers' script does to a real flight: missing rows, stuck samples, duplicated rows, rising noise, and at the end every value is zero." |
| 0:35–1:00 | Terminal: `python3 research/official/degrade_imu.py <clean> data/imu0/data.csv`, then `python3 src/main.py data/imu0/data.csv estimated_trajectory.txt`, then `head -3 estimated_trajectory.txt` | "One command. Python standard library only, nothing to install. One pose per input row in TUM format." |
| 1:00–1:35 | Deck slide 4 (architecture) | "Two streaming passes, so the file is never held in memory. First pass: clean the rows and integrate attitude. Then a small filter with a backward smoother. Its key measurement is physics: on a multirotor the sideways accelerometer reading is proportional to speed, because of rotor drag. Second pass writes the poses. After the sensor dies the path relaxes to the centre of where the vehicle has been." |
| 1:35–1:55 | Terminal: `scripts/measure_budget.sh ...` output | "Budgets: 6.5 megabytes of heap counting the interpreter itself, limit 8. Two to four milliseconds per second of data, limit 20." |
| 1:55–2:25 | Deck slide 5 (held-out bars), then `docs/figures/error_MH_05.png` | "On four held-out sequences that we never used for any choice, degraded with the organizers' own settings, our error is 2.67 metres against 2.87 for a tracker that never moves, better on all eight runs. That is a 7 percent gain. We say that plainly: an IMU alone cannot hold a position for minutes, and we compare every number with doing nothing." |
| 2:25–2:40 | Deck slide 6, then repo `DECISIONS.md` scrolling | "Every decision, including the ideas that failed, is logged with its evidence in the repository. Thank you." |

Recording checklist: terminal font at least 18 pt; run the commands live from a fresh clone; keep under 3:00; upload to YouTube or Drive and put the link on deck slide 7 and in the form.
