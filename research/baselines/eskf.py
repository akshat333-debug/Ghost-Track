"""L1: error-state Kalman filter on IMU alone.

With no external sensor, position and velocity are corrected only by physical priors: gravity
direction (tilt), stillness, and bounded indoor motion. Attitude error is body-frame (right) perturbation.
State order in the error vector: dp, dv, dtheta, dbg, dba.

Interface matches naive.run, so the manifest (failure time, dropouts) cannot leak into the estimator.
"""
from collections import deque

import numpy as np
from scipy.spatial.transform import Rotation as R

G = 9.81
UPDATE_EVERY = 20  # samples; pseudo-measurements run at about 10 Hz
CENTROID_NODES = 200  # about 20 s of positions at that rate
STATIC_WINDOW = 100  # samples
VEL_WINDOW = 200  # samples; must equal research.nets.vel_net.WINDOW

PARAMS = {
    "gyro_noise": 1.7e-4, "accel_noise": 2.0e-3,   # per sqrt(Hz)
    "gyro_walk": 1.9e-5, "accel_walk": 3.0e-3,     # per sqrt(Hz) * s^-1
    "tilt_sigma": 4.0,      # m/s^2, gravity measurement while moving; broad optimum across severities
    "vel_sigma": 1.5,       # m/s, bounded-motion prior per update
    "pos_sigma": 15.0,      # m, indoor-extent prior per update
    "static_vel_sigma": 0.1,
    "static_ratio": 3.0,    # window variance / high-frequency noise variance
    "blind_tau": 1.0,       # s, velocity decay once the IMU has failed
    "blind_pull_tau": 1.0,  # s, how fast the blind forecast pulls toward the recent flown area
    "net_sigma_scale": 1.0,  # inflation of the velocity net's reported uncertainty
    "gap_att_q": 0.3,       # rad^2/s, attitude uncertainty growth with no gyro
    "gap_vel_q": 1.0,       # (m/s)^2/s, velocity uncertainty growth with no accel
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
        self.Phi = np.eye(15)  # transition since the last smoother node

    def state(self):
        return self.p.copy(), self.v.copy(), self.C.copy(), self.bg.copy(), self.ba.copy()

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
        self.Phi = F @ self.Phi
        self.p = self.p + self.v * dt + 0.5 * acc * dt**2
        self.v = self.v + acc * dt
        self.C = self.C @ exp_so3(w * dt)

    def coast(self, dt, decay):
        """No IMU this step: keep moving on current velocity and grow uncertainty."""
        c = self.c
        self.p = self.p + self.v * dt
        self.v = self.v * decay
        F = np.eye(15)
        F[:3, 3:6] = np.eye(3) * dt
        self.P = F @ self.P @ F.T
        self.Phi = F @ self.Phi
        self.P[np.diag_indices(15)] += np.r_[np.zeros(3), np.full(3, c["gap_vel_q"]), np.full(3, c["gap_att_q"]),
                                             np.zeros(6)] * dt

    def update(self, r, H, sigma):
        """sigma is a scalar or one value per measurement component."""
        R_ = np.eye(len(r)) * sigma**2
        S = H @ self.P @ H.T + R_
        K = np.linalg.solve(S, H @ self.P).T
        dx = K @ r
        I_KH = np.eye(15) - K @ H
        self.P = I_KH @ self.P @ I_KH.T + K @ R_ @ K.T
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

    def update_velocity(self, sigma, target=np.zeros(3)):
        H = np.zeros((3, 15))
        H[:, 3:6] = np.eye(3)
        self.update(target - self.v, H, sigma)

    def update_position(self, sigma):
        H = np.zeros((3, 15))
        H[:, :3] = np.eye(3)
        self.update(-self.p, H, sigma)

    def update_gyro_bias(self, w_mean, sigma):
        H = np.zeros((3, 15))
        H[:, 9:12] = np.eye(3)
        self.update(w_mean - self.bg, H, sigma)


def align_to_up(a):
    """Smallest rotation taking accel direction a to +z. C++ uses the same formula, so yaw matches."""
    n = a / np.linalg.norm(a)
    c = n[2]
    if c < -1 + 1e-9:  # upside down: the axis formula below is singular
        return np.diag([1.0, -1.0, -1.0])
    S = skew([n[1], -n[0], 0.0])
    return np.eye(3) + S + S @ S / (1 + c)


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


def blind_position(t, p0, v0, centre, c):
    """Decaying coast from the failure point, pulled toward where the flight has recently been."""
    tau = c["blind_tau"]
    pull = 1 - np.exp(-t / c["blind_pull_tau"])
    return (p0 + tau * (1 - np.exp(-t / tau)) * v0) * (1 - pull) + centre * pull


def boxminus(a, b):
    """Error state taking nominal b to a, in the filter's own convention."""
    return np.r_[a[0] - b[0], a[1] - b[1], R.from_matrix(b[2].T @ a[2]).as_rotvec(), a[3] - b[3], a[4] - b[4]]


def rts(nodes):
    """Backward pass over nodes (i, x_pred, P_pred, x_filt, P_filt, Phi). Returns correction at each node."""
    N = len(nodes)
    # correction relative to the filtered state, and relative to the predicted state at the same node
    after, before = [np.zeros(15) for _ in range(N)], [np.zeros(15) for _ in range(N)]
    before[-1] = boxminus(nodes[-1][3], nodes[-1][1])
    for k in range(N - 2, -1, -1):
        _, xp, _, xf, _, _ = nodes[k]
        _, _, Pp1, _, _, Phi1 = nodes[k + 1]
        G = np.linalg.solve(Pp1 + 1e-9 * np.eye(15), Phi1 @ nodes[k][4]).T
        after[k] = G @ before[k + 1]
        # the smoothed state at k expressed against the prediction at k
        before[k] = boxminus(xf, xp) + after[k]
    return after, before


def apply_corrections(p_out, C_out, nodes, after, before):
    """Spreads node corrections over every output row so the trajectory stays continuous."""
    p, C = p_out.copy(), C_out.copy()
    for k in range(len(nodes) - 1):
        i0, i1 = nodes[k][0], nodes[k + 1][0]
        for i in range(i0, i1):
            lam = (i - i0) / (i1 - i0)
            d = (1 - lam) * after[k] + lam * before[k + 1]
            p[i] = p_out[i] + d[:3]
            C[i] = C_out[i] @ exp_so3(d[6:9])
    return p, C


def run(t_ns, gyro, accel, params=PARAMS, vel_fn=None, smooth=False):
    """vel_fn(C, gyro, accel, axis) maps one window to (velocity, per-axis sigma); None runs classical L1.
    smooth=True adds the offline RTS backward pass (L4)."""
    T = (t_ns - t_ns[0]) * 1e-9
    n = len(T)
    good = ~(np.isnan(gyro).any(axis=1) | np.isnan(accel).any(axis=1))
    if not good.any():
        raise ValueError("no valid IMU rows")
    last_good = np.flatnonzero(good)[-1]
    median_dt = float(np.median(np.diff(T[:10001])))  # bounded, so the C++ port needs no full-file buffer
    scale = np.maximum(noise_scale(gyro, params["gyro_noise"], median_dt),
                       noise_scale(accel, params["accel_noise"], median_dt))

    flt = Filter(params)
    first = good & (T < T[np.argmax(good)] + 1.0)
    a0 = accel[first].mean(axis=0)
    flt.C = align_to_up(a0)

    p_out, C_out = np.zeros((n, 3)), np.zeros((n, 3, 3))
    p_out[0], C_out[0] = flt.p, flt.C
    f_sum = np.zeros(3)
    recent, blind = deque(maxlen=CENTROID_NODES), None
    nodes = [(0, flt.state(), flt.P.copy(), flt.state(), flt.P.copy(), np.eye(15))]
    for i in range(1, n):
        dt = T[i] - T[i - 1]
        if good[i]:
            flt.propagate(gyro[i], accel[i], dt, scale[i])
            f_sum += accel[i]
        else:
            # after the final valid row the IMU is dead; short gaps keep velocity
            flt.coast(dt, np.exp(-dt / params["blind_tau"]) if i > last_good else 1.0)
            if i > last_good:
                if blind is None:
                    blind = (flt.p - flt.v * dt, flt.v.copy(), np.mean(recent, axis=0) if recent else flt.p.copy())
                flt.p = blind_position(T[i] - T[last_good], *blind, params)
        pred = (flt.state(), flt.P.copy()) if smooth and i % UPDATE_EVERY == 0 else None
        if good[i] and i % UPDATE_EVERY == 0:
            recent.append(flt.p.copy())
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
                if vel_fn is None:
                    flt.update_velocity(params["vel_sigma"])
            flt.update_position(params["pos_sigma"])
        if vel_fn is not None and good[i] and i >= VEL_WINDOW and i % UPDATE_EVERY == 0:
            C_out[i] = flt.C
            v_net, sigma = vel_fn(C_out[i - VEL_WINDOW + 1:i + 1], gyro[i - VEL_WINDOW + 1:i + 1],
                                  accel[i - VEL_WINDOW + 1:i + 1], f_sum / np.linalg.norm(f_sum))
            flt.update_velocity(sigma * params["net_sigma_scale"], v_net)
        p_out[i], C_out[i] = flt.p, flt.C
        if pred is not None:
            nodes.append((i, *pred, flt.state(), flt.P.copy(), flt.Phi.copy()))
            flt.Phi = np.eye(15)
    if smooth:
        p_out, C_out = apply_corrections(p_out, C_out, nodes, *rts(nodes))
    return p_out, R.from_matrix(C_out).as_quat()
