"""Simularea: modul idealizat (orizont fix la 0°, E06) și modul `dem` (orizont din DEM, E09).

Modul `dem` (E09) folosește profilul H(a) calculat din rasterele DEM (api/horizon.py): seria
conține `horizon_elevation_deg = H(a(t))`, interpolat liniar între azimuturile profilului, iar
observatorul stă pe teren (altitudinea din rasterul de calcul). Vizibilitatea față de relief,
evenimentele și indicatorii sunt etapa E10: în modul `dem` câmpul `visible` este `null` cu motiv,
iar grupurile `events` și `summary` apar în `quality.not_computed`. Nu există trecere tăcută la
modul idealizat.

Folosește motorul astronomic existent (`astro.bodies.body_direction`); nu există un al doilea motor.
Modul idealizat NU include efectele terenului local: orizontul este planul local la 0° elevație,
observatorul se află pe sfera de referință la înălțimea `observer_height_m`. Elevația din catalog nu
se folosește.

Criterii (provizorii, deciziile D-04 și D-16 [ASTRO] deschise):
- Soarele este vizibil când elevația centrului discului este ≥ 0° (`solar_criterion = disc_center`);
- Pământul este vizibil când elevația centrului este ≥ `earth_criterion.min_elevation_deg`
  (deasupra orizontului local, care este 0° în acest mod).

Evenimentele se caută pe o grilă de scanare, apoi se rafinează prin bisecție la 1 ms. O pereche de
treceri între două eșantioane vecine ale grilei nu poate fi detectată; pasul grilei este în
proveniență.
Pașii seriei și ai grilei se numără pe scala civilă UTC (fără secundă intercalară inserată).
"""

import math
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Final

from lunarhorizon import __version__
from lunarhorizon.astro.bodies import Body, ObserverSite, body_direction, body_radius_km
from lunarhorizon.astro.kernels import SPICE_LOCK, LoadedProfile, activate
from lunarhorizon.contracts.horizon import HorizonProfile
from lunarhorizon.contracts.manifests import TerrainManifest
from lunarhorizon.contracts.simulation import (
    BodyEvents,
    BodySeries,
    DemProductUse,
    Event,
    KernelFileUse,
    KernelProfileUse,
    NotComputed,
    Provenance,
    Quality,
    QualityIssue,
    ResultSite,
    SimulationRequest,
    SimulationResult,
    SiteEvents,
    SiteHorizon,
    SiteSeries,
    SiteSummary,
    SiteTerrain,
    TimeInterval,
)
from lunarhorizon.core.conventions import APPARENT_CORRECTION, SCHEMA_VERSION
from lunarhorizon.core.coords import azimuth_convention
from lunarhorizon.core.errors import ErrorCode, LunarHorizonError
from lunarhorizon.core.utc import format_utc, parse_utc
from lunarhorizon.terrain.horizon import interpolate_horizon

BODIES: tuple[Body, ...] = ("sun", "earth")
REFINEMENT_MS = 1
SCAN_STEP_BASE_S = 900
MAX_SCAN_SAMPLES = 20_000
HORIZON_AZIMUTH_STEP_DEG = 1.0
SERIES_STEP_CANDIDATES_S = (60, 300, 600, 900, 1800, 3600, 7200, 21600, 43200, 86400)
TARGET_SERIES_POINTS = 1500

ProgressCallback = Callable[[str, float], None]
Interval = tuple[int, int, bool, bool]  # start_ms, end_ms, truncated_start, truncated_end
# azimut (None la zenit/nadir), elevație, distanță_km, rază_unghiulară
Direction = tuple[float | None, float, float, float]


@dataclass(frozen=True)
class SiteInput:
    """Un sit rezolvat din cerere: poziția în cadrul cererii, fără înălțime a terenului."""

    site_ref: str
    label: str
    kind: str  # "catalog" | "custom"
    catalog_id: str | None
    latitude_deg: float
    longitude_deg: float


