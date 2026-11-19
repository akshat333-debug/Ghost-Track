# Walkthrough video

**[ZeroDrift_demo.mp4](ZeroDrift_demo.mp4)** · 2:56 · 1080p · captions burned in, also as [ZeroDrift_demo.srt](ZeroDrift_demo.srt).

Built by `research/demo/video.py`: every frame is rendered from real data, and the terminal scene runs the
organizers' `degrade_imu.py`, `src/main.py`, the format validator and `scripts/measure_budget.sh` for real on
room5 (validation), showing their actual output. Spoken numbers are taken from that same run.
Voice-over: Sarvam AI `bulbul:v4-flash`, Indian English (`sunny_en_social`), one request per caption line so
captions and annotations are timed from the real audio.

| # | Scene | What is shown |
|---|---|---|
| 1 | Title | Tagline, team |
| 2 | The problem | room5 signal through the organizers' script; plain integration ends ~2 km away |
| 3 | Live run | degrade, estimate, rows in = poses out, validator OK, heap and runtime vs budget |
| 4 | How it works | Probe, repair, attitude, rotor-drag speed sensor, smoother, blind forecast |
| 5 | Sensor dies | Trajectory drawn over ground truth, through the 5 s blind window; ATE vs never-moving |
| 6 | The numbers | Held-out 8/8, any seed 20/20, 7× under memory, 13× under compute, 0 dependencies |
| 7 | Results & Impact for Samsung XR | 14–45% lower error on handheld motion, 5 s tracked after the IMU dies, live compute; camera-loss failover for XR headsets, near-zero cost, same file for GPS-denied drones |
| 8 | Close | Title, tagline, team |

Rebuild (clips are cached in `build/video/`, so only changed lines are re-voiced):

    SARVAM_API_KEY=... python3 -m research.demo.video            # --voice, --pace, --preview <seconds...>

Render on an idle machine: the budget scene measures live, so a busy CPU shows a slower runtime.
Upload the mp4 to YouTube or Drive and put the link in `research/demo/build_deck.py` (`VIDEO_URL`) and the form.
