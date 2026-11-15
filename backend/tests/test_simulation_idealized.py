"""E06: simularea idealizată față de motorul astronomic, schemă, determinism și concurență."""

import threading
from dataclasses import replace
from datetime import timedelta
from typing import Any

import pytest
from jsonschema import Draft202012Validator

from lunarhorizon.astro import bodies
from lunarhorizon.astro.bodies import ObserverSite, body_direction
from lunarhorizon.astro.kernels import DEFAULT_KERNEL_DIR, LoadedProfile, load_profile
from lunarhorizon.contracts.export import document_schema
from lunarhorizon.contracts.simulation import SimulationRequest, SimulationResult
from lunarhorizon.core.conventions import APPARENT_CORRECTION
from lunarhorizon.core.errors import ErrorCode, LunarHorizonError
from lunarhorizon.core.utc import format_utc, parse_utc
from lunarhorizon.simulation.idealized import SiteInput, simulate_idealized
from tests.support import SCHEMA_PATH, read_json

pytestmark = [
    pytest.mark.kernels,
    pytest.mark.skipif(
        not (DEFAULT_KERNEL_DIR / "de440s.bsp").is_file(),
        reason="kernelurile lipsesc; rulați scripts/download_kernels.py",
    ),
]

SITES = [
    SiteInput("apollo11_lm", "Apollo 11", "catalog", "apollo11_lm", 0.67416, 23.47314),
    SiteInput("custom-2", "synthetic_pol", "custom", None, -89.5, 10.0),
]
APOLLO = ObserverSite(0.67416, 23.47314, 0.0, 2.0)


def make_request(
    *, start: str = "2026-11-15T00:00:00Z", end: str = "2026-11-17T00:00:00Z", min_elev: float = 0.0
) -> SimulationRequest:
    custom = {"label": "p", "latitude_deg": -89.5, "longitude_deg": 10.0}
    return SimulationRequest.model_validate(
        {
            "sites": [{"site_id": "apollo11_lm"}, {"custom": custom}],
            "frame_id": "MOON_ME_DE440_ME421",
            "start_utc": start,
            "end_utc": end,
            "observer_height_m": 2.0,
            "solar_criterion": "disc_positive_area",
            "earth_criterion": {"kind": "center_above_horizon", "min_elevation_deg": min_elev},
            "terrain_mode": "idealized_local_plane",
            "series_step_s": 1800,
        }
    )


@pytest.fixture(scope="module")
def profile() -> LoadedProfile:
    return load_profile("de440_me421")


@pytest.fixture(scope="module")
def result(profile: LoadedProfile) -> SimulationResult:
    return simulate_idealized(make_request(), SITES, profile)


def comparable(model: SimulationResult) -> dict[str, Any]:
    data = model.model_dump(mode="json")
    data["provenance"]["computed_at_utc"] = "<ignorat>"
    return data


def shifted(utc: str, milliseconds: int) -> str:
    return format_utc(parse_utc(utc) + timedelta(milliseconds=milliseconds))


def test_result_conforms_to_json_schema(result: SimulationResult) -> None:
    schema = document_schema(read_json(SCHEMA_PATH), "SimulationResult")
    Draft202012Validator(schema).validate(result.model_dump(mode="json"))


def test_idealized_mode_is_explicit_and_has_no_terrain(result: SimulationResult) -> None:
    assert {h.mode for h in result.horizon} == {"idealized_local_plane"}
    assert all(set(h.elevation_deg) == {0.0} for h in result.horizon)
    assert all(not t.available and "idealized" in (t.reason or "").lower() for t in result.terrain)
    assert result.provenance.dem_products == []
    assert any("local terrain not included" in text for text in result.quality.approximations)
    assert all(s.on_reference_surface and s.terrain_elevation_m is None for s in result.sites)
    assert {i.field for i in result.quality.issues} == {"sites.terrain_elevation_m"}


def test_series_equals_engine_samples(result: SimulationResult, profile: LoadedProfile) -> None:
    series = result.series[0]
    for body in ("sun", "earth"):
        data = getattr(series, body)
        for index in (0, 7, len(series.time_utc) - 1):
            direct = body_direction(
                profile, APOLLO, body, series.time_utc[index], APPARENT_CORRECTION
            )
            assert data.azimuth_deg[index] == direct.azimuth_deg
            assert data.elevation_deg[index] == direct.elevation_deg
            assert data.distance_km[index] == direct.distance_km
            assert data.angular_radius_deg[index] == direct.angular_radius_deg
    assert series.time_utc[0] == "2026-11-15T00:00:00Z"
    assert series.time_utc[-1] == "2026-11-17T00:00:00Z"


def test_visibility_flags_follow_the_criteria(result: SimulationResult) -> None:
    for series in result.series:
        assert series.sun.visible == [e >= 0.0 for e in series.sun.elevation_deg]
        assert series.earth.visible == [e >= 0.0 for e in series.earth.elevation_deg]
        assert set(series.sun.horizon_elevation_deg) == {0.0}


def test_events_are_real_crossings_refined_to_one_millisecond(
    result: SimulationResult, profile: LoadedProfile
) -> None:
    group = result.events[0].sun
    assert group.status == "found"
    for event in group.events:
        at = body_direction(profile, APOLLO, "sun", event.time_utc, APPARENT_CORRECTION)
        assert at.elevation_deg == pytest.approx(0.0, abs=1e-4)
        assert event.cause == "idealized_horizon" and event.obstacle_distance_m is None
        assert event.refinement_tolerance_s == 0.001
        before = body_direction(
            profile, APOLLO, "sun", shifted(event.time_utc, -2000), APPARENT_CORRECTION
        )
        after = body_direction(
            profile, APOLLO, "sun", shifted(event.time_utc, 2000), APPARENT_CORRECTION
        )
        assert (after.elevation_deg > before.elevation_deg) == (event.type == "appearance")


