"""Degradation simulator mirroring the Track 3 brief. Replace or validate against the organizer script.

Escalating noise and bias drift, 2 s dropouts, unknown sensor mounting, then total IMU failure
at a random mid-flight time followed by 5 s of blind rows. The sequence is cut at failure + 5 s
so the blind window is mid-flight rather than the easy end-of-sequence landing.

shortcut: invalid rows are written as NaN, upgrade once organizers say how dropouts appear (Q6, Q7).
"""
import argparse
import json

import numpy as np
from scipy.spatial.transform import Rotation as R

from research.io_euroc import DATA, load_seq, write_imu_csv
from research.split import SPLITS, sequences

BLIND_S = 5.0
DROPOUT_S = 2.0
# EuRoC ADIS16448 datasheet-style densities from the dataset's sensor.yaml
GYRO_NOISE, ACCEL_NOISE = 1.7e-4, 2.0e-3   # per sqrt(Hz)
GYRO_WALK, ACCEL_WALK = 1.9e-5, 3.0e-3     # per sqrt(Hz) * s^-1


def degrade(t_ns, gyro, accel, seed, severity=1.0):
    """Returns (t_ns, gyro, accel, manifest). Input arrays are not modified."""
    rng = np.random.default_rng(seed)
    T = (t_ns - t_ns[0]) * 1e-9
    if T[-1] < 30:
        raise ValueError(f"sequence too short to degrade: {T[-1]:.1f} s")
    t_fail = rng.uniform(0.6, 0.9) * (T[-1] - BLIND_S)
    keep = T <= t_fail + BLIND_S
    t_ns, gyro, accel, T = t_ns[keep], gyro[keep].copy(), accel[keep].copy(), T[keep]
    n = len(T)
    dt = np.median(np.diff(T))
    f = np.clip(T / t_fail, 0, 1) ** 2  # jamming grows with mission time

    mount = R.random(random_state=int(rng.integers(2**31)))
    gyro, accel = mount.apply(gyro), mount.apply(accel)

    sqrt_hz = np.sqrt(1 / dt)
    noise = (severity * (1 + 9 * f))[:, None]
    gyro += GYRO_NOISE * sqrt_hz * noise * rng.standard_normal((n, 3))
    accel += ACCEL_NOISE * sqrt_hz * noise * rng.standard_normal((n, 3))

    walk = (severity * (1 + 29 * f) * np.sqrt(dt))[:, None]
    gyro += rng.normal(0, 0.01, 3) + np.cumsum(GYRO_WALK * walk * rng.standard_normal((n, 3)), axis=0)
    accel += rng.normal(0, 0.05, 3) + np.cumsum(ACCEL_WALK * walk * rng.standard_normal((n, 3)), axis=0)

    # three candidate slots keep windows disjoint without rejection sampling
    slots = np.linspace(0.2, 0.95, 4) * t_fail
    count = int(rng.integers(1, 4))
    chosen = sorted(rng.choice(3, count, replace=False))
    dropouts = []
    bad = T > t_fail
    for s in chosen:
        start = rng.uniform(slots[s], slots[s + 1] - DROPOUT_S)
        bad |= (T >= start) & (T < start + DROPOUT_S)
        dropouts.append([int(t_ns[0] + start * 1e9), int(t_ns[0] + (start + DROPOUT_S) * 1e9)])
    gyro[bad] = np.nan
    accel[bad] = np.nan

    manifest = {"seed": seed, "severity": severity,
                "t_fail_ns": int(t_ns[0] + t_fail * 1e9),
                "dropouts_ns": dropouts,
                "mount_xyzw": mount.as_quat().tolist()}
    return t_ns, gyro, accel, manifest


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--seq", required=True)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--severity", type=float, default=1.0)
    a = ap.parse_args()
    split = next(s for s, names in SPLITS.items() if a.seq in names)
    sequences(split)  # enforces the held-out guard
    t_ns, gyro, accel, _ = load_seq(a.seq)
    t_ns, gyro, accel, man = degrade(t_ns, gyro, accel, a.seed, a.severity)
    out = DATA / "degraded" / f"{a.seq}_s{a.seed}"
    write_imu_csv(str(out / "mav0/imu0/data.csv"), t_ns, gyro, accel)
    (out / "manifest.json").write_text(json.dumps(man, indent=1))
    print(out)
