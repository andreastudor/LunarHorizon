"""E10: criteriile de vizibilitate (D-04), stările în timp și evenimentele (T-08), pe cazuri sintetice.

Profilurile și funcțiile-criteriu sunt sintetice (`synthetic_`) și există numai în teste.
"""

import math
from collections.abc import Callable
from typing import Any

import numpy as np
import pytest

from lunarhorizon.api.jobs import engine_identity, request_key
from lunarhorizon.astro.kernels import DEFAULT_KERNEL_DIR, load_profile
from lunarhorizon.contracts.horizon import HorizonProfile
from lunarhorizon.contracts.manifests import TerrainManifest
from lunarhorizon.contracts.simulation import SimulationRequest
from lunarhorizon.core.utc import parse_utc
from lunarhorizon.simulation.idealized import DemSiteInput, SiteInput, simulate_idealized
from lunarhorizon.simulation.timeline import ScanResult, Sample, scan
from lunarhorizon.simulation.visibility import (
    EPS_NUMERIC_DEG,
    HorizonModel,
    earth_visibility,
    idealized_disc_fraction,
    sun_visibility,
)
from tests.support import REPO_ROOT

RHO = 0.2666  # rază unghiulară solară tipică (grade)


def profile_model(
    step: float, values: list[float | None], partial: set[int] | None = None
) -> HorizonModel:
    elevation = np.array([math.nan if v is None else v for v in values], dtype=float)
    lower = np.zeros(len(values), dtype=bool)
    for index in partial or set():
        lower[index] = True
    return HorizonModel(step, elevation, lower, np.full(len(values), 1000.0), "dem")


def flat(step: float, height: float) -> list[float | None]:
    return [height] * round(360.0 / step)


# --- discul solar în modul idealizat ------------------------------------------------------------


@pytest.mark.parametrize("elevation", [-0.25, -0.1, 0.0, 0.13, 0.25])
def test_idealized_partial_fraction_matches_the_analytic_segment(elevation: float) -> None:
    state = sun_visibility(HorizonModel.idealized(), 120.0, elevation, RHO)
    assert state.state == "partially_visible"
    assert state.fraction == pytest.approx(idealized_disc_fraction(elevation, RHO), abs=2e-3)
    assert state.fraction_uncertainty is not None and state.fraction_uncertainty < 5e-3


def test_idealized_hidden_and_fully_visible() -> None:
    hidden = sun_visibility(HorizonModel.idealized(), 120.0, -RHO - 0.01, RHO)
    full = sun_visibility(HorizonModel.idealized(), 120.0, RHO + 0.01, RHO)
    assert (hidden.state, hidden.fraction) == ("hidden", 0.0)
    assert (full.state, full.fraction) == ("fully_visible", 1.0)
    assert hidden.timeline_state == "hidden" and full.timeline_state == "visible"


def test_tangent_contact_is_not_positive_area() -> None:
    """e + rho = 0: contact tangent, nu vizibilitate; puțin deasupra: arie pozitivă, deci vizibil."""
    model = HorizonModel.idealized()
    touching = sun_visibility(model, 120.0, -RHO, RHO)
    assert touching.state == "undetermined" and touching.reason == "near_threshold"
    assert touching.timeline_state == "unknown"
    above = sun_visibility(model, 120.0, -RHO + 1e-4, RHO)
    assert above.state == "partially_visible"
    assert above.fraction is not None and 0.0 <= above.fraction < 1e-3
    below = sun_visibility(model, 120.0, -RHO - 1e-4, RHO)
    assert below.state == "hidden"


# --- discul solar pe relief neregulat ------------------------------------------------------------


def notch_model(centre: float, lo: float, hi: float, wall: float, gap: float) -> HorizonModel:
    step = 0.01
    values = flat(step, wall)
    for index in range(len(values)):
        offset = (index * step - centre + 180.0) % 360.0 - 180.0
        if lo <= offset <= hi:
            values[index] = gap
    return profile_model(step, values)


