"""Cererea, starea și rezultatul simulării (docs/API.md §2.5, §2.6, §3).

Trei stări distincte, impuse de validatorii lui `SimulationResult`:
- valoare zero reală: `0`;
- valoare necunoscută: `null`, cu o intrare în `quality.issues` pentru câmpul respectiv;
- funcție necalculată: grupul lipsește pentru acel sit și apare în `quality.not_computed`.
"""

import itertools
from typing import Annotated, Literal

from pydantic import Field, model_validator

from lunarhorizon.contracts.common import (
    Azimuth,
    Contract,
    Elevation,
    Fraction,
    FrameId,
    Identifier,
    Latitude,
    Longitude,
    LongitudeInput,
    NonEmptyText,
    NonNegative,
    Positive,
    PositiveInt,
    SchemaVersion,
    Sha256,
    UtcTimestamp,
)
from lunarhorizon.contracts.manifests import TerrainRole
from lunarhorizon.contracts.service import Problem
from lunarhorizon.core.coords import azimuth_convention
from lunarhorizon.core.utc import parse_utc

Body = Literal["sun", "earth"]
TerrainMode = Literal["dem", "idealized_local_plane"]
ResultGroup = Literal["series", "events", "summary", "horizon", "terrain"]
RESULT_GROUPS: tuple[ResultGroup, ...] = ("series", "events", "summary", "horizon", "terrain")
AngularRadius = Annotated[float, Field(gt=0.0, le=90.0)]
ParameterValue = float | int | str | bool


def _strictly_after(start_utc: str, end_utc: str) -> bool:
    return parse_utc(end_utc) > parse_utc(start_utc)


# --- Cerere --------------------------------------------------------------------------------------


class CatalogSiteSelection(Contract):
    site_id: Identifier


class CustomPoint(Contract):
    label: NonEmptyText
    latitude_deg: Latitude
    longitude_deg: LongitudeInput


class CustomSiteSelection(Contract):
    custom: CustomPoint


class EarthCriterion(Contract):
    kind: Literal["center_above_horizon"]
    # Pragul implicit este provizoriu (decizia D-04 [ASTRO]); cererea îl declară explicit.
    min_elevation_deg: Elevation


class SimulationRequest(Contract):
    sites: list[CatalogSiteSelection | CustomSiteSelection] = Field(min_length=1, max_length=4)
    frame_id: FrameId
    start_utc: UtcTimestamp
    end_utc: UtcTimestamp
    observer_height_m: NonNegative
    solar_criterion: Literal["disc_center"]
    earth_criterion: EarthCriterion
    terrain_mode: TerrainMode
    series_step_s: PositiveInt | None = None
    # Rezervat bonusului „putere relativă” (P1); în versiunea de schemă 0.1.0 este mereu null.
    panel: None = None

    @model_validator(mode="after")
    def _interval(self) -> "SimulationRequest":
        if not _strictly_after(self.start_utc, self.end_utc):
            raise ValueError("end_utc trebuie să fie după start_utc")
        return self


# --- Rezultat ------------------------------------------------------------------------------------


class ResultSite(Contract):
    site_ref: Identifier
    label: NonEmptyText
    kind: Literal["catalog", "custom"]
    catalog_id: Identifier | None
    latitude_deg: Latitude
    longitude_deg: Longitude
    frame_id: FrameId
    terrain_elevation_m: float | None
    observer_height_m: NonNegative
    on_reference_surface: bool
    azimuth_convention: Literal["standard", "pole_meridian"]
    coordinates_rounded: bool

    @model_validator(mode="after")
    def _consistency(self) -> "ResultSite":
        if (self.kind == "catalog") != (self.catalog_id is not None):
            raise ValueError("catalog_id este obligatoriu pentru kind=catalog și interzis altfel")
        if self.azimuth_convention != azimuth_convention(self.latitude_deg):
            raise ValueError("azimuth_convention nu corespunde latitudinii")
        return self


class BodySeries(Contract):
    azimuth_deg: list[Azimuth]
    elevation_deg: list[Elevation]
    distance_km: list[Positive]
    angular_radius_deg: list[AngularRadius]
    horizon_elevation_deg: list[Elevation | None]
    visible: list[bool | None]

    def lengths(self) -> set[int]:
        return {
            len(self.azimuth_deg),
            len(self.elevation_deg),
            len(self.distance_km),
            len(self.angular_radius_deg),
            len(self.horizon_elevation_deg),
            len(self.visible),
        }


class SiteSeries(Contract):
    site_ref: Identifier
    step_s: Positive
    time_utc: list[UtcTimestamp] = Field(min_length=1)
    sun: BodySeries
    earth: BodySeries

    @model_validator(mode="after")
    def _parallel_and_ordered(self) -> "SiteSeries":
        n = len(self.time_utc)
        if self.sun.lengths() != {n} or self.earth.lengths() != {n}:
            raise ValueError("toate tablourile seriei trebuie să aibă lungimea lui time_utc")
        times = [parse_utc(t) for t in self.time_utc]
        if any(b <= a for a, b in itertools.pairwise(times)):
            raise ValueError("time_utc trebuie să fie strict crescător")
        return self


