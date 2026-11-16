"""The submission script, run exactly as an evaluator would: a subprocess on a CSV file."""
import subprocess
import sys
import zipfile
from pathlib import Path

import numpy as np
import pytest
from scipy.spatial.transform import Rotation as R

from research.eval.score import score
from research.eval.validate_format import validate
from research.official_degrade import degrade_arrays, write_csv
from test_eval import flight

MAIN = str(Path(__file__).resolve().parent.parent / "src" / "main.py")
MEMORY_MB, MS_PER_IMU_S = 6.0, 6.0  # D-020 gates; the organizers' limits are 8 MB and 20 ms


def run_main(*args, cwd=None):
    subprocess.run([sys.executable, MAIN, *map(str, args)], check=True, cwd=cwd)


def degraded(tmp_path, order="A", seconds=60, **cfg):
    t, w, a, gt = flight(seconds)
    df, man = degrade_arrays(t, w, a, order=order, **cfg)
    csv = tmp_path / "imu0" / "data.csv"
    write_csv(df, str(csv))
    return csv, df, man, gt


@pytest.mark.parametrize("order", ["A", "B"])
def test_official_degradation_gives_a_valid_scoreable_file(tmp_path, order):
    csv, df, man, gt = degraded(tmp_path, order)
    est = tmp_path / "estimated_trajectory.txt"
    run_main(csv, est)
    validate(str(est), str(csv))
    out = np.loadtxt(est)
    r = score(df.iloc[:, 0].to_numpy(), out[:, 1:4], out[:, 4:8], gt, man)  # raises if evo cannot align
    assert np.isfinite(r["ate"]) and r["ate"] < 5
    # tilt: the estimated body z axis must stay near world up on this level flight, in either column order
    up = R.from_quat(out[:, 4:8]).apply([0, 0, 1.0])[:, 2]
    assert np.degrees(np.arccos(up.clip(-1, 1))).max() < 10


def test_same_input_same_bytes(tmp_path):
    csv, *_ = degraded(tmp_path)
    run_main(csv, tmp_path / "a.txt")
    run_main(csv, tmp_path / "b.txt")
    assert (tmp_path / "a.txt").read_bytes() == (tmp_path / "b.txt").read_bytes()


def test_input_forms_folder_zip_and_default_output(tmp_path):
    csv, *_ = degraded(tmp_path, seconds=20)
    run_main(csv, tmp_path / "ref.txt")
    ref = (tmp_path / "ref.txt").read_bytes()
    run_main(tmp_path, cwd=tmp_path)  # folder holding imu0/data.csv, output defaults to the working directory
    assert (tmp_path / "estimated_trajectory.txt").read_bytes() == ref
    with zipfile.ZipFile(tmp_path / "eval.zip", "w") as z:
        z.write(csv, "dataset/imu0/data.csv")
    run_main(tmp_path / "eval.zip", tmp_path / "z.txt")
    assert (tmp_path / "z.txt").read_bytes() == ref


def rows(est):
    return [ln.split() for ln in open(est) if not ln.startswith("#")]


