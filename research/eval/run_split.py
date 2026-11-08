#!/usr/bin/env python3
"""Runs one method over a split: degrade, estimate, validate format, score, print a summary.

python -m research.eval.run_split --method research.baselines.naive --split val --seeds 0 1 2
"""
import argparse
import importlib
import tempfile
from pathlib import Path

import numpy as np

from research.degrade import degrade
from research.eval.score import score
from research.eval.validate_format import validate
from research.io_euroc import load_seq, write_imu_csv, write_tum
from research.split import sequences

KEYS = ["ate", "ate_origin", "ate_rot_deg", "rpe_1s", "waypoint", "blind", "blind_end", "dropout", "null_ate", "null_blind", "proxy60"]


def evaluate(run, split, seeds, severity=1.0):
    results = []
    for name in sequences(split):
        t_ns, gyro, accel, gt = load_seq(name)
        for seed in seeds:
            t, w, a, man = degrade(t_ns, gyro, accel, seed, severity)
            p, q = run(t, w, a)
            with tempfile.TemporaryDirectory() as d:
                imu, est = f"{d}/mav0/imu0/data.csv", f"{d}/est.txt"
                write_imu_csv(imu, t, w, a)
                write_tum(est, t, p, q)
                validate(est, imu)
            r = score(t, p, q, gt, man)
            results.append({"seq": name, "seed": seed, **r})
            print(name, seed, " ".join(f"{k}={r[k]:.3f}" for k in KEYS), flush=True)
    return results


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--method", required=True)
    ap.add_argument("--split", default="val")
    ap.add_argument("--seeds", type=int, nargs="+", default=[0, 1, 2])
    ap.add_argument("--severity", type=float, default=1.0)
    a = ap.parse_args()
    res = evaluate(importlib.import_module(a.method).run, a.split, a.seeds, a.severity)
    print("MEAN", " ".join(f"{k}={np.mean([r[k] for r in res]):.3f}" for k in KEYS))
