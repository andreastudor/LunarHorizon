"""Simularea (E06, E09, E10): direcții, vizibilitate, evenimente și indicatori, în ambele moduri de
teren.

Un singur motor astronomic (`astro.bodies`, corecția `CN+S` din `core.conventions`, D-02) și un
singur lanț de calcul pentru ambele moduri:

- `idealized_local_plane`: orizontul este planul local la 0°; observatorul stă pe sfera de referință
  (+ înălțimea echipamentului); elevația din catalog nu se folosește. Etichetat ca idealizat.
- `dem`: orizontul H(A) vine din profilul DEM fin (E09, pas azimutal `VISIBILITY_AZIMUTH_STEP_DEG`),
  observatorul stă pe teren. Nu există trecere tăcută la modul idealizat.

Vizibilitate (`simulation.visibility`): Soarele după criteriul discului cu arie pozitivă vizibilă
(D-04), Pământul după e > max(H(A), e_min); stările nedeterminate au motiv și nu devin „ascuns”.
Evenimente (`simulation.timeline`): scanare adaptivă pe pas fin, subdiviziune unde criteriul poate
atinge pragul între eșantioane, bisecție la `REFINEMENT_TOLERANCE_S`; contactele tangente sunt
evenimente distincte, iar granițele zonelor fără date nu creează evenimente. Seria pentru slider
este calculată separat, la momentele ei, cu aceleași funcții; evenimentele nu se deduc din serie.

Timpul de scanare se numără pe scala civilă UTC; ET se obține exact prin TT (fără secundă
intercalară în interval) sau, altfel, prin SPICE pentru fiecare eșantion. Eclipsele nu sunt incluse.
"""

import itertools
import math
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Final, Literal

import numpy as np
import spiceypy

from lunarhorizon import __version__
from lunarhorizon.astro.bodies import (
    Body,
    ObserverSite,
    body_direction,
    body_direction_et,
    body_radius_km,
)
from lunarhorizon.astro.kernels import SPICE_LOCK, LoadedProfile, activate
from lunarhorizon.astro.timeconv import utc_to_et
from lunarhorizon.contracts.horizon import HorizonProfile
from lunarhorizon.contracts.manifests import TerrainManifest
from lunarhorizon.contracts.simulation import (
    BodyEvents,
    BodySeries,
    DemProductUse,
    Event,
    KernelFileUse,
    KernelProfileUse,
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
    StateInterval,
    TimeInterval,
)
from lunarhorizon.core.conventions import APPARENT_CORRECTION, SCHEMA_VERSION
from lunarhorizon.core.coords import azimuth_convention
from lunarhorizon.core.errors import ErrorCode, LunarHorizonError
from lunarhorizon.core.utc import format_utc, parse_utc
from lunarhorizon.simulation.timeline import Sample, Segment, Transition, scan
from lunarhorizon.simulation.visibility import (
    DISC_COLUMNS,
    EPS_NUMERIC_DEG,
    EarthVisibility,
    HorizonModel,
    SunVisibility,
    earth_visibility,
    sun_visibility,
)

BODIES: tuple[Body, ...] = ("sun", "earth")
VISIBILITY_ALGORITHM_VERSION: Final = "e10.1"
# Pașii grilei de scanare (s), aleși prin testele de convergență (VALIDARE, E10). În modul DEM,
# pasul Soarelui ține avansul azimutal sub jumătate din pasul profilului fin; subdiviziunea
# acoperă restul.
SCAN_STEP_S: Final[dict[str, dict[Body, float]]] = {
    "idealized_local_plane": {"sun": 300.0, "earth": 600.0},
    "dem": {"sun": 60.0, "earth": 300.0},
}
REFINEMENT_TOLERANCE_S: Final = 1e-3
MIN_SUBDIVISION_STEP_S: Final = 1.0
# Pasul azimutal al profilului fin folosit pentru vizibilitate; profilul afișat rămâne de 0,5°.
VISIBILITY_AZIMUTH_STEP_DEG: Final = 0.025
HORIZON_AZIMUTH_STEP_DEG: Final = 1.0  # profilul plat afișat în modul idealizat
SERIES_STEP_CANDIDATES_S = (60, 300, 600, 900, 1800, 3600, 7200, 21600, 43200, 86400)
TARGET_SERIES_POINTS = 1500
SOLAR_DEFINITION: Final = (
    "Sun visible when any part of the solar disc with positive area is above the modelled horizon "
    "(D-04); exact tangency is not visibility"
)
EARTH_DEFINITION: Final = "Earth centre elevation > max(horizon at its azimuth, minimum elevation)"