@dataclass(frozen=True)
class DemSiteInput:
    """Pentru modul `dem`: profilul de orizont (disponibil) și produsul de teren al sitului."""

    horizon: HorizonProfile
    terrain: TerrainManifest


E10_PENDING: Final = (
    "Terrain-based visibility, events and indicators are stage E10; not computed in DEM mode yet."
)


def default_series_step_s(duration_s: float) -> int:
    for step in SERIES_STEP_CANDIDATES_S:
        if duration_s / step + 1 <= TARGET_SERIES_POINTS:
            return step
    return SERIES_STEP_CANDIDATES_S[-1]


def scan_step_s(duration_s: float) -> int:
    """Pasul grilei de scanare: multiplu de 60 s, ≥ 900 s, cu cel mult MAX_SCAN_SAMPLES puncte."""
    needed = math.ceil(duration_s / MAX_SCAN_SAMPLES / 60.0) * 60
    return max(SCAN_STEP_BASE_S, needed)


def _ms_between(start: datetime, end: datetime) -> int:
    delta = end - start
    return delta.days * 86_400_000 + delta.seconds * 1000 + delta.microseconds // 1000


def _utc_at(start: datetime, offset_ms: int) -> str:
    return format_utc(start + timedelta(milliseconds=offset_ms))


class _Evaluator:
    """Direcțiile corpurilor pentru un sit, cu memorarea eșantioanelor deja calculate."""

    def __init__(
        self,
        profile: LoadedProfile,
        site: SiteInput,
        observer_height_m: float,
        surface_height_m: float = 0.0,
    ) -> None:
        self.profile = profile
        self.observer = ObserverSite(
            site.latitude_deg, site.longitude_deg, surface_height_m, observer_height_m
        )
        self._memo: dict[tuple[Body, str], Direction] = {}

    def direction(self, body: Body, utc: str) -> Direction:
        key = (body, utc)
        cached = self._memo.get(key)
        if cached is not None:
            return cached
        # Lacătul acoperă activarea și calculul: alt fir nu poate comuta profilul între ele.
        with SPICE_LOCK:
            activate(self.profile)
            result = body_direction(self.profile, self.observer, body, utc, APPARENT_CORRECTION)
        value = (
            result.azimuth_deg,
            result.elevation_deg,
            result.distance_km,
            result.angular_radius_deg,
        )
        self._memo[key] = value
        return value


def _azimuth_issue(site_ref: str, field: str) -> QualityIssue:
    return QualityIssue(
        code="azimuth_undefined",
        severity="info",
        site_ref=site_ref,
        field=field,
        message_key="quality.azimuth_undefined_zenith_nadir",
    )


def _intervals(
    states: list[bool], crossings: list[tuple[int, bool]], total_ms: int
) -> list[Interval]:
    """Intervalele de vizibilitate, din starea la început și din trecerile rafinate."""
    result: list[Interval] = []
    open_at: int | None = 0 if states[0] else None
    truncated_start = states[0]
    for moment, becomes_visible in crossings:
        if becomes_visible:
            open_at, truncated_start = moment, False
        elif open_at is not None:
            if moment > open_at:
                result.append((open_at, moment, truncated_start, False))
            open_at = None
    if open_at is not None and total_ms > open_at:
        result.append((open_at, total_ms, truncated_start, True))
    return result


def _overlap_ms(a: list[Interval], b: list[Interval]) -> int:
    total, i, j = 0, 0, 0
    while i < len(a) and j < len(b):
        low, high = max(a[i][0], b[j][0]), min(a[i][1], b[j][1])
        if high > low:
            total += high - low
        if a[i][1] < b[j][1]:
            i += 1
        else:
            j += 1
    return total


def _to_interval(start: datetime, item: Interval) -> TimeInterval:
    return TimeInterval(
        start_utc=_utc_at(start, item[0]),
        end_utc=_utc_at(start, item[1]),
        truncated_start=item[2],
        truncated_end=item[3],
    )