def variant(name, lines):
    """Rewrites clean CSV lines (header first) into one robustness case."""
    head, body = lines[0], lines[1:]
    cell = lambda ln: ln.split(",")
    if name == "no_header":
        return body
    if name == "motionless":
        return [head] + [cell(ln)[0] + ",0.0,0.0,0.0,0.0,0.0,9.81" for ln in body]
    if name == "crlf":
        return [ln + "\r" for ln in lines]
    if name == "shorter_than_failure_block":
        return [head] + body[:800]
    if name == "nan_tail":
        return [head] + body[:-600] + [cell(ln)[0] + ",nan,nan,nan,nan,nan,nan" for ln in body[-600:]]
    if name == "empty_fields_mid_file":
        return [head] + body[:2000] + [cell(ln)[0] + ",,,,,," for ln in body[2000:2400]] + body[2400:]
    if name == "all_rows_dead":
        return [head] + [cell(ln)[0] + ",0.0,0.0,0.0,0.0,0.0,0.0" for ln in body]
    if name == "float_timestamps":
        return [head] + ["%.1f," % int(cell(ln)[0]) + ",".join(cell(ln)[1:]) for ln in body]
    if name == "seconds":
        return [head] + ["%.6f," % (int(cell(ln)[0]) * 1e-9) + ",".join(cell(ln)[1:]) for ln in body]
    if name == "microseconds":
        return [head] + ["%d," % (int(cell(ln)[0]) // 1000) + ",".join(cell(ln)[1:]) for ln in body]
    if name == "accel_in_g":
        return [head] + [",".join(cell(ln)[:4] + ["%.9f" % (float(x) / 9.80665) for x in cell(ln)[4:]]) for ln in body]
    if name == "duplicates_at_start":
        return [head, body[0], body[0], body[0]] + body[1:]
    if name == "half_rate":
        return [head] + body[::2]
    raise KeyError(name)


CASES = ["motionless", "no_header", "crlf", "shorter_than_failure_block", "nan_tail", "empty_fields_mid_file", "all_rows_dead",
         "float_timestamps", "seconds", "microseconds", "accel_in_g", "duplicates_at_start", "half_rate"]


@pytest.mark.parametrize("name", CASES)
def test_robustness_matrix(tmp_path, name):
    from research.io_euroc import write_imu_csv
    t, w, a, _ = flight(20)
    clean = tmp_path / "clean.csv"
    write_imu_csv(str(clean), t, w, a)
    lines = variant(name, clean.read_text().splitlines())
    csv, est = tmp_path / "case.csv", tmp_path / "est.txt"
    csv.write_text("\n".join(lines) + "\n")
    run_main(csv, est)
    out = np.array(rows(est), dtype=float)
    n_in = sum(1 for ln in lines if ln.strip() and not ln.startswith("#"))
    assert out.shape == (n_in, 8) and np.isfinite(out).all()
    assert np.abs(np.linalg.norm(out[:, 4:], axis=1) - 1).max() < 1e-6
    assert (np.diff(out[:, 0]) >= 0).all()
    assert np.linalg.matrix_rank(out[:, 1:4] - out[:, 1:4].mean(axis=0), tol=1e-3) >= 2, "evo cannot align a line"
    if name in ("no_header", "crlf", "float_timestamps", "microseconds", "accel_in_g", "duplicates_at_start"):
        expect = t[0] * 1e-9
        assert abs(out[0, 0] - expect) < 1e-5, "timestamps must come out in seconds"
        up = R.from_quat(out[:, 4:8]).apply([0, 0, 1.0])[:, 2]
        # the circling flight starts with 1 m/s^2 centripetal acceleration: 5.8 deg of honest start tilt error
        assert up.min() > np.cos(np.radians(7)), "level flight must stay level"


def measure(csv, est):
    code = ("import runpy, sys, time, tracemalloc\n"
            "t = time.perf_counter()\n"
            f"sys.argv = ['main.py', {str(csv)!r}, {str(est)!r}]\n"
            f"runpy.run_path({MAIN!r}, run_name='__main__')\n"
            "print(tracemalloc.get_traced_memory()[1] / 1e6, time.perf_counter() - t)\n")
    out = subprocess.run([sys.executable, "-X", "tracemalloc", "-c", code], check=True, capture_output=True, text=True)
    return map(float, out.stdout.split())


@pytest.mark.parametrize("seconds", [180, 900])
def test_memory_budget_does_not_grow_with_length(tmp_path, seconds):
    csv, *_ = degraded(tmp_path, seconds=seconds)
    peak_mb, _ = measure(csv, tmp_path / "est.txt")
    assert peak_mb < MEMORY_MB, f"{peak_mb:.2f} MB traced from interpreter start, imports included"


def test_runtime_budget(tmp_path):
    import time
    csv, *_ = degraded(tmp_path, seconds=180)
    walls = []
    for _ in range(3):  # best of three: other processes on the machine only ever add time
        start = time.perf_counter()
        run_main(csv, tmp_path / "est.txt")  # whole process: interpreter start, parsing, estimation, writing
        walls.append(time.perf_counter() - start)
    ms = min(walls) * 1000 / 180
    assert ms < MS_PER_IMU_S, f"{ms:.2f} ms per IMU-second"