ProgressCallback = Callable[[str, float], None]
Criterion = Literal["sun_disc_positive_area", "earth_center_above_horizon_and_threshold"]
CRITERIA: Final[dict[Body, Criterion]] = {
    "sun": "sun_disc_positive_area",
    "earth": "earth_center_above_horizon_and_threshold",
}


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
    """Pentru modul `dem`: profilul afișat (0,5°), profilul fin pentru vizibilitate și terenul."""

    horizon: HorizonProfile
    terrain: TerrainManifest
    visibility_horizon: HorizonProfile | None = None


def default_series_step_s(duration_s: float) -> int:
    for step in SERIES_STEP_CANDIDATES_S:
        if duration_s / step + 1 <= TARGET_SERIES_POINTS:
            return step
    return SERIES_STEP_CANDIDATES_S[-1]


def _ms_between(start: datetime, end: datetime) -> int:
    delta = end - start
    return delta.days * 86_400_000 + delta.seconds * 1000 + delta.microseconds // 1000


def _utc_at(start: datetime, offset_ms: int) -> str:
    return format_utc(start + timedelta(milliseconds=offset_ms))


class _Clock:
    """t (s de la început, scala civilă UTC) → ET, exact prin TT dacă nu există secundă
    intercalară."""

    def __init__(self, request: SimulationRequest, profile: LoadedProfile) -> None:
        self.start = parse_utc(request.start_utc)
        self.total_ms = _ms_between(self.start, parse_utc(request.end_utc))
        self.total_s = self.total_ms / 1000.0
        self.profile = profile
        with SPICE_LOCK:
            activate(profile)
            et0 = utc_to_et(request.start_utc, profile)
            et1 = utc_to_et(request.end_utc, profile)
            self.tt0 = float(spiceypy.unitim(et0, "TDB", "TT"))
            tt1 = float(spiceypy.unitim(et1, "TDB", "TT"))
        self.leap_free = abs((tt1 - self.tt0) - self.total_s) < 1e-6

    def et(self, t: float) -> float:
        if self.leap_free:
            return float(spiceypy.unitim(self.tt0 + t, "TT", "TDB"))
        return utc_to_et(self.utc(t), self.profile)

    def utc(self, t: float) -> str:
        return _utc_at(self.start, round(t * 1000.0))


@dataclass(frozen=True)
class _Direction:
    azimuth_deg: float | None
    elevation_deg: float
    distance_km: float
    angular_radius_deg: float


class _Evaluator:
    """Direcțiile unui sit: seria prin UTC (identică cu `body_direction`), scanarea prin ET."""

    def __init__(self, profile: LoadedProfile, observer: ObserverSite, clock: _Clock) -> None:
        self.profile = profile
        self.observer = observer
        self.clock = clock

    def at_utc(self, body: Body, utc: str) -> _Direction:
        with SPICE_LOCK:
            activate(self.profile)
            r = body_direction(self.profile, self.observer, body, utc, APPARENT_CORRECTION)
        return _Direction(r.azimuth_deg, r.elevation_deg, r.distance_km, r.angular_radius_deg)

    def at(self, body: Body, t: float) -> _Direction:
        with SPICE_LOCK:
            activate(self.profile)
            r = body_direction_et(
                self.profile, self.observer, body, self.clock.et(t), "", APPARENT_CORRECTION
            )
        return _Direction(r.azimuth_deg, r.elevation_deg, r.distance_km, r.angular_radius_deg)


def _sun_state(model: HorizonModel, d: _Direction) -> SunVisibility:
    return sun_visibility(model, d.azimuth_deg, d.elevation_deg, d.angular_radius_deg)


def _earth_state(model: HorizonModel, d: _Direction, min_elevation: float) -> EarthVisibility:
    return earth_visibility(model, d.azimuth_deg, d.elevation_deg, min_elevation)


def _sample(state: SunVisibility | EarthVisibility, t: float) -> Sample:
    value = state.clearance_deg if isinstance(state, SunVisibility) else state.margin_deg
    return Sample(t, value, state.eps_deg, state.timeline_state, state.reason)


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


