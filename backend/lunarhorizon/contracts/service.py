"""Documentele de serviciu: starea, acoperirea și erorile (docs/API.md §2.1, §2.3, §6)."""

from typing import Literal

from pydantic import Field, model_validator

from lunarhorizon.contracts.common import (
    Contract,
    GeoJsonPolygon,
    Identifier,
    Latitude,
    NonEmptyText,
    Positive,
    SchemaVersion,
    UtcTimestamp,
)
from lunarhorizon.contracts.manifests import TerrainRole
from lunarhorizon.core.errors import ErrorCode


class Health(Contract):
    status: Literal["ok", "degraded"]
    app_version: NonEmptyText
    kernel_profile: str | None
    kernels_loaded: bool
    dem_products: list[Identifier]
    time_utc: UtcTimestamp
    issues: list[NonEmptyText]

    @model_validator(mode="after")
    def _degraded_has_reason(self) -> "Health":
        if self.status == "degraded" and not self.issues:
            raise ValueError("starea degraded cere cel puțin un motiv în issues")
        return self


class TemporalCoverage(Contract):
    start_utc: UtcTimestamp
    end_utc: UtcTimestamp
    kernel_profile: NonEmptyText


class TerrainCoverage(Contract):
    product_id: Identifier
    role: TerrainRole
    resolution_m: Positive
    footprint: GeoJsonPolygon | None
    min_latitude_deg: Latitude
    max_latitude_deg: Latitude


class Coverage(Contract):
    schema_version: SchemaVersion
    temporal: TemporalCoverage
    terrain: list[TerrainCoverage]


class FieldError(Contract):
    loc: list[str | int]
    message: NonEmptyText


class Problem(Contract):
    """Eroare în formatul `application/problem+json` (RFC 9457), cu un `code` stabil."""

    type: NonEmptyText
    title: NonEmptyText
    # Statusul HTTP; `null` numai pentru erorile sursei de date statice (fără HTTP).
    status: int | None = Field(ge=100, le=599)
    detail: NonEmptyText
    code: ErrorCode
    field_errors: list[FieldError] | None = None
    coverage_start_utc: UtcTimestamp | None = None
    coverage_end_utc: UtcTimestamp | None = None
