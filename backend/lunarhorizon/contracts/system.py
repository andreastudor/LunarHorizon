"""E10A: geometric body centres, separate from topocentric apparent observations."""

from collections.abc import Sized
from itertools import pairwise
from typing import Annotated, Literal

from pydantic import Field, model_validator

from lunarhorizon.contracts.common import Contract, NonEmptyText, Positive, Sha256, UtcTimestamp
from lunarhorizon.core.utc import parse_utc

SystemBody = Literal["sun", "earth", "moon"]
VectorKm = Annotated[list[float], Field(min_length=3, max_length=3)]


class SystemRequest(Contract):
    # Exact epochs let the simulation slider consume the series without interpolation.
    time_utc: Annotated[list[UtcTimestamp], Field(min_length=1, max_length=20001)]

    @model_validator(mode="after")
    def _time_order(self) -> "SystemRequest":
        times = [parse_utc(t) for t in self.time_utc]
        if any(b <= a for a, b in pairwise(times)):
            raise ValueError("time_utc must be strictly increasing")
        if (times[-1] - times[0]).total_seconds() > 366 * 86400:
            raise ValueError("system interval exceeds 366 days")
        return self


class SystemPositions(Contract):
    sun: list[VectorKm]
    earth: list[VectorKm]
    moon: list[VectorKm]


class SystemDistances(Contract):
    earth_moon: list[Positive]
    sun_earth: list[Positive]
    sun_moon: list[Positive]


class SystemSeries(Contract):
    # Independent additive contract: existing simulation/terrain schema 0.8.0 is unchanged.
    system_schema_version: Literal["1.0.0"] = "1.0.0"
    time_utc: list[UtcTimestamp] = Field(min_length=1, max_length=20001)
    frame_id: Literal["J2000"] = "J2000"
    origin: Literal["SUN"] = "SUN"
    aberration_correction: Literal["NONE"] = "NONE"
    position_km: SystemPositions
    distance_km: SystemDistances
    kernel_profile: NonEmptyText
    kernel_sha256: list[Sha256] = Field(min_length=1)
    coverage_start_utc: UtcTimestamp
    coverage_end_utc: UtcTimestamp
    algorithm_version: Literal["system-centres-1"] = "system-centres-1"

    @model_validator(mode="after")
    def _aligned(self) -> "SystemSeries":
        SystemRequest(time_utc=self.time_utc)
        n = len(self.time_utc)
        columns: list[Sized] = [
            self.position_km.sun,
            self.position_km.earth,
            self.position_km.moon,
            self.distance_km.earth_moon,
            self.distance_km.sun_earth,
            self.distance_km.sun_moon,
        ]
        if any(len(column) != n for column in columns):
            raise ValueError("system series lengths differ")
        return self
