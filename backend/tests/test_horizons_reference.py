"""Comparația cu referințele Horizons arhivate (T-01, T-02) și diferența dintre profiluri (T-03).

Pragurile sunt PROPUSE (`PROPOSED_TOLERANCES`) și nevalidate; acordul cu Horizons compară două
implementări JPL (DE440s local, DE441 la Horizons), nu observații independente.
"""

from collections.abc import Iterator

import numpy as np
import pytest

from lunarhorizon.astro.bodies import body_direction
from lunarhorizon.astro.kernels import DEFAULT_KERNEL_DIR, LoadedProfile, activate, load_profile
from lunarhorizon.astro.reference import (
    PROPOSED_TOLERANCES,
    ReferenceCase,
    compare_direction,
    compare_vector,
    load_cases,
    separation_deg,
)

pytestmark = [
    pytest.mark.kernels,
    pytest.mark.skipif(
        not (DEFAULT_KERNEL_DIR / "de440s.bsp").is_file(),
        reason="kernelurile lipsesc; rulați scripts/download_kernels.py",
    ),
]
CASES = load_cases()
VALIDATION_CASES = [c for c in CASES if not c.diagnostic]


@pytest.fixture(scope="module")
def de440() -> Iterator[LoadedProfile]:
    profile = load_profile("de440_me421")
    yield profile


@pytest.mark.parametrize("correction", ["LT+S", "CN+S"])
@pytest.mark.parametrize("body", ["sun", "earth"])
@pytest.mark.parametrize("case", VALIDATION_CASES, ids=[c.case_id for c in VALIDATION_CASES])
def test_apparent_direction_and_range_match_horizons(
    de440: LoadedProfile, case: ReferenceCase, body: str, correction: str
) -> None:
    result = compare_direction(de440, case, body, correction)  # type: ignore[arg-type]
    assert result.separation_deg <= PROPOSED_TOLERANCES["T-01_separation_deg"]
    assert abs(result.distance_diff_km) <= PROPOSED_TOLERANCES["T-02_distance_km"]


@pytest.mark.parametrize("body", ["sun", "earth"])
def test_geometric_icrf_vectors_match_horizons(de440: LoadedProfile, body: str) -> None:
    case = next(c for c in CASES if "vectors" in c.queries)
    result = compare_vector(de440, case, body)  # type: ignore[arg-type]
    assert result.vector_diff_km <= PROPOSED_TOLERANCES["T-02_vector_km"]


def test_exact_pole_diagnostic_is_recorded(de440: LoadedProfile) -> None:
    # Diagnostic (D-03/D-18): nu este un criteriu T-01; verifică doar că rezultatul este definit.
    case = next(c for c in CASES if c.diagnostic)
    for body in ("sun", "earth"):
        result = compare_direction(de440, case, body, "LT+S")
        assert np.isfinite(result.separation_deg)


def test_profile_difference_t03(de440: LoadedProfile) -> None:
    de421 = load_profile("de421")
    try:
        for case in CASES:
            for body in ("sun", "earth"):
                a = body_direction(de440, case.site, body, case.utc)
                b = body_direction(de421, case.site, body, case.utc)
                separation = separation_deg(np.array(a.direction_enu), np.array(b.direction_enu))
                assert separation <= PROPOSED_TOLERANCES["T-03_separation_deg"]
    finally:
        activate(de440)
