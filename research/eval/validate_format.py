#!/usr/bin/env python3
"""Checks estimated_trajectory.txt against the input IMU CSV. Exit 1 and a reason on any violation."""
import sys

import numpy as np


def validate(est_path, imu_path):
    """Raises ValueError on the first violation of the Track 3 output spec."""
    rows = [ln.split() for ln in open(est_path) if ln.strip() and not ln.startswith("#")]
    if not rows:
        raise ValueError("no pose rows")
    if any(len(r) != 8 for r in rows):
        raise ValueError(f"row {next(i for i, r in enumerate(rows) if len(r) != 8)}: expected 8 columns")
    est = np.array(rows, dtype=float)
    if not np.isfinite(est).all():
        raise ValueError("non-finite value")
    t_in = np.loadtxt(imu_path, delimiter=",", comments="#", usecols=0, dtype=np.int64)
    if len(est) != len(t_in):
        raise ValueError(f"{len(est)} poses for {len(t_in)} IMU rows")
    if (np.diff(est[:, 0]) < 0).any():  # equal is legal: the official script duplicates rows
        raise ValueError("timestamps decreasing")
    # 1 microsecond: doubles at 1.4e9 s resolve about 0.24 microseconds
    off = np.abs(est[:, 0] - t_in * 1e-9).max()
    if off > 1e-6:
        raise ValueError(f"timestamp off by {off:.3e} s, expected ns * 1e-9")
    norm_err = np.abs(np.linalg.norm(est[:, 4:], axis=1) - 1).max()
    if norm_err > 1e-6:
        raise ValueError(f"quaternion norm off by {norm_err:.3e}")


if __name__ == "__main__":
    try:
        validate(sys.argv[1], sys.argv[2])
    except ValueError as e:
        sys.exit(f"INVALID: {e}")
    print("OK")
