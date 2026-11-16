"""L1 + rotor-drag velocity measurement (D-019). Research prototype of the idea before the pure-Python port."""
from research.baselines import eskf

PARAMS = dict(eskf.PARAMS, drag_k=0.177, drag_sigma=0.15, drag_gate=11.3)


def run(t_ns, gyro, accel, params=PARAMS):
    return eskf.run(t_ns, gyro, accel, params)
