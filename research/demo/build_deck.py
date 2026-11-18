#!/usr/bin/env python3
"""Fills the organizers' deck template (presentation/template.pptx) -> presentation/VITVellore_ZeroDrift.pptx.

Numbers are the held-out run 1 and budget rows of EXPERIMENTS.md. Figures: python -m research.demo.figures --dark
python -m research.demo.build_deck
"""
from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.util import Inches, Pt

ROOT = Path(__file__).resolve().parent.parent.parent
MEMBERS = ["Akshat Agrawal (23MIC0079)", "Hemang Dubey (23MIC0069)", "Ishita Solanki (23MID0443)"]
VIDEO_URL = "[add link]"  # set before the final rebuild
FIG = ROOT / "demo" / "figures" / "dark"
INK, MUTED, BLUE, ORANGE, CARD = RGBColor(0xF0, 0xEF, 0xEC), RGBColor(0xA9, 0xB1, 0xC4), RGBColor(0x39, 0x87, 0xE5), \
    RGBColor(0xD9, 0x59, 0x26), RGBColor(0x14, 0x1B, 0x2E)


def text(slide, x, y, w, h, paras, size=14, color=INK, bold=False):
    """paras: strings or (string, {size, color, bold}) tuples, one paragraph each."""
    box = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = box.text_frame
    tf.word_wrap = True
    for i, para in enumerate(paras):
        s, o = para if isinstance(para, tuple) else (para, {})
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        r = p.add_run()
        r.text = s
        r.font.size = Pt(o.get("size", size))
        r.font.bold = o.get("bold", bold)
        r.font.color.rgb = o.get("color", color)
        r.font.name = "Calibri"
        p.space_after = Pt(o.get("after", 6))
    return box


def card(slide, x, y, w, h):
    s = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h))
    s.adjustments[0] = 0.06
    s.fill.solid()
    s.fill.fore_color.rgb = CARD
    s.line.fill.background()
    return s


def stat(slide, x, y, w, value, label, color=BLUE):
    card(slide, x, y, w, 1.15)
    text(slide, x + 0.12, y + 0.05, w - 0.24, 0.6, [value], size=20, color=color, bold=True)
    text(slide, x + 0.12, y + 0.52, w - 0.24, 0.6, [label], size=10.5, color=MUTED)


def picture(slide, name, x, y, w):
    slide.shapes.add_picture(str(FIG / name), Inches(x), Inches(y), width=Inches(w))


def set_text(shape, s):
    run = shape.text_frame.paragraphs[0].runs[0]
    run.text = s