def test_summary_is_consistent_with_intervals(result: SimulationResult) -> None:
    total = 2 * 86400.0
    for summary in result.summary:
        sun = sum(
            (parse_utc(i.end_utc) - parse_utc(i.start_utc)).total_seconds()
            for i in summary.sun_intervals
        )
        assert summary.sun_visible_duration_s == pytest.approx(sun, abs=1e-6)
        assert summary.sun_visible_fraction == pytest.approx(sun / total, abs=1e-9)
        both = summary.both_visible_duration_s
        assert both is not None
        assert both <= (summary.sun_visible_duration_s or 0.0) + 1e-6
        assert both <= (summary.earth_visible_duration_s or 0.0) + 1e-6
        starts = [parse_utc(i.start_utc) for i in summary.sun_intervals]
        assert starts == sorted(starts)


def test_truncated_flags_mark_intervals_open_at_the_interval_edges(
    result: SimulationResult,
) -> None:
    summary = result.summary[0]
    first, last = summary.sun_intervals[0], summary.sun_intervals[-1]
    assert (first.start_utc == result.request.start_utc) == first.truncated_start
    assert (last.end_utc == result.request.end_utc) == last.truncated_end


def test_earth_threshold_shortens_visibility(profile: LoadedProfile) -> None:
    low = simulate_idealized(make_request(min_elev=0.0), SITES, profile)
    high = simulate_idealized(make_request(min_elev=20.0), SITES, profile)
    for a, b in zip(low.summary, high.summary, strict=True):
        assert (b.earth_visible_duration_s or 0.0) <= (a.earth_visible_duration_s or 0.0)
    assert high.provenance.criteria["earth_min_elevation_deg"] == 20.0


def test_same_request_gives_the_same_result(
    result: SimulationResult, profile: LoadedProfile
) -> None:
    assert comparable(simulate_idealized(make_request(), SITES, profile)) == comparable(result)


def test_outside_ephemeris_coverage_reports_real_limits(profile: LoadedProfile) -> None:
    request = make_request(start="1849-12-26T00:00:00Z", end="1849-12-27T00:00:00Z")
    with pytest.raises(LunarHorizonError) as info:
        simulate_idealized(request, SITES, profile)
    assert info.value.code == ErrorCode.OUT_OF_EPHEMERIS_COVERAGE
    assert info.value.context["coverage_end_utc"].startswith("2150-01-21")


def test_dem_mode_is_never_replaced_silently(profile: LoadedProfile) -> None:
    request = make_request().model_copy(update={"terrain_mode": "dem"})
    with pytest.raises(LunarHorizonError) as info:
        simulate_idealized(request, SITES, profile)
    assert info.value.code == ErrorCode.OUT_OF_DEM_COVERAGE


def test_undefined_azimuth_is_null_with_a_reason_not_zero_or_failure(
    monkeypatch: pytest.MonkeyPatch, profile: LoadedProfile
) -> None:
    real = bodies.body_direction

    def zenith(*args: Any, **kwargs: Any) -> Any:
        direction = real(*args, **kwargs)
        return replace(direction, azimuth_deg=None) if args[2] == "sun" else direction

    monkeypatch.setattr("lunarhorizon.simulation.idealized.body_direction", zenith)
    result = simulate_idealized(make_request(), SITES, profile)
    sun = result.series[0].sun
    assert set(sun.azimuth_deg) == {None}
    assert None not in result.series[0].earth.azimuth_deg
    fields = {(i.code, i.field) for i in result.quality.issues}
    assert ("azimuth_undefined", "series.sun.azimuth_deg") in fields
    assert ("azimuth_undefined", "events.sun.azimuth_deg") in fields
    assert all(e.azimuth_deg is None for e in result.events[0].sun.events)
    schema = document_schema(read_json(SCHEMA_PATH), "SimulationResult")
    Draft202012Validator(schema).validate(result.model_dump(mode="json"))


def test_null_azimuth_without_a_reason_is_rejected_by_the_contract(
    result: SimulationResult,
) -> None:
    data = result.model_dump(mode="json")
    data["series"][0]["sun"]["azimuth_deg"][0] = None
    with pytest.raises(ValueError, match=r"series\.sun\.azimuth_deg"):
        SimulationResult.model_validate(data)


def test_concurrent_simulations_with_two_profiles_match_sequential_results() -> None:
    p440, p421 = load_profile("de440_me421"), load_profile("de421")
    requests = {
        "de440": (make_request(), p440),
        "de421": (make_request().model_copy(update={"frame_id": "MOON_ME_DE421"}), p421),
    }
    expected = {
        name: comparable(simulate_idealized(request, SITES, profile))
        for name, (request, profile) in requests.items()
    }
    found: dict[str, dict[str, Any]] = {}
    errors: list[Exception] = []

    def worker(name: str, copy: int) -> None:
        request, profile = requests[name]
        try:
            found[f"{name}-{copy}"] = comparable(simulate_idealized(request, SITES, profile))
        except Exception as error:
            errors.append(error)

    threads = [
        threading.Thread(target=worker, args=(name, copy)) for name in requests for copy in range(3)
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert not errors
    assert len(found) == 6
    for key, value in found.items():
        assert value == expected[key.split("-")[0]]
    assert expected["de440"] != expected["de421"]
