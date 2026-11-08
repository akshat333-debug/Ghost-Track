"""The C++ submission must produce the Python estimator's trajectory. Run: python -m pytest tests -q"""
import subprocess
from pathlib import Path

import numpy as np
import pytest

from research.baselines.eskf import run
from research.degrade import degrade
from research.eval.validate_format import validate
from research.io_euroc import write_imu_csv
from test_eval import flight

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="module")
def binary(tmp_path_factory):
    exe = tmp_path_factory.mktemp("bin") / "pathfinder"
    subprocess.run(["g++", "-O2", "-std=c++17", "-Wall", "-Werror", str(ROOT / "src/main.cpp"), "-o", str(exe)],
                   check=True)
    return exe


def test_matches_python_on_degraded_flight(binary, tmp_path):
    t, w, a, _ = flight(120)
    t, w, a, _ = degrade(t, w, a, seed=5)
    imu, est = str(tmp_path / "x/imu.csv"), str(tmp_path / "est.txt")
    write_imu_csv(imu, t, w, a)
    subprocess.run([str(binary), imu, est], check=True)
    validate(est, imu)
    got = np.loadtxt(est)
    p, q = run(t, w, a)
    assert np.abs(got[:, 1:4] - p).max() < 1e-5
    assert (1 - np.abs(np.sum(got[:, 4:] * q, axis=1))).max() < 1e-9


def test_rejects_garbage_gracefully(binary, tmp_path):
    bad = tmp_path / "bad.csv"
    bad.write_text("#header\n123,nan,nan,nan,nan,nan,nan\n")
    r = subprocess.run([str(binary), str(bad), str(tmp_path / "o.txt")], capture_output=True, text=True)
    assert r.returncode == 1 and "no valid IMU rows" in r.stderr


def test_malformed_row_is_treated_as_invalid(binary, tmp_path):
    t, w, a, _ = flight(30)
    imu = tmp_path / "x/imu.csv"
    write_imu_csv(str(imu), t, w, a)
    lines = imu.read_text().splitlines()
    lines[2000] = lines[2000].split(",")[0] + ",abc,,1"  # valid timestamp, broken values
    imu.write_text("\n".join(lines) + "\n")
    est = tmp_path / "e.txt"
    subprocess.run([str(binary), str(imu), str(est)], check=True)
    validate(str(est), str(imu))