@dataclass
class _SiteOutput:
    site: ResultSite
    series: SiteSeries
    events: SiteEvents
    summary: SiteSummary
    horizon: SiteHorizon
    terrain: SiteTerrain
    issues: list[QualityIssue]
    evaluations: int


def _series(
    evaluator: _Evaluator,
    model: HorizonModel,
    request: SimulationRequest,
    series_ms: list[int],
) -> tuple[BodySeries, BodySeries]:
    start = evaluator.clock.start
    e_min = request.earth_criterion.min_elevation_deg
    result: dict[Body, BodySeries] = {}
    for body in BODIES:
        rows = [evaluator.at_utc(body, _utc_at(start, ms)) for ms in series_ms]
        states: list[SunVisibility | EarthVisibility] = [
            _sun_state(model, d) if body == "sun" else _earth_state(model, d, e_min) for d in rows
        ]
        horizon: list[float | None] = []
        for d in rows:
            if d.azimuth_deg is None:
                horizon.append(None)
            else:
                value = float(model.evaluate(np.array([d.azimuth_deg]))[0][0])
                horizon.append(None if math.isnan(value) else value)
        result[body] = BodySeries(
            azimuth_deg=[d.azimuth_deg for d in rows],
            elevation_deg=[d.elevation_deg for d in rows],
            distance_km=[d.distance_km for d in rows],
            angular_radius_deg=[d.angular_radius_deg for d in rows],
            horizon_elevation_deg=horizon,
            visible=[None if s.state == "undetermined" else s.state != "hidden" for s in states],
            state=[s.state for s in states],
            state_reason=[s.reason for s in states],
            visible_fraction=[s.fraction if isinstance(s, SunVisibility) else None for s in states],
            visible_fraction_uncertainty=[
                s.fraction_uncertainty if isinstance(s, SunVisibility) else None for s in states
            ],
        )
    return result["sun"], result["earth"]


def _segments_ms(segments: list[Segment], total_ms: int) -> list[tuple[int, int, str, str | None]]:
    """Segmentele în ms întregi, fără lungimi nule, unite când au aceeași stare."""
    cuts: list[tuple[int, int, str, str | None]] = []
    for segment in segments:
        a = 0 if segment.start <= 0 else round(segment.start * 1000.0)
        b = total_ms if segment.end >= total_ms / 1000.0 else round(segment.end * 1000.0)
        if cuts:
            a = cuts[-1][1]
        if b <= a:
            continue
        if cuts and (cuts[-1][2], cuts[-1][3]) == (segment.state, segment.reason):
            cuts[-1] = (cuts[-1][0], b, segment.state, segment.reason)
        else:
            cuts.append((a, b, segment.state, segment.reason))
    if cuts and cuts[-1][1] != total_ms:
        last = cuts[-1]
        cuts[-1] = (last[0], total_ms, last[2], last[3])
    return cuts


def _timeline(
    start: datetime, cuts: list[tuple[int, int, str, str | None]], total_ms: int
) -> list[StateInterval]:
    return [
        StateInterval.model_validate(
            {
                "start_utc": _utc_at(start, a),
                "end_utc": _utc_at(start, b),
                "state": state,
                "reason": reason,
                "truncated_start": a == 0,
                "truncated_end": b == total_ms,
            }
        )
        for a, b, state, reason in cuts
    ]


def _duration(cuts: list[tuple[int, int, str, str | None]], state: str) -> float:
    return sum(b - a for a, b, s, _ in cuts if s == state) / 1000.0


def _visible_intervals(
    start: datetime, cuts: list[tuple[int, int, str, str | None]], total_ms: int
) -> list[TimeInterval]:
    return [
        TimeInterval(
            start_utc=_utc_at(start, a),
            end_utc=_utc_at(start, b),
            truncated_start=a == 0,
            truncated_end=b == total_ms,
        )
        for a, b, s, _ in cuts
        if s == "visible"
    ]


