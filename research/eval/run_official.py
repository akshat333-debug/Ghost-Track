#!/usr/bin/env python3
"""Scores one estimator on the organizers' degradation, through the same file interface they use.

python -m research.eval.run_official --method src/main.py --split train --variant dev --n 4
python -m research.eval.run_official --method research.baselines.eskf --split val --variant official

--method is a script path (run as `python <script> <imu.csv> <out.txt>`) or a module with run(t_ns, gyro, accel).
--variant official = script defaults with its own seed, both column orders (D-016). Report only.
--variant dev = randomized configs from official_degrade.dev_variant. The only variant allowed for tuning (D-017).
--variant seeds = script defaults with seeds 1..n instead of 42, both column orders. Report only (D-030).
"""
import argparse
import importlib
import json
import subprocess
import sys
import tempfile

import numpy as np

from research.eval.score import score
from research.eval.validate_format import validate
from research.io_euroc import load_seq, write_tum
from research.official_degrade import degrade_arrays, dev_variant, read_csv, write_csv
from research.split import sequences

KEYS = ["ate", "null_ate", "rpe_1s", "rpe_rot_deg", "waypoint20", "blind_full", "blind", "null_blind",
        "dropout_full", "ate_rot_deg"]


def estimate(method, csv, est):
    """Writes the estimate to `est` and returns (p, q) per input row."""
    if method.endswith(".py"):
        subprocess.run([sys.executable, method, csv, est], check=True)
        out = np.loadtxt(est)
        return out[:, 1:4], out[:, 4:8]
    t, w, a = read_csv(csv)
    dead = ~(w.any(axis=1) | a.any(axis=1))  # adapter: array baselines mark invalid rows with NaN, the script with 0
    w[dead], a[dead] = np.nan, np.nan
    p, q = importlib.import_module(method).run(t, w, a)
    write_tum(est, t, p, q)
    return p, q


def variants(kind, n):
    if kind == "official":
        return [{"order": "A"}, {"order": "B"}]
    if kind == "seeds":
        return [{"seed": s, "order": o} for s in range(1, n + 1) for o in "AB"]
    return [dev_variant(i) for i in range(n)]


def evaluate(method, split, kind, n, only=None):
    rows = []
    for name in [s for s in sequences(split) if not only or s in only]:
        t_ns, gyro, accel, gt = load_seq(name)
        for i, var in enumerate(variants(kind, n)):
            df, man = degrade_arrays(t_ns, gyro, accel, **var)
            with tempfile.TemporaryDirectory() as d:
                csv, est = f"{d}/imu0/data.csv", f"{d}/estimated_trajectory.txt"
                write_csv(df, csv)
                p, q = estimate(method, csv, est)
                validate(est, csv)
            r = score(df.iloc[:, 0].to_numpy(), p, q, gt, man)
            rows.append({"seq": name, "variant": i, "order": man["order"], **r})
            print(name, i, man["order"], " ".join(f"{k}={r[k]:.3f}" for k in KEYS), flush=True)
    return rows


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--method", required=True)
    ap.add_argument("--split", default="train")
    ap.add_argument("--variant", choices=["dev", "official", "seeds"], default="dev")
    ap.add_argument("--n", type=int, default=4, help="dev variants per sequence")
    ap.add_argument("--seqs", nargs="+", help="subset of the split")
    ap.add_argument("--out", help="write per-run rows as JSON, for paired keep-rule comparisons")
    a = ap.parse_args()
    if a.variant in ("official", "seeds") and a.split == "train":
        sys.exit("official config is report-only: use val or held-out (D-017)")
    rows = evaluate(a.method, a.split, a.variant, a.n, a.seqs)
    for stat in (np.nanmean, np.nanmedian):
        print(stat.__name__[3:].upper(), " ".join(f"{k}={stat([r[k] for r in rows]):.3f}" for k in KEYS))
    if a.out:
        json.dump(rows, open(a.out, "w"), indent=1)
