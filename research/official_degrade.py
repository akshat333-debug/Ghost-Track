"""Runs the organizers' degrade_imu.py (vendored unchanged in research/official/) on a clean sequence.

Column order is ambiguous (D-016): the script treats columns 1-3 as accel, EuRoC files put gyro there.
  order "A": script sees accel first, as its docstring says. Output is written back in EuRoC order.
  order "B": script is run on the raw EuRoC layout, so gyro columns get accel-scale corruption.
The file is written with pandas exactly as the script's CLI does, so parsing is tested on the real format.
"""
import os

import numpy as np
import pandas as pd

from research.official.degrade_imu import CONFIG, SEED, degrade

HEADER = ["#timestamp [ns]", "w_RS_S_x [rad s^-1]", "w_RS_S_y [rad s^-1]", "w_RS_S_z [rad s^-1]",
          "a_RS_S_x [m s^-2]", "a_RS_S_y [m s^-2]", "a_RS_S_z [m s^-2]"]
GAP_ROWS = 5  # shortest burst the script removes; single dropped rows are not scored as dropouts


def dev_variant(index):
    """Deterministic tuning-time variant (D-017): never the official seed or exact defaults."""
    rng = np.random.default_rng(10_000 + index)
    return {"seed": 1000 + index, "order": "AB"[index % 2],
            "max_level": float(np.exp(rng.uniform(np.log(0.5), np.log(2.0)))),
            "gamma": float(rng.uniform(1.0, 2.5)),
            "burst_len": (5, 50) if rng.random() < 0.5 else (5, 400)}


def degrade_arrays(t_ns, gyro, accel, seed=SEED, order="A", **overrides):
    """Returns (DataFrame in EuRoC column order, manifest). Input arrays are untouched."""
    cfg = dict(CONFIG, **overrides)
    gcols, acols = HEADER[1:4], HEADER[4:7]
    first, second = (acols, accel), (gcols, gyro)
    if order == "B":
        first, second = second, first
    df = pd.DataFrame({HEADER[0]: t_ns})
    for cols, vals in (first, second):
        for j, c in enumerate(cols):
            df[c] = vals[:, j]
    out, stats = degrade(df, cfg, seed)
    out = out[HEADER]
    t = out[HEADER[0]].to_numpy()
    step = np.diff(t)
    med = np.median(step[step > 0])
    cut = np.flatnonzero(step > (GAP_ROWS + 0.5) * med)
    manifest = {"seed": seed, "order": order, "config": stats["config"],
                "t_fail_ns": int(t[-1] - cfg["failure_seconds"] * 1e9) if stats["failure_frames"] else int(t[-1]),
                # no poses exist inside a gap, so the scored window is the second after it
                "dropouts_ns": [[int(t[i + 1]), int(t[i + 1]) + 10**9] for i in cut],
                "mount_xyzw": [0, 0, 0, 1.0],
                "stats": {k: v for k, v in stats.items() if k != "config"}}
    return out, manifest


def write_csv(df, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    df.to_csv(path, index=False)


def read_csv(path):
    """Degraded file back as (t_ns, gyro, accel) in EuRoC order, for array-interface baselines."""
    df = pd.read_csv(path)
    v = df.to_numpy(dtype=float)
    return df.iloc[:, 0].to_numpy(dtype=np.int64), v[:, 1:4], v[:, 4:7]