class Event(Contract):
    body: Body
    type: Literal["appearance", "disappearance"]
    cause: Literal["terrain", "idealized_horizon"]
    time_utc: UtcTimestamp
    azimuth_deg: Azimuth
    elevation_deg: Elevation
    obstacle_distance_m: NonNegative | None
    refinement_tolerance_s: Positive


class BodyEvents(Contract):
    status: Literal["found", "none_in_interval", "unavailable"]
    reason: str | None
    events: list[Event]

    @model_validator(mode="after")
    def _status_consistency(self) -> "BodyEvents":
        if (self.status == "found") != bool(self.events):
            raise ValueError("status=found dacă și numai dacă lista events nu este goală")
        if (self.status == "unavailable") != bool(self.reason):
            raise ValueError("reason este obligatoriu pentru status=unavailable și interzis altfel")
        return self


class SiteEvents(Contract):
    site_ref: Identifier
    sun: BodyEvents
    earth: BodyEvents

    @model_validator(mode="after")
    def _bodies_match(self) -> "SiteEvents":
        for body in ("sun", "earth"):
            group: BodyEvents = getattr(self, body)
            if any(event.body != body for event in group.events):
                raise ValueError(f"evenimentele din {body} trebuie să aibă body={body}")
        return self


class TimeInterval(Contract):
    start_utc: UtcTimestamp
    end_utc: UtcTimestamp
    truncated_start: bool
    truncated_end: bool

    @model_validator(mode="after")
    def _ordered(self) -> "TimeInterval":
        if not _strictly_after(self.start_utc, self.end_utc):
            raise ValueError("end_utc trebuie să fie după start_utc")
        return self


class SiteSummary(Contract):
    site_ref: Identifier
    sun_visible_duration_s: NonNegative | None
    sun_visible_fraction: Fraction | None
    earth_visible_duration_s: NonNegative | None
    both_visible_duration_s: NonNegative | None
    sun_intervals: list[TimeInterval]
    earth_windows: list[TimeInterval]


class DemProductUse(Contract):
    product_id: Identifier
    role: TerrainRole


class SiteHorizon(Contract):
    site_ref: Identifier
    mode: TerrainMode
    azimuth_step_deg: Annotated[float, Field(gt=0.0, le=360.0)]
    elevation_deg: list[Elevation | None]
    obstacle_distance_m: list[NonNegative | None]
    quality: list[Literal["complete", "partial", "no_data"]]
    max_search_distance_m: Positive | None
    coverage_fraction: Fraction
    dem_products: list[DemProductUse]

    @model_validator(mode="after")
    def _consistency(self) -> "SiteHorizon":
        count = 360.0 / self.azimuth_step_deg
        if abs(count - round(count)) > 1e-9:
            raise ValueError("azimuth_step_deg trebuie să dividă exact 360")
        n = round(count)
        if {len(self.elevation_deg), len(self.obstacle_distance_m), len(self.quality)} != {n}:
            raise ValueError(f"profilul trebuie să aibă {n} valori (360 / azimuth_step_deg)")
        for elevation, quality in zip(self.elevation_deg, self.quality, strict=True):
            if (elevation is None) != (quality == "no_data"):
                raise ValueError("elevation_deg este null dacă și numai dacă quality=no_data")
        if self.mode == "idealized_local_plane":
            if self.dem_products or self.max_search_distance_m is not None:
                raise ValueError("modul idealizat nu folosește produse DEM sau rază de căutare")
            if any(e != 0.0 for e in self.elevation_deg) or set(self.quality) != {"complete"}:
                raise ValueError("modul idealizat are orizontul la 0° pentru orice azimut")
        elif not self.dem_products:
            raise ValueError("modul dem cere cel puțin un produs DEM")
        return self


class SiteTerrain(Contract):
    site_ref: Identifier
    available: bool
    reason: str | None
    terrain_id: Identifier | None
    product_id: Identifier | None
    calc_resolution_m: Positive | None
    visual_resolutions_m: list[Positive]
    frame_id: FrameId | None

    @model_validator(mode="after")
    def _consistency(self) -> "SiteTerrain":
        required = (self.terrain_id, self.product_id, self.calc_resolution_m, self.frame_id)
        if self.available and any(value is None for value in required):
            raise ValueError(
                "terenul disponibil cere terrain_id, product_id, calc_resolution_m, frame_id"
            )
        if not self.available and not self.reason:
            raise ValueError("terenul indisponibil cere reason")
        return self


class KernelFileUse(Contract):
    filename: NonEmptyText
    sha256: Sha256 | None


class KernelProfileUse(Contract):
    profile_id: NonEmptyText
    files: list[KernelFileUse]


class Provenance(Contract):
    app_version: NonEmptyText
    computed_at_utc: UtcTimestamp
    source_mode: Literal["live", "precomputed"]
    kernel_profile: KernelProfileUse
    frame_id: FrameId
    # Corecția de aberație folosită (provizoriu „LT+S”, decizia D-02 [ASTRO]).
    aberration_correction: NonEmptyText
    body_radii_km: dict[str, Positive]
    dem_products: list[DemProductUse]
    horizon_parameters: dict[str, ParameterValue]
    event_parameters: dict[str, ParameterValue]
    criteria: dict[str, ParameterValue]


