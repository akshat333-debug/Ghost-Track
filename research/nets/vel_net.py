"""L3: 1 s of gravity-aligned IMU to world-frame velocity with uncertainty (TLIO-style frame, D-009)."""
import torch
from torch import nn

WINDOW = 200
GYRO_SCALE, ACCEL_SCALE = 3.0, 5.0
IN_CHANNELS = 10  # world gyro 3, world accel 3, validity 1, tilt cue 3


class VelNet(nn.Module):
    """Plain strided convolutions, with no normalization layers, so the C++ forward pass stays trivial."""

    def __init__(self):
        super().__init__()
        chans = [IN_CHANNELS, 16, 32, 48, 64, 64, 64]
        layers = []
        for a, b in zip(chans, chans[1:]):
            layers += [nn.Conv1d(a, b, 5, stride=2, padding=2), nn.ReLU()]
        self.conv = nn.Sequential(*layers)
        self.head = nn.Sequential(nn.Flatten(), nn.Linear(64 * 4, 64), nn.ReLU(), nn.Linear(64, 6))

    def forward(self, x):
        out = self.head(self.conv(x))
        return out[:, :3], out[:, 3:].clamp(-8, 4)


def param_count(model):
    return sum(p.numel() for p in model.parameters())
