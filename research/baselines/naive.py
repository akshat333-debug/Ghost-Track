"""L0: plain strapdown integration. The floor every other layer has to beat."""
import numpy as np
from scipy.spatial.transform import Rotation as R

G = 9.81


def hold_last(x):
    """Replaces NaN rows with the previous valid row."""
    good = ~np.isnan(x[:, 0])
    if not good.any():
        raise ValueError("no valid IMU rows")
    idx = np.maximum.accumulate(np.where(good, np.arange(len(x)), good.argmax()))
    return x[idx]


def run(t_ns, gyro, accel):
    """Returns position and xyzw quaternion per row, in a gravity-aligned frame starting at origin."""
    T = (t_ns - t_ns[0]) * 1e-9
    w, f = hold_last(gyro), hold_last(accel)
    first = (T < 1.0) & ~np.isnan(accel[:, 0])
    a0 = np.nanmean(accel[first], axis=0)
    rot, _ = R.align_vectors([[0, 0, 1.0]], [a0 / np.linalg.norm(a0)])

    dt = np.diff(T, prepend=T[0])
    steps = R.from_rotvec(w * dt[:, None]).as_matrix()
    C = rot.as_matrix()
    v, pos = np.zeros(3), np.zeros(3)
    gravity = np.array([0, 0, G])
    p_out, C_out = np.zeros((len(T), 3)), np.zeros((len(T), 3, 3))
    for i in range(len(T)):
        if i:
            a = C @ f[i] - gravity
            pos = pos + v * dt[i] + 0.5 * a * dt[i] ** 2
            v = v + a * dt[i]
            C = C @ steps[i]
        p_out[i], C_out[i] = pos, C
    return p_out, R.from_matrix(C_out).as_quat()
