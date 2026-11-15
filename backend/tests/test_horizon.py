"""E09: orizontul din DEM (T-06 pe teren sintetic; serviciul și API-ul pe date reale, dacă există).

Terenul sintetic are prefixul `synthetic_`; nu înlocuiește date reale în aplicație.
"""

import json
import math
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import numpy as np
import pytest
from fastapi.testclient import TestClient
from jsonschema import Draft202012Validator

from lunarhorizon.api.app import create_app
from lunarhorizon.api.settings import DATA_DIR, Settings
from lunarhorizon.contracts.export import build_schema, document_schema
from lunarhorizon.terrain.horizon import (
    HeightGrid,
    HorizonInputError,
    HorizonParameters,
    compute_horizon,
    interpolate_horizon,
)
from lunarhorizon.terrain.lola_gdr import load_lola_polar_grid

R = 1_737_400.0
FRAME = "MOON_ME_DE421"
LAT, LON = -85.0, 30.0


def project(lat: float, lon: float) -> tuple[float, float]:
    rho = 2.0 * R * math.tan(math.pi / 4.0 + math.radians(lat) / 2.0)
    return rho * math.sin(math.radians(lon)), rho * math.cos(math.radians(lon))


def synthetic_grid(
    heights: np.ndarray,
    resolution_m: float,
    center_x: float,
    center_y: float,
    product_id: str = "synthetic_near",
    role: str = "near",
    frame_id: str = FRAME,
    radius: float = R,
) -> HeightGrid:
    rows, cols = heights.shape
    return HeightGrid(
        product_id=product_id,
        role=role,  # type: ignore[arg-type]
        frame_id=frame_id,
        reference_radius_m=radius,
        resolution_m=resolution_m,
        x_first_m=center_x - (cols - 1) / 2 * resolution_m,
        y_first_m=center_y + (rows - 1) / 2 * resolution_m,
        heights=heights.astype(np.float32),
    )


def local_xy(grid: HeightGrid, lat: float, lon: float) -> tuple[float, float]:
    """Indicii (coloană, rând) fracționari ai unui punct geografic în raster."""
    x, y = project(lat, lon)
    return (x - grid.x_first_m) / grid.resolution_m, (grid.y_first_m - y) / grid.resolution_m


def destination(
    lat: float, lon: float, azimuth_deg: float, distance_m: float
) -> tuple[float, float]:
    """Problema geodezică directă pe sferă (aceeași geometrie ca algoritmul)."""
    phi, lam, az, delta = (
        math.radians(lat),
        math.radians(lon),
        math.radians(azimuth_deg),
        distance_m / R,
    )
    phi2 = math.asin(
        math.sin(phi) * math.cos(delta) + math.cos(phi) * math.sin(delta) * math.cos(az)
    )
    lam2 = lam + math.atan2(
        math.sin(az) * math.sin(delta) * math.cos(phi),
        math.cos(delta) - math.sin(phi) * math.sin(phi2),
    )
    return math.degrees(phi2), math.degrees(lam2)


def curved_elevation(height_m: float, observer_m: float, distance_m: float) -> float:
    delta = distance_m / R
    return math.degrees(
        math.atan2(
            (R + height_m) * math.cos(delta) - (R + observer_m), (R + height_m) * math.sin(delta)
        )
    )


# --- T-06: teren sintetic cu soluție cunoscută ----------------------------------------------------


def test_flat_sphere_gives_the_geometric_dip_and_horizon_distance() -> None:
    x, y = project(LAT, LON)
    grid = synthetic_grid(np.zeros((1201, 1201)), 100.0, x, y)
    observer = 100.0
    params = HorizonParameters(30.0, 50.0, 55_000.0, 10.0, 10.0)
    result = compute_horizon(LAT, LON, 0.0, observer, [grid], params)
    dip = -math.degrees(math.acos(R / (R + observer)))
    distance = R * math.acos(R / (R + observer))
    assert set(result.quality) == {"complete"}
    for elevation, obstacle in zip(result.elevation_deg, result.obstacle_distance_m, strict=True):
        assert elevation is not None and obstacle is not None
        assert abs(elevation - dip) < 1e-4
        assert abs(obstacle - distance) < 600.0  # maximul este plat în jurul distanței orizontului