def test_lateral_opening_makes_the_disc_visible_although_the_centre_column_is_hidden() -> None:
    # Perete de 1° cu o deschidere îngustă la marginea dreaptă a discului (azimut +0,20…+0,25°).
    model = notch_model(100.0, 0.20, 0.25, 1.0, -1.0)
    elevation = 0.5  # vârful discului: 0,767° < 1°, deci „centru + rho > H(A_c)” ar spune ascuns
    assert elevation + RHO < 1.0
    state = sun_visibility(model, 100.0, elevation, RHO)
    assert state.state == "partially_visible"
    assert state.fraction is not None and 0.0 < state.fraction < 0.2
    assert state.contact_azimuth_deg is not None and 100.19 < state.contact_azimuth_deg < 100.26
    closed = sun_visibility(notch_model(100.0, 0.40, 0.45, 1.0, -1.0), 100.0, elevation, RHO)
    assert closed.state == "hidden"


def test_opening_across_north_is_found_on_both_sides_of_0_360() -> None:
    model = notch_model(359.95, -0.05, 0.05, 2.0, -2.0)  # deschidere 359,90…0,00°
    for centre in (359.9, 0.1):
        state = sun_visibility(model, centre, 1.0, RHO)
        assert state.state == "partially_visible", centre
        assert state.contact_azimuth_deg is not None


def test_nodata_on_the_disc_is_undetermined_never_hidden() -> None:
    step = 0.05
    values = flat(step, 0.0)
    values[round(200.1 / step)] = None  # în interiorul discului
    state = sun_visibility(profile_model(step, values), 200.0, 1.0, RHO)
    assert (state.state, state.reason, state.fraction) == ("undetermined", "no_data", None)
    far = sun_visibility(profile_model(step, values), 150.0, 1.0, RHO)
    assert far.state == "fully_visible"


def test_partial_horizon_is_a_lower_bound() -> None:
    step = 0.05
    values = flat(step, 0.0)
    index = round(80.0 / step)
    model = profile_model(step, values, partial={index - 1, index, index + 1})
    # Deasupra limitei inferioare: orizontul real poate fi mai sus, deci starea nu poate fi decisă.
    assert sun_visibility(model, 80.0, 1.0, RHO).reason == "partial_data"
    # Sub limita inferioară: sigur ascuns.
    assert sun_visibility(model, 80.0, -1.0, RHO).state == "hidden"


# --- Pământul -------------------------------------------------------------------------------------


def test_earth_criterion_uses_terrain_and_threshold() -> None:
    model = profile_model(1.0, flat(1.0, 2.0))
    assert earth_visibility(model, 45.0, 2.5, 0.0).state == "visible"
    assert earth_visibility(model, 45.0, 1.5, 0.0).cause == "terrain"
    blocked = earth_visibility(model, 45.0, 2.5, 3.0)
    assert (blocked.state, blocked.cause) == ("hidden", "elevation_threshold")
    values = flat(1.0, 2.0)
    values[45] = None
    unknown = earth_visibility(profile_model(1.0, values), 45.0, 10.0, 0.0)
    assert (unknown.state, unknown.reason) == ("undetermined", "no_data")


# --- stări în timp și evenimente (T-08) -----------------------------------------------------------


def criterion(
    function: Callable[[float], float], gap: tuple[float, float] | None = None
) -> Callable[[float], Sample]:
    def evaluate(t: float) -> Sample:
        if gap is not None and gap[0] <= t <= gap[1]:
            return Sample(t, None, EPS_NUMERIC_DEG, "unknown", "no_data")
        value = function(t)
        if value > EPS_NUMERIC_DEG:
            return Sample(t, value, EPS_NUMERIC_DEG, "visible", None)
        if value < -EPS_NUMERIC_DEG:
            return Sample(t, value, EPS_NUMERIC_DEG, "hidden", None)
        return Sample(t, value, EPS_NUMERIC_DEG, "unknown", "near_threshold")

    return evaluate