def _scan_body(
    evaluator: _Evaluator,
    body: Body,
    threshold_deg: float,
    start: datetime,
    scan_points: list[int],
    total_ms: int,
) -> tuple[BodyEvents, list[Interval]]:
    def visible(offset_ms: int) -> bool:
        return evaluator.direction(body, _utc_at(start, offset_ms))[1] >= threshold_deg

    states = [visible(ms) for ms in scan_points]
    crossings: list[tuple[int, bool]] = []
    found: list[Event] = []
    for k in range(len(scan_points) - 1):
        if states[k] == states[k + 1]:
            continue
        low, high, low_state = scan_points[k], scan_points[k + 1], states[k]
        while high - low > REFINEMENT_MS:
            middle = (low + high) // 2
            if visible(middle) == low_state:
                low = middle
            else:
                high = middle
        moment = _utc_at(start, high)
        azimuth, elevation, _, _ = evaluator.direction(body, moment)
        crossings.append((high, not low_state))
        found.append(
            Event(
                body=body,
                type="disappearance" if low_state else "appearance",
                cause="idealized_horizon",
                time_utc=moment,
                azimuth_deg=azimuth,
                elevation_deg=elevation,
                obstacle_distance_m=None,
                refinement_tolerance_s=REFINEMENT_MS / 1000.0,
            )
        )
    events = BodyEvents(status="found" if found else "none_in_interval", reason=None, events=found)
    return events, _intervals(states, crossings, total_ms)


def _series_body(
    evaluator: _Evaluator, body: Body, threshold_deg: float, start: datetime, series_ms: list[int]
) -> BodySeries:
    rows = [evaluator.direction(body, _utc_at(start, ms)) for ms in series_ms]
    return BodySeries(
        azimuth_deg=[r[0] for r in rows],
        elevation_deg=[r[1] for r in rows],
        distance_km=[r[2] for r in rows],
        angular_radius_deg=[r[3] for r in rows],
        horizon_elevation_deg=[0.0] * len(rows),
        visible=[r[1] >= threshold_deg for r in rows],
    )


def _series_dem(
    evaluator: _Evaluator, horizon: HorizonProfile, start: datetime, series_ms: list[int]
) -> tuple[BodySeries, BodySeries]:
    """Seria în modul `dem`: H(a(t)) din profil; `visible` rămâne necalculat (E10)."""
    result: list[BodySeries] = []
    for body in BODIES:
        rows = [evaluator.direction(body, _utc_at(start, ms)) for ms in series_ms]
        result.append(
            BodySeries(
                azimuth_deg=[r[0] for r in rows],
                elevation_deg=[r[1] for r in rows],
                distance_km=[r[2] for r in rows],
                angular_radius_deg=[r[3] for r in rows],
                horizon_elevation_deg=[
                    None
                    if r[0] is None
                    else interpolate_horizon(horizon.elevation_deg, horizon.azimuth_step_deg, r[0])
                    for r in rows
                ],
                visible=[None] * len(rows),
            )
        )
    return result[0], result[1]


