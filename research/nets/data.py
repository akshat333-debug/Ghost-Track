"""Builds velocity-net training batches from sequences, with no sequence-level leakage (D-007)."""
import numpy as np
from scipy.spatial.transform import Rotation as R, Slerp

from research.augment import corrupt
from research.io_euroc import load_seq
from research.nets.vel_net import ACCEL_SCALE, GYRO_SCALE, WINDOW

G = 9.81
TILT_SCALE = np.deg2rad(2.0)  # exponential: matches ESKF tilt error on train (p50 about 1 deg, p95 about 7)


class Sequence:
    """IMU, attitude and smoothed velocity, all on IMU timestamps."""

    def __init__(self, name):
        t_ns, gyro, accel, (gt_t, gt_p, gt_q) = load_seq(name)
        T = (t_ns - gt_t[0]) * 1e-9
        Tg = (gt_t - gt_t[0]) * 1e-9
        self.name, self.gyro, self.accel = name, gyro, accel
        self.C = Slerp(Tg, R.from_quat(gt_q))(T).as_matrix()
        p = np.c_[[np.interp(T, Tg, gt_p[:, i]) for i in range(3)]].T
        box = np.ones(11) / 11  # 55 ms: mocap differentiation is too noisy unsmoothed
        p = np.c_[[np.convolve(np.pad(p[:, i], 5, mode="edge"), box, "valid") for i in range(3)]].T
        self.v = np.gradient(p, T, axis=0)
        self.n = len(T)


def make_batch(seqs, size, rng):
    """Returns x (B, 7, WINDOW) and target velocity (B, 3), both yaw-randomized together."""
    which = rng.integers(0, len(seqs), size)
    gyro, accel, C, v = [np.zeros((size, WINDOW, 3)) for _ in range(2)] + [np.zeros((size, WINDOW, 3, 3)), np.zeros((size, 3))]
    for b, s in enumerate(which):
        q = seqs[s]
        end = rng.integers(WINDOW, q.n)
        idx = range(end - WINDOW + 1, end + 1)
        gyro[b], accel[b], C[b], v[b] = q.gyro[idx], q.accel[idx], q.C[idx], q.v[end]
    return _features(gyro, accel, C, v, rng)


def _features(gyro, accel, C, v, rng):
    g, a, mask = corrupt(gyro, accel, rng)
    b = len(g)
    tilt = rng.exponential(TILT_SCALE, b)
    az = rng.uniform(0, 2 * np.pi, b)
    err = R.from_rotvec(np.c_[np.cos(az) * tilt, np.sin(az) * tilt, 0 * tilt]).as_matrix()[:, None]
    yaw = R.from_euler("z", rng.uniform(0, 2 * np.pi, b)).as_matrix()
    W = yaw[:, None] @ err @ C

    return to_input(W, g, a, mask), np.einsum("bij,bj->bi", yaw, v).astype(np.float32)


def to_input(W, g, a, mask):
    """Net input from body-to-world attitude W (B, N, 3, 3). Shared by training and the estimator."""
    gw = np.einsum("bnij,bnj->bni", W, g)
    aw = np.einsum("bnij,bnj->bni", W, a) - mask[..., None] * np.array([0, 0, G])
    x = np.concatenate([gw / GYRO_SCALE, aw / ACCEL_SCALE, mask[..., None]], axis=2).transpose(0, 2, 1)
    return x.astype(np.float32)
