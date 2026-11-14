"""Proiecția stereografică polară sudică, comparată cu PROJ (prin Rasterio)."""

import itertools
import math

import pytest
from rasterio.crs import CRS
from rasterio.warp import transform

from lunarhorizon.core.conventions import REFERENCE_RADIUS_M as R
from lunarhorizon.core.coords import CoordinateError
from lunarhorizon.core.projection import SouthPolarStereographic

PROJECTION = SouthPolarStereographic()
LATITUDES = [-90.0, -89.99, -89.0, -87.0, -85.0, -80.0, -70.0, -60.0, -30.0]
LONGITUDES = [-180.0, -179.999999, -135.0, -90.0, -0.001, 0.0, 45.0, 90.0, 179.999999]


def test_forward_matches_proj(tolerances: dict[str, dict[str, float]]) -> None:
    tol = tolerances["T-04"]["length_m"]
    geographic = CRS.from_proj4(f"+proj=longlat +R={R!r} +no_defs")
    stereo = CRS.from_proj4(PROJECTION.to_proj4())
    points = list(itertools.product(LATITUDES, LONGITUDES))
    xs, ys = transform(geographic, stereo, [p[1] for p in points], [p[0] for p in points])
    for (lat, lon), x_proj, y_proj in zip(points, xs, ys, strict=True):
        x, y = PROJECTION.forward(lat, lon)
        assert math.hypot(x - x_proj, y - y_proj) <= tol, (lat, lon)


def test_default_parameters_equal_iau_2015_30135() -> None:
    # Coincidență cu codul IAU; NU confirmă CRS-ul fișierelor PGDA (decizia D-06 rămâne deschisă).
    iau = CRS.from_user_input("IAU_2015:30135").to_dict()
    ours = CRS.from_proj4(PROJECTION.to_proj4()).to_dict()
    for key in ("proj", "lat_0", "lon_0", "k", "x_0", "y_0", "R"):
        assert iau[key] == ours[key], key
    assert PROJECTION.status == "provisional"


def test_inverse_round_trip(tolerances: dict[str, dict[str, float]]) -> None:
    tol = tolerances["T-04"]["angle_deg"]
    for lat, lon in itertools.product(LATITUDES, LONGITUDES):
        lat2, lon2 = PROJECTION.inverse(*PROJECTION.forward(lat, lon))
        assert abs(lat2 - lat) <= tol
        if lat > -90.0:
            assert abs((lon2 - lon + 180.0) % 360.0 - 180.0) * math.cos(math.radians(lat)) <= tol
    assert PROJECTION.inverse(0.0, 0.0) == (-90.0, 0.0)


def test_axes_orientation() -> None:
    x, y = PROJECTION.forward(-89.0, 0.0)
    assert x == pytest.approx(0.0, abs=1e-9)
    assert y > 0.0
    x, y = PROJECTION.forward(-89.0, 90.0)
    assert x > 0.0
    assert y == pytest.approx(0.0, abs=1e-9)


def test_continuity_across_antimeridian() -> None:
    east = PROJECTION.forward(-80.0, 179.999999)
    west = PROJECTION.forward(-80.0, -179.999999)
    assert math.dist(east, west) < 1.0


def test_scale_factor_matches_numerical_derivative() -> None:
    for lat in (-90.0, -89.0, -85.0, -70.0):
        step_deg = 1e-6
        y1 = math.hypot(*PROJECTION.forward(lat, 0.0))
        y2 = math.hypot(*PROJECTION.forward(lat + step_deg, 0.0))
        numeric = (y2 - y1) / (math.radians(step_deg) * R)
        assert numeric == pytest.approx(PROJECTION.scale(lat + step_deg / 2.0), rel=1e-6)
    assert PROJECTION.scale(-90.0) == 1.0


def test_north_pole_not_representable() -> None:
    with pytest.raises(CoordinateError):
        PROJECTION.forward(90.0, 0.0)
