# AI disclosure

Path Finder was designed and built by Team Zero Drift: Akshat Agrawal, Hemang Dubey and Ishita Solanki. We chose the track, the approach and every major design decision: a pure-standard-library estimator in two streaming passes, measuring column order and units from the data instead of assuming them, using rotor drag as a speed sensor, a backward smoother, relaxing the blind 5 s toward the flown centre, and freezing a held-out split on day one with a keep rule fixed in advance. We reviewed every output and own everything submitted.

Along the way we used AI tools as assistants, as most engineering teams now do:

| Tool | How it assisted us |
|---|---|
| Claude Code (Anthropic) | Coding assistant: helped draft and debug scripts, tests and documentation, and helped with literature and dataset search. |
| Sarvam AI Bulbul (text-to-speech) | Read our demo script aloud in Indian English for the demo video voice-over. |
| Sarvam AI Saarika (speech-to-text) | Checked that every voice-over line is pronounced correctly. |

## What is not AI-generated

- **No trained model is part of the estimator.** `src/main.py` is explicit code: a filter, a smoother and physics (rotor drag, gravity), standard library only. A learned velocity network was built, failed our keep rule and was dropped ([DECISIONS.md](docs/DECISIONS.md), D-014, D-018).
- **No image or video frame comes from a generative model.** Every figure, the hero animation and every video frame are drawn by our matplotlib scripts from real data (`research/demo/`). The terminal scene in the video is a live run.
- **Every number we report is printed by a script in this repo** and has a row in [EXPERIMENTS.md](docs/EXPERIMENTS.md) with its commit, so anyone can check it.
