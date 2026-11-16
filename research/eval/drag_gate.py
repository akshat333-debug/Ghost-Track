#!/usr/bin/env python3
"""Gate G1 (D-019): is body-lateral specific force proportional to body velocity on this data?

Rotor drag makes a multirotor's accelerometer read -k * v in the plane normal to thrust (Leishman et al. 2014).
Fit on clean data with ground truth: f_lat = -k * v_lat + bias. Thresholds were fixed before the first run:
keep the drag measurement only if median R^2 >= 0.3 on EuRoC train and k varies < 30% across sequences.

python -m research.eval.drag_gate
"""
import numpy as np
from scipy.spatial.transform import Rotation as R, Slerp

from research.io_euroc import load_seq
from research.split import SPLITS

R2_MIN, K_SPREAD_MAX = 0.3, 0.3
WINDOW_S = 0.5  # fixed in advance; 0.2 s and 1.0 s are printed for sensitivity only


def box(x, n):
    k = np.ones(n) / n
    return np.c_[[np.convolve(x[:, i], k, "same") for i in range(x.shape[1])]].T


def fit(name, window_s=WINDOW_S):
    t_ns, _, accel, (gt_t, gt_p, gt_q) = load_seq(name)
    T, Tg = (t_ns - gt_t[0]) * 1e-9, (gt_t - gt_t[0]) * 1e-9
    dt = float(np.median(np.diff(T)))
    rot = Slerp(Tg, R.from_quat(gt_q))(T)
    p = np.c_[[np.interp(T, Tg, gt_p[:, i]) for i in range(3)]].T
    v_body = rot.inv().apply(np.gradient(box(p, 11), T, axis=0))
    n = max(1, int(round(window_s / dt)))
    f, v = box(accel, n)[n:-n:n], box(v_body, n)[n:-n:n]
    up = f.mean(axis=0) / np.linalg.norm(f.mean(axis=0))  # thrust axis in the sensor frame, mount-independent
    lat = lambda x: x - np.outer(x @ up, up)
    y, x = lat(f), lat(v)
    y, x = y - y.mean(axis=0), x - x.mean(axis=0)
    k = -np.sum(x * y) / np.sum(x * x)
    return k, 1 - np.sum((y + k * x) ** 2) / np.sum(y ** 2), float(np.sqrt(np.mean(np.sum(x ** 2, axis=1))))


if __name__ == "__main__":
    euroc = []
    for name in SPLITS["train"]:
        k, r2, speed = fit(name)
        extra = " ".join(f"r2@{w}s={fit(name, w)[1]:.2f}" for w in (0.2, 1.0))
        print(f"{name}: k={k:.3f} 1/s r2={r2:.3f} lateral_speed_rms={speed:.2f} m/s  {extra}")
        if not name.startswith("room"):
            euroc.append((k, r2))
    ks, r2s = np.array(euroc).T
    spread = ks.std() / abs(ks.mean())
    ok = np.median(r2s) >= R2_MIN and spread < K_SPREAD_MAX
    print(f"G1 EuRoC train: median r2={np.median(r2s):.3f} (need >= {R2_MIN}), k mean={ks.mean():.3f} "
          f"spread={spread:.2f} (need < {K_SPREAD_MAX}) -> {'PASS' if ok else 'FAIL'}")
