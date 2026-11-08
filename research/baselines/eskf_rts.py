"""L1 + L4: ESKF followed by an offline RTS backward pass."""
from research.baselines import eskf


def run(t_ns, gyro, accel):
    return eskf.run(t_ns, gyro, accel, smooth=True)