def simulate_idealized(
    request: SimulationRequest,
    sites: list[SiteInput],
    profile: LoadedProfile,
    progress: ProgressCallback | None = None,
    dem: dict[str, DemSiteInput] | None = None,
) -> SimulationResult:
    """Rezultatul complet pentru `terrain_mode = idealized_local_plane` sau `dem` (cu `dem` dat).

    `request.series_step_s` trebuie să fie deja stabilit. Ridică `LunarHorizonError` pentru
    acoperire temporală. Azimutul nedefinit (zenit/nadir) devine `null`, cu motiv în
    `quality.issues`.
    """
    dem_mode = request.terrain_mode == "dem"
    if dem_mode and (dem is None or any(site.site_ref not in dem for site in sites)):
        raise LunarHorizonError(
            ErrorCode.OUT_OF_DEM_COVERAGE,
            "terrain_mode=dem cere profilul de orizont din DEM pentru fiecare sit; modul "
            "idealizat nu se substituie automat",
        )
    if not dem_mode and dem:
        raise ValueError("profilurile DEM se folosesc numai cu terrain_mode=dem")
    if request.series_step_s is None:
        raise ValueError("series_step_s trebuie stabilit înaintea simulării")
    report = progress or (lambda _stage, _fraction: None)
    start = parse_utc(request.start_utc)
    total_ms = _ms_between(start, parse_utc(request.end_utc))
    series_ms = list(range(0, total_ms + 1, request.series_step_s * 1000))
    scan_ms = scan_step_s(total_ms / 1000.0) * 1000
    scan_points = sorted({*range(0, total_ms, scan_ms), total_ms})
    thresholds: dict[Body, float] = {
        "sun": 0.0,
        "earth": request.earth_criterion.min_elevation_deg,
    }
    total_s = total_ms / 1000.0

    result_sites: list[ResultSite] = []
    series: list[SiteSeries] = []
    events: list[SiteEvents] = []
    summary: list[SiteSummary] = []
    horizon: list[SiteHorizon] = []
    terrain: list[SiteTerrain] = []
    issues: list[QualityIssue] = []
    not_computed: list[NotComputed] = []
    count = round(360.0 / HORIZON_AZIMUTH_STEP_DEG)

    for index, site in enumerate(sites):
        stage = f"sit {index + 1}/{len(sites)}"
        report(stage, index / len(sites))
        if dem_mode:
            assert dem is not None
            out = _Out()
            _dem_site(request, site, dem[site.site_ref], profile, start, series_ms, out)
            result_sites.extend(out.sites)
            series.extend(out.series)
            horizon.extend(out.horizon)
            terrain.extend(out.terrain)
            issues.extend(out.issues)
            not_computed.extend(out.not_computed)
            report(stage, (index + 1.0) / len(sites))
            continue
        evaluator = _Evaluator(profile, site, request.observer_height_m)
        body_events: dict[Body, BodyEvents] = {}
        intervals: dict[Body, list[Interval]] = {}
        body_series: dict[Body, BodySeries] = {}
        # Un sit se calculează sub același lacăt: comutarea profilului între eșantioane ar reîncărca
        # kernelurile la fiecare apel; alt fir așteaptă terminarea sitului.
        with SPICE_LOCK:
            activate(profile)
            for body in BODIES:
                body_events[body], intervals[body] = _scan_body(
                    evaluator, body, thresholds[body], start, scan_points, total_ms
                )
                body_series[body] = _series_body(
                    evaluator, body, thresholds[body], start, series_ms
                )

        sun_ms = sum(end - begin for begin, end, _, _ in intervals["sun"])
        earth_ms = sum(end - begin for begin, end, _, _ in intervals["earth"])
        result_sites.append(
            ResultSite(
                site_ref=site.site_ref,
                label=site.label,
                kind="catalog" if site.kind == "catalog" else "custom",
                catalog_id=site.catalog_id,
                latitude_deg=site.latitude_deg,
                longitude_deg=site.longitude_deg,
                frame_id=request.frame_id,
                terrain_elevation_m=None,
                observer_height_m=request.observer_height_m,
                on_reference_surface=True,
                azimuth_convention=azimuth_convention(site.latitude_deg),
                coordinates_rounded=False,
            )
        )
        for body in BODIES:
            if any(value is None for value in body_series[body].azimuth_deg):
                issues.append(_azimuth_issue(site.site_ref, f"series.{body}.azimuth_deg"))
            if any(event.azimuth_deg is None for event in body_events[body].events):
                issues.append(_azimuth_issue(site.site_ref, f"events.{body}.azimuth_deg"))
        issues.append(
            QualityIssue(
                code="terrain_elevation_not_used",
                severity="info",
                site_ref=site.site_ref,
                field="sites.terrain_elevation_m",
                message_key="quality.idealized_reference_surface",
            )
        )
        series.append(
            SiteSeries(
                site_ref=site.site_ref,
                step_s=float(request.series_step_s),
                time_utc=[_utc_at(start, ms) for ms in series_ms],
                sun=body_series["sun"],
                earth=body_series["earth"],
            )
        )
        events.append(
            SiteEvents(site_ref=site.site_ref, sun=body_events["sun"], earth=body_events["earth"])
        )
        summary.append(
            SiteSummary(
                site_ref=site.site_ref,
                sun_visible_duration_s=sun_ms / 1000.0,
                sun_visible_fraction=sun_ms / 1000.0 / total_s,
                earth_visible_duration_s=earth_ms / 1000.0,
                both_visible_duration_s=_overlap_ms(intervals["sun"], intervals["earth"]) / 1000.0,
                sun_intervals=[_to_interval(start, i) for i in intervals["sun"]],
                earth_windows=[_to_interval(start, i) for i in intervals["earth"]],
            )
        )
        horizon.append(
            SiteHorizon(
                site_ref=site.site_ref,
                mode="idealized_local_plane",
                azimuth_step_deg=HORIZON_AZIMUTH_STEP_DEG,
                elevation_deg=[0.0] * count,
                obstacle_distance_m=[None] * count,
                quality=["complete"] * count,
                max_search_distance_m=None,
                coverage_fraction=1.0,
                dem_products=[],
            )
        )
        terrain.append(
            SiteTerrain(
                site_ref=site.site_ref,
                available=False,
                reason="Idealized mode: local terrain is not included.",
                terrain_id=None,
                product_id=None,
                calc_resolution_m=None,
                visual_resolutions_m=[],
                frame_id=None,
            )
        )
        report(stage, (index + 1.0) / len(sites))

    scan_s = scan_ms // 1000
    if dem_mode:
        assert dem is not None
        return _dem_result(
            request, profile, dem, result_sites, series, horizon, terrain, issues, not_computed
        )
    provenance = Provenance(
        app_version=__version__,
        computed_at_utc=format_utc(datetime.now(tz=UTC)),
        source_mode="live",
        kernel_profile=KernelProfileUse(
            profile_id=profile.profile_id,
            files=[
                KernelFileUse(filename=path.name, sha256=digest or None)
                for path, digest in zip(profile.paths, profile.sha256, strict=True)
            ],
        ),
        frame_id=request.frame_id,
        aberration_correction=APPARENT_CORRECTION,
        body_radii_km={body: body_radius_km(body, profile) for body in BODIES},
        dem_products=[],
        horizon_parameters={
            "mode": "idealized_local_plane",
            "fixed_horizon_elevation_deg": 0.0,
            "azimuth_step_deg": HORIZON_AZIMUTH_STEP_DEG,
        },
        event_parameters={
            "method": "scan_and_bisection",
            "scan_step_s": scan_s,
            "refinement_tolerance_s": REFINEMENT_MS / 1000.0,
        },
        criteria={
            "solar_criterion": request.solar_criterion,
            "solar_threshold_deg": 0.0,
            "earth_criterion": request.earth_criterion.kind,
            "earth_min_elevation_deg": request.earth_criterion.min_elevation_deg,
        },
    )
    quality = Quality(
        issues=issues,
        not_computed=[],
        approximations=[
            "Idealized mode: flat local horizon at 0°, local terrain not included; "
            "this is not a terrain-based result.",
            "Sun visibility uses the disc centre (angular radius not applied); no refraction.",
            "Apparent positions with the CN+S correction (D-02, confirmed by the astronomers; no "
            "gravitational light deflection).",
            "The observer is on the reference sphere; the catalog elevation is not used.",
        ],
        limits=[
            f"Events are searched on a {scan_s} s grid and refined to "
            f"{REFINEMENT_MS / 1000.0} s; two crossings between neighbouring samples are missed.",
            "Steps are counted on the civil UTC scale; no leap second is inserted.",
            "DEM horizon coverage is not validated; terrain mode 'dem' is not available yet.",
            "Earth threshold and visibility criteria are provisional (D-04, D-16 [ASTRO]).",
            "Catalog coordinates are adopted in MOON_ME_DE440_ME421 as a hypothesis (E04).",
        ],
    )
    return SimulationResult(
        schema_version=SCHEMA_VERSION,
        request=request,
        sites=result_sites,
        series=series,
        events=events,
        summary=summary,
        horizon=horizon,
        terrain=terrain,
        provenance=provenance,
        quality=quality,
    )


