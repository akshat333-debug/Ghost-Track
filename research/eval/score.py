"""evo ATE/RPE plus per-tier errors and a proxy for the 60 trajectory points.

Proxy points use our own error scales (organizers have not published theirs). Use them to rank
our own methods only, never quote them as an expected competition score.
"""
import copy

import numpy as np
from evo.core import geometry, metrics, sync
from evo.core.trajectory import PoseTrajectory3D
from scipy.spatial.transform import Rotation as R

WAYPOINTS = 10
PROXY = {"waypoint": (30, 2.0), "blind": (20, 2.0), "dropout": (10, 1.0)}  # max points, metres scale


def _traj(t_ns, p, q_xyzw):
    return PoseTrajectory3D(positions_xyz=p, orientations_quat_wxyz=q_xyzw[:, [3, 0, 1, 2]],
                            timestamps=t_ns * 1e-9)


def _ape(gt, est, relation=metrics.PoseRelation.translation_part):
    m = metrics.APE(relation)
    m.process_data((gt, est))
    return float(m.get_statistic(metrics.StatisticsType.rmse))


def _rmse(e):
    return float(np.sqrt(np.mean(np.sum(e ** 2, axis=1)))) if len(e) else float("nan")


def score(t_ns, p, q, gt, manifest):
    """t_ns, p, q: one pose per input row. gt: (t_ns, p, q) from load_gt, in the original body frame."""
    gt_t, gt_p, gt_q = gt
    first = np.r_[True, np.diff(t_ns) > 0]  # the official script duplicates rows; score each timestamp once
    t_ns, p, q = t_ns[first], p[first], q[first]
    mount = R.from_quat(manifest["mount_xyzw"])
    gt_q = (R.from_quat(gt_q) * mount.inv()).as_quat()  # GT orientation of the mounted sensor
    a, b = sync.associate_trajectories(_traj(gt_t, gt_p, gt_q), _traj(t_ns, p, q), max_diff=0.01)
    ts = a.timestamps
    # mocap can be slower than the IMU (TUM-VI 120 Hz vs 200 Hz), so compare against the slower stream
    expected = min(len(t_ns), int(((gt_t >= t_ns[0]) & (gt_t <= t_ns[-1])).sum()))
    if len(ts) < 0.9 * expected:
        raise ValueError(f"only {len(ts)} of {expected} expected poses matched ground truth")

    aligned = copy.deepcopy(b)
    aligned.align(a)
    out = {"ate": _ape(a, aligned),
           "ate_rot_deg": _ape(a, aligned, metrics.PoseRelation.rotation_angle_deg)}
    origin = copy.deepcopy(b)
    origin.align_origin(a)
    out["ate_origin"] = _ape(a, origin)
    rpe = metrics.RPE(metrics.PoseRelation.translation_part, delta=int(round(1 / np.median(np.diff(ts)))),
                      delta_unit=metrics.Unit.frames,
                      all_pairs=False)
    rpe.process_data((a, b))
    out["rpe_1s"] = float(rpe.get_statistic(metrics.StatisticsType.rmse))
    rot = metrics.RPE(metrics.PoseRelation.rotation_angle_deg, delta=rpe.delta, delta_unit=metrics.Unit.frames,
                      all_pairs=False)
    rot.process_data((a, b))
    out["rpe_rot_deg"] = float(rot.get_statistic(metrics.StatisticsType.rmse))
    full = aligned.positions_xyz - a.positions_xyz  # organizers align once over everything (FAQ section 4)

    # Align on the flown part only, so blind-window error cannot be hidden by the alignment.
    t_fail = manifest["t_fail_ns"] * 1e-9
    flown = ts <= t_fail
    rot, trans, _ = geometry.umeyama_alignment(b.positions_xyz[flown].T, a.positions_xyz[flown].T)
    err = (rot @ b.positions_xyz.T).T + trans - a.positions_xyz

    wp = np.linspace(0, flown.sum() - 1, WAYPOINTS).astype(int)
    out["waypoint"] = _rmse(err[flown][wp])
    out["waypoint20"] = _rmse(full[flown][np.linspace(0, flown.sum() - 1, 2 * WAYPOINTS).astype(int)])
    blind = ~flown
    out["blind"] = _rmse(err[blind])
    out["blind_full"] = _rmse(full[blind])
    out["blind_end"] = float(np.linalg.norm(err[blind][-1])) if blind.any() else float("nan")
    in_drop = np.zeros(len(ts), bool)
    for s, e in manifest["dropouts_ns"]:
        in_drop |= (ts >= s * 1e-9) & (ts < e * 1e-9)
    out["dropout"] = _rmse(err[in_drop])
    out["dropout_full"] = _rmse(full[in_drop])
    # Zero-effort reference: a tracker that never moves from the flown centroid. Must be beaten to claim skill.
    still = a.positions_xyz - a.positions_xyz[flown].mean(axis=0)
    out["null_ate"], out["null_blind"] = _rmse(still), _rmse(still[blind])
    out["proxy60"] = float(np.nansum([mx * np.exp(-out[k] / scale) for k, (mx, scale) in PROXY.items()]))
    return out