def test_known_obstacle_includes_curvature() -> None:
    x, y = project(LAT, LON)
    heights = np.zeros((801, 801))
    grid = synthetic_grid(heights, 50.0, x, y)
    # Un bloc de 500 m pe azimutul 90° (est), care începe la 10 km.
    near_lat, near_lon = destination(LAT, LON, 90.0, 10_000.0)
    far_lat, far_lon = destination(LAT, LON, 90.0, 11_000.0)
    (c0, r0), (c1, r1) = local_xy(grid, near_lat, near_lon), local_xy(grid, far_lat, far_lon)
    rows = slice(int(min(r0, r1)) - 20, int(max(r0, r1)) + 21)
    cols = slice(math.ceil(min(c0, c1)), int(max(c0, c1)) + 1)
    heights[rows, cols] = 500.0
    grid = synthetic_grid(heights, 50.0, x, y)
    params = HorizonParameters(1.0, 10.0, 15_000.0, 5.0, 5.0)
    result = compute_horizon(LAT, LON, 0.0, 2.0, [grid], params)
    elevation, obstacle = result.elevation_deg[90], result.obstacle_distance_m[90]
    assert elevation is not None and obstacle is not None
    assert 10_000.0 <= obstacle <= 10_150.0
    expected = curved_elevation(500.0, 2.0, obstacle)
    flat_earth = math.degrees(math.atan2(498.0, obstacle))
    assert abs(elevation - expected) < 0.02
    assert flat_earth - elevation > 0.1  # curbura coboară obstacolul cu aproximativ d / 2R
    # Azimuturile fără obstacol rămân sub orizontul local (sferă plată).
    assert (result.elevation_deg[270] or 0.0) < 0.0


def test_nodata_is_not_zero_and_marks_the_azimuth_partial() -> None:
    x, y = project(LAT, LON)
    heights = np.full((401, 401), 300.0)
    grid = synthetic_grid(heights, 50.0, x, y)
    target_lat, target_lon = destination(LAT, LON, 180.0, 5_000.0)
    c, r = local_xy(grid, target_lat, target_lon)
    heights[int(r) - 3 : int(r) + 4, int(c) - 40 : int(c) + 41] = np.nan
    grid = synthetic_grid(heights, 50.0, x, y)
    params = HorizonParameters(1.0, 10.0, 8_000.0, 10.0, 10.0)
    result = compute_horizon(LAT, LON, 300.0, 2.0, [grid], params)
    assert result.quality[180] == "partial"
    assert result.quality[0] == "complete"
    assert result.elevation_deg[180] is not None
    assert result.coverage_fraction < 1.0
    # Același teren cu zero în loc de NoData dă alt rezultat: NoData nu este tratat ca zero.
    zeros = np.where(np.isnan(heights), 0.0, heights)
    filled = compute_horizon(LAT, LON, 300.0, 2.0, [synthetic_grid(zeros, 50.0, x, y)], params)
    assert filled.quality[180] == "complete"


def test_azimuth_without_any_sample_is_no_data_not_free_horizon() -> None:
    x, y = project(LAT, LON)
    # Observatorul la 300 m de marginea vestică a rasterului.
    grid = synthetic_grid(np.zeros((201, 201)), 50.0, x + 4_700.0, y)
    params = HorizonParameters(1.0, 1_000.0, 3_000.0, 10.0, 10.0)
    result = compute_horizon(LAT, LON, 0.0, 2.0, [grid], params)
    assert result.quality[270] == "no_data"
    assert result.elevation_deg[270] is None and result.obstacle_distance_m[270] is None
    assert result.quality[90] == "complete"


