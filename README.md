# Path Finder — IMU-only 6-DoF trajectory under sensor degradation

Samsung PRISM XR Hackathon 2026, Track 3.

Start here:
- Rules & specs: `docs/hackathondetails.md`
- Agent/team rules: `CLAUDE.md`, `docs/WORKFLOW.md`
- Pipeline: `docs/PROJECT_FLOW.md` · Design: `docs/ARCHITECTURE.md`
- Live status: `TASKS.md` · Decisions: `DECISIONS.md` · Results: `EXPERIMENTS.md`

Status 16 Nov: organizer FAQ applied (Python-only, official degradation script). Submission entry point will be `src/main.py`, standard library only. Research harness needs `numpy scipy pandas evo pytest`.

    python3 scripts/download_euroc.py && bash scripts/download_tumvi.sh
    python3 -m pytest tests -q
    python3 -m research.eval.drag_gate
