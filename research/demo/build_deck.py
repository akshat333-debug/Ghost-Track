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
    text(s[0], 0.55, 3.75, 7.6, 1.2, [("IMU-only 6-DoF trajectory under sensor degradation", {"size": 18, "bold": True}),
                                      ("Pure standard-library Python · about 1 MB of heap · under 2 ms per second of IMU", {"size": 13, "color": MUTED})])

    # 2 problem
    text(s[1], 0.4, 1.1, 4.3, 4.2, [
        ("One sensor, getting worse, then gone", {"size": 20, "bold": True, "after": 10}),
        "Only an IMU: gyroscope and accelerometer. No camera, no GPS, no waypoints.",
        "Jamming grows through the mission: noise, bias drift, stuck samples, spikes, missing and duplicated rows.",
        "Then every reading is zero for 5 seconds and the path must still be predicted.",
        "Double integration of a noisy accelerometer drifts by hundreds of metres within a minute.",
        ("Limits: 8 MB of memory, 20 ms of compute per second of data, one thread, Python only.", {"color": MUTED, "size": 12}),
    ], size=13)
    picture(s[1], "health_MH_05.png", 4.85, 1.05, 4.95)

    # 3 solution
    text(s[2], 0.4, 1.05, 9.2, 0.5, [("Estimate what the IMU can really tell us, and nothing it cannot", {"size": 20, "bold": True})])
    steps = [("1  Clean", "Dead, stuck, duplicated and missing rows are recognised from the data. A 3-sample median removes spikes with no threshold to tune."),
             ("2  Attitude", "Gyro integration, bias seeded from the first rows, gentle pull toward the measured gravity direction."),
             ("3  Drag velocity", "On a multirotor, sideways accelerometer reading is proportional to speed (rotor drag). A small filter fuses it and smooths backward in time."),
             ("4  Blind 5 s", "With no data the path relaxes smoothly to the centre of where the vehicle has been. Tested: coasting on the last velocity is worse.")]
    for i, (head, body) in enumerate(steps):
        x = 0.4 + i * 2.33
        card(s[2], x, 1.7, 2.2, 2.55)
        text(s[2], x + 0.12, 1.78, 1.96, 0.4, [head], size=14, color=BLUE, bold=True)
        text(s[2], x + 0.12, 2.2, 1.96, 2.0, [body], size=11.5)
    text(s[2], 0.4, 4.45, 9.2, 0.8, [
        ("Nothing about the file is assumed: column order, units, sample rate, gravity and start attitude are measured from the first rows.", {"size": 12, "color": MUTED})])

    # 4 architecture
    stages = [("Degraded\nIMU CSV", ORANGE), ("Probe\nlayout, units,\nrate, gravity", BLUE), ("Pass 1\nclean rows,\nattitude,\nnode sums", BLUE),
              ("Node filter\n+ backward\nsmoother\n(drag)", BLUE), ("Blind\nforecast", BLUE), ("Pass 2\nattitude again,\nwrite rows", BLUE), ("TUM\ntrajectory", ORANGE)]
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
        ("Why two streaming passes", {"size": 14, "bold": True, "color": BLUE}),
        "The file is never held in memory. Only one record per 0.2 s of flight is stored, capped at 2000, so memory does not grow with file length.",
        "Offline processing is allowed, so the smoother uses the future to correct the past."], size=12)
    text(s[3], 5.1, 3.2, 4.5, 2.1, [
        ("One file, no dependencies", {"size": 14, "bold": True, "color": BLUE}),
        "src/main.py imports only the Python standard library. Importing numpy alone costs 9.9 MB of traced heap, above the whole budget. Ours: 1.1 MB while estimating, 2.9 MB with script compilation.",
        "Filter state: position, velocity, acceleration error and accelerometer bias in the horizontal plane (8 numbers).",
        ("Tools and tech stack: Python 3 standard library (submission); numpy, scipy, pandas, evo, pytest, matplotlib (evaluation only); Docker; Git.", {"color": MUTED, "size": 11})], size=12)

    # 5 track final output
    set_text([sh for sh in s[4].shapes if sh.name == "Text 2"][0], "TRACK FINAL OUTPUT")
    text(s[4], 0.4, 1.05, 4.5, 1.6, [
        ("estimated_trajectory.txt, TUM format", {"size": 16, "bold": True}),
        "timestamp tx ty tz qx qy qz qw: seconds, metres, unit quaternion.",
        "Exactly one pose per input row, duplicated rows included; rows are never added.",
        "Run: python3 src/main.py <imu0/data.csv> estimated_trajectory.txt"], size=12)
    stat(s[4], 0.4, 2.85, 1.42, "2.67 m", "held-out ATE (never moving: 2.87 m)")
    stat(s[4], 1.94, 2.85, 1.42, "8 of 8", "held-out runs better than never moving")
    stat(s[4], 3.48, 2.85, 1.42, "1.1 MB", "heap while estimating (limit 8)")
    stat(s[4], 0.4, 4.12, 1.42, "1.5 ms", "per second of IMU (limit 20)")
    stat(s[4], 1.94, 4.12, 1.42, "0.59 m", "relative error over 1 s")
    stat(s[4], 3.48, 4.12, 1.42, "1.92 m", "blind 5 s (never moving: 2.13 m)")
    picture(s[4], "heldout_ate.png", 5.05, 1.1, 4.75)
    text(s[4], 5.05, 3.75, 4.75, 1.5, [
        ("Held-out: MH_04, V1_03, V2_02, room6. Never used for a design choice. Degraded with the organizers' script at its defaults and seed, both column orders. Error after SE(3) alignment, as the organizers score.", {"size": 11, "color": MUTED}),
        ("Limit: an IMU alone cannot hold position for minutes. Our gain over never moving is 7%; what is recovered is attitude and local motion.", {"size": 11, "color": INK})])

    # 6 differentiation
    points = [("Physics instead of a black box", "Rotor drag turns the accelerometer into a speed sensor. One coefficient, 0.177 per second, fitted on training flights and consistent to 10% across six of them."),
              ("Assumes nothing about the file", "The organizers' script and the slides disagree on column order. We detect it, and units, rate and gravity too. Tested in both orders."),
              ("Numbers that survive scrutiny", "Train / validation / held-out split frozen on day one. Tuned only on randomised variants of the organizers' degradation, reported on their exact config."),
              ("Always versus doing nothing", "A tracker that never moves is a strong baseline indoors. Each result is printed next to it, including where we do not beat it."),
              ("Built for the budget", "No numpy: 8-state filter and smoother hand-written in plain Python. Memory independent of file length."),
              ("Hard to break", "15 malformed-input cases under test, plus a forced crash: no header, CRLF, NaN tails, other units and rates, 15-minute files, a sensor that never moves.")]
    for i, (head, body) in enumerate(points):
        x, y = 0.4 + (i % 3) * 3.1, 1.1 + (i // 3) * 2.1
        card(s[5], x, y, 2.95, 1.95)
        text(s[5], x + 0.14, y + 0.1, 2.67, 0.4, [head], size=13.5, color=BLUE, bold=True)
        text(s[5], x + 0.14, y + 0.55, 2.67, 1.35, [body], size=11.5)

    # 7 demo and local setup
    card(s[6], 0.4, 1.1, 5.6, 2.15)
    text(s[6], 0.55, 1.18, 5.3, 2.0, [
        ("Run it (Python 3, nothing to install)", {"size": 14, "bold": True, "color": BLUE}),
        ("python3 src/main.py imu0/data.csv estimated_trajectory.txt", {"size": 12}),
        ("Or with Docker", {"size": 14, "bold": True, "color": BLUE}),
        ("docker build -t pathfinder .", {"size": 12}),
        ("docker run --rm -v \"$PWD/data:/data\" pathfinder /data/imu0/data.csv /data/estimated_trajectory.txt", {"size": 12})], size=12)
    card(s[6], 0.4, 3.4, 5.6, 1.9)
    text(s[6], 0.55, 3.48, 5.3, 1.75, [
        ("Reproduce every number", {"size": 14, "bold": True, "color": BLUE}),
        ("python3 scripts/download_euroc.py && bash scripts/download_tumvi.sh", {"size": 12}),
        ("python3 -m pytest tests -q", {"size": 12}),
        ("python3 -m research.eval.run_official --method src/main.py --split val --variant official", {"size": 12}),
        ("scripts/make_zip.sh", {"size": 12})], size=12)
    text(s[6], 6.25, 1.15, 3.4, 4.1, [
        ("Links", {"size": 14, "bold": True, "color": BLUE}),
        "Code: github.com/akshat333-debug/Ghost-Track",
        "Demo video: " + VIDEO_URL,
        ("In the repository", {"size": 14, "bold": True, "color": BLUE}),
        "README.md: results and limits",
        "docs/DECISIONS.md: every design decision with its evidence, including the ones that failed",
        "docs/EXPERIMENTS.md: every reported number with its commit",
        "submission/VITVellore_ZeroDrift.zip: the bundle"], size=12)

    # 8 brownie
    text(s[7], 0.4, 1.0, 9.2, 0.45, [("Sensor-health view and an honest look at the error", {"size": 18, "bold": True})])
    picture(s[7], "error_MH_05.png", 0.4, 1.5, 5.3)
    picture(s[7], "trajectory_MH_05.png", 5.85, 1.5, 3.95)
    text(s[7], 0.4, 4.2, 5.3, 1.2, [
        "Error over a degraded machine-hall flight, against the never-moving reference. The gain is steady, not dramatic.",
        ("The health timeline on the problem slide is computed from the degraded file alone: the same faults the front end has to repair.", {"color": MUTED})], size=12)
    text(s[7], 5.85, 4.35, 3.95, 1.0, [
        ("Top view: our estimate stays near the centre of a 20 m path. This is the limit of IMU-only tracking, shown rather than hidden.", {"size": 11.5, "color": MUTED})])

    out = ROOT / "presentation" / "VITVellore_ZeroDrift.pptx"
    prs.save(str(out))
    return out


if __name__ == "__main__":
    print(build())
