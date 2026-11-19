#!/usr/bin/env python3
"""Walkthrough video: real run of src/main.py, Sarvam AI voice-over (Indian English), burned-in captions.

SARVAM_API_KEY=... python -m research.demo.video [--voice sunny_en_social] [--pace 1.05]
writes demo/ZeroDrift_demo.mp4 and demo/ZeroDrift_demo.srt. Voice clips are cached in build/video/.

Each caption line is one TTS request, so captions and annotations are timed from the real audio lengths.
The terminal scene shows commands that are actually run here, with their real output.
"""
import argparse
import base64
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import textwrap
import urllib.request
import wave
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import FancyBboxPatch, Rectangle

from research.baselines import naive
from research.demo.figures import ROOT, estimate

W, H, FPS, SR = 1920, 1080, 30, 44100
BG, INK, DIM, GRID = "#0a0e1a", "#f0efec", "#8b93a7", "#2a3145"
OURS, NULL, TRUTH, GOOD, PANEL = "#3987e5", "#d95926", "#c3c2b7", "#3fb950", "#121829"
MONO = "Menlo"
CACHE = ROOT / "build" / "video"
plt.rcParams.update({"font.family": ["Arial", "DejaVu Sans"], "text.color": INK, "axes.facecolor": BG,
                     "figure.facecolor": BG, "axes.edgecolor": GRID, "axes.labelcolor": DIM, "xtick.color": DIM,
                     "ytick.color": DIM, "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True,
                     "grid.color": GRID, "font.size": 16})

# what the captions show instead of the spelled-out form the voice needs
SHOW = {"I-M-U": "IMU", "six D O F": "6-DoF", "X-R": "XR", "G-P-S": "GPS", "G-P-Us": "GPUs", "T-U-M": "TUM"}


def caption(say):
    for k, v in SHOW.items():
        say = say.replace(k, v)
    return say


# ---------------------------------------------------------------- voice

def tts(text, voice, pace, key):
    CACHE.mkdir(parents=True, exist_ok=True)
    path = CACHE / (hashlib.sha1(f"{voice}|{pace}|{text}".encode()).hexdigest()[:16] + ".wav")
    if not path.exists():
        body = {"text": text, "language_code": "en-IN", "model": "bulbul:v4-flash", "speaker": voice,
                "pace": pace, "speech_sample_rate": SR}
        req = urllib.request.Request("https://api.sarvam.ai/text-to-speech", json.dumps(body).encode(),
                                     {"api-subscription-key": key, "Content-Type": "application/json"})
        r = json.load(urllib.request.urlopen(req, timeout=120))
        path.write_bytes(base64.b64decode("".join(r["audios"])))
    with wave.open(str(path)) as w:
        assert w.getframerate() == SR and w.getnchannels() == 1 and w.getsampwidth() == 2, path
        return np.frombuffer(w.readframes(w.getnframes()), np.int16)


# ---------------------------------------------------------------- real data