def _combined(
    sun: list[tuple[int, int, str, str | None]], earth: list[tuple[int, int, str, str | None]]
) -> tuple[float, float]:
    """(ambele vizibile, ambele necunoscute) în secunde, pe partiția comună a celor două linii."""
    points = sorted({a for a, *_ in sun} | {a for a, *_ in earth} | {sun[-1][1]})
    both_visible = both_unknown = 0

    def state_at(cuts: list[tuple[int, int, str, str | None]], t: int) -> str:
        for a, b, s, _ in cuts:
            if a <= t < b:
                return s
        return cuts[-1][2]

    for a, b in itertools.pairwise(points):
        s, e = state_at(sun, a), state_at(earth, a)
        if s == "visible" and e == "visible":
            both_visible += b - a
        elif s != "hidden" and e != "hidden":
            both_unknown += b - a
    return both_visible / 1000.0, both_unknown / 1000.0


def _events(
    body: Body,
    transitions: list[Transition],
    evaluator: _Evaluator,
    model: HorizonModel,
    request: SimulationRequest,
    total_ms: int,
) -> list[Event]:
    events: list[Event] = []
    start = evaluator.clock.start
    for transition in transitions:
        direction = evaluator.at(body, transition.time)
        if body == "sun":
            state = _sun_state(model, direction)
            cause = "terrain" if model.kind == "dem" else "idealized_horizon"
            obstacle_azimuth = state.contact_azimuth_deg
        else:
            earth = _earth_state(model, direction, request.earth_criterion.min_elevation_deg)
            cause = earth.cause
            obstacle_azimuth = direction.azimuth_deg if cause == "terrain" else None
        lo = max(0, math.floor(transition.window_start * 1000.0))
        hi = min(total_ms, math.ceil(transition.window_end * 1000.0))
        at = min(max(round(transition.time * 1000.0), lo), hi)
        width = transition.window_end - transition.window_start
        events.append(
            Event.model_validate(
                {
                    "body": body,
                    "type": transition.kind,
                    "cause": cause,
                    "criterion": CRITERIA[body],
                    "time_utc": _utc_at(start, at),
                    "window_start_utc": _utc_at(start, lo),
                    "window_end_utc": _utc_at(start, hi),
                    "quality": "refined" if width <= 2 * REFINEMENT_TOLERANCE_S else "window",
                    "azimuth_deg": direction.azimuth_deg,
                    "elevation_deg": direction.elevation_deg,
                    "obstacle_distance_m": (
                        None
                        if obstacle_azimuth is None
                        else model.obstacle_distance_at(obstacle_azimuth)
                    ),
                    "refinement_tolerance_s": REFINEMENT_TOLERANCE_S,
                }
            )
        )
    return events