def build():
    prs = Presentation(str(ROOT / "presentation" / "template.pptx"))
    s = list(prs.slides)

    # 1 title
    by = {sh.name: sh for sh in s[0].shapes}
    set_text(by["Text 7"], "Track 03 · Path Finder")
    set_text(by["Text 8"], "XR Hackathon")
    members = by["Text Box 22"].text_frame
    members.word_wrap = True
    members.paragraphs[0].runs[0].text = "Team members"
    members.paragraphs[0].runs[0].font.bold = True
    for name in MEMBERS:
        r = members.add_paragraph().add_run()
        r.text = name
        r.font.size = Pt(13)
        r.font.color.rgb = INK
        r.font.name = "Calibri"
    tf = by["Text 10"].text_frame
    tf.paragraphs[0].runs[0].text = "Team Zero Drift (VITVellore_ZeroDrift)"
    tf.paragraphs[1].runs[0].text = "Vellore Institute of Technology, Vellore"
    text(s[0], 0.55, 3.75, 7.6, 1.2, [("Jammed IMU in. Full 6-DoF out. Even after the sensor dies.", {"size": 20, "bold": True}),
                                      ("8/8 held-out wins · 1.1 MB heap · 1.5 ms per IMU-second · zero dependencies", {"size": 13, "color": BLUE})])

    # 2 problem
    text(s[1], 0.4, 1.1, 4.3, 4.2, [
        ("One sensor. Getting worse. Then gone.", {"size": 20, "bold": True, "after": 12}),
        "IMU only: no camera, no GPS.",
        "Jamming ramps up noise, bias, spikes, stuck and missing rows.",
        "Last 5 s: every reading is zero. Predict the path anyway.",
        ("Plain integration: kilometres off.", {"color": ORANGE, "bold": True}),
        ("8 MB · 20 ms per IMU-second · one thread · Python only", {"color": MUTED, "size": 12}),
    ], size=14)
    picture(s[1], "health_MH_05.png", 4.85, 1.05, 4.95)

    # 3 solution
    text(s[2], 0.4, 1.05, 9.2, 0.5, [("Extract everything the IMU knows. Invent nothing.", {"size": 20, "bold": True})])
    steps = [("1  Repair", "Dead, stuck, spiky and missing rows fixed from the data itself."),
             ("2  Attitude", "Gyro integration with a gentle pull to measured gravity."),
             ("3  Drag = speed", "Rotor drag turns the accelerometer into a velocity sensor. Filter + backward smoother."),
             ("4  Blind 5 s", "Smooth relax to the flown centre. Beats coasting.")]
    for i, (head, body) in enumerate(steps):
        x = 0.4 + i * 2.33
        card(s[2], x, 1.7, 2.2, 2.2)
        text(s[2], x + 0.12, 1.78, 1.96, 0.4, [head], size=15, color=BLUE, bold=True)
        text(s[2], x + 0.12, 2.25, 1.96, 1.6, [body], size=13)
    text(s[2], 0.4, 4.15, 9.2, 0.8, [
        ("Self-calibrating: column order, units, rate, gravity and start attitude are measured, never assumed.", {"size": 13, "color": MUTED})])

    # 4 architecture
    stages = [("Degraded\nIMU CSV", ORANGE), ("Probe\nlayout, units,\nrate, gravity", BLUE), ("Pass 1\nrepair,\nattitude,\nnode sums", BLUE),
              ("Node filter\n+ smoother\n(drag)", BLUE), ("Blind\nforecast", BLUE), ("Pass 2\nwrite every\nrow", BLUE), ("TUM\ntrajectory", ORANGE)]
    w, gap, y = 1.14, 0.2, 1.45
    for i, (label, col) in enumerate(stages):
        x = 0.4 + i * (w + gap)
        c = card(s[3], x, y, w, 1.5)
        c.line.color.rgb = col
        c.line.width = Pt(1.5)
        text(s[3], x + 0.04, y + 0.12, w - 0.08, 1.3, label.split("\n"), size=11, bold=False)
        if i < len(stages) - 1:
            a = s[3].shapes.add_shape(MSO_SHAPE.RIGHT_ARROW, Inches(x + w + 0.02), Inches(y + 0.63), Inches(gap - 0.04), Inches(0.24))
            a.fill.solid(); a.fill.fore_color.rgb = MUTED; a.line.fill.background()
    text(s[3], 0.4, 3.2, 4.5, 2.1, [
        ("Streaming, flat memory", {"size": 14, "bold": True, "color": BLUE}),
        "File never held in memory. One record per 0.2 s, capped at 2000: a 15-minute file still fits in 2.1 MB.",
        "Offline allowed, so the future corrects the past."], size=12.5)
    text(s[3], 5.1, 3.2, 4.5, 2.1, [
        ("One file, zero dependencies", {"size": 14, "bold": True, "color": BLUE}),
        "Standard library only. numpy's import alone (9.9 MB) would blow the whole budget.",
        "8-state filter and smoother hand-written in plain Python.",
        ("Evaluation stack: numpy, scipy, evo, pytest, matplotlib, Docker, GitHub Actions.", {"color": MUTED, "size": 11})], size=12.5)

    # 5 track final output
    set_text([sh for sh in s[4].shapes if sh.name == "Text 2"][0], "TRACK FINAL OUTPUT")
    text(s[4], 0.4, 1.05, 4.5, 1.6, [
        ("estimated_trajectory.txt · TUM", {"size": 16, "bold": True}),
        "timestamp tx ty tz qx qy qz qw, one pose per input row.",
        ("python3 src/main.py imu0/data.csv estimated_trajectory.txt", {"color": BLUE})], size=12)
    stat(s[4], 0.4, 2.55, 1.42, "8 / 8", "held-out runs beat never-moving")
    stat(s[4], 1.94, 2.55, 1.42, "20 / 20", "validation runs, seeds 1–5, both orders")
    stat(s[4], 3.48, 2.55, 1.42, "2.67 m", "held-out ATE (never-moving 2.87)")
    stat(s[4], 0.4, 3.82, 1.42, "1.1 MB", "heap · 7× under 8 MB", color=ORANGE)
    stat(s[4], 1.94, 3.82, 1.42, "1.5 ms", "per IMU-second · 13× under 20", color=ORANGE)
    stat(s[4], 3.48, 3.82, 1.42, "2.2°", "rotation drift per second")
    picture(s[4], "heldout_ate.png", 5.05, 1.1, 4.75)
    text(s[4], 5.05, 4.2, 4.75, 1.1, [
        ("Held-out MH_04, V1_03, V2_02, room6: frozen on day one, never used for a choice. Organizers' script, both column orders, SE(3)-aligned ATE.", {"size": 11, "color": MUTED})])

    # 6 differentiation
    points = [("Wins in both column orders", "Script and slides disagree on the layout. We detect it, and win either way."),
              ("Physics, not a black box", "Rotor drag = speed. One coefficient, consistent to 10% across flights."),
              ("Any seed, any file", "20/20 seeds, 15 malformed inputs, forced crash: always a valid trajectory."),
              ("Numbers that survive scrutiny", "Frozen held-out split. Tuned on variants, scored on the official config."),
              ("Built for the edge", "1.1 MB, 1.5 ms, one thread. Byte-identical on Python 3.9–3.14 and Docker."),
              ("Every claim traceable", "35 tests in CI. Each number tied to a commit. Each rejected idea logged.")]
    for i, (head, body) in enumerate(points):
        x, y = 0.4 + (i % 3) * 3.1, 1.1 + (i // 3) * 2.1
        card(s[5], x, y, 2.95, 1.95)
        text(s[5], x + 0.14, y + 0.12, 2.67, 0.5, [head], size=14.5, color=BLUE, bold=True)
        text(s[5], x + 0.14, y + 0.75, 2.67, 1.15, [body], size=12.5)

    # 7 demo and local setup
    card(s[6], 0.4, 1.1, 5.6, 2.15)
    text(s[6], 0.55, 1.18, 5.3, 2.0, [
        ("Run it: Python 3, nothing to install", {"size": 14, "bold": True, "color": BLUE}),
        ("python3 src/main.py imu0/data.csv estimated_trajectory.txt", {"size": 12}),
        ("Or Docker", {"size": 14, "bold": True, "color": BLUE}),
        ("docker build -t pathfinder .", {"size": 12}),
        ("docker run --rm -v \"$PWD/data:/data\" pathfinder /data/imu0/data.csv /data/estimated_trajectory.txt", {"size": 12})], size=12)
    card(s[6], 0.4, 3.4, 5.6, 1.9)
    text(s[6], 0.55, 3.48, 5.3, 1.75, [
        ("Reproduce every number", {"size": 14, "bold": True, "color": BLUE}),
        ("python3 -m pytest tests -q", {"size": 12}),
        ("python3 -m research.eval.run_official --method src/main.py --split val --variant official", {"size": 12}),
        ("Full list: docs/REPRODUCE.md", {"size": 12, "color": MUTED})], size=12)
    text(s[6], 6.25, 1.15, 3.4, 4.1, [
        ("Links", {"size": 14, "bold": True, "color": BLUE}),
        "Code: github.com/akshat333-debug/Ghost-Track",
        "Demo video: " + VIDEO_URL,
        ("Deep dives", {"size": 14, "bold": True, "color": BLUE}),
        "docs/RESULTS.md · docs/ARCHITECTURE.md · docs/DECISIONS.md"], size=12)

    # 8 brownie: where it ships
    set_text([sh for sh in s[7].shapes if sh.name == "Text 2"][0], "BROWNIE · WHERE IT SHIPS")
    uses = [("GPS-denied aircraft", "Pose through jamming, 5 s forecast after IMU loss."),
            ("XR headset failover", "Cameras blind in dark, occlusion, fast motion: IMU keeps 6-DoF alive."),
            ("Wearables, sensor hubs", "~1 MB, single thread: fits where models and numpy cannot.")]
    for i, (head, body) in enumerate(uses):
        y = 1.1 + i * 1.4
        card(s[7], 0.4, y, 4.6, 1.25)
        text(s[7], 0.55, y + 0.1, 4.3, 0.4, [head], size=15, color=BLUE, bold=True)
        text(s[7], 0.55, y + 0.55, 4.3, 0.7, [body], size=12.5)
    picture(s[7], "trajectory_room5.png", 5.25, 1.05, 4.5)
    text(s[7], 5.25, 4.75, 4.5, 0.6, [("Handheld (head-like) motion, validation: 17–45% better than never-moving across seeds.", {"size": 11, "color": MUTED})])

    out = ROOT / "presentation" / "VITVellore_ZeroDrift.pptx"
    prs.save(str(out))
    return out


if __name__ == "__main__":
    print(build())
