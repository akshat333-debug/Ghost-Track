"""L1 + L3: ESKF with velocity measurements from a trained net. Research-side inference only."""
import numpy as np
import torch

from research.baselines import eskf
from research.nets.data import to_input
from research.nets.vel_net import VelNet


def make_vel_fn(weights):
    torch.set_num_threads(1)
    model = VelNet()
    model.load_state_dict(torch.load(weights, map_location="cpu"))
    model.eval()

    @torch.no_grad()
    def vel_fn(C, gyro, accel):
        mask = (~(np.isnan(gyro).any(axis=1) | np.isnan(accel).any(axis=1))).astype(np.float32)
        g, a = np.nan_to_num(gyro) * mask[:, None], np.nan_to_num(accel) * mask[:, None]
        x = to_input(C[None], g[None], a[None], mask[None])
        mu, logvar = model(torch.from_numpy(x))
        return mu[0].numpy().astype(float), np.exp(0.5 * logvar[0].numpy()).astype(float)

    return vel_fn


def run_weights(weights, params=eskf.PARAMS):
    fn = make_vel_fn(weights)
    return lambda t_ns, gyro, accel: eskf.run(t_ns, gyro, accel, params, vel_fn=fn)
