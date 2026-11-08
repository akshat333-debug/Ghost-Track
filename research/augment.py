"""Training-time IMU corruption (D-007): deliberately a different family from the evaluation simulator.

Works per 1 s window on arrays shaped (batch, samples, 3): heavy-tailed noise, offset + slope +
sinusoid + step bias, gain errors, and random masked spans. Returns NaN-free data plus a validity mask.
"""
import numpy as np


def _noise(rng, shape, sigma):
    df = rng.uniform(3, 30, (shape[0], 1, 1))
    t = rng.standard_t(df, shape)
    return t / np.sqrt(df / (df - 2)) * sigma


def _bias(rng, shape, offset, drift):
    b, n, _ = shape
    x = np.linspace(0, 1, n)[None, :, None]
    freq, phase = rng.uniform(0.2, 3, (b, 1, 3)), rng.uniform(0, 2 * np.pi, (b, 1, 3))
    wave = np.sin(2 * np.pi * freq * x + phase) * rng.uniform(0, drift, (b, 1, 3))
    step_at = rng.uniform(0, 1, (b, 1, 3))
    step = (x > step_at) * rng.normal(0, drift, (b, 1, 3))
    slope = x * rng.normal(0, drift, (b, 1, 3))
    return rng.normal(0, offset, (b, 1, 3)) + slope + wave + step


def corrupt(gyro, accel, rng, severity_range=(0.3, 3.0)):
    """gyro, accel: clean (B, N, 3). Returns corrupted copies and mask (B, N), 1 = valid sample."""
    shape = gyro.shape
    b, n, _ = shape
    sev = np.exp(rng.uniform(*np.log(severity_range), (b, 1, 1)))
    # log-uniform scale spans quiet sensors through heavy jamming
    jam = np.exp(rng.uniform(0, np.log(10), (b, 1, 1)))
    g = gyro * (1 + rng.normal(0, 0.005, (b, 1, 3))) + _noise(rng, shape, 2.4e-3 * sev * jam) + _bias(rng, shape, 0.02 * sev, 0.005 * sev)
    a = accel * (1 + rng.normal(0, 0.005, (b, 1, 3))) + _noise(rng, shape, 2.8e-2 * sev * jam) + _bias(rng, shape, 0.1 * sev, 0.05 * sev)

    mask = np.ones((b, n), np.float32)
    dropped = rng.random(b) < 0.3
    for i in np.flatnonzero(dropped):
        length = int(rng.uniform(0.05, 0.9) * n)
        start = rng.integers(0, n - length + 1)
        mask[i, start:start + length] = 0
    g, a = g * mask[..., None], a * mask[..., None]
    return g, a, mask
