#!/usr/bin/env python3
"""Figures for the deck and README, from validation sequences on the organizers' degradation (report only).

python -m research.demo.figures        # writes docs/figures/*.png
"""
import subprocess
import sys
import tempfile
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from evo.core import geometry

from research.io_euroc import load_seq
from research.official_degrade import degrade_arrays, write_csv

ROOT = Path(__file__).resolve().parent.parent.parent
OUT = ROOT / "docs" / "figures"
DARK = "--dark" in sys.argv  # for the deck, whose template is dark; saved with a transparent background
if DARK:
    OUT = OUT / "dark"
    OURS, NULL, TRUTH, INK, SURFACE, GRID, SHADE = "#3987e5", "#d95926", "#c3c2b7", "#f0efec", "#0a0e1a", "#2a3145", "#1c2438"
else:
    OURS, NULL, TRUTH, INK, SURFACE, GRID, SHADE = "#2a78d6", "#eb6834", "#52514e", "#0b0b0b", "#fcfcfb", "#ebeae6", "#ebeae6"
plt.rcParams.update({"figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "axes.edgecolor": GRID, "savefig.transparent": DARK,
                     "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True, "grid.color": GRID,
                     "grid.linewidth": 0.8, "font.size": 11, "axes.titlesize": 13, "axes.titleweight": "bold",
                     "axes.titlelocation": "left", "text.color": INK, "axes.labelcolor": TRUTH, "xtick.color": TRUTH,
                     "ytick.color": TRUTH, "legend.frameon": False, "savefig.dpi": 170, "savefig.bbox": "tight"})


def estimate(name, order="A"):
    t_ns, gyro, accel, (gt_t, gt_p, _) = load_seq(name)
    df, man = degrade_arrays(t_ns, gyro, accel, order=order)
    with tempfile.TemporaryDirectory() as d:
        write_csv(df, f"{d}/imu0/data.csv")
        subprocess.run([sys.executable, str(ROOT / "src/main.py"), f"{d}/imu0/data.csv", f"{d}/e.txt"], check=True)
        est = np.loadtxt(f"{d}/e.txt")
    t = df.iloc[:, 0].to_numpy()
    keep = np.r_[True, np.diff(t) > 0] & (t >= gt_t[0]) & (t <= gt_t[-1])
    gt = np.c_[[np.interp(t[keep], gt_t, gt_p[:, i]) for i in range(3)]].T
    p = est[keep, 1:4]
    rot, tr, _ = geometry.umeyama_alignment(p.T, gt.T)
    T = (t[keep] - t[0]) * 1e-9
    return dict(T=T, gt=gt, p=(rot @ p.T).T + tr, t_fail=(man["t_fail_ns"] - t[0]) * 1e-9, df=df, clean_rows=len(t_ns))


def trajectory(name, title):
    r = estimate(name)
    fig, ax = plt.subplots(figsize=(6.4, 5.6))
    flown = r["T"] <= r["t_fail"]
    ax.plot(r["gt"][:, 0], r["gt"][:, 1], color=TRUTH, lw=1.2, label="Ground truth")
    ax.plot(r["p"][flown, 0], r["p"][flown, 1], color=OURS, lw=2, label="Our estimate (aligned)")
    ax.plot(r["p"][~flown, 0], r["p"][~flown, 1], color=OURS, lw=2, ls=(0, (1, 1.5)), label="Our estimate, blind 5 s")
    c = r["gt"][flown].mean(axis=0)
    ax.scatter([c[0]], [c[1]], s=90, color=NULL, edgecolor=SURFACE, linewidth=2, zorder=5, label="Never-moving reference")
    ax.set_aspect("equal")
    ax.set_xlabel("x (m)"); ax.set_ylabel("y (m)")
    ax.set_title(title)
    ax.legend(loc="upper left", bbox_to_anchor=(1.0, 1.0))
    fig.savefig(OUT / f"trajectory_{name}.png"); plt.close(fig)
    return r


