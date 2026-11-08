#!/usr/bin/env python3
"""Applies the D-007 keep rule: each fold's net is scored only on the environment it never saw.

python -m research.eval.run_cv
"""
import numpy as np

from research.baselines import eskf
from research.baselines.eskf_net import run_weights
from research.degrade import degrade
from research.eval.score import score
from research.io_euroc import DATA, load_seq
from research.split import FOLDS

SEEDS = [0, 1, 2]
METRICS = ["ate", "waypoint", "blind", "dropout"]


def keep_rule(new, base, seqs):
    """new, base: arrays of one metric per (sequence, seed). seqs labels each row."""
    med_new = [np.median(new[seqs == s]) for s in np.unique(seqs)]
    med_base = [np.median(base[seqs == s]) for s in np.unique(seqs)]
    gain = 1 - np.median(med_new) / np.median(med_base)
    wins = float(np.mean(new < base))
    worst = max(a / b - 1 for a, b in zip(med_new, med_base))
    return {"gain": gain, "wins": wins, "worst_seq_worse": worst,
            "keep": bool(gain >= 0.10 and wins >= 2 / 3 and worst <= 0.25)}


def main():
    rows = []
    for k, fold in enumerate(FOLDS):
        net = run_weights(DATA.parent / "results" / f"vel_fold{k}.pt")
        for name in fold:
            t_ns, gyro, accel, gt = load_seq(name)
            for seed in SEEDS:
                t, w, a, man = degrade(t_ns, gyro, accel, seed)
                row = {"seq": name, "seed": seed}
                row["base"] = score(t, *eskf.run(t, w, a), gt, man)
                row["net"] = score(t, *net(t, w, a), gt, man)
                rows.append(row)
                print(name, seed, " ".join(
                    f"{m}: {row['base'][m]:.2f}>{row['net'][m]:.2f} (null {row['net'].get('null_' + m, float('nan')):.2f})"
                    for m in METRICS), flush=True)
    seqs = np.array([r["seq"] for r in rows])
    for m in METRICS:
        base = np.array([r["base"][m] for r in rows])
        new = np.array([r["net"][m] for r in rows])
        print(f"KEEP {m}: {keep_rule(new, base, seqs)} median base {np.median(base):.2f} net {np.median(new):.2f}")


if __name__ == "__main__":
    main()
