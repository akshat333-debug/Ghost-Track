#!/usr/bin/env python3
"""Gate G1b (D-019, amended by D-022): is body-lateral specific force proportional to body velocity in flight?

Rotor drag makes a multirotor's accelerometer read -k * v in the plane normal to thrust (Leishman et al. 2014).
Fit on clean data with ground truth, per 15 s segment: f_lat = -k * v_lat + bias. Only segments that an
IMU-only test calls rotor flight count (lateral specific-force rms below FLIGHT_RMS), because the estimator
can use the measurement only where it can recognise flight by itself.
Pass: median segment R^2 >= 0.3 and k spread across sequences < 30%, on EuRoC train without MH_02
(MH_02 was looked at while defining this, so it cannot confirm it).

python -m research.eval.drag_gate
"""
import numpy as np
from scipy.spatial.transform import Rotation as R, Slerp

from research.io_euroc import load_seq
from research.split import SPLITS

R2_MIN, K_SPREAD_MAX = 0.3, 0.3
WINDOW_S, SEGMENT_S = 0.5, 15.0
FLIGHT_RMS = 0.25  # m/s^2; MH_02: flight segments 0.05 to 0.20, handheld shaking 0.4 to 1.9
EXPLORED = {"MH_02"}


def box(x, n):
    k = np.ones(n) / n
    return np.c_[[np.convolve(x[:, i], k, "same") for i in range(x.shape[1])]].T


def segments(name):
    """Per segment: (lateral force rms, k, R^2, lateral speed rms)."""
    t_ns, _, accel, (gt_t, gt_p, gt_q) = load_seq(name)
    T, Tg = (t_ns - gt_t[0]) * 1e-9, (gt_t - gt_t[0]) * 1e-9
    rot = Slerp(Tg, R.from_quat(gt_q))(T)
    p = np.c_[[np.interp(T, Tg, gt_p[:, i]) for i in range(3)]].T
    v_body = rot.inv().apply(np.gradient(box(p, 11), T, axis=0))
    n = max(1, int(round(WINDOW_S / np.median(np.diff(T)))))
    f, v, tt = box(accel, n)[n:-n:n], box(v_body, n)[n:-n:n], T[n:-n:n]
    out = []
    for start in np.arange(0, tt[-1] - SEGMENT_S, SEGMENT_S):
        m = (tt >= start) & (tt < start + SEGMENT_S)
        up = f[m].mean(axis=0) / np.linalg.norm(f[m].mean(axis=0))  # thrust axis in the sensor frame
        lat = lambda x: x - np.outer(x @ up, up)
        y, x = lat(f[m]), lat(v[m])
        y, x = y - y.mean(axis=0), x - x.mean(axis=0)
        k = -np.sum(x * y) / np.sum(x * x)
        out.append((np.sqrt(np.mean(np.sum(y ** 2, axis=1))), k, 1 - np.sum((y + k * x) ** 2) / np.sum(y ** 2),
                    np.sqrt(np.mean(np.sum(x ** 2, axis=1)))))
    return np.array(out)


if __name__ == "__main__":
    ks, r2s = [], []
    for name in SPLITS["train"]:
        try:
            seg = segments(name)
        except FileNotFoundError:
            print(f"{name}: not downloaded")
            continue
        fly = seg[seg[:, 0] < FLIGHT_RMS]
        line = f"{name}: {len(fly)}/{len(seg)} segments pass the flight test"
        if len(fly):
            line += f", k median={np.median(fly[:, 1]):.3f} 1/s, R2 median={np.median(fly[:, 2]):.3f}"
        print(line + ("  (explored, not counted)" if name in EXPLORED else ""))
        if not name.startswith("room") and name not in EXPLORED and len(fly):
            ks.append(np.median(fly[:, 1]))
            r2s.extend(fly[:, 2])
    if ks:
        spread = np.std(ks) / abs(np.mean(ks))
        ok = np.median(r2s) >= R2_MIN and spread < K_SPREAD_MAX
        print(f"G1b EuRoC train: median segment R2={np.median(r2s):.3f} (need >= {R2_MIN}), k mean={np.mean(ks):.3f} "
              f"spread={spread:.2f} (need < {K_SPREAD_MAX}) -> {'PASS' if ok else 'FAIL'}")