def live_run():
    """Runs the organizers' script and our estimator on room5 exactly as a judge would; returns terminal lines."""
    d = Path(tempfile.mkdtemp())
    (d / "data/imu0").mkdir(parents=True)
    os.symlink(ROOT / "research/official/degrade_imu.py", d / "degrade_imu.py")
    os.symlink(ROOT / "src/main.py", d / "main.py")
    os.symlink(ROOT / "research/eval/validate_format.py", d / "validate_format.py")
    os.symlink(ROOT / "research/data/tumvi/dataset-room5_512_16/mav0/imu0/data.csv", d / "room5_clean.csv")

    def sh(cmd, show=None):
        p = subprocess.run(["bash", "-c", cmd], cwd=d, capture_output=True, text=True)
        assert p.returncode == 0, (cmd, p.stderr)
        out = (p.stdout + p.stderr).replace(str(d) + "/", "").replace(str(ROOT) + "/", "")
        return [show or cmd, [ln for ln in out.splitlines() if ln.strip()]]

    steps = [sh("python3 degrade_imu.py room5_clean.csv data/imu0/data.csv")]
    sh("python3 main.py data/imu0/data.csv estimated_trajectory.txt")  # warm the file cache, as any second run would
    steps += [
             sh("TIMEFORMAT='real %3Rs'; time python3 main.py data/imu0/data.csv estimated_trajectory.txt",
                "time python3 main.py data/imu0/data.csv estimated_trajectory.txt"),
             sh("head -3 estimated_trajectory.txt"),
             sh("wc -l < estimated_trajectory.txt; tail -n +2 data/imu0/data.csv | wc -l",
                "wc -l estimated_trajectory.txt data/imu0/data.csv"),
             sh("python3 validate_format.py estimated_trajectory.txt data/imu0/data.csv"),
             sh(f"'{ROOT}/scripts/measure_budget.sh' data/imu0/data.csv", "scripts/measure_budget.sh data/imu0/data.csv")]
    rows = [int(x) for x in steps[3][1]]
    assert rows[0] == rows[1], rows
    steps[3][1] = [f"{rows[0]:>7} estimated_trajectory.txt", f"{rows[1]:>7} data/imu0/data.csv  (rows, header excluded)"]
    real = float(steps[1][1][-1].split()[1].rstrip("s"))
    heap = json.loads(steps[5][1][0].split(": ", 1)[1])
    ms = float(steps[5][1][1].split("ms_per_imu_s=")[1].split()[0])
    shutil.rmtree(d)
    return steps, dict(rows=rows[0], real=real, heap=heap["algorithm_mb"], ms=ms)


def demo_data():
    r = estimate("room5")
    rmse = lambda e: float(np.sqrt(np.mean(np.sum(e ** 2, axis=1))))
    flown = r["T"] <= r["t_fail"]
    r["ate"], r["null"] = rmse(r["p"] - r["gt"]), rmse(r["gt"] - r["gt"][flown].mean(axis=0))
    v = r["df"].to_numpy(dtype=float)
    r["acc"] = np.linalg.norm(v[:, 4:7], axis=1)
    r["t_raw"] = (v[:, 0] - v[0, 0]) * 1e-9
    # plain strapdown integration of the same file: the "regular" approach
    pn, _ = naive.run(r["df"].iloc[:, 0].to_numpy(dtype=np.int64), v[:, 1:4], v[:, 4:7])
    r["naive_end_km"] = float(np.linalg.norm(pn[-1] - pn[0]) / 1000)
    return r


# ---------------------------------------------------------------- helpers

def ease(x):
    x = min(max(x, 0.0), 1.0)
    return x * x * (3 - 2 * x)


def appear(lt, t0, d=0.45):
    return ease((lt - t0) / d)


def card(fig, x, y, w, h, color=PANEL, edge=GRID, lw=1.5):
    p = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=0.012", transform=fig.transFigure,
                       facecolor=color, edgecolor=edge, linewidth=lw)
    fig.add_artist(p)
    return p


def fade_group(arts, a):
    for t in arts:
        t.set_alpha(a)


# ---------------------------------------------------------------- scenes
# each scene: (lines to say, setup). setup(fig, cues, dur, ctx) returns update(local_time).

def s_title(fig, cues, dur, ctx):
    r = ctx["r"]
    ax = fig.add_axes([0.55, 0.12, 0.42, 0.76]); ax.axis("off"); ax.set_aspect("equal")
    ax.plot(r["gt"][:, 0], r["gt"][:, 1], color=GRID, lw=1.5)
    trail, = ax.plot([], [], color=OURS, lw=2.5, alpha=0.9)
    ax.set_xlim(r["gt"][:, 0].min(), r["gt"][:, 0].max()); ax.set_ylim(r["gt"][:, 1].min(), r["gt"][:, 1].max())
    t1 = fig.text(0.06, 0.60, "Zero Drift", fontsize=92, fontweight="bold")
    t2 = fig.text(0.06, 0.52, "Path Finder", fontsize=52, color=OURS, fontweight="bold")
    tag = [fig.text(0.06, 0.40 - 0.055 * i, s, fontsize=30, color=c) for i, (s, c) in
           enumerate([("Jammed IMU in.", INK), ("Full 6-DoF trajectory out.", INK), ("Even after the sensor dies.", NULL)])]
    sub = fig.text(0.06, 0.14, "Samsung PRISM XR Hackathon 2026  ·  Track 03  ·  Team Zero Drift, VIT Vellore",
                   fontsize=20, color=DIM)
    n = len(r["gt"])

    def update(lt):
        fade_group([t1, t2], appear(lt, 0.2))
        sub.set_alpha(appear(lt, 0.8))
        for i, t in enumerate(tag):
            t.set_alpha(appear(lt, cues[1] + 0.9 * i))
        k = int(n * ease(lt / dur))
        trail.set_data(r["gt"][:k, 0], r["gt"][:k, 1])
    return update


