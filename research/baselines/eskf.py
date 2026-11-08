"""L1: error-state Kalman filter on IMU alone.

With no external sensor, position and velocity are corrected only by physical priors: gravity
direction (tilt), stillness, and bounded indoor motion. Attitude error is body-frame (right) perturbation.
State order in the error vector: dp, dv, dtheta, dbg, dba.

Interface matches naive.run, so the manifest (failure time, dropouts) cannot leak into the estimator.
"""
import numpy as np
from scipy.spatial.transform import Rotation as R

G = 9.81
UPDATE_EVERY = 20  # samples; pseudo-measurements run at about 10 Hz
STATIC_WINDOW = 100  # samples

PARAMS = {
    "gyro_noise": 1.7e-4, "accel_noise": 2.0e-3,   # per sqrt(Hz)
    "gyro_walk": 1.9e-5, "accel_walk": 3.0e-3,     # per sqrt(Hz) * s^-1
    "tilt_sigma": 0.5,      # m/s^2, gravity measurement while moving
    "vel_sigma": 1.5,       # m/s, bounded-motion prior per update
    "pos_sigma": 15.0,      # m, indoor-extent prior per update
    "static_vel_sigma": 0.1,
    "static_ratio": 3.0,    # window variance / high-frequency noise variance
    "blind_tau": 2.0,       # s, velocity decay once the IMU has failed
}


def skew(v):
    return np.array([[0, -v[2], v[1]], [v[2], 0, -v[0]], [-v[1], v[0], 0]])


def exp_so3(phi):
    a = np.linalg.norm(phi)
    S = skew(phi)
    if a < 1e-8:
        return np.eye(3) + S
    return np.eye(3) + np.sin(a) / a * S + (1 - np.cos(a)) / a**2 * S @ S


class Filter:
    def __init__(self, params):
        self.c = params
        self.p, self.v = np.zeros(3), np.zeros(3)
        self.C = np.eye(3)
        self.bg, self.ba = np.zeros(3), np.zeros(3)
        self.P = np.diag([1e-6] * 3 + [0.5**2] * 3 + [0.05**2] * 3 + [0.02**2] * 3 + [0.2**2] * 3)

    def propagate(self, w_m, f_m, dt, scale):
        c = self.c
        w, f = w_m - self.bg, f_m - self.ba
        acc = self.C @ f - [0, 0, G]
        Cf = self.C @ skew(f)
        F = np.eye(15)
        F[:3, 3:6] = np.eye(3) * dt
        F[3:6, 6:9] = -Cf * dt
        F[3:6, 12:15] = -self.C * dt
        F[6:9, 6:9] = np.eye(3) - skew(w) * dt
        F[6:9, 9:12] = -np.eye(3) * dt
        q = np.r_[np.zeros(3), np.full(3, (c["accel_noise"] * scale) ** 2),
                  np.full(3, (c["gyro_noise"] * scale) ** 2), np.full(3, (c["gyro_walk"] * scale) ** 2),
                  np.full(3, (c["accel_walk"] * scale) ** 2)] * dt
        self.P = F @ self.P @ F.T
        self.P[np.diag_indices(15)] += q
        self.p = self.p + self.v * dt + 0.5 * acc * dt**2
        self.v = self.v + acc * dt
        self.C = self.C @ exp_so3(w * dt)

    def coast(self, dt, decay, attitude_q=1e-4, accel_q=1.0):
        """No IMU this step: keep moving on current velocity and grow uncertainty."""
        self.p = self.p + self.v * dt
        self.v = self.v * decay
        F = np.eye(15)
        F[:3, 3:6] = np.eye(3) * dt
        self.P = F @ self.P @ F.T
        self.P[np.diag_indices(15)] += np.r_[np.zeros(3), np.full(3, accel_q), np.full(3, attitude_q),
                                             np.zeros(6)] * dt

    def update(self, r, H, sigma):
        S = H @ self.P @ H.T + np.eye(len(r)) * sigma**2
        K = np.linalg.solve(S, H @ self.P).T
        dx = K @ r
        I_KH = np.eye(15) - K @ H
        self.P = I_KH @ self.P @ I_KH.T + K @ K.T * sigma**2
        self.p = self.p + dx[:3]
        self.v = self.v + dx[3:6]
        self.C = self.C @ exp_so3(dx[6:9])
        self.bg = self.bg + dx[9:12]
        self.ba = self.ba + dx[12:15]

    def update_tilt(self, f_mean, sigma):
        up = self.C.T @ [0, 0, G]
        H = np.zeros((3, 15))
        H[:, 6:9] = skew(up)
        H[:, 12:15] = np.eye(3)
        self.update(f_mean - self.ba - up, H, sigma)

    def update_velocity(self, sigma):
        H = np.zeros((3, 15))
        H[:, 3:6] = np.eye(3)
        self.update(-self.v, H, sigma)

    def update_position(self, sigma):
        H = np.zeros((3, 15))
        H[:, :3] = np.eye(3)
        self.update(-self.p, H, sigma)

    def update_gyro_bias(self, w_mean, sigma):
        H = np.zeros((3, 15))
        H[:, 9:12] = np.eye(3)
        self.update(w_mean - self.bg, H, sigma)


