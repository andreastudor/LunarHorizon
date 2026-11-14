"""Checks for the exploratory PGDA pixel validity logic."""

import importlib.util
from pathlib import Path

import numpy as np

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "check_pgda_coverage.py"
spec = importlib.util.spec_from_file_location("check_pgda_coverage", SCRIPT)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_pixel_validity_preserves_zero_and_rejects_nodata() -> None:
    assert module.valid_elevation(np.ma.array([[0.0]], mask=False)) == 0.0
    assert module.valid_elevation(np.ma.array([[7.0]], mask=True)) is None
    assert module.valid_elevation(np.ma.array([[float("nan")]], mask=False)) is None