def s_problem(fig, cues, dur, ctx):
    r = ctx["r"]
    fig.text(0.06, 0.86, "The problem: one sensor, under attack", fontsize=40, fontweight="bold")
    ax = fig.add_axes([0.07, 0.30, 0.60, 0.46])
    t, a = r["t_raw"], r["acc"]
    ax.set_xlim(0, t[-1]); ax.set_ylim(0, min(np.nanmax(a), 45))
    ax.set_xlabel("time (s)"); ax.set_ylabel("|accel| (m/s²)")
    ax.set_title("room5, degraded with the organizers' degrade_imu.py", loc="left", fontsize=17, color=DIM)
    sig, = ax.plot([], [], color=TRUTH, lw=0.7)
    dead = ax.axvspan(r["t_fail"], t[-1], color=NULL, alpha=0.0, lw=0)
    deadt = ax.text(r["t_fail"] - 1, ax.get_ylim()[1] * 0.9, "IMU dead\nlast 5 s ", ha="right", va="top", color=NULL,
                    fontsize=18, fontweight="bold", alpha=0)
    ramp = ax.annotate("noise, spikes, stuck & missing rows\nramp up over the flight", xy=(t[-1] * 0.82, ax.get_ylim()[1] * 0.62),
                       xytext=(t[-1] * 0.22, ax.get_ylim()[1] * 0.85), color=INK, fontsize=17,
                       arrowprops=dict(arrowstyle="->", color=INK, lw=1.5), alpha=0)
    ramp.arrow_patch.set_alpha(0)
    bullets = [fig.text(0.72, 0.70 - 0.075 * i, s, fontsize=22, color=c, alpha=0) for i, (s, c) in enumerate([
        ("GPS jammed: IMU is all you have", INK), ("noise and bias ramp up", INK), ("rows freeze, duplicate, vanish", INK),
        ("then 5 s with no data at all", NULL)])]
    box = card(fig, 0.72, 0.22, 0.24, 0.17, edge=NULL)
    big = fig.text(0.84, 0.32, f"{r['naive_end_km']:,.1f} km", fontsize=46, color=NULL, fontweight="bold", ha="center", alpha=0)
    small = fig.text(0.84, 0.25, "where plain double integration ends up\n(the real path stays inside a room)",
                     fontsize=14, color=DIM, ha="center", alpha=0)
    step = max(1, len(t) // 4000)

    def update(lt):
        k = int(len(t) * ease(lt / max(cues[2], 1.0)))
        sig.set_data(t[:k:step], a[:k:step])
        aa = appear(lt, cues[1] + 0.4)
        ramp.set_alpha(aa); ramp.arrow_patch.set_alpha(aa)
        dead.set_alpha(0.25 * appear(lt, cues[1] + 2.8)); deadt.set_alpha(appear(lt, cues[1] + 2.8))
        for i, b in enumerate(bullets):
            b.set_alpha(appear(lt, [cues[0] + 0.5, cues[1] + 0.2, cues[1] + 1.4, cues[1] + 2.8][i]))
        box.set_alpha(appear(lt, cues[2])); big.set_alpha(appear(lt, cues[2])); small.set_alpha(appear(lt, cues[2] + 0.3))
    return update


def s_terminal(fig, cues, dur, ctx):
    steps, live = ctx["steps"], ctx["live"]
    fig.text(0.06, 0.88, "Live run: exactly what a judge runs", fontsize=40, fontweight="bold")
    card(fig, 0.04, 0.17, 0.62, 0.66, color="#05070d")
    for i, c in enumerate(["#ff5f56", "#ffbd2e", "#27c93f"]):
        fig.add_artist(plt.Circle((0.06 + 0.012 * i, 0.81), 0.0045, color=c, transform=fig.transFigure))
    fig.text(0.35, 0.805, "zero-drift — bash", fontsize=13, color=DIM, ha="center")
    nrow = 22
    rows = [fig.text(0.055, 0.77 - i * 0.0265, "", fontsize=14, family=MONO, color=INK, va="top") for i in range(nrow)]
    # (time, text, colour, typed); commands are typed, outputs appear a beat later
    at = [cues[0] + 0.3, cues[1] + 0.2, cues[3] + 0.1, cues[3] + 1.6, cues[3] + 3.0, cues[4] + 0.1]
    lines = []
    for (cmd, out), t0 in zip(steps, at):
        typed = len(cmd) / 45
        lines.append((t0, "$ " + cmd, GOOD, typed))
        for j, o in enumerate(out):
            col = GOOD if o.strip() == "OK" else INK
            lines.append((t0 + typed + 0.35 + 0.06 * j, textwrap.shorten(o, 100, placeholder="…"), col, 0))
    tiles = [("142 s of IMU", f"in {live['real']:.2f} s", cues[2] + 0.2),
             ("rows in = poses out", f"{live['rows']:,}", cues[3] + 1.0),
             ("validator", "OK", cues[3] + 3.6),
             ("heap  (limit 8 MB)", f"{live['heap']:.2f} MB", cues[4] + 1.6),
             ("per IMU-second  (limit 20 ms)", f"{live['ms']:.2f} ms", cues[4] + 3.4)]
    arts = []
    for i, (lab, val, t0) in enumerate(tiles):
        y = 0.70 - i * 0.125
        c = card(fig, 0.69, y, 0.27, 0.105)
        a1 = fig.text(0.705, y + 0.067, lab, fontsize=16, color=DIM)
        a2 = fig.text(0.705, y + 0.015, val, fontsize=34, fontweight="bold", color=GOOD if val == "OK" else INK)
        arts.append(([c, a1, a2], t0))

    def update(lt):
        vis = []
        for t0, s, col, typed in lines:
            if lt < t0:
                break
            if typed:
                s = s[:2 + int((len(s) - 2) * min(1, (lt - t0) / typed))]
            vis.append((s, col))
        vis = vis[-nrow:]
        blink = int(lt * 2) % 2 == 0
        for i, row in enumerate(rows):
            s, col = vis[i] if i < len(vis) else ("", INK)
            if i == len(vis) - 1 and blink:
                s += " █"
            row.set_text(s); row.set_color(col)
        for group, t0 in arts:
            fade_group(group, appear(lt, t0))
    return update


def s_pipeline(fig, cues, dur, ctx):
    fig.text(0.06, 0.86, "How it works: one file, two streaming passes", fontsize=40, fontweight="bold")
    blocks = [("Probe", "layout · units\nrate · gravity", cues[0] + 0.6),
              ("Repair", "dead · stuck\nspikes · gaps", cues[1] + 0.2),
              ("Attitude", "gyro + gentle\ngravity pull", cues[1] + 1.6),
              ("Rotor drag", "sideways accel\n= speed sensor", cues[2] + 0.5),
              ("Smoother", "the future\ncorrects the past", cues[3] + 0.2),
              ("Blind 5 s", "relax to the\nflown centre", cues[3] + 2.6)]
    arts = []
    for i, (name, sub, t0) in enumerate(blocks):
        x = 0.05 + i * 0.152
        hi = name == "Rotor drag"
        c = card(fig, x, 0.50, 0.135, 0.19, edge=OURS if hi else GRID, lw=3 if hi else 1.5)
        a1 = fig.text(x + 0.0675, 0.635, name, fontsize=26, fontweight="bold", ha="center", color=OURS if hi else INK)
        a2 = fig.text(x + 0.0675, 0.535, sub, fontsize=17, ha="center", color=DIM, linespacing=1.4)
        arr = fig.text(x + 0.1425, 0.585, "›", fontsize=40, color=DIM, ha="center", va="center") if i < 5 else None
        arts.append(([c, a1, a2] + ([arr] if arr else []), t0))
    eq = [fig.text(0.5, 0.36, "a_lateral  =  − k · v_lateral", fontsize=40, family=MONO, ha="center", color=OURS),
          fig.text(0.5, 0.29, "one coefficient, k = 0.177 s⁻¹ · a chi-square gate switches it off when the data is not rotor flight",
                   fontsize=19, ha="center", color=DIM)]
    foot = fig.text(0.5, 0.19, "Python standard library only  ·  memory flat with file length  ·  never sees ground truth",
                    fontsize=20, ha="center", color=INK)

    def update(lt):
        for group, t0 in arts:
            fade_group(group, appear(lt, t0))
        fade_group(eq, appear(lt, cues[2] + 1.5))
        foot.set_alpha(appear(lt, cues[3] + 4.0))
    return update


def s_hero(fig, cues, dur, ctx):
    r = ctx["r"]
    T, gt, p, tf = r["T"], r["gt"], r["p"], r["t_fail"]
    fig.text(0.06, 0.88, "Handheld room5: the sensor dies, we keep tracking", fontsize=40, fontweight="bold")
    axs = fig.add_axes([0.06, 0.24, 0.40, 0.48]); axt = fig.add_axes([0.53, 0.20, 0.42, 0.62])
    t_raw, acc = r["t_raw"], r["acc"]
    step = max(1, len(t_raw) // 4000)
    t_raw, acc = t_raw[::step], acc[::step]
    axs.set_xlim(0, T[-1]); axs.set_ylim(0, min(acc.max(), 45)); axs.set_xlabel("time (s)")
    axs.set_title("what the sensor gives us: |accel| (m/s²)", loc="left", fontsize=18, color=DIM)
    axs.axvspan(tf, T[-1], color=NULL, alpha=0.2, lw=0)
    sig, = axs.plot([], [], color=TRUTH, lw=0.7)
    axt.plot(gt[:, 0], gt[:, 1], color=GRID, lw=5, label="ground truth")
    axt.set_aspect("equal"); axt.set_xlabel("x (m)")
    axt.set_title("what we recover, top view", loc="left", fontsize=18, color=DIM)
    pad = 0.4
    axt.set_xlim(min(gt[:, 0].min(), p[:, 0].min()) - pad, max(gt[:, 0].max(), p[:, 0].max()) + pad)
    axt.set_ylim(min(gt[:, 1].min(), p[:, 1].min()) - pad, max(gt[:, 1].max(), p[:, 1].max()) + pad)
    flown, = axt.plot([], [], color=OURS, lw=2.6, label="Zero Drift")
    blind, = axt.plot([], [], color=NULL, lw=3, ls=(0, (1, 1.2)), label="Zero Drift, blind 5 s")
    dot, = axt.plot([], [], "o", color=OURS, ms=12)
    axt.legend(loc="lower left", fontsize=15, frameon=False)
    clock = fig.text(0.06, 0.80, "", fontsize=22, color=INK)
    res = [fig.text(0.06, 0.16, f"ATE {r['ate']:.2f} m   vs   {r['null']:.2f} m never-moving", fontsize=26,
                    fontweight="bold", color=GOOD),
           fig.text(0.06, 0.125, "evo, SE(3) Umeyama alignment, organizers' default degradation", fontsize=15, color=DIM)]
    t_end = dur - 1.2

    def now_at(lt):  # flown part during the first sentence, blind part during the second
        if lt < cues[1]:
            return T[0] + (tf - T[0]) * ease(lt / cues[1]) if cues[1] > 0 else tf
        return tf + (T[-1] - tf) * min(1, (lt - cues[1]) / max(t_end - cues[1], 0.5))

    def update(lt):
        now = now_at(lt)
        sig.set_data(t_raw[:np.searchsorted(t_raw, now)], acc[:np.searchsorted(t_raw, now)])
        j = max(1, np.searchsorted(T, now))
        f = T[:j] <= tf
        flown.set_data(p[:j][f, 0], p[:j][f, 1]); blind.set_data(p[:j][~f, 0], p[:j][~f, 1])
        dot.set_data([p[j - 1, 0]], [p[j - 1, 1]]); dot.set_color(NULL if now > tf else OURS)
        clock.set_text(f"t = {now:5.1f} s" + ("     IMU dead · still tracking" if now > tf else ""))
        clock.set_color(NULL if now > tf else INK)
        fade_group(res, appear(lt, t_end - 0.6))
    return update


def s_numbers(fig, cues, dur, ctx):
    fig.text(0.06, 0.88, "The numbers", fontsize=40, fontweight="bold")
    ax = fig.add_axes([0.07, 0.24, 0.42, 0.52])
    seqs = ["MH_04\ndrone", "V1_03\ndrone", "V2_02\ndrone", "room6\nhandheld"]
    ours, null = np.array([6.64, 1.47, 1.715, 0.855]), np.array([6.81, 1.58, 2.12, 0.99])  # docs/RESULTS.md §1
    x = np.arange(4)
    bo = ax.bar(x - 0.2, np.zeros(4), 0.38, color=OURS, label="Zero Drift")
    bn = ax.bar(x + 0.2, np.zeros(4), 0.38, color=NULL, label="never-moving reference")
    ax.set_xticks(x, seqs, fontsize=15); ax.set_ylim(0, 8.8); ax.set_ylabel("ATE (m), lower is better")
    ax.set_title("held-out, never used for any choice: 8 of 8 runs better", loc="left", fontsize=18, color=DIM)
    ax.legend(loc="upper right", fontsize=15, frameon=False); ax.grid(axis="x", visible=False)
    tiles = [("held-out runs", "8 / 8", cues[0] + 2.0), ("any seed, both orders", "20 / 20", cues[1] + 0.3),
             ("handheld, best seed", "−45 %", cues[1] + 2.6), ("memory", "7× under", cues[2] + 0.1),
             ("compute", "13× under", cues[2] + 1.6), ("dependencies", "0", cues[2] + 3.0)]
    arts = []
    for i, (lab, val, t0) in enumerate(tiles):
        cx, cy = 0.55 + (i % 2) * 0.215, 0.62 - (i // 2) * 0.19
        c = card(fig, cx, cy, 0.195, 0.165)
        a1 = fig.text(cx + 0.015, cy + 0.115, lab, fontsize=16, color=DIM)
        a2 = fig.text(cx + 0.015, cy + 0.03, val, fontsize=48, fontweight="bold", color=GOOD)
        arts.append(([c, a1, a2], t0))

    def update(lt):
        g = ease((lt - cues[0] - 0.3) / 1.5)
        for b, v in zip(bo, ours):
            b.set_height(v * g)
        for b, v in zip(bn, null):
            b.set_height(v * g)
        for group, t0 in arts:
            fade_group(group, appear(lt, t0))
    return update


def s_usecases(fig, cues, dur, ctx):
    fig.text(0.06, 0.86, "Where it ships", fontsize=40, fontweight="bold")
    cards = [("GPS-denied drones", "the track's brief", "Jamming ramps up, the IMU dies:\na pose for every row anyway,\n5 s forecast after failure.", cues[0] + 1.2),
             ("XR headsets", "Galaxy XR-class 6-DoF", "Cameras lose tracking in the dark,\nunder occlusion or fast motion:\nIMU-only failover keeps the pose.", cues[1]),
             ("Wearables & hubs", "tiny compute", "~1 MB, single thread,\nno numpy, no GPU, no model:\nany Python 3.9+.", cues[2])]
    arts = []
    for i, (h, s, b, t0) in enumerate(cards):
        x = 0.06 + i * 0.30
        c = card(fig, x, 0.27, 0.27, 0.48, edge=OURS if i == 1 else GRID, lw=3 if i == 1 else 1.5)
        a = [fig.text(x + 0.02, 0.67, h, fontsize=30, fontweight="bold"),
             fig.text(x + 0.02, 0.62, s, fontsize=18, color=OURS),
             fig.text(x + 0.02, 0.36, b, fontsize=19, color=INK, linespacing=1.6)]
        arts.append(([c] + a, t0))

    def update(lt):
        for group, t0 in arts:
            fade_group(group, appear(lt, t0))
    return update


def s_close(fig, cues, dur, ctx):
    hon = [fig.text(0.06, 0.78 - 0.075 * i, s, fontsize=26, color=c) for i, (s, c) in enumerate([
        ("Honest by design", INK), ("· every number compared with doing nothing", DIM),
        ("· held-out frozen on day one, tuned only on variants", DIM), ("· every decision logged, failures included", DIM)])]
    hon[0].set_fontweight("bold"); hon[0].set_fontsize(34)
    end = [fig.text(0.5, 0.36, "Zero Drift · Path Finder", fontsize=64, fontweight="bold", ha="center"),
           fig.text(0.5, 0.29, "Jammed IMU in. Full 6-DoF trajectory out.", fontsize=28, ha="center", color=OURS),
           fig.text(0.5, 0.22, "Akshat Agrawal  ·  Hemang Dubey  ·  Ishita Solanki   —   VIT Vellore", fontsize=20,
                    ha="center", color=DIM)]

    def update(lt):
        for i, t in enumerate(hon):
            t.set_alpha(appear(lt, 0.2 + 0.6 * i))
        fade_group(end, appear(lt, cues[-1]))
    return update


SCENES = [
    (["Hi! We're Team Zero Drift, from VIT Vellore, and this is Path Finder, for Samsung PRISM Track Three.",
      "Jammed sensor in. Full six D O F trajectory out. Even after the sensor dies."], s_title),
    (["Picture a drone where G-P-S is jammed. All it has left is one I-M-U.",
      "And the jamming gets worse every minute. Noise climbs, samples freeze, rows go missing. And in the last five seconds, the sensor is completely dead.",
      "Integrate that the regular way, and you land {naive_say} away."], s_problem),
    (["Let's run it, live. We degrade a real recording with the organisers' own script.",
      "Then, just one command. Pure Python, standard library only. Nothing to install.",
      "A hundred and forty two seconds of data, done in {real_say}.",
      "Every input row gets a pose, in exact T-U-M format, and the validator says OK.",
      "Budget check: {heap_say} of heap, against a limit of eight. {ms_say} per second of data, against twenty."], s_terminal),
    (["So how does it work? First, it measures the file itself: column order, units, sample rate and gravity. Nothing is assumed.",
      "Then it repairs dead, stuck and spiky rows, and tracks attitude from the gyro.",
      "And here's the trick. On a multirotor, rotor drag makes the sideways accelerometer reading proportional to speed. So physics becomes our speedometer.",
      "A backward smoother lets the future correct the past. And when the sensor dies, the path relaxes toward where the vehicle has been."], s_pipeline),
    (["Here it is on a handheld recording. Left, the raw signal. Right, what we recover, drawn over ground truth.",
      "Now the I-M-U dies, and we keep tracking, blind, for five full seconds."], s_hero),
    (["On four held-out sequences we never touched while building, we beat a tracker that never moves in eight runs out of eight.",
      "Fresh random seeds, both column orders: twenty out of twenty, and up to forty five percent better on handheld motion.",
      "Seven times under the memory limit. Thirteen times under compute. Zero dependencies."], s_numbers),
    (["Where does it matter? G-P-S denied drones, exactly the brief.",
      "X-R headsets, like Galaxy X-R, when the cameras lose tracking in the dark. We keep the pose alive until vision returns.",
      "And tiny wearables, with no room for numpy, G-P-Us or big models."], s_usecases),
    (["We stay honest. Every number is compared with doing nothing, and every decision is logged, even the failures.",
      "Team Zero Drift. Thank you!"], s_close),
]
LEAD, GAP, TAIL = 0.45, 0.35, 0.7


# ---------------------------------------------------------------- assembly

def chunks(text, n=64):
    """Splits a caption into the fewest pieces of at most n characters, balanced so no piece is a stray word."""
    k = -(-len(text) // n)
    for width in range(-(-len(text) // k), n + 1):
        parts = textwrap.wrap(text, width)
        if len(parts) <= k:
            return parts
    return textwrap.wrap(text, n)


def srt_time(t):
    ms = int(round(t * 1000))
    return f"{ms // 3600000:02}:{ms // 60000 % 60:02}:{ms // 1000 % 60:02},{ms % 1000:03}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--voice", default="sunny_en_social")
    ap.add_argument("--pace", type=float, default=1.05)
    ap.add_argument("--preview", type=float, nargs="+", default=None, help="render only stills at these times (s)")
    a = ap.parse_args()
    key = os.environ.get("SARVAM_API_KEY") or sys.exit("set SARVAM_API_KEY")

    steps, live = live_run()
    ctx = dict(r=demo_data(), steps=steps, live=live)
    print("live run:", live, f"| naive end {ctx['r']['naive_end_km']:.2f} km | ATE {ctx['r']['ate']:.3f} vs {ctx['r']['null']:.3f}")
    # spoken numbers come from this run, so the voice never claims more than the screen shows
    say_vals = dict(naive_say=f"about {ctx['r']['naive_end_km']:.0f} kilometres",
                    real_say=f"just {live['real']:.1f} seconds",
                    heap_say="under one megabyte" if live["heap"] < 1 else f"{live['heap']:.1f} megabytes",
                    ms_say=f"{live['ms']:.1f} milliseconds")

    timeline, caps, audio_parts, t = [], [], [], 0.0
    for lines, setup in SCENES:
        start = t
        t += LEAD
        cues = []
        for say in lines:
            say = say.format(**say_vals)
            pcm = tts(say, a.voice, a.pace, key)
            d = len(pcm) / SR
            cues.append(t - start)
            audio_parts.append((t, pcm))
            pieces = chunks(caption(say))
            total = sum(len(p) for p in pieces)
            c0 = t
            for p in pieces:
                c1 = c0 + d * len(p) / total
                caps.append((c0, c1, p)); c0 = c1
            t += d + GAP
        t += TAIL - GAP
        timeline.append((start, t, cues, setup))
    total = t
    print(f"duration {total:.1f} s, {len(caps)} captions")
    assert total <= 180, "video over the 3:00 limit"


    out = ROOT / "demo" / "ZeroDrift_demo.mp4"
    CACHE.mkdir(parents=True, exist_ok=True)
    track = np.zeros(int(total * SR) + SR, np.int16)
    for t0, pcm in audio_parts:
        i = int(t0 * SR); track[i:i + len(pcm)] = pcm
    with wave.open(str(CACHE / "voice.wav"), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes(track.tobytes())
    with open(ROOT / "demo" / "ZeroDrift_demo.srt", "w") as f:
        for i, (c0, c1, p) in enumerate(caps, 1):
            f.write(f"{i}\n{srt_time(c0)} --> {srt_time(c1)}\n{p}\n\n")

    fig = plt.figure(figsize=(W / 100, H / 100), dpi=100)
    times = a.preview if a.preview is not None else np.arange(int(np.ceil(total * FPS))) / FPS
    ff = None if a.preview is not None else subprocess.Popen(
        ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgba", "-s", f"{W}x{H}", "-r", str(FPS),
         "-i", "-", "-i", str(CACHE / "voice.wav"), "-c:v", "libx264", "-preset", "medium", "-crf", "20",
         "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart", str(out)],
        stdin=subprocess.PIPE)
    current, update = None, None
    for n, tt in enumerate(times):
        sc = next(s for s in timeline if tt < s[1]) if tt < total else timeline[-1]
        if sc is not current:
            fig.clf(); current = sc
            update = sc[3](fig, sc[2], sc[1] - sc[0], ctx)
            cap_box = card(fig, 0.15, 0.02, 0.70, 0.075, color="#000000", edge="#000000")
            cap_txt = fig.text(0.5, 0.0575, "", fontsize=27, ha="center", va="center", color="#ffffff")
            fade = fig.add_artist(Rectangle((0, 0), 1, 1, transform=fig.transFigure, color=BG, zorder=100))
        lt = tt - sc[0]
        update(lt)
        cap = next((p for c0, c1, p in caps if c0 <= tt < c1 + 0.15), "")
        cap_txt.set_text(cap); cap_box.set_alpha(0.72 if cap else 0); cap_txt.set_alpha(1 if cap else 0)
        fade.set_alpha(1 - ease(lt / 0.35))
        fig.canvas.draw()
        frame = np.asarray(fig.canvas.buffer_rgba())
        if ff is None:
            plt.imsave(CACHE / f"preview_{tt:.1f}.png", frame); print(CACHE / f"preview_{tt:.1f}.png")
        else:
            ff.stdin.write(frame.tobytes())
            if n % (FPS * 10) == 0:
                print(f"{tt:5.1f} / {total:.1f} s", flush=True)
    if ff:
        ff.stdin.close(); ff.wait()
        assert ff.returncode == 0
        print(out, out.stat().st_size // 1024, "KB")


if __name__ == "__main__":
    main()