def _simulate_site(
    request: SimulationRequest,
    site: SiteInput,
    profile: LoadedProfile,
    clock: _Clock,
    dem: DemSiteInput | None,
) -> _SiteOutput:
    mode = request.terrain_mode
    if dem is not None:
        source = dem.visibility_horizon or dem.horizon
        if source.status == "unavailable" or source.observer_terrain_elevation_m is None:
            raise LunarHorizonError(
                ErrorCode.OUT_OF_DEM_COVERAGE,
                f"{site.site_ref}: orizontul DEM este indisponibil ({source.reason_code})",
            )
        model = HorizonModel.from_profile(source)
        surface = source.observer_terrain_elevation_m
    else:
        model = HorizonModel.idealized()
        surface = 0.0
    observer = ObserverSite(
        site.latitude_deg, site.longitude_deg, surface, request.observer_height_m
    )
    evaluator = _Evaluator(profile, observer, clock)
    assert request.series_step_s is not None
    series_ms = list(range(0, clock.total_ms + 1, request.series_step_s * 1000))
    sun_series, earth_series = _series(evaluator, model, request, series_ms)
    e_min = request.earth_criterion.min_elevation_deg

    def sun_eval(t: float) -> Sample:
        return _sample(_sun_state(model, evaluator.at("sun", t)), t)

    def earth_eval(t: float) -> Sample:
        return _sample(_earth_state(model, evaluator.at("earth", t), e_min), t)

    steps = SCAN_STEP_S[mode]
    scans = {
        "sun": scan(
            sun_eval, clock.total_s, steps["sun"], REFINEMENT_TOLERANCE_S, MIN_SUBDIVISION_STEP_S
        ),
        "earth": scan(
            earth_eval,
            clock.total_s,
            steps["earth"],
            REFINEMENT_TOLERANCE_S,
            MIN_SUBDIVISION_STEP_S,
        ),
    }
    cuts = {body: _segments_ms(scans[body].segments, clock.total_ms) for body in BODIES}
    groups: dict[Body, BodyEvents] = {}
    for body in BODIES:
        found = _events(body, scans[body].transitions, evaluator, model, request, clock.total_ms)
        data_gaps = any(s == "unknown" and r != "near_threshold" for *_, s, r in cuts[body])
        if found:
            groups[body] = BodyEvents(status="found", reason=None, events=found)
        elif data_gaps:
            groups[body] = BodyEvents(
                status="unavailable",
                reason=(
                    "Visibility could not be determined during part of the interval (horizon data "
                    "missing or partial); events there are unknown."
                ),
                events=[],
            )
        else:
            groups[body] = BodyEvents(status="none_in_interval", reason=None, events=[])

    start = clock.start
    total = clock.total_s
    sun_visible = _duration(cuts["sun"], "visible")
    both_visible, both_unknown = _combined(cuts["sun"], cuts["earth"])
    summary = SiteSummary(
        site_ref=site.site_ref,
        sun_visible_duration_s=sun_visible,
        sun_visible_fraction=sun_visible / total,
        earth_visible_duration_s=_duration(cuts["earth"], "visible"),
        both_visible_duration_s=both_visible,
        sun_unknown_duration_s=_duration(cuts["sun"], "unknown"),
        earth_unknown_duration_s=_duration(cuts["earth"], "unknown"),
        both_unknown_duration_s=both_unknown,
        sun_intervals=_visible_intervals(start, cuts["sun"], clock.total_ms),
        earth_windows=_visible_intervals(start, cuts["earth"], clock.total_ms),
        sun_timeline=_timeline(start, cuts["sun"], clock.total_ms),
        earth_timeline=_timeline(start, cuts["earth"], clock.total_ms),
    )

    ref = site.site_ref
    issues: list[QualityIssue] = []
    for body, body_series in (("sun", sun_series), ("earth", earth_series)):
        if any(v is None for v in body_series.azimuth_deg):
            issues.append(
                _issue(
                    "azimuth_undefined",
                    "info",
                    ref,
                    f"series.{body}.azimuth_deg",
                    "quality.azimuth_undefined_zenith_nadir",
                )
            )
        if any(v is None for v in body_series.horizon_elevation_deg):
            issues.append(
                _issue(
                    "horizon_no_data",
                    "warning",
                    ref,
                    f"series.{body}.horizon_elevation_deg",
                    "quality.horizon_no_data_or_undefined_azimuth",
                )
            )
        if any(v is None for v in body_series.visible):
            issues.append(
                _issue(
                    "visibility_undetermined",
                    "warning",
                    ref,
                    f"series.{body}.visible",
                    "quality.visibility_undetermined",
                )
            )
        if any(e.azimuth_deg is None for e in groups[body].events):
            issues.append(
                _issue(
                    "azimuth_undefined",
                    "info",
                    ref,
                    f"events.{body}.azimuth_deg",
                    "quality.azimuth_undefined_zenith_nadir",
                )
            )
    if any(v is None for v in sun_series.visible_fraction):
        issues.append(
            _issue(
                "visible_fraction_undetermined",
                "warning",
                ref,
                "series.sun.visible_fraction",
                "quality.visible_fraction_undetermined",
            )
        )
    if summary.sun_unknown_duration_s > 0 or summary.earth_unknown_duration_s > 0:
        issues.append(
            _issue(
                "unknown_intervals",
                "info",
                ref,
                "summary.unknown_duration",
                "quality.unknown_intervals",
            )
        )

    if dem is not None:
        display = dem.horizon
        if any(v is None for v in display.elevation_deg):
            issues.append(
                _issue(
                    "horizon_no_data",
                    "warning",
                    ref,
                    "horizon.elevation_deg",
                    "quality.horizon_no_data",
                )
            )
        if (dem.visibility_horizon or display).status == "partial":
            issues.append(
                _issue(
                    "horizon_partial", "warning", ref, "horizon.quality", "quality.horizon_partial"
                )
            )
        horizon = SiteHorizon(
            site_ref=ref,
            mode="dem",
            azimuth_step_deg=display.azimuth_step_deg,
            elevation_deg=display.elevation_deg,
            obstacle_distance_m=display.obstacle_distance_m,
            quality=display.quality,
            max_search_distance_m=display.max_search_distance_m,
            coverage_fraction=display.coverage_fraction,
            dem_products=[
                DemProductUse(product_id=p.product_id, role=p.role) for p in display.dem_products
            ],
        )
        manifest = dem.terrain
        terrain = SiteTerrain(
            site_ref=ref,
            available=True,
            reason=None,
            terrain_id=manifest.terrain_id,
            product_id=manifest.source.product_id,
            calc_resolution_m=manifest.calc_resolution_m,
            visual_resolutions_m=sorted({lod.visual_resolution_m for lod in manifest.lods}),
            frame_id=manifest.frame_id,
        )
        terrain_elevation: float | None = surface
    else:
        issues.append(
            _issue(
                "terrain_elevation_not_used",
                "info",
                ref,
                "sites.terrain_elevation_m",
                "quality.idealized_reference_surface",
            )
        )
        count = round(360.0 / HORIZON_AZIMUTH_STEP_DEG)
        horizon = SiteHorizon(
            site_ref=ref,
            mode="idealized_local_plane",
            azimuth_step_deg=HORIZON_AZIMUTH_STEP_DEG,
            elevation_deg=[0.0] * count,
            obstacle_distance_m=[None] * count,
            quality=["complete"] * count,
            max_search_distance_m=None,
            coverage_fraction=1.0,
            dem_products=[],
        )
        terrain = SiteTerrain(
            site_ref=ref,
            available=False,
            reason="Idealized mode: local terrain is not included.",
            terrain_id=None,
            product_id=None,
            calc_resolution_m=None,
            visual_resolutions_m=[],
            frame_id=None,
        )
        terrain_elevation = None

    result_site = ResultSite(
        site_ref=ref,
        label=site.label,
        kind="catalog" if site.kind == "catalog" else "custom",
        catalog_id=site.catalog_id,
        latitude_deg=site.latitude_deg,
        longitude_deg=site.longitude_deg,
        frame_id=request.frame_id,
        terrain_elevation_m=terrain_elevation,
        observer_height_m=request.observer_height_m,
        on_reference_surface=dem is None,
        azimuth_convention=azimuth_convention(site.latitude_deg),
        coordinates_rounded=False,
    )
    series = SiteSeries(
        site_ref=ref,
        step_s=float(request.series_step_s),
        time_utc=[_utc_at(start, ms) for ms in series_ms],
        sun=sun_series,
        earth=earth_series,
    )
    return _SiteOutput(
        result_site,
        series,
        SiteEvents(site_ref=ref, sun=groups["sun"], earth=groups["earth"]),
        summary,
        horizon,
        terrain,
        issues,
        scans["sun"].evaluations + scans["earth"].evaluations,
    )