@dataclass
class _Out:
    sites: list[ResultSite] = field(default_factory=list)
    series: list[SiteSeries] = field(default_factory=list)
    horizon: list[SiteHorizon] = field(default_factory=list)
    terrain: list[SiteTerrain] = field(default_factory=list)
    issues: list[QualityIssue] = field(default_factory=list)
    not_computed: list[NotComputed] = field(default_factory=list)


def _issue(code: str, severity: str, site_ref: str, field_name: str, key: str) -> QualityIssue:
    return QualityIssue.model_validate(
        {
            "code": code,
            "severity": severity,
            "site_ref": site_ref,
            "field": field_name,
            "message_key": key,
        }
    )


def _dem_site(
    request: SimulationRequest,
    site: SiteInput,
    inputs: DemSiteInput,
    profile: LoadedProfile,
    start: datetime,
    series_ms: list[int],
    out: _Out,
) -> None:
    horizon = inputs.horizon
    if horizon.status == "unavailable" or horizon.observer_terrain_elevation_m is None:
        raise LunarHorizonError(
            ErrorCode.OUT_OF_DEM_COVERAGE,
            f"{site.site_ref}: orizontul DEM este indisponibil ({horizon.reason_code})",
        )
    surface = horizon.observer_terrain_elevation_m
    evaluator = _Evaluator(profile, site, request.observer_height_m, surface)
    with SPICE_LOCK:
        activate(profile)
        sun, earth = _series_dem(evaluator, horizon, start, series_ms)
    ref = site.site_ref
    out.sites.append(
        ResultSite(
            site_ref=ref,
            label=site.label,
            kind="catalog" if site.kind == "catalog" else "custom",
            catalog_id=site.catalog_id,
            latitude_deg=site.latitude_deg,
            longitude_deg=site.longitude_deg,
            frame_id=request.frame_id,
            terrain_elevation_m=surface,
            observer_height_m=request.observer_height_m,
            on_reference_surface=False,
            azimuth_convention=azimuth_convention(site.latitude_deg),
            coordinates_rounded=False,
        )
    )
    for body, body_series in (("sun", sun), ("earth", earth)):
        if any(value is None for value in body_series.azimuth_deg):
            out.issues.append(_azimuth_issue(ref, f"series.{body}.azimuth_deg"))
        if any(value is None for value in body_series.horizon_elevation_deg):
            out.issues.append(
                _issue(
                    "horizon_no_data",
                    "warning",
                    ref,
                    f"series.{body}.horizon_elevation_deg",
                    "quality.horizon_no_data_or_undefined_azimuth",
                )
            )
        out.issues.append(
            _issue(
                "visibility_pending_e10",
                "info",
                ref,
                f"series.{body}.visible",
                "quality.terrain_visibility_not_computed",
            )
        )
    if any(value is None for value in horizon.elevation_deg):
        out.issues.append(
            _issue(
                "horizon_no_data",
                "warning",
                ref,
                "horizon.elevation_deg",
                "quality.horizon_no_data",
            )
        )
    if horizon.status == "partial":
        out.issues.append(
            _issue("horizon_partial", "warning", ref, "horizon.quality", "quality.horizon_partial")
        )
    out.series.append(
        SiteSeries(
            site_ref=ref,
            step_s=float(request.series_step_s or 0),
            time_utc=[_utc_at(start, ms) for ms in series_ms],
            sun=sun,
            earth=earth,
        )
    )
    out.horizon.append(
        SiteHorizon(
            site_ref=ref,
            mode="dem",
            azimuth_step_deg=horizon.azimuth_step_deg,
            elevation_deg=horizon.elevation_deg,
            obstacle_distance_m=horizon.obstacle_distance_m,
            quality=horizon.quality,
            max_search_distance_m=horizon.max_search_distance_m,
            coverage_fraction=horizon.coverage_fraction,
            dem_products=[
                DemProductUse(product_id=p.product_id, role=p.role) for p in horizon.dem_products
            ],
        )
    )
    manifest = inputs.terrain
    out.terrain.append(
        SiteTerrain(
            site_ref=ref,
            available=True,
            reason=None,
            terrain_id=manifest.terrain_id,
            product_id=manifest.source.product_id,
            calc_resolution_m=manifest.calc_resolution_m,
            visual_resolutions_m=sorted({lod.visual_resolution_m for lod in manifest.lods}),
            frame_id=manifest.frame_id,
        )
    )
    out.not_computed.append(NotComputed(group="events", site_ref=ref, reason=E10_PENDING))
    out.not_computed.append(NotComputed(group="summary", site_ref=ref, reason=E10_PENDING))