def error_over_time(r, name, title):
    err = np.linalg.norm(r["p"] - r["gt"], axis=1)
    null = np.linalg.norm(r["gt"] - r["gt"][r["T"] <= r["t_fail"]].mean(axis=0), axis=1)
    box = lambda x: np.convolve(x, np.ones(400) / 400, "same")
    fig, ax = plt.subplots(figsize=(8.6, 3.6))
    ax.axvspan(r["t_fail"], r["T"][-1], color=SHADE, lw=0)
    mid = slice(200, -200)  # the 2 s mean is undefined at the very ends
    ax.plot(r["T"][mid], box(null)[mid], color=NULL, lw=2, label="Never-moving reference")
    ax.plot(r["T"][mid], box(err)[mid], color=OURS, lw=2, label="Our estimate")
    ax.set_xlabel("time (s)"); ax.set_ylabel("position error (m), 2 s mean")
    ax.set_title(title); ax.set_ylim(bottom=0); ax.legend(loc="upper left", ncol=2)
    ax.text(r["t_fail"], ax.get_ylim()[1] * 0.97, "IMU dead ", va="top", ha="right", color=TRUTH, fontsize=10)
    fig.savefig(OUT / f"error_{name}.png"); plt.close(fig)


def health(r, name):
    """What the front end has to survive, counted per 5 s from the degraded file alone."""
    v = r["df"].to_numpy(dtype=float)
    t = r["df"].iloc[:, 0].to_numpy()
    T = (t - t[0]) * 1e-9
    step = np.diff(t, prepend=t[0])
    med = np.median(step[step > 0])
    dup = step == 0
    dup[0] = False
    missing = np.where(step > 1.5 * med, np.round(step / med) - 1, 0)
    dead = ~v[:, 1:].any(axis=1)
    stuck = np.r_[False, (v[1:, 1:] == v[:-1, 1:]).all(axis=1)] & ~dup & ~dead
    acc = v[:, 4:7]
    jump = np.r_[0, np.linalg.norm(acc[1:] - acc[:-1], axis=1)]
    noise = np.where(dead | dup | stuck, np.nan, jump)
    bins = np.arange(0, T[-1] + 5, 5)
    idx = np.digitize(T, bins) - 1
    count = lambda m: np.bincount(idx, weights=m.astype(float), minlength=len(bins))[:len(bins) - 1]
    rows = [("Rows missing", count(missing)), ("Stuck rows (exact repeats)", count(stuck)),
            ("Duplicated rows", count(dup)),
            ("Accel sample-to-sample jump, median (m/s²): rotor vibration from take-off, then injected noise on top",
             np.array([np.nanmedian(noise[idx == i]) if (idx == i).any() else np.nan for i in range(len(bins) - 1)]))]
    fig, axes = plt.subplots(len(rows), 1, figsize=(8.6, 6.8), sharex=True)
    for ax, (label, y) in zip(axes, rows):
        ax.axvspan(r["t_fail"], T[-1], color=SHADE, lw=0)
        ax.bar(bins[:-1] + 2.5, y, width=4.2, color=OURS)
        ax.set_title(label, fontsize=11, fontweight="normal")
        ax.set_ylim(bottom=0)
    axes[1].text(r["t_fail"], axes[1].get_ylim()[1], "IMU dead: rows are all zeros ", va="top", ha="right",
                 color=TRUTH, fontsize=10)
    axes[-1].set_xlabel("time (s), 5 s bins")
    fig.suptitle(f"Sensor health over the mission ({name}, organizers' script at defaults)", x=0.01, ha="left",
                 fontweight="bold", fontsize=13)
    fig.tight_layout()
    fig.savefig(OUT / f"health_{name}.png"); plt.close(fig)


def heldout_bars():
    """Numbers are the held-out run 1 row of EXPERIMENTS.md (mean of column orders A and B)."""
    names = ["MH_04", "V1_03", "V2_02", "room6"]
    ours, null = [6.64, 1.47, 1.71, 0.86], [6.81, 1.58, 2.12, 0.99]
    x = np.arange(len(names))
    fig, ax = plt.subplots(figsize=(7.2, 3.8))
    b1 = ax.bar(x - 0.2, null, 0.36, color=NULL, label="Never-moving reference")
    b2 = ax.bar(x + 0.2, ours, 0.36, color=OURS, label="Our estimate")
    for bars in (b1, b2):
        ax.bar_label(bars, fmt="%.2f", padding=2, color=INK, fontsize=10)
    ax.set_xticks(x, names); ax.set_ylabel("ATE RMSE after SE(3) alignment (m)")
    ax.set_title("Held-out sequences, never used for any design choice")
    ax.grid(axis="x", visible=False); ax.legend(loc="upper right")
    fig.savefig(OUT / "heldout_ate.png"); plt.close(fig)


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    for name, title in (("MH_05", "MH_05, drone in a machine hall (validation)"), ("room5", "room5, handheld in a room (validation)")):
        r = trajectory(name, title + ", top view")
        error_over_time(r, name, title)
        if name == "MH_05":
            health(r, name)
    heldout_bars()
    print(sorted(p.name for p in OUT.glob("*.png")))
