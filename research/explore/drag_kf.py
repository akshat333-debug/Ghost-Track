"""Prototype (numpy): joint drag fusion at 5 Hz nodes on top of src/main.py's attitude (D-024 follow-up).

Horizontal state [p(2), v(2), da(2), beta(2)]: da = slow world-acceleration error (tilt), beta = accel bias in the
plane normal to thrust. Drag measurement: -R f_lat / k = v - R E beta / k. Weak zero-velocity and position
priors make it fall back to a leaky integrator when the drag measurement is gated out. RTS smoothed.

python -m research.explore.drag_kf            # prototype vs main.py on cached dev variants
"""
import os
import sys
import tempfile
from multiprocessing import Pool

import numpy as np
from evo.core import geometry
from scipy.spatial.transform import Rotation as R

from research.explore.tune import cases, load_main
from research.io_euroc import load_seq

P = dict(k=0.177, node=0.2, sig_z=0.3, gate=30.0, q_da=0.02, q_beta=0.002, sig_v0=0.3, sig_p=1.0, sig_v0_fly=1.0, sig_p_fly=3.0, trust_rate=0.05, q_v=0.05,
         blind_tau=1.0, da0=0.3, beta0=0.3)


def node_data(csv, mod, prm):
    with tempfile.TemporaryDirectory() as d:
        est = os.path.join(d, "e.txt")
        cfg = mod.run((csv, None), est)
        out = np.loadtxt(est)
    raw = np.loadtxt(csv, delimiter=",", skiprows=1)
    t_ns = np.loadtxt(csv, delimiter=",", skiprows=1, usecols=0, dtype=np.int64)
    acc = raw[:, 1 + cfg["acc"]:4 + cfg["acc"]] * cfg["unit"]
    ok = raw[:, 1:].any(axis=1) & np.r_[True, np.diff(t_ns) > 0]
    med = acc.copy()
    idx = np.flatnonzero(ok)
    med[idx[1:-1]] = np.median(np.stack([acc[idx[:-2]], acc[idx[1:-1]], acc[idx[2:]]]), axis=0)
    T = (t_ns - t_ns[0]) * 1e-9
    dt = np.diff(T, prepend=T[0])
    use = ok & (dt < 0.1)
    rot = R.from_quat(out[:, 4:8])
    node = np.floor(T / prm["node"]).astype(int)
    n = node[-1] + 1
    up = med[use].mean(axis=0)
    up /= np.linalg.norm(up)
    e1 = np.cross(up, [1.0, 0, 0] if abs(up[0]) < 0.9 else [0, 1.0, 0])
    e1 /= np.linalg.norm(e1)
    E = np.c_[e1, np.cross(up, e1)]
    lat_w = rot.apply(med - np.outer(med @ up, up))
    a_w = rot.apply(med) - [0, 0, cfg["g"]]
    cnt = np.bincount(node[use], minlength=n)
    acc_sum = lambda x: np.c_[[np.bincount(node[use], weights=x[use, i], minlength=n) for i in range(x.shape[1])]].T
    dV = acc_sum(a_w * dt[:, None])
    m = acc_sum(lat_w) / np.maximum(cnt, 1)[:, None]
    RE = rot.as_matrix() @ E                                   # rows x 3 x 2
    REn = np.stack([acc_sum(RE[:, :, j]) for j in range(2)], axis=2) / np.maximum(cnt, 1)[:, None, None]
    return dict(t_ns=t_ns, T=T, out=out, n=n, cnt=cnt, dV=dV, m=m, RE=REn, full=cnt >= 0.5 * np.median(cnt[cnt > 0]))


