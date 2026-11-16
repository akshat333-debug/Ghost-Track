"""Fast constant sweeps for src/main.py on cached dev variants of train sequences (D-017). Tuning only.

python -m research.explore.tune "VEL_TAU=0.5,1,2" "POS_TAU=2,5"      # grid over the listed module constants
"""
import importlib.util
import itertools
import os
import sys
import tempfile
from multiprocessing import Pool
from pathlib import Path

import numpy as np
from evo.core import geometry
from scipy.spatial.transform import Rotation as R, Slerp

from research.io_euroc import DATA, load_seq
from research.official_degrade import degrade_arrays, dev_variant, write_csv
from research.split import SPLITS

ROOT = Path(__file__).resolve().parent.parent.parent
CACHE = DATA / "dev_cache"
N_VARIANTS = 2


def cases(split="train"):
    out = []
    for si, name in enumerate(SPLITS[split]):
        gt = None
        for i in range(N_VARIANTS):
            idx = si * 7 + i  # different variants per sequence, mixed column orders
            csv = CACHE / f"{name}_{idx}" / "imu0" / "data.csv"
            if not csv.exists():
                t_ns, gyro, accel, gt = load_seq(name)
                df, man = degrade_arrays(t_ns, gyro, accel, **dev_variant(idx))
                write_csv(df, str(csv))
                np.save(csv.parent / "fail.npy", np.array([man["t_fail_ns"]]))
            out.append((name, idx, str(csv)))
    return out


def load_main(overrides):
    spec = importlib.util.spec_from_file_location("pf_main", ROOT / "src" / "main.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    for k, v in overrides.items():
        assert hasattr(mod, k), k
        setattr(mod, k, v)
    return mod


def one(args):
    (name, idx, csv), overrides = args
    mod = load_main(overrides)
    with tempfile.TemporaryDirectory() as d:
        est = os.path.join(d, "e.txt")
        mod.run((csv, None), est)
        out = np.loadtxt(est)
    t_ns = np.loadtxt(csv, delimiter=",", skiprows=1, usecols=0, dtype=np.int64)
    fail = int(np.load(Path(csv).parent / "fail.npy")[0])
    _, _, _, (gt_t, gt_p, gt_q) = load_seq(name)
    keep = np.r_[True, np.diff(t_ns) > 0] & (t_ns >= gt_t[0]) & (t_ns <= gt_t[-1])
    T, Tg = (t_ns[keep] - gt_t[0]) * 1e-9, (gt_t - gt_t[0]) * 1e-9
    gt = np.c_[[np.interp(T, Tg, gt_p[:, i]) for i in range(3)]].T
    p = out[keep, 1:4]
    rot, tr, _ = geometry.umeyama_alignment(p.T, gt.T)
    err = (rot @ p.T).T + tr - gt
    rmse = lambda e: float(np.sqrt(np.mean(np.sum(e ** 2, axis=1)))) if len(e) else float("nan")
    blind = t_ns[keep] > fail
    flown_mean = gt[~blind].mean(axis=0)
    G, E = Slerp(Tg, R.from_quat(gt_q))(T), R.from_quat(out[keep, 4:8])
    k = 200
    rel = lambda X: X[:-k].inv() * X[k:]
    rpe_rot = np.degrees(np.median((rel(G).inv() * rel(E)).magnitude()))
    step = lambda X: X[k:] - X[:-k]
    rpe = rmse(step(p) @ rot.T - step(gt))
    return {"seq": name, "ate": rmse(err), "null": rmse(gt - flown_mean), "blind": rmse(err[blind]),
            "null_blind": rmse((gt - flown_mean)[blind]), "rpe": rpe, "rpe_null": rmse(step(gt)), "rpe_rot": rpe_rot}


def sweep(grid, split="train"):
    cs = cases(split)
    names = list(grid)
    with Pool(6) as pool:
        for combo in itertools.product(*grid.values()):
            ov = dict(zip(names, combo))
            rows = pool.map(one, [(c, ov) for c in cs])
            ratio = np.array([r["ate"] / r["null"] for r in rows])
            drone = np.array([not r["seq"].startswith("room") for r in rows])
            med = lambda k: np.nanmedian([r[k] for r in rows])
            print(" ".join(f"{k}={v:g}" for k, v in ov.items()) or "defaults",
                  f"| ATE/null median {np.median(ratio):.3f} drone {np.median(ratio[drone]):.3f} rooms {np.median(ratio[~drone]):.3f}"
                  f" worst {ratio.max():.2f} | blind/null {med('blind') / med('null_blind'):.2f}"
                  f" | rpe/null {med('rpe') / med('rpe_null'):.2f} | rot deg/s {med('rpe_rot'):.2f}", flush=True)


if __name__ == "__main__":
    grid = {}
    for arg in sys.argv[1:]:
        k, vs = arg.split("=")
        grid[k] = [float(v) for v in vs.split(",")]
    sweep(grid)