def test_beyond_the_raster_is_partial_and_the_far_tier_completes_it() -> None:
    x, y = project(LAT, LON)
    near = synthetic_grid(np.zeros((101, 101)), 20.0, x, y)  # ±1 km
    params = HorizonParameters(10.0, 20.0, 20_000.0, 20.0, 200.0)
    alone = compute_horizon(LAT, LON, 0.0, 2.0, [near], params)
    assert set(alone.quality) == {"partial"}
    far_heights = np.zeros((501, 501))
    far = synthetic_grid(far_heights, 200.0, x, y, product_id="synthetic_far", role="far")
    both = compute_horizon(LAT, LON, 0.0, 2.0, [near, far], params)
    assert set(both.quality) == {"complete"}
    assert both.product_fractions["synthetic_near"] > 0.0
    assert both.product_fractions["synthetic_far"] > 0.0
    # Nivelul apropiat are prioritate: un vârf numai în cel îndepărtat, aflat în întregime sub
    # rasterul apropiat (±600 m cu interpolarea, față de ±1 km), nu contează.
    far_heights[248:253, 248:253] = 5_000.0
    hidden = synthetic_grid(far_heights, 200.0, x, y, product_id="synthetic_far", role="far")
    masked = compute_horizon(LAT, LON, 0.0, 2.0, [near, hidden], params)
    assert masked.elevation_deg == both.elevation_deg


def test_incompatible_tiers_are_never_combined() -> None:
    x, y = project(LAT, LON)
    near = synthetic_grid(np.zeros((11, 11)), 20.0, x, y)
    other_frame = synthetic_grid(
        np.zeros((11, 11)), 20.0, x, y, "synthetic_far", "far", "MOON_ME_DE440_ME421"
    )
    other_sphere = synthetic_grid(
        np.zeros((11, 11)), 20.0, x, y, "synthetic_far", "far", FRAME, R + 1
    )
    params = HorizonParameters(90.0, 20.0, 100.0, 20.0, 20.0)
    for far in (other_frame, other_sphere):
        with pytest.raises(HorizonInputError):
            compute_horizon(LAT, LON, 0.0, 2.0, [near, far], params)
    with pytest.raises(HorizonInputError):
        compute_horizon(LAT, LON, math.nan, 2.0, [near], params)


@pytest.mark.parametrize(
    "values",
    [
        (0.7, 20.0, 10.0, 5.0, 5.0),
        (1.0, 0.0, 10.0, 5.0, 5.0),
        (1.0, 20.0, 10.0, 5.0, 5.0),
        (1.0, 5.0, 10.0, 0.0, 5.0),
    ],
)
def test_parameters_are_validated(values: tuple[float, float, float, float, float]) -> None:
    with pytest.raises(HorizonInputError):
        HorizonParameters(*values)


def test_interpolation_wraps_at_north_and_keeps_unknown_unknown() -> None:
    profile: list[float | None] = [1.0, 2.0, None, 4.0]
    assert interpolate_horizon(profile, 90.0, 45.0) == pytest.approx(1.5)
    assert interpolate_horizon(profile, 90.0, 315.0) == pytest.approx(2.5)  # între 270° și 360°
    assert interpolate_horizon(profile, 90.0, 360.0) == pytest.approx(1.0)
    assert interpolate_horizon(profile, 90.0, 200.0) is None