def smooth(nd, prm):
    n, dt, k = nd["n"], prm["node"], prm["k"]
    x = np.zeros(8)
    Pm = np.diag([1e-4] * 2 + [0.25] * 2 + [prm["da0"] ** 2] * 2 + [prm["beta0"] ** 2] * 2)
    Q = np.diag([0, 0] + [prm["q_v"] ** 2 * dt] * 2 + [prm["q_da"] ** 2 * dt] * 2 + [prm["q_beta"] ** 2 * dt] * 2)
    xs, Ps, xp, Pp, Fs = [], [], [], [], []
    last = np.flatnonzero(nd["cnt"] > 0)[-1]
    used, trust = 0, 0.0
    I2, Z2 = np.eye(2), np.zeros((2, 2))
    for i in range(n):
        F = np.eye(8)
        F[0:2, 2:4] = I2 * dt
        u = np.zeros(8)
        if nd["cnt"][i] > 0:
            F[2:4, 4:6] = -I2 * dt
            u[2:4] = nd["dV"][i, :2]
            u[0:2] = 0.5 * nd["dV"][i, :2] * dt
        elif i > last:
            F[2:4, 2:4] = I2 * np.exp(-dt / prm["blind_tau"])
        x = F @ x + u
        Pm = F @ Pm @ F.T + Q
        xp.append(x.copy()); Pp.append(Pm.copy()); Fs.append(F)

        def upd(z, H, sig, gate=None):
            nonlocal x, Pm
            r = z - H @ x
            S = H @ Pm @ H.T + np.eye(len(z)) * sig ** 2
            if gate is not None and r @ np.linalg.solve(S, r) > gate:
                return False
            K = np.linalg.solve(S, H @ Pm).T
            x = x + K @ r
            Pm = (np.eye(8) - K @ H) @ Pm
            return True
        got = False
        if nd["full"][i]:
            H = np.hstack([Z2, I2, Z2, -nd["RE"][i, :2, :] / k])
            got = upd(-nd["m"][i, :2] / k, H, prm["sig_z"], prm["gate"])
            used += got
        trust += prm["trust_rate"] * ((1.0 if got else 0.0) - trust)  # recent share of accepted drag measurements
        w = min(1.0, max(0.0, (trust - 0.5) * 4))                     # priors loosen only in sustained rotor flight
        if i <= last:
            upd(np.zeros(2), np.hstack([Z2, I2, Z2, Z2]), prm["sig_v0"] * (1 - w) + prm["sig_v0_fly"] * w)
        upd(np.zeros(2), np.hstack([I2, Z2, Z2, Z2]), prm["sig_p"] * (1 - w) + prm["sig_p_fly"] * w)
        xs.append(x.copy()); Ps.append(Pm.copy())
    xs = np.array(xs)
    for i in range(n - 2, -1, -1):
        G = np.linalg.solve(Pp[i + 1] + 1e-9 * np.eye(8), Fs[i + 1] @ Ps[i]).T
        xs[i] = xs[i] + G @ (xs[i + 1] - xp[i + 1])
    return xs, used / max(1, nd["full"].sum())


def positions(csv, prm, mod):
    nd = node_data(csv, mod, prm)
    xs, frac = smooth(nd, prm)
    tn = (np.arange(nd["n"]) + 1) * prm["node"]
    p = nd["out"][:, 1:4].copy()
    for j in range(2):
        p[:, j] = np.interp(nd["T"], tn, xs[:, j])
    return nd["t_ns"], p, nd["out"], frac


def one(args):
    (name, idx, csv), prm = args
    mod = load_main({})
    t_ns, p, out, frac = positions(csv, prm, mod)
    fail = int(np.load(os.path.join(os.path.dirname(csv), "fail.npy"))[0])
    _, _, _, (gt_t, gt_p, _) = load_seq(name)
    keep = np.r_[True, np.diff(t_ns) > 0] & (t_ns >= gt_t[0]) & (t_ns <= gt_t[-1])
    gt = np.c_[[np.interp(t_ns[keep], gt_t, gt_p[:, i]) for i in range(3)]].T
    blind = t_ns[keep] > fail
    rmse = lambda e: float(np.sqrt(np.mean(np.sum(e ** 2, axis=1)))) if len(e) else float("nan")
    res = {"seq": name, "idx": idx, "frac": frac, "null": rmse(gt - gt[~blind].mean(axis=0)),
           "null_blind": rmse((gt - gt[~blind].mean(axis=0))[blind])}
    for lab, q in (("kf", p[keep]), ("base", out[keep, 1:4])):
        rot, tr, _ = geometry.umeyama_alignment(q.T, gt.T)
        err = (rot @ q.T).T + tr - gt
        res[lab], res[lab + "_blind"] = rmse(err), rmse(err[blind])
    return res


def report(prm, label="", show=False, split="train"):
    with Pool(6) as pool:
        rows = pool.map(one, [(c, prm) for c in cases(split)])
    drone = np.array([not r["seq"].startswith("room") for r in rows])
    ratio = np.array([r["kf"] / r["base"] for r in rows])
    vs_null = np.array([r["kf"] / r["null"] for r in rows])
    if show:
        for r in rows:
            print(f"  {r['seq']} {r['idx']}: null {r['null']:.2f} base {r['base']:.2f} kf {r['kf']:.2f} "
                  f"| blind null {r['null_blind']:.2f} base {r['base_blind']:.2f} kf {r['kf_blind']:.2f} | drag used {r['frac']:.2f}")
    print(f"{label} kf/base median {np.median(ratio):.3f} drone {np.median(ratio[drone]):.3f} rooms {np.median(ratio[~drone]):.3f} "
          f"worst {ratio.max():.2f} wins {np.mean(ratio < 1):.2f} | kf/null drone {np.median(vs_null[drone]):.3f} "
          f"| blind kf/base {np.nanmedian([r['kf_blind'] / r['base_blind'] for r in rows]):.2f}", flush=True)
    return rows


if __name__ == "__main__":
    import itertools
    grid = {a.split("=")[0]: [float(v) for v in a.split("=")[1].split(",")] for a in sys.argv[1:]}
    if not grid:
        report(P, "default", show=True)
    for combo in itertools.product(*grid.values()):
        ov = dict(zip(grid, combo))
        report(dict(P, **ov), " ".join(f"{k}={v:g}" for k, v in ov.items()) + " |")