def simulate_idealized(
    request: SimulationRequest,
    sites: list[SiteInput],
    profile: LoadedProfile,
    progress: ProgressCallback | None = None,
    dem: dict[str, DemSiteInput] | None = None,
) -> SimulationResult:
    """Rezultatul complet pentru `terrain_mode = idealized_local_plane` sau `dem` (cu `dem` dat).

    `request.series_step_s` trebuie să fie deja stabilit. Ridică `LunarHorizonError` pentru
    acoperire
    temporală sau orizont indisponibil; valorile necunoscute devin `null` cu motiv în
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
    clock = _Clock(request, profile)
    outputs: list[_SiteOutput] = []
    for index, site in enumerate(sites):
        stage = f"sit {index + 1}/{len(sites)}"
        report(stage, index / len(sites))
        outputs.append(
            _simulate_site(request, site, profile, clock, dem[site.site_ref] if dem else None)
        )
        report(stage, (index + 1.0) / len(sites))
    return _result(request, profile, dem, outputs)


def _result(
    request: SimulationRequest,
    profile: LoadedProfile,
    dem: dict[str, DemSiteInput] | None,
    outputs: list[_SiteOutput],
) -> SimulationResult:
    mode = request.terrain_mode
    steps = SCAN_STEP_S[mode]
    products: dict[str, DemProductUse] = {}
    horizon_parameters: dict[str, float | int | str | bool]
    if dem:
        first = next(iter(dem.values()))
        horizon_parameters = {"mode": "dem"}
        horizon_parameters.update(first.horizon.parameters)
        horizon_parameters["display_azimuth_step_deg"] = first.horizon.azimuth_step_deg
        horizon_parameters["visibility_azimuth_step_deg"] = (
            first.visibility_horizon or first.horizon
        ).azimuth_step_deg
        horizon_parameters["parameters_status"] = "provisional (D-08/D-09 open)"
        for ref, inputs in dem.items():
            horizon_parameters[f"cache_key.{ref}"] = (
                inputs.visibility_horizon or inputs.horizon
            ).cache_key
            for use in inputs.horizon.dem_products:
                products.setdefault(
                    use.product_id, DemProductUse(product_id=use.product_id, role=use.role)
                )
    else:
        horizon_parameters = {
            "mode": "idealized_local_plane",
            "fixed_horizon_elevation_deg": 0.0,
            "azimuth_step_deg": HORIZON_AZIMUTH_STEP_DEG,
        }
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
        horizon_parameters=horizon_parameters,
        event_parameters={
            "algorithm_version": VISIBILITY_ALGORITHM_VERSION,
            "method": "adaptive_scan_subdivision_bisection",
            "sun_scan_step_s": steps["sun"],
            "earth_scan_step_s": steps["earth"],
            "refinement_tolerance_s": REFINEMENT_TOLERANCE_S,
            "min_subdivision_step_s": MIN_SUBDIVISION_STEP_S,
            "eps_numeric_deg": EPS_NUMERIC_DEG,
            "disc_columns": DISC_COLUMNS,
            "criterion_evaluations": sum(o.evaluations for o in outputs),
        },
        criteria={
            "solar_criterion": request.solar_criterion,
            "solar_definition": SOLAR_DEFINITION,
            "earth_criterion": request.earth_criterion.kind,
            "earth_definition": EARTH_DEFINITION,
            "earth_min_elevation_deg": request.earth_criterion.min_elevation_deg,
            "eclipses": "not_included",
        },
    )
    terrain_text = (
        "DEM horizon: H(A) from the DEM calculation rasters (near PGDA product, far LOLA GDR "
        f"product), sampled every {VISIBILITY_AZIMUTH_STEP_DEG} deg for visibility and linear "
        "between samples; the observer stands on the DEM surface plus the equipment height."
        if mode == "dem"
        else "Idealized mode: flat local horizon at 0 deg, local terrain not included; this is not "
        "a terrain-based result. The observer is on the reference sphere."
    )
    quality = Quality(
        issues=[issue for o in outputs for issue in o.issues],
        not_computed=[],
        approximations=[
            terrain_text,
            "Sun: visible when any part of the disc with positive area is above the horizon; "
            "disc radius asin(R_sun / D) at each moment; tangent-plane disc model (relative error "
            "of order rho^2). The visible fraction is an apparent-area fraction, not solar power.",
            "Earth: geometric line of sight to the Earth's centre above max(horizon, minimum "
            "elevation); not a communication-link assessment.",
            "Apparent positions with the CN+S correction (D-02); no refraction, no gravitational "
            "light deflection.",
        ],
        limits=[
            "Visibility is with respect to terrain only; eclipses are not included.",
            f"Events: scan every {steps['sun']:g} s (Sun) and {steps['earth']:g} s (Earth), "
            f"subdivision to {MIN_SUBDIVISION_STEP_S:g} s where the criterion may reach the "
            f"threshold, roots refined to {REFINEMENT_TOLERANCE_S:g} s. This is numerical "
            "precision, not physical (DEM, ephemeris) uncertainty.",
            "Undetermined periods (missing or partial horizon data, or within the horizon "
            "resolution of the threshold) are reported separately, never as hidden.",
            "Earth minimum elevation is a configurable threshold (default 0 deg).",
            "Steps are counted on the civil UTC scale; no leap second is inserted.",
        ]
        + (
            [
                "Horizon parameters are technical proposals (D-08/D-09 open); the DEM frame "
                "MOON_ME_DE421 is a working hypothesis (D-10).",
                "Narrow obstacles between horizon samples cannot be excluded; near-terrain "
                "resolution convergence is not demonstrable (5 m is the finest product).",
            ]
            if mode == "dem"
            else ["Catalog coordinates are adopted in their declared frame as a hypothesis (E04)."]
        ),
    )
    return SimulationResult(
        schema_version=SCHEMA_VERSION,
        request=request,
        sites=[o.site for o in outputs],
        series=[o.series for o in outputs],
        events=[o.events for o in outputs],
        summary=[o.summary for o in outputs],
        horizon=[o.horizon for o in outputs],
        terrain=[o.terrain for o in outputs],
        provenance=provenance,
        quality=quality,
    )