def test_pds_polar_label_is_read_not_assumed(tmp_path: Path) -> None:
    size = 4
    label = tmp_path / "synthetic_LDEM.LBL"
    image = tmp_path / "synthetic_LDEM.IMG"
    text = f"""LINES = {size}
LINE_SAMPLES = {size}
SAMPLE_TYPE = LSB_INTEGER
SAMPLE_BITS = 16
SCALING_FACTOR = 0.5
OFFSET = 1737400.
MAP_PROJECTION_TYPE = "POLAR STEREOGRAPHIC"
A_AXIS_RADIUS = 1737.4 <km>
CENTER_LATITUDE = -90 <deg>
CENTER_LONGITUDE = 0 <deg>
MAP_SCALE = 100 <m/pix>
MAXIMUM_LATITUDE = -89 <deg>
LINE_PROJECTION_OFFSET = 1.5 <pix>
SAMPLE_PROJECTION_OFFSET = 1.5 <pix>
COORDINATE_SYSTEM_NAME = "MEAN EARTH/POLAR AXIS OF DE421"
"""
    label.write_text(text, encoding="ascii")
    np.arange(size * size, dtype="<i2").tofile(image)
    grid = load_lola_polar_grid(label, image, "synthetic_far", None)
    assert grid.frame_id == FRAME
    assert (grid.x_first_m, grid.y_first_m) == (-150.0, 150.0)
    # Centrul pixelului (rând 0, coloană 1) = DN 1, adică 0,5 m.
    assert float(grid.sample(np.array([-50.0]), np.array([150.0]))[0]) == pytest.approx(0.5)
    label.write_text(text.replace("DE421", "DE430"), encoding="ascii")
    with pytest.raises(HorizonInputError):
        load_lola_polar_grid(label, image, "synthetic_far", None)
    label.write_text(text, encoding="ascii")
    short = tmp_path / "synthetic_short.IMG"  # imaginea de mai sus rămâne deschisă (memmap)
    short.write_bytes(b"\x00" * 10)
    with pytest.raises(HorizonInputError):
        load_lola_polar_grid(label, short, "synthetic_far", None)


# --- serviciul și API-ul pe datele reale -------------------------------------------------------

LEIBNITZ_RASTER = DATA_DIR / "_cache" / "terrain" / "leibnitz_beta" / "calculation.tif"
FAR_IMAGE = DATA_DIR / "_raw" / "lola_gdr" / "LDEM_75S_120M.IMG"
real = pytest.mark.skipif(
    not (LEIBNITZ_RASTER.is_file() and FAR_IMAGE.is_file()),
    reason="Leibnitz raster (E05) or LDEM_75S_120M (scripts/acquire_lola_gdr.py) missing",
)
LEIBNITZ = {"latitude_deg": -85.4266039743, "longitude_deg": 31.7441821732}
SCHEMA = build_schema()


@pytest.fixture
def api(tmp_path: Path) -> Iterator[TestClient]:
    with TestClient(create_app(Settings(horizon_cache_dir=tmp_path / "horizon"))) as client:
        yield client


def horizon(client: TestClient, **params: Any) -> dict[str, Any]:
    response = client.get("/api/horizon", params=params)
    assert response.status_code == 200, response.text
    body: dict[str, Any] = response.json()
    Draft202012Validator(document_schema(SCHEMA, "HorizonProfile")).validate(body)
    return body


@real
def test_leibnitz_profile_is_complete_two_tier_and_cached(api: TestClient, tmp_path: Path) -> None:
    body = horizon(api, frame_id=FRAME, observer_height_m=2, **LEIBNITZ)
    assert body["status"] == "complete" and body["reason_code"] is None
    assert len(body["elevation_deg"]) == 720 and body["azimuth_step_deg"] == 0.5
    assert body["parameters_status"] == "provisional"
    roles = {p["role"]: p for p in body["dem_products"]}
    assert roles["near"]["product_id"] == "pgda104_leibnitz_beta"
    assert roles["far"]["product_id"] == "lola_gdr_ldem_75s_120m"
    assert roles["far"]["valid_sample_fraction"] > 0.0
    assert abs(body["observer_terrain_elevation_m"] - 6398.92) < 0.01
    # Cache: aceeași cheie, fișier pe disc; altă înălțime a echipamentului dă altă cheie.
    assert (tmp_path / "horizon" / f"{body['cache_key']}.json").is_file()
    again = horizon(api, frame_id=FRAME, observer_height_m=2, **LEIBNITZ)
    assert again == body
    taller = horizon(api, frame_id=FRAME, observer_height_m=10, **LEIBNITZ)
    assert taller["cache_key"] != body["cache_key"]
    assert max(taller["elevation_deg"]) < max(body["elevation_deg"])


@real
def test_missing_far_product_keeps_a_partial_profile(tmp_path: Path) -> None:
    settings = Settings(horizon_cache_dir=None, far_terrain_dir=tmp_path / "synthetic_absent")
    with TestClient(create_app(settings)) as client:
        body = horizon(client, frame_id=FRAME, observer_height_m=2, **LEIBNITZ)
    assert body["status"] == "partial" and body["reason_code"] == "missing_samples"
    assert "far-terrain" in body["reason"]
    assert [p["role"] for p in body["dem_products"]] == ["near"]


