#!/usr/bin/env python3
"""Confirms ground-truth orientation really is the IMU frame: GT-derived body rates must match the gyro.

If this fails for a sequence, scores and training labels for it are wrong.
Usage: python3 -m research.eval.check_gt train val
"""
import sys

import numpy as np
from scipy.spatial.transform import Rotation as R

from research.io_euroc import load_seq
from research.split import sequences


def check(name):
    t_ns, gyro, _, (gt_t, _, gt_q) = load_seq(name)
    step = max(1, int(round(0.05 / np.median(np.diff(gt_t * 1e-9)))))  # 50 ms smooths mocap jitter
    T = (gt_t[::step] - t_ns[0]) * 1e-9
    r = R.from_quat(gt_q[::step])
    rate = (r[:-1].inv() * r[1:]).as_rotvec() / np.diff(T)[:, None]
    mid = (T[:-1] + T[1:]) / 2
    imu_T = (t_ns - t_ns[0]) * 1e-9
    w = np.c_[[np.interp(mid, imu_T, gyro[:, i]) for i in range(3)]].T
    corr = [np.corrcoef(rate[:, i], w[:, i])[0, 1] for i in range(3)]
    bias = np.median(w - rate, axis=0)
    rms = float(np.sqrt(np.mean(np.sum((w - bias - rate) ** 2, axis=1))))
    return imu_T[-1], corr, bias, rms


if __name__ == "__main__":
    failed = []
    for split in sys.argv[1:]:
        for name in sequences(split):
            try:
                dur, corr, bias, rms = check(name)
            except FileNotFoundError:
                print(f"{name}: not downloaded")
                continue
            print(f"{name}: {dur:.0f}s corr={np.round(corr, 3)} bias={np.round(bias, 4)} rms={rms:.3f} rad/s")
            if min(corr) < 0.9:
                failed.append(name)
    if failed:
        sys.exit(f"FRAME MISMATCH: {failed}")
