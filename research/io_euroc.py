"""EuRoC-format IMU / ground-truth loading and TUM trajectory writing.

Quaternions are xyzw everywhere in memory (scipy and TUM order); EuRoC files store wxyz.
Timestamps stay int64 ns: 1.4e18 does not fit a double exactly.
"""
import glob
import os
from pathlib import Path

import numpy as np

DATA = Path(__file__).resolve().parent / "data"


def seq_dir(name):
    """'MH_01' -> .../euroc/MH_01_easy, 'room1' -> .../tumvi/dataset-room1_512_16."""
    pattern = f"tumvi/dataset-{name}_512_16" if name.startswith("room") else f"euroc/{name}_*"
    hits = [h for h in glob.glob(str(DATA / pattern)) if os.path.isdir(h)]
    if len(hits) != 1:
        raise FileNotFoundError(f"{name}: expected one directory for {pattern}, found {hits}")
    return Path(hits[0])


def _load(path):
    t_ns = np.loadtxt(path, delimiter=",", comments="#", usecols=0, dtype=np.int64)
    vals = np.loadtxt(path, delimiter=",", comments="#")[:, 1:]
    return t_ns, vals


def load_imu(path):
    """Returns t_ns, gyro (rad/s), accel (m/s^2 including gravity). Invalid rows stay NaN."""
    t_ns, v = _load(path)
    return t_ns, v[:, :3], v[:, 3:6]


def load_gt(name):
    """Returns t_ns, position, quaternion xyzw of the IMU body in the world frame."""
    d = seq_dir(name)
    euroc = d / "mav0/state_groundtruth_estimate0/data.csv"
    t_ns, v = _load(euroc if euroc.exists() else d / "mav0/mocap0/data.csv")
    return t_ns, v[:, :3], v[:, [4, 5, 6, 3]]


def load_seq(name):
    """IMU and ground truth, with the IMU cut to the time span ground truth covers."""
    t_ns, gyro, accel = load_imu(seq_dir(name) / "mav0/imu0/data.csv")
    gt = load_gt(name)
    keep = (t_ns >= gt[0][0]) & (t_ns <= gt[0][-1])
    return t_ns[keep], gyro[keep], accel[keep], gt


def write_imu_csv(path, t_ns, gyro, accel):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write("#timestamp [ns],w_RS_S_x [rad s^-1],w_RS_S_y [rad s^-1],w_RS_S_z [rad s^-1],"
                "a_RS_S_x [m s^-2],a_RS_S_y [m s^-2],a_RS_S_z [m s^-2]\n")
        for t, w, a in zip(t_ns, gyro, accel):
            f.write(f"{t},{w[0]:.17g},{w[1]:.17g},{w[2]:.17g},{a[0]:.17g},{a[1]:.17g},{a[2]:.17g}\n")


def write_tum(path, t_ns, p, q):
    q = q / np.linalg.norm(q, axis=1, keepdims=True)
    with open(path, "w") as f:
        for t, a, b in zip(t_ns, p, q):
            # integer split keeps all 9 decimals; t * 1e-9 would round
            f.write(f"{t // 10**9}.{t % 10**9:09d} {a[0]:.6f} {a[1]:.6f} {a[2]:.6f} "
                    f"{b[0]:.9f} {b[1]:.9f} {b[2]:.9f} {b[3]:.9f}\n")