class QualityIssue(Contract):
    code: Annotated[str, Field(pattern=r"^[a-z0-9_.]+$")]
    severity: Literal["info", "warning", "error"]
    site_ref: Identifier | None
    # Calea câmpului afectat, de exemplu `summary.sun_visible_fraction`.
    field: str | None
    message_key: NonEmptyText


class NotComputed(Contract):
    group: ResultGroup
    site_ref: Identifier
    reason: NonEmptyText


class Quality(Contract):
    issues: list[QualityIssue]
    not_computed: list[NotComputed]
    approximations: list[NonEmptyText]
    limits: list[NonEmptyText]


class SimulationResult(Contract):
    schema_version: SchemaVersion
    request: SimulationRequest
    sites: list[ResultSite] = Field(min_length=1, max_length=4)
    series: list[SiteSeries]
    events: list[SiteEvents]
    summary: list[SiteSummary]
    horizon: list[SiteHorizon]
    terrain: list[SiteTerrain]
    provenance: Provenance
    quality: Quality

    @model_validator(mode="after")
    def _consistency(self) -> "SimulationResult":
        refs = [site.site_ref for site in self.sites]
        if len(refs) != len(set(refs)):
            raise ValueError("site_ref trebuie să fie unic")
        if len(refs) != len(self.request.sites):
            raise ValueError("sites trebuie să corespundă siturilor din cerere")
        frames = {self.request.frame_id, self.provenance.frame_id} | {
            s.frame_id for s in self.sites
        }
        if len(frames) != 1:
            raise ValueError("cererea, proveniența și siturile trebuie să folosească același cadru")

        not_computed = {(nc.group, nc.site_ref) for nc in self.quality.not_computed}
        present_by_group: dict[ResultGroup, list[str]] = {
            "series": [entry.site_ref for entry in self.series],
            "events": [entry.site_ref for entry in self.events],
            "summary": [entry.site_ref for entry in self.summary],
            "horizon": [entry.site_ref for entry in self.horizon],
            "terrain": [entry.site_ref for entry in self.terrain],
        }
        for group in RESULT_GROUPS:
            present = present_by_group[group]
            if len(present) != len(set(present)):
                raise ValueError(f"{group}: cel mult o intrare pe sit")
            for ref in present:
                if ref not in refs:
                    raise ValueError(f"{group}: site_ref necunoscut {ref!r}")
            for ref in refs:
                if (ref in present) == ((group, ref) in not_computed):
                    raise ValueError(
                        f"{group}/{ref}: grupul trebuie să existe sau să fie declarat în "
                        "quality.not_computed (exact una dintre variante)"
                    )
        if self.request.terrain_mode != "dem" and any(h.mode == "dem" for h in self.horizon):
            raise ValueError("profilurile de orizont trebuie să folosească modul de teren cerut")

        self._unknown_values_have_reasons()
        return self

    def _unknown_values_have_reasons(self) -> None:
        explained = {(i.site_ref, i.field) for i in self.quality.issues}

        def require(site_ref: str, field: str) -> None:
            if (site_ref, field) not in explained:
                raise ValueError(
                    f"{field} este null pentru {site_ref!r} fără o intrare în quality.issues"
                )

        for site in self.sites:
            if site.terrain_elevation_m is None:
                require(site.site_ref, "sites.terrain_elevation_m")
        for summary in self.summary:
            for name in (
                "sun_visible_duration_s",
                "sun_visible_fraction",
                "earth_visible_duration_s",
                "both_visible_duration_s",
            ):
                if getattr(summary, name) is None:
                    require(summary.site_ref, f"summary.{name}")
        for series in self.series:
            for body in ("sun", "earth"):
                body_series: BodySeries = getattr(series, body)
                for name in ("horizon_elevation_deg", "visible"):
                    if any(value is None for value in getattr(body_series, name)):
                        require(series.site_ref, f"series.{body}.{name}")
        for horizon in self.horizon:
            if any(value is None for value in horizon.elevation_deg):
                require(horizon.site_ref, "horizon.elevation_deg")


# --- Starea simulării ----------------------------------------------------------------------------

SimulationState = Literal["queued", "running", "done", "failed"]


class SimulationAccepted(Contract):
    id: Identifier
    status: SimulationState
    cache_hit: bool


class Progress(Contract):
    stage: NonEmptyText
    completed_fraction: Fraction


class SimulationStatus(Contract):
    id: Identifier
    status: SimulationState
    progress: Progress | None
    error: Problem | None
    result: SimulationResult | None

    @model_validator(mode="after")
    def _payload_matches_status(self) -> "SimulationStatus":
        if (self.status == "done") != (self.result is not None):
            raise ValueError("result este prezent dacă și numai dacă status=done")
        if (self.status == "failed") != (self.error is not None):
            raise ValueError("error este prezent dacă și numai dacă status=failed")
        return self
