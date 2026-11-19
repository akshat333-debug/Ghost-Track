# YouTube upload

File: `demo/ZeroDrift_demo.mp4` (2:56, 1080p). Captions: upload `demo/ZeroDrift_demo.srt` as English (India) subtitles; they are also burned into the video.
Uploaded 19 Nov: **https://youtu.be/jDXwcx7TNOk**

Visibility: **Unlisted** (anyone with the link can watch, judges included). After upload, put the link in `VIDEO_URL` in `research/demo/build_deck.py`, run `python3 -m research.demo.build_deck`, and replace the video row in `README.md`.

## Title

Zero Drift · Path Finder: 6-DoF trajectory from a jammed, dying IMU | Samsung PRISM XR Hackathon 2026, Track 3

## Description

Team Zero Drift (VIT Vellore): Akshat Agrawal, Hemang Dubey, Ishita Solanki.

Path Finder turns a degraded IMU recording into a full 6-DoF trajectory, one pose per input row, and keeps going for 5 seconds after the sensor dies. One Python file, standard library only.

- 8 of 8 held-out runs beat a never-moving tracker; 20 of 20 with other seeds and both column orders
- 14–45% lower error on handheld motion
- About 1 MB of memory and 1.5 ms per second of IMU (limits: 8 MB, 20 ms)

The terminal scene is a live run: the organizers' degradation script, our estimator, the format validator and the budget check.

Code, results and reproduction: https://github.com/akshat333-debug/Ghost-Track

Chapters
0:00 Zero Drift · Path Finder
0:15 The problem: jammed GPS, a dying IMU
0:35 Live run
1:09 How it works
1:42 Tracking after the sensor dies
1:57 The numbers
2:18 Results & Impact for Samsung XR
2:53 Thank you

Voice-over: Sarvam AI (bulbul, Indian English). Datasets: EuRoC MAV (ETH Zürich), TUM-VI (TU Munich).

## Tags

IMU, inertial navigation, trajectory estimation, 6DoF, sensor fusion, XR, Samsung PRISM, GPS-denied, Kalman filter, Python
