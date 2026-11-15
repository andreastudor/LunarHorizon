"""Geometric, simultaneous Sun/Earth/Moon centres in J2000, relative to the Sun.

SPICE spkpos(..., NONE, SUN); no local observer and no apparent-direction correction.
The translating solar origin does not change the inertial orientation of the J2000 axes.
"""

import math

import spiceypy

from lunarhorizon.astro.kernels import SPICE_LOCK, LoadedProfile, activate
from lunarhorizon.astro.timeconv import require_in_coverage, utc_to_et
from lunarhorizon.contracts.system import (
    SystemDistances,
    SystemPositions,
    SystemRequest,
    SystemSeries,
)


def centre_distance_km(a: list[float], b: list[float]) -> float:
    return math.dist(a, b)


def system_series(profile: LoadedProfile, request: SystemRequest) -> SystemSeries:
    positions: dict[str, list[list[float]]] = {name: [] for name in ("sun", "earth", "moon")}
    # Validate all epochs before producing a result. Shared lock also prevents profile switching.
    with SPICE_LOCK:
        activate(profile)
        epochs = [utc_to_et(t, profile) for t in request.time_utc]
        for et in epochs:
            require_in_coverage(et, profile)
        for et in epochs:
            positions["sun"].append([0.0, 0.0, 0.0])
            for body in ("earth", "moon"):
                vector, _ = spiceypy.spkpos(body.upper(), et, "J2000", "NONE", "SUN")
                positions[body].append([float(v) for v in vector])

    def distances(a: str, b: str) -> list[float]:
        return [centre_distance_km(x, y) for x, y in zip(positions[a], positions[b], strict=True)]

    return SystemSeries(
        time_utc=request.time_utc,
        position_km=SystemPositions(**positions),
        distance_km=SystemDistances(
            earth_moon=distances("earth", "moon"),
            sun_earth=distances("sun", "earth"),
            sun_moon=distances("sun", "moon"),
        ),
        kernel_profile=profile.profile_id,
        kernel_sha256=list(profile.sha256),
        coverage_start_utc=profile.coverage_start_utc,
        coverage_end_utc=profile.coverage_end_utc,
    )
