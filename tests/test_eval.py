"""Self-checks for the harness on a synthetic flight. Run: python -m pytest tests -q"""
import re
from pathlib import Path

import numpy as np
import pytest
from scipy.spatial.transform import Rotation as R

from research.baselines.naive import G, hold_last, run
from research.degrade import BLIND_S, degrade
from research.eval.score import score
from research.eval.validate_format import validate
from research.io_euroc import write_imu_csv, write_tum
from research.split import sequences


def flight(seconds=60, hz=200):
    """Level body circling at 1 rad/s yaw; returns noiseless IMU plus ground truth."""
    t_ns = 1_400_000_000_000_000_000 + np.arange(seconds * hz) * (10**9 // hz)
    T = (t_ns - t_ns[0]) * 1e-9
    p = np.c_[np.cos(T) - 1, np.sin(T), 0 * T]
    q = R.from_euler("z", T).as_quat()
    acc_w = np.c_[-np.cos(T), -np.sin(T), 0 * T]
    accel = R.from_quat(q).inv().apply(acc_w + [0, 0, G])
    gyro = np.tile([0.0, 0, 1], (len(T), 1))
    return t_ns, gyro, accel, (t_ns, p, q)


def manifest(t_ns):
    return {"t_fail_ns": int(t_ns[-1000]), "dropouts_ns": [[int(t_ns[2000]), int(t_ns[2400])]],
            "mount_xyzw": [0, 0, 0, 1.0], "seed": 0, "severity": 0}


def test_perfect_estimate_scores_full():
    t, _, _, gt = flight()
    r = score(t, gt[1], gt[2], gt, manifest(t))
    assert r["ate"] < 1e-6 and r["rpe_1s"] < 1e-6 and r["blind"] < 1e-6
    assert r["proxy60"] == pytest.approx(60, abs=1e-3)


def test_blind_error_not_hidden_by_alignment():
    t, _, _, gt = flight()
    p = gt[1].copy()
    p[-999:] += [5, 0, 0]  # strictly after t_fail, which is row -1000
    r = score(t, p, gt[2], gt, manifest(t))
    assert r["blind"] == pytest.approx(5, abs=1e-6) and r["waypoint"] < 1e-6


def test_naive_recovers_clean_flight():
    # spinning in place: no linear acceleration, so gravity init and position are exact
    t, w, _, gt = flight()
    q_true = gt[2]
    a = R.from_quat(q_true).inv().apply([0, 0, G])
    p, q = run(t, w, a)
    assert (R.from_quat(q) * R.from_quat(q_true).inv()).magnitude().max() < 1e-3
    assert np.abs(p).max() < 1e-3


def test_hold_last():
    x = np.array([[1.0], [np.nan], [2.0], [np.nan]])
    assert hold_last(x).ravel().tolist() == [1, 1, 2, 2]


def test_degrade_structure():
    t, w, a, _ = flight(120)
    t2, w2, a2, m = degrade(t, w, a, seed=3)
    T = t2 * 1e-9
    bad = np.isnan(w2[:, 0])
    assert (t2 - t2[0]).max() * 1e-9 == pytest.approx((m["t_fail_ns"] - t2[0]) * 1e-9 + BLIND_S, abs=0.02)
    assert bad[T > m["t_fail_ns"] * 1e-9].all()
    for s, e in m["dropouts_ns"]:
        inside = (t2 >= s + 10**7) & (t2 < e - 10**7)
        assert bad[inside].all() and (e - s) == pytest.approx(2e9, abs=1e6)
    # same seed reproduces, different seed does not
    assert m == degrade(t, w, a, seed=3)[3] and m != degrade(t, w, a, seed=4)[3]
    assert np.isnan(w).sum() == 0, "input must stay untouched"


def test_validator(tmp_path):
    t, w, a, gt = flight(30)
    imu, est = str(tmp_path / "x/imu.csv"), str(tmp_path / "est.txt")
    write_imu_csv(imu, t, w, a)
    write_tum(est, t, gt[1], gt[2])
    validate(est, imu)
    lines = open(est).read().splitlines()
    cases = {"missing row": lines[:-1], "bad columns": [lines[0] + " 1"] + lines[1:],
             "bad quaternion": [" ".join(lines[0].split()[:4] + ["2", "0", "0", "0"])] + lines[1:],
             "swapped time": [lines[1], lines[0]] + lines[2:]}
    for name, c in cases.items():
        open(est, "w").write("\n".join(c) + "\n")
        with pytest.raises(ValueError):
            validate(est, imu)
            pytest.fail(name)


def test_heldout_guard(monkeypatch):
    monkeypatch.delenv("PF_HELDOUT", raising=False)
    with pytest.raises(PermissionError):
        sequences("heldout")


def test_nets_do_not_train_on_the_evaluation_generator():
    # D-007: sharing one degradation generator would flatter every measured number
    root = Path(__file__).resolve().parent.parent / "research"
    for f in [root / "augment.py", *(root / "nets").rglob("*.py")]:
        if f.exists():
            assert not re.search(r"\bdegrade\b", f.read_text()), f"{f} references degrade"


def test_slower_ground_truth_is_accepted():
    t, _, _, gt = flight()
    slow = (gt[0][::2], gt[1][::2], gt[2][::2])  # 100 Hz ground truth, 200 Hz estimate
    assert score(t, gt[1], gt[2], slow, manifest(t))["ate"] < 1e-6