def durations(result: ScanResult) -> dict[str, float]:
    totals: dict[str, float] = {}
    for segment in result.segments:
        totals[segment.state] = totals.get(segment.state, 0.0) + segment.end - segment.start
    return totals


def test_short_transition_between_grid_samples_is_found() -> None:
    # Arc pozitiv de 40 s între două eșantioane ale unei grile de 600 s (tranziție scurtă).
    def bump(t: float) -> float:
        return 1e-3 * (1.0 - ((t - 1290.0) / 20.0) ** 2) if abs(t - 1290.0) < 400 else -0.05

    result = scan(criterion(bump), 3600.0, 600.0)
    kinds = [t.kind for t in result.transitions]
    assert kinds == ["appearance", "disappearance"]
    assert result.transitions[0].time == pytest.approx(1270.0, abs=1e-2)
    assert result.transitions[1].time == pytest.approx(1310.0, abs=1e-2)
    assert durations(result)["visible"] == pytest.approx(40.0, abs=0.05)


def test_near_tangent_contact_is_distinct_from_visibility() -> None:
    def graze(peak: float) -> Callable[[float], float]:
        return lambda t: peak - 1e-6 * ((t - 1000.0) / 10.0) ** 2

    touch = scan(criterion(graze(5e-7)), 2000.0, 300.0)
    assert [t.kind for t in touch.transitions] == ["tangent_contact"]
    assert "visible" not in durations(touch)
    assert touch.transitions[0].time == pytest.approx(1000.0, abs=1.0)
    clear = scan(criterion(graze(1e-4)), 2000.0, 300.0)
    assert [t.kind for t in clear.transitions] == ["appearance", "disappearance"]


def test_no_events_at_the_borders_of_missing_data() -> None:
    result = scan(criterion(lambda t: 1.0 - t / 1000.0, gap=(800.0, 1200.0)), 2000.0, 60.0)
    assert result.transitions == []  # trecerea prin zero cade în zona fără date
    states = [(s.state, s.reason) for s in result.segments]
    assert states == [("visible", None), ("unknown", "no_data"), ("hidden", None)]
    assert sum(s.end - s.start for s in result.segments) == pytest.approx(2000.0)


@pytest.mark.parametrize("step", [60.0, 300.0, 900.0])
def test_durations_and_event_times_are_stable_with_the_scan_step(step: float) -> None:
    def wave(t: float) -> float:
        return 0.3 * math.sin(2 * math.pi * t / 7200.0) + 0.05

    result = scan(criterion(wave), 14_400.0, step)
    reference = scan(criterion(wave), 14_400.0, 10.0)
    assert durations(result)["visible"] == pytest.approx(durations(reference)["visible"], abs=0.01)
    times = [t.time for t in result.transitions]
    expected = [t.time for t in reference.transitions]
    assert len(times) == len(expected) == 4
    assert times == pytest.approx(expected, abs=0.002)


# --- simulare: un obstacol controlat față de modul idealizat; identitatea cache-ului ---------------

kernels = pytest.mark.skipif(
    not (DEFAULT_KERNEL_DIR / "de440s.bsp").is_file(), reason="kernelurile lipsesc"
)
SITE = SiteInput("custom-1", "synthetic_site", "custom", None, 0.67416, 23.47314)


def request(mode: str) -> SimulationRequest:
    point = {"label": "synthetic_site", "latitude_deg": 0.67416, "longitude_deg": 23.47314}
    return SimulationRequest.model_validate(
        {
            "sites": [{"custom": point}],
            "frame_id": "MOON_ME_DE440_ME421",
            "start_utc": "2026-11-15T00:00:00Z",
            "end_utc": "2026-11-17T00:00:00Z",
            "observer_height_m": 2.0,
            "solar_criterion": "disc_positive_area",
            "earth_criterion": {"kind": "center_above_horizon", "min_elevation_deg": 0.0},
            "terrain_mode": mode,
            "series_step_s": 1800,
        }
    )


