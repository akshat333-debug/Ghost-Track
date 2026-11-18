#!/usr/bin/env python3
"""README hero animation: the jammed IMU signal on the left, our trajectory drawing over ground truth on the right.

python -m research.demo.hero        # writes demo/figures/hero.gif (room5 validation, official degradation)
"""
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.animation import FuncAnimation, PillowWriter

from research.demo.figures import GRID, INK, NULL, OURS, ROOT, TRUTH, estimate

FRAMES, FPS = 90, 15
SEQ = "room5"  # handheld: the head-like motion of an XR headset


def main():
    r = estimate(SEQ)
    T, gt, p, t_fail = r["T"], r["gt"], r["p"], r["t_fail"]
    raw = r["df"].to_numpy(dtype=float)
    t_raw = (raw[:, 0] - raw[0, 0]) * 1e-9
    acc = np.linalg.norm(raw[:, 4:7], axis=1)
    step = max(1, len(t_raw) // 3000)  # thin the signal so the GIF stays small
    t_raw, acc = t_raw[::step], acc[::step]

    fig, (axs, axt) = plt.subplots(1, 2, figsize=(9.6, 4.2), gridspec_kw={"width_ratios": [1.15, 1]}, dpi=80)
    fig.subplots_adjust(left=0.06, right=0.98, top=0.84, bottom=0.13, wspace=0.18)
    fig.text(0.06, 0.93, "Jammed IMU in.  Full 6-DoF trajectory out.  Even after the sensor dies.", fontsize=14,
             fontweight="bold", color=INK)

    axs.set_xlim(0, T[-1]); axs.set_ylim(0, min(acc.max(), 60))
    axs.set_xlabel("time (s)"); axs.set_title("What the sensor gives us: |accel| (m/s²)", fontsize=11)
    axs.axvspan(t_fail, T[-1], color=NULL, alpha=0.15, lw=0)
    axs.text(t_fail, axs.get_ylim()[1] * 0.92, " IMU dead", color=NULL, fontsize=10, fontweight="bold")
    sig, = axs.plot([], [], color=TRUTH, lw=0.6)

    axt.plot(gt[:, 0], gt[:, 1], color=GRID, lw=3, label="Ground truth")
    axt.set_aspect("equal"); axt.set_xlabel("x (m)"); axt.set_title(f"What we recover: {SEQ}, top view", fontsize=11)
    pad = 0.5
    axt.set_xlim(min(gt[:, 0].min(), p[:, 0].min()) - pad, max(gt[:, 0].max(), p[:, 0].max()) + pad)
    axt.set_ylim(min(gt[:, 1].min(), p[:, 1].min()) - pad, max(gt[:, 1].max(), p[:, 1].max()) + pad)
    flown, = axt.plot([], [], color=OURS, lw=2, label="Ours")
    blind, = axt.plot([], [], color=NULL, lw=2, ls=(0, (1, 1.2)), label="Ours, blind 5 s")
    dot, = axt.plot([], [], "o", color=OURS, ms=7)
    axt.legend(loc="lower left", fontsize=8, frameon=False)
    clock = axt.text(0.02, 0.95, "", transform=axt.transAxes, fontsize=10, color=INK, va="top")

    ends = np.r_[np.linspace(T[0], t_fail, int(FRAMES * 0.8)), np.linspace(t_fail, T[-1], FRAMES - int(FRAMES * 0.8))]
    ends = np.r_[ends, np.full(FPS * 2, T[-1])]  # hold the last frame for two seconds

    def draw(i):
        now = ends[i]
        k = np.searchsorted(t_raw, now)
        sig.set_data(t_raw[:k], acc[:k])
        j = max(1, np.searchsorted(T, now))
        f = T[:j] <= t_fail
        flown.set_data(p[:j][f, 0], p[:j][f, 1])
        blind.set_data(p[:j][~f, 0], p[:j][~f, 1])
        dot.set_data([p[j - 1, 0]], [p[j - 1, 1]])
        dot.set_color(NULL if now > t_fail else OURS)
        clock.set_text(f"t = {now:5.1f} s" + ("   sensor dead, still tracking" if now > t_fail else ""))
        return sig, flown, blind, dot, clock

    out = ROOT / "demo" / "figures" / "hero.gif"
    FuncAnimation(fig, draw, frames=len(ends), blit=True).save(out, writer=PillowWriter(fps=FPS))
    print(out, out.stat().st_size // 1024, "KB")


if __name__ == "__main__":
    main()