def test_unavailable_profiles_carry_a_reason_never_a_free_horizon(api: TestClient) -> None:
    cases: list[tuple[dict[str, Any], str]] = [
        ({"site_id": "apollo11_lm"}, "no_dem_coverage"),
        (
            {"latitude_deg": -69.37, "longitude_deg": 32.32, "frame_id": FRAME},
            "coverage_unverified",
        ),
        (
            {"latitude_deg": -89.5, "longitude_deg": 10.0, "frame_id": FRAME},
            "terrain_not_downloaded",
        ),
    ]
    if LEIBNITZ_RASTER.is_file():
        cases.append(({**LEIBNITZ, "frame_id": "MOON_ME_DE440_ME421"}, "frame_mismatch"))
    for params, code in cases:
        body = horizon(api, observer_height_m=2, **params)
        assert body["status"] == "unavailable" and body["reason_code"] == code, params
        assert body["elevation_deg"] == [] and body["coverage_fraction"] == 0.0


def test_horizon_request_is_validated(api: TestClient) -> None:
    bad: list[dict[str, Any]] = [
        {"observer_height_m": 2},
        {"observer_height_m": 2, "latitude_deg": -85.0, "longitude_deg": 30.0},  # fără cadru
        {"observer_height_m": -1, "site_id": "apollo11_lm"},
        {"site_id": "apollo11_lm"},  # înălțimea echipamentului este obligatorie
        {"observer_height_m": 2, "site_id": "synthetic_absent"},
    ]
    for params in bad:
        assert api.get("/api/horizon", params=params).status_code == 422, params
    response = api.get(
        "/api/horizon",
        params={"observer_height_m": 2, "site_id": "apollo11_lm", "frame_id": FRAME},
    )
    assert response.status_code == 422 and response.json()["code"] == "UNSUPPORTED_FRAME"


@real
def test_dem_simulation_uses_the_profile_and_leaves_visibility_to_e10(api: TestClient) -> None:
    site = next(s for s in api.get("/api/sites").json()["sites"] if "leibnitz" in s["id"])
    body = {
        "sites": [{"site_id": site["id"]}],
        "frame_id": site["frame_id"],
        "start_utc": "2026-11-15T00:00:00Z",
        "end_utc": "2026-11-16T00:00:00Z",
        "observer_height_m": 2,
        "solar_criterion": "disc_center",
        "earth_criterion": {"kind": "center_above_horizon", "min_elevation_deg": 0},
        "terrain_mode": "dem",
        "series_step_s": 3600,
    }
    accepted = api.post("/api/simulations", json=body)
    assert accepted.status_code in (200, 202), accepted.text
    simulation_id = accepted.json()["id"]
    status: dict[str, Any] = {}
    for _ in range(600):
        status = api.get(f"/api/simulations/{simulation_id}").json()
        if status["status"] in ("done", "failed"):
            break
    assert status["status"] == "done", json.dumps(status.get("error"))
    result = status["result"]
    Draft202012Validator(document_schema(SCHEMA, "SimulationResult")).validate(result)
    (site_horizon,) = result["horizon"]
    assert site_horizon["mode"] == "dem" and len(site_horizon["elevation_deg"]) == 720
    profile = horizon(api, site_id=site["id"], observer_height_m=2)
    assert site_horizon["elevation_deg"] == profile["elevation_deg"]
    series = result["series"][0]
    assert any(abs(h) > 0.01 for h in series["sun"]["horizon_elevation_deg"] if h is not None)
    assert set(series["sun"]["visible"]) == {None}
    assert {(n["group"], n["site_ref"]) for n in result["quality"]["not_computed"]} == {
        ("events", site["id"]),
        ("summary", site["id"]),
    }
    assert result["sites"][0]["on_reference_surface"] is False
    assert result["terrain"][0]["available"] is True
    assert result["provenance"]["horizon_parameters"]["mode"] == "dem"