def synthetic_profile(heights: list[float]) -> HorizonProfile:
    count = len(heights)
    return HorizonProfile.model_validate(
        {
            "schema_version": "0.8.0",
            "status": "complete",
            "reason_code": None,
            "reason": None,
            "latitude_deg": 0.67416,
            "longitude_deg": 23.47314,
            "frame_id": "MOON_ME_DE440_ME421",
            "azimuth_convention": "standard",
            "observer_terrain_elevation_m": 0.0,
            "observer_height_m": 2.0,
            "azimuth_step_deg": 360.0 / count,
            "elevation_deg": heights,
            "obstacle_distance_m": [1000.0] * count,
            "quality": ["complete"] * count,
            "max_search_distance_m": 10_000.0,
            "coverage_fraction": 1.0,
            "dem_products": [
                {
                    "product_id": "synthetic_dem",
                    "role": "near",
                    "frame_id": "MOON_ME_DE440_ME421",
                    "resolution_m": 5.0,
                    "reference_radius_m": 1_737_400.0,
                    "sha256": None,
                    "valid_sample_fraction": 1.0,
                }
            ],
            "parameters": {"algorithm_version": "synthetic"},
            "parameters_status": "provisional",
            "cache_key": "0" * 64,
            "compute_time_s": None,
            "note": "synthetic profile, tests only",
        }
    )


def terrain_manifest() -> TerrainManifest:
    path = REPO_ROOT / "data" / "manifests" / "leibnitz_terrain.json"
    return TerrainManifest.model_validate_json(path.read_text(encoding="utf-8"))


def seconds(utc: str) -> float:
    return parse_utc(utc).timestamp()


@kernels
def test_controlled_obstacle_changes_visibility_versus_the_idealized_mode() -> None:
    profile = load_profile("de440_me421")
    ideal = simulate_idealized(request("idealized_local_plane"), [SITE], profile)
    sunrise = next(e for e in ideal.events[0].sun.events if e.type == "appearance")
    step = 0.25
    flat_heights = [0.0] * round(360.0 / step)
    wall = list(flat_heights)
    azimuth = sunrise.azimuth_deg or 0.0
    for index in range(len(wall)):
        if abs(((index * step - azimuth + 180.0) % 360.0) - 180.0) <= 3.0:
            wall[index] = 2.0  # obstacol sintetic de 2° spre răsărit
    runs: dict[str, Any] = {}
    for name, heights in (("flat", flat_heights), ("wall", wall)):
        horizon = synthetic_profile(heights)
        dem = {SITE.site_ref: DemSiteInput(horizon, terrain_manifest(), horizon)}
        runs[name] = simulate_idealized(request("dem"), [SITE], profile, None, dem)
    flat_rise = next(e for e in runs["flat"].events[0].sun.events if e.type == "appearance")
    wall_rise = next(e for e in runs["wall"].events[0].sun.events if e.type == "appearance")
    # H = 0 peste tot reproduce modul idealizat; un perete de 2° întârzie răsăritul și scurtează lumina.
    assert abs(seconds(flat_rise.time_utc) - seconds(sunrise.time_utc)) < 0.01
    assert seconds(wall_rise.time_utc) - seconds(sunrise.time_utc) > 3600.0
    assert wall_rise.cause == "terrain" and wall_rise.obstacle_distance_m == 1000.0
    ideal_light = ideal.summary[0].sun_visible_duration_s or 0.0
    wall_light = runs["wall"].summary[0].sun_visible_duration_s or 0.0
    assert wall_light < ideal_light - 3600.0


def test_cache_identity_separates_correction_and_algorithm_versions() -> None:
    base = request("idealized_local_plane")
    assert request_key(base) == request_key(request("idealized_local_plane"))  # repetabil
    identity = engine_identity()
    assert identity["aberration_correction"] == "CN+S"
    for key, value in (
        ("aberration_correction", "LT+S"),
        ("visibility_algorithm", "e09.0"),
        ("refinement_tolerance_s", 0.01),
    ):
        changed = {**identity, key: value}
        assert request_key(base, changed) != request_key(base)
