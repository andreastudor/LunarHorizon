"""Profilul orizontului din DEM (GET /api/horizon, E09; docs/SPEC_FIZICA.md §6).

Trei stări distincte ale profilului:
- `complete`: toate azimuturile au date până la `max_search_distance_m`;
- `partial`: lipsesc eșantioane pe cel puțin un azimut (maximul real poate fi mai mare);
- `unavailable`: profilul nu se poate calcula (motiv în `reason_code` și `reason`); tablourile
  sunt goale. Necunoscutul nu devine niciodată zero sau orizont liber.
"""

from typing import Annotated, Literal

from pydantic import Field, model_validator

from lunarhorizon.contracts.common import (
    Contract,
    Elevation,
    Fraction,
    FrameId,
    Identifier,
    Latitude,
    Longitude,
    NonEmptyText,
    NonNegative,
    Positive,
    SchemaVersion,
    Sha256,
)
from lunarhorizon.contracts.manifests import TerrainRole
from lunarhorizon.core.coords import azimuth_convention

HorizonStatus = Literal["complete", "partial", "unavailable"]
HorizonUnavailableReason = Literal[
    "frame_mismatch",
    "terrain_not_downloaded",
    "coverage_unverified",
    "no_dem_coverage",
    "observer_elevation_unknown",
]
AzimuthQuality = Literal["complete", "partial", "no_data"]
HorizonParameterValue = float | int | str


class HorizonProductUse(Contract):
    product_id: Identifier
    role: TerrainRole
    frame_id: FrameId
    resolution_m: Positive
    reference_radius_m: Positive
    sha256: Sha256 | None
    # Partea eșantioanelor valide ale profilului care provine din acest produs.
    valid_sample_fraction: Fraction


class HorizonProfile(Contract):
    schema_version: SchemaVersion
    status: HorizonStatus
    reason_code: HorizonUnavailableReason | Literal["missing_samples"] | None
    reason: str | None
    latitude_deg: Latitude
    longitude_deg: Longitude
    frame_id: FrameId
    azimuth_convention: Literal["standard", "pole_meridian"]
    observer_terrain_elevation_m: float | None
    observer_height_m: NonNegative
    azimuth_step_deg: Annotated[float, Field(gt=0.0, le=360.0)]
    elevation_deg: list[Elevation | None]
    obstacle_distance_m: list[NonNegative | None]
    quality: list[AzimuthQuality]
    max_search_distance_m: Positive
    coverage_fraction: Fraction
    dem_products: list[HorizonProductUse]
    parameters: dict[str, HorizonParameterValue]
    # D-08/D-09 [GEO] sunt deschise: parametrii sunt propuneri tehnice, nu valori validate.
    parameters_status: Literal["provisional"]
    cache_key: Sha256
    compute_time_s: NonNegative | None
    note: NonEmptyText

    @model_validator(mode="after")
    def _consistency(self) -> "HorizonProfile":
        if self.azimuth_convention != azimuth_convention(self.latitude_deg):
            raise ValueError("azimuth_convention nu corespunde latitudinii")
        arrays = (self.elevation_deg, self.obstacle_distance_m, self.quality)
        if self.status == "unavailable":
            if any(arrays):
                raise ValueError("un profil indisponibil nu are valori pe azimut")
            if self.reason_code in (None, "missing_samples") or not self.reason:
                raise ValueError("un profil indisponibil cere reason_code și reason")
            if self.coverage_fraction != 0.0:
                raise ValueError("un profil indisponibil are coverage_fraction = 0")
            return self
        count = 360.0 / self.azimuth_step_deg
        if abs(count - round(count)) > 1e-9:
            raise ValueError("azimuth_step_deg trebuie să dividă exact 360")
        if {len(array) for array in arrays} != {round(count)}:
            raise ValueError("profilul trebuie să aibă 360 / azimuth_step_deg valori")
        for elevation, distance, quality in zip(*arrays, strict=True):
            if (elevation is None) != (quality == "no_data") or (elevation is None) != (
                distance is None
            ):
                raise ValueError(
                    "elevația și distanța sunt null dacă și numai dacă quality=no_data"
                )
        if self.observer_terrain_elevation_m is None or not self.dem_products:
            raise ValueError("un profil calculat cere altitudinea observatorului și produsele DEM")
        all_complete = set(self.quality) == {"complete"}
        if (self.status == "complete") != all_complete:
            raise ValueError("status=complete dacă și numai dacă toate azimuturile sunt complete")
        if self.status == "complete" and (self.reason_code or self.reason):
            raise ValueError("un profil complet nu are motiv de lipsă")
        if self.status == "partial" and (self.reason_code != "missing_samples" or not self.reason):
            raise ValueError("un profil parțial cere reason_code=missing_samples și reason")
        return self