def _dem_result(
    request: SimulationRequest,
    profile: LoadedProfile,
    dem: dict[str, DemSiteInput],
    sites: list[ResultSite],
    series: list[SiteSeries],
    horizon: list[SiteHorizon],
    terrain: list[SiteTerrain],
    issues: list[QualityIssue],
    not_computed: list[NotComputed],
) -> SimulationResult:
    profiles = [dem[site.site_ref].horizon for site in sites]
    products: dict[str, DemProductUse] = {}
    for item in profiles:
        for use in item.dem_products:
            products.setdefault(
                use.product_id, DemProductUse(product_id=use.product_id, role=use.role)
            )
    parameters: dict[str, float | int | str | bool] = {"mode": "dem"}
    parameters.update(profiles[0].parameters)
    parameters["parameters_status"] = "provisional (D-08/D-09 open)"
    for item, site in zip(profiles, sites, strict=True):
        parameters[f"cache_key.{site.site_ref}"] = item.cache_key
    provenance = Provenance(
        app_version=__version__,
        computed_at_utc=format_utc(datetime.now(tz=UTC)),
        source_mode="live",
        kernel_profile=KernelProfileUse(
            profile_id=profile.profile_id,
            files=[
                KernelFileUse(filename=path.name, sha256=digest or None)
                for path, digest in zip(profile.paths, profile.sha256, strict=True)
            ],
        ),
        frame_id=request.frame_id,
        aberration_correction=APPARENT_CORRECTION,
        body_radii_km={body: body_radius_km(body, profile) for body in BODIES},
        dem_products=list(products.values()),
        horizon_parameters=parameters,
        event_parameters={"method": "not_computed_e10"},
        criteria={
            "solar_criterion": request.solar_criterion,
            "earth_criterion": request.earth_criterion.kind,
            "earth_min_elevation_deg": request.earth_criterion.min_elevation_deg,
            "terrain_visibility": "not_computed_e10",
        },
    )
    quality = Quality(
        issues=issues,
        not_computed=not_computed,
        approximations=[
            "Horizon H(a) from the DEM calculation rasters (near PGDA product, far LOLA GDR "
            "product), linear between sampled azimuths; the display mesh is not used.",
            "The observer stands on the DEM surface (bilinear height) plus the equipment height.",
            "Apparent positions with the CN+S correction (D-02, confirmed by the astronomers; no "
            "gravitational light deflection).",
        ],
        limits=[
            "Horizon parameters (d_max, radial and azimuth steps, far product) are technical "
            "proposals from the E09 convergence study; D-08/D-09 [GEO] are open.",
            "Terrain-based visibility, events and indicators are stage E10 and are not computed.",
            "The DEM frame MOON_ME_DE421 is a working hypothesis (D-10); no frame conversion.",
            "Near-terrain resolution convergence cannot be shown: 5 m is the finest product.",
        ],
    )
    return SimulationResult(
        schema_version=SCHEMA_VERSION,
        request=request,
        sites=sites,
        series=series,
        events=[],
        summary=[],
        horizon=horizon,
        terrain=terrain,
        provenance=provenance,
        quality=quality,
    )
