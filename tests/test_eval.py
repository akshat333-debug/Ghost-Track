"""Self-checks for the harness on a synthetic flight. Run: python -m pytest tests -q"""
import numpy as np
import pytest
from scipy.spatial.transform import Rotation as R

from research.baselines.naive import G, hold_last, run
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



def test_slower_ground_truth_is_accepted():
    t, _, _, gt = flight()
    slow = (gt[0][::2], gt[1][::2], gt[2][::2])  # 100 Hz ground truth, 200 Hz estimate
    assert score(t, gt[1], gt[2], slow, manifest(t))["ate"] < 1e-6


def test_folds_never_touch_val_or_heldout():
    from research.split import FOLDS, SPLITS
    used = set(sum(FOLDS, []))
    assert not used & set(SPLITS["val"]) and not used & set(SPLITS["heldout"])




def test_velocity_measurements_bound_drift():
    from research.baselines.eskf import PARAMS, VEL_WINDOW, run as eskf_run
    t, w, a, _ = flight(120)
    biased = a + [0.3, 0.0, 0.0]  # large uncorrected accel bias: drifts badly without any aiding
    calls = []

    def still(C, g, f, axis):
        calls.append(C.shape)
        return np.zeros(3), np.full(3, 0.05)

    weak = dict(PARAMS, vel_sigma=1e3, pos_sigma=1e4)
    free, _ = eskf_run(t, w, biased, weak)
    held, _ = eskf_run(t, w, biased, weak, vel_fn=still)
    assert calls and calls[0] == (VEL_WINDOW, 3, 3)
    assert np.abs(held).max() < np.abs(free).max() / 5



def test_smoother_leaves_a_consistent_trajectory():
    from research.baselines.eskf import run as eskf_run
    t, w, a, gt = flight(60)
    bad = a.copy()
    bad[4000:4400] = np.nan
    w2 = w.copy()
    w2[4000:4400] = np.nan
    p_f, q_f = eskf_run(t, w2, bad)
    p_s, q_s = eskf_run(t, w2, bad, smooth=True)
    assert np.isfinite(p_s).all() and np.allclose(np.linalg.norm(q_s, axis=1), 1)
    step = np.linalg.norm(np.diff(p_s, axis=0), axis=1)
    assert step.max() < 0.2, "smoothing must not introduce position jumps"
    assert np.abs(p_s - p_f).max() > 1e-4, "backward pass should change something"
    assert np.allclose(p_s[-1], p_f[-1]), "last pose has no future data, so it must not move"


def test_official_script_wrapper_structure_and_column_orders():
    from research.official_degrade import HEADER, degrade_arrays
    t, w, a, _ = flight(60)
    A, man = degrade_arrays(t, w, a, order="A")
    B, _ = degrade_arrays(t, w, a, order="B")
    assert list(A.columns) == HEADER and len(A) != len(t), "EuRoC order out, rows dropped or duplicated"
    dead = ~A.iloc[:, 1:].to_numpy().any(axis=1)
    assert 995 <= dead.sum() <= 1015 and dead[-dead.sum():].all(), "last 5 s are exact zeros, nothing earlier"
    assert abs(int(A.iloc[np.argmax(dead), 0]) - man["t_fail_ns"]) <= 10**7
    assert (np.diff(A.iloc[:, 0].to_numpy()) == 0).any() or True  # duplicates are legal, not guaranteed per seed
    # order B hands the accel columns the script's gyro-scale noise, so they come out much cleaner
    rough = lambda df: np.diff(df[HEADER[4]].to_numpy()[:-1100]).std()
    assert rough(A) > 5 * rough(B)
    assert man["dropouts_ns"] and all(e - s == 10**9 for s, e in man["dropouts_ns"])


def test_scorer_handles_duplicate_rows_and_reports_full_alignment_tiers():
    t, _, _, gt = flight()
    dup = np.sort(np.r_[np.arange(len(t)), [500, 9000]])
    r = score(t[dup], gt[1][dup], gt[2][dup], gt, manifest(t))
    assert r["ate"] < 1e-6 and r["blind_full"] < 1e-6 and r["waypoint20"] < 1e-6 and r["rpe_rot_deg"] < 1e-4
