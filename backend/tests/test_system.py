"""E10A numerical invariants; tolerances are floating-point checks, not ASTRO acceptance."""

import math

import pytest
import spiceypy
from pydantic import ValidationError

from lunarhorizon.astro.kernels import SPICE_LOCK, load_profile
from lunarhorizon.astro.system import centre_distance_km, system_series
from lunarhorizon.astro.timeconv import utc_to_et
from lunarhorizon.contracts.system import SystemRequest


def test_distance_translation_symmetry_and_units() -> None:
    a, b = [1.0, 2.0, 3.0], [4.0, 6.0, 3.0]
    assert centre_distance_km(a, b) == centre_distance_km(b, a) == 5.0
    assert centre_distance_km([v + 1e8 for v in a], [v + 1e8 for v in b]) == 5.0


def test_request_rejects_duplicate_epochs() -> None:
    with pytest.raises(ValidationError):
        SystemRequest(time_utc=["2026-11-15T00:00:00Z"] * 2)


@pytest.mark.kernels
def test_real_centres_direct_pair_vectors() -> None:
    profile = load_profile("de440_me421")
    times = ["2026-11-15T00:00:00Z", "2026-12-15T00:00:00Z"]
    result = system_series(profile, SystemRequest(time_utc=times))
    assert result.aberration_correction == "NONE"
    for i, utc in enumerate(times):
        with SPICE_LOCK:
            direct, _ = spiceypy.spkpos("MOON", utc_to_et(utc, profile), "J2000", "NONE", "EARTH")
        # Subtraction of heliocentric doubles loses ~1e-8 km; 1e-6 km leaves margin.
        assert result.distance_km.earth_moon[i] == pytest.approx(
            math.dist(direct, [0, 0, 0]), abs=1e-6
        )
        assert 300000 < result.distance_km.earth_moon[i] < 450000
    assert result.distance_km.earth_moon[0] != result.distance_km.earth_moon[1]