def noise_scale(x, nominal_density, dt):
    """Per-row noise inflation from first differences: motion is slow at 200 Hz, noise is not."""
    d = np.nan_to_num(np.diff(x, axis=0, prepend=x[:1]))
    alpha = 1 / 200
    power, out = 0.0, np.ones(len(x))
    seeded = False
    for i, e in enumerate(np.sum(d**2, axis=1) / 6):
        if e == 0:
            out[i] = out[i - 1] if i else 1.0
            continue
        power = e if not seeded else power + alpha * (e - power)
        seeded = True
        out[i] = max(1.0, np.sqrt(power * dt) / nominal_density)
    return out


def is_static(w, f, ratio):
    """Window spread indistinguishable from sensor noise on both gyro and accel."""
    for x in (w, f):
        var = np.sum(np.var(x, axis=0))
        hf = np.sum(np.mean(np.diff(x, axis=0) ** 2, axis=0)) / 2
        if var > ratio * hf:
            return False
    return True


def run(t_ns, gyro, accel, params=PARAMS):
    T = (t_ns - t_ns[0]) * 1e-9
    n = len(T)
    good = ~np.isnan(gyro[:, 0]) & ~np.isnan(accel[:, 0])
    if not good.any():
        raise ValueError("no valid IMU rows")
    last_good = np.flatnonzero(good)[-1]
    median_dt = float(np.median(np.diff(T)))
    scale = np.maximum(noise_scale(gyro, params["gyro_noise"], median_dt),
                       noise_scale(accel, params["accel_noise"], median_dt))

    flt = Filter(params)
    first = good & (T < T[np.argmax(good)] + 1.0)
    a0 = accel[first].mean(axis=0)
    flt.C = R.align_vectors([[0, 0, 1.0]], [a0 / np.linalg.norm(a0)])[0].as_matrix()

    p_out, C_out = np.zeros((n, 3)), np.zeros((n, 3, 3))
    p_out[0], C_out[0] = flt.p, flt.C
    for i in range(1, n):
        dt = T[i] - T[i - 1]
        if good[i]:
            flt.propagate(gyro[i], accel[i], dt, scale[i])
        else:
            # after the final valid row the IMU is dead; short gaps keep velocity
            flt.coast(dt, np.exp(-dt / params["blind_tau"]) if i > last_good else 1.0)
        if good[i] and i >= STATIC_WINDOW and i % UPDATE_EVERY == 0 and good[i - STATIC_WINDOW:i + 1].all():
            w_win, f_win = gyro[i - STATIC_WINDOW:i + 1], accel[i - STATIC_WINDOW:i + 1]
            f_mean = f_win[-UPDATE_EVERY:].mean(axis=0)
            if is_static(w_win, f_win, params["static_ratio"]):
                flt.update_velocity(params["static_vel_sigma"])
                flt.update_tilt(f_win.mean(axis=0), 0.05 * scale[i] ** 0.5)
                flt.update_gyro_bias(w_win.mean(axis=0),
                                     params["gyro_noise"] * scale[i] * np.sqrt(1 / median_dt / STATIC_WINDOW))
            else:
                flt.update_tilt(f_mean, params["tilt_sigma"])
                flt.update_velocity(params["vel_sigma"])
            flt.update_position(params["pos_sigma"])
        p_out[i], C_out[i] = flt.p, flt.C
    return p_out, R.from_matrix(C_out).as_quat()
