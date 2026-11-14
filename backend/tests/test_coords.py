"""Coordonate, cadru local, azimut și elevație (docs/SPEC_FIZICA.md §3.2, §4)."""

import itertools
import math

import pytest

from lunarhorizon.core.conventions import REFERENCE_RADIUS_M as R
from lunarhorizon.core.coords import (
    CoordinateError,
    Vec3,
    az_el_from_enu,
    azimuth_convention,
    enu_basis,
    enu_from_az_el,
    enu_to_me,
    geographic_to_me,
    local_enu_to_me,
    me_to_enu,
    me_to_geographic,
    me_to_local_enu,
    normalize_longitude_deg,
    validate_latitude_deg,
)

LATITUDES = [-90.0, -89.999999, -89.9, -88.0, -60.0, -1e-9, 0.0, 33.3, 89.9, 90.0]
LONGITUDES = [-180.0, -179.999999, -120.0, -0.5, 0.0, 45.0, 179.999999]
HEIGHTS = [-9000.0, 0.0, 2.0, 11000.0]


def _cross(a: Vec3, b: Vec3) -> Vec3:
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def _dot(a: Vec3, b: Vec3) -> float:
    return sum(x * y for x, y in zip(a, b, strict=True))


def _angle_diff_deg(a: float, b: float) -> float:
    return abs((a - b + 180.0) % 360.0 - 180.0)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (0.0, 0.0),
        (-180.0, -180.0),
        (180.0, -180.0),
        (359.5, -0.5),
        (270.0, -90.0),
        (179.999999, 179.999999),
    ],
)
def test_longitude_normalization(value: float, expected: float) -> None:
    assert normalize_longitude_deg(value) == pytest.approx(expected, abs=1e-12)


@pytest.mark.parametrize("value", [360.0, -180.0001, math.nan, math.inf])
def test_longitude_rejected(value: float) -> None:
    with pytest.raises(CoordinateError):
        normalize_longitude_deg(value)


@pytest.mark.parametrize("value", [90.0000001, -90.5, math.nan, -math.inf])
def test_latitude_rejected(value: float) -> None:
    with pytest.raises(CoordinateError):
        validate_latitude_deg(value)


@pytest.mark.parametrize(
    ("lat", "lon", "expected"),
    [
        (0.0, 0.0, (R, 0.0, 0.0)),
        (0.0, 90.0, (0.0, R, 0.0)),
        (0.0, -180.0, (-R, 0.0, 0.0)),
        (90.0, 0.0, (0.0, 0.0, R)),
        (-90.0, 77.0, (0.0, 0.0, -R)),
    ],
)
def test_me_axes_are_analytic(lat: float, lon: float, expected: Vec3) -> None:
    point = geographic_to_me(lat, lon, 0.0, R)
    assert point == pytest.approx(expected, abs=1e-6)


def test_geographic_me_round_trip(tolerances: dict[str, dict[str, float]]) -> None:
    tol = tolerances["T-04"]
    for lat, lon, h in itertools.product(LATITUDES, LONGITUDES, HEIGHTS):
        lat2, lon2, h2 = me_to_geographic(geographic_to_me(lat, lon, h, R), R)
        assert abs(lat2 - lat) <= tol["angle_deg"]
        assert abs(h2 - h) <= tol["length_m"]
        # Longitudinea se compară ca distanță pe sferă: la pol nu este definită.
        horizontal_error_m = (
            math.radians(_angle_diff_deg(lon2, lon)) * (R + h) * math.cos(math.radians(lat))
        )
        assert horizontal_error_m <= tol["length_m"]


def test_exact_polar_axis_gives_longitude_zero() -> None:
    assert me_to_geographic((0.0, 0.0, -R), R) == (-90.0, 0.0, 0.0)


def test_longitude_continuity_across_antimeridian() -> None:
    east = geographic_to_me(-87.0, 179.999999, 0.0, R)
    west = geographic_to_me(-87.0, -179.999999, 0.0, R)
    gap_m = math.dist(east, west)
    expected_m = math.radians(2e-6) * R * math.cos(math.radians(-87.0))
    assert gap_m == pytest.approx(expected_m, rel=1e-6)
    assert me_to_geographic(geographic_to_me(10.0, 180.0, 0.0, R), R)[1] == -180.0


@pytest.mark.parametrize(("lat", "lon"), list(itertools.product(LATITUDES, LONGITUDES)))
def test_enu_basis_is_orthonormal_and_right_handed(lat: float, lon: float) -> None:
    east, north, up = enu_basis(lat, lon)
    for a, b in [(east, north), (east, up), (north, up)]:
        assert abs(_dot(a, b)) < 1e-15
    for v in (east, north, up):
        assert _dot(v, v) == pytest.approx(1.0, abs=1e-15)
    assert _cross(east, north) == pytest.approx(up, abs=1e-15)
    assert up == pytest.approx(geographic_to_me(lat, lon, 0.0, 1.0), abs=1e-15)


def test_pole_convention_north_points_to_given_meridian() -> None:
    # La polul sud, „nordul” este direcția orizontală spre meridianul dat (D-03, provizoriu).
    for lon in (0.0, 90.0, -135.0):
        _, north, up = enu_basis(-90.0, lon)
        toward_meridian = geographic_to_me(0.0, lon, 0.0, 1.0)
        assert north == pytest.approx(toward_meridian, abs=1e-15)
        assert up == pytest.approx((0.0, 0.0, -1.0), abs=1e-15)
    assert azimuth_convention(-90.0) == "pole_meridian"
    assert azimuth_convention(-89.999999) == "standard"


@pytest.mark.parametrize(
    ("enu", "azimuth", "elevation"),
    [
        ((0.0, 1.0, 0.0), 0.0, 0.0),
        ((1.0, 0.0, 0.0), 90.0, 0.0),
        ((0.0, -1.0, 0.0), 180.0, 0.0),
        ((-1.0, 0.0, 0.0), 270.0, 0.0),
        ((0.0, 0.0, 1.0), 0.0, 90.0),
        ((1.0, 1.0, math.sqrt(2.0)), 45.0, 45.0),
    ],
)
def test_azimuth_from_north_toward_east(enu: Vec3, azimuth: float, elevation: float) -> None:
    az, el = az_el_from_enu(enu)
    assert az == pytest.approx(azimuth, abs=1e-12)
    assert el == pytest.approx(elevation, abs=1e-12)


def test_azimuth_range_is_half_open() -> None:
    az, _ = az_el_from_enu((-1e-300, 1.0, 0.0))
    assert 0.0 <= az < 360.0
    with pytest.raises(CoordinateError):
        az_el_from_enu((0.0, 0.0, 0.0))


def test_az_el_direction_round_trip() -> None:
    for az, el in itertools.product([0.0, 1.0, 89.0, 180.0, 271.5, 359.999], [-89.0, 0.0, 45.0]):
        az2, el2 = az_el_from_enu(enu_from_az_el(az, el))
        assert _angle_diff_deg(az2, az) <= 1e-9
        assert el2 == pytest.approx(el, abs=1e-9)


def test_enu_me_round_trip_and_local_origin(tolerances: dict[str, dict[str, float]]) -> None:
    tol = tolerances["T-04"]["length_m"]
    origin = (-89.5, 30.0, 1200.0)
    origin_me = geographic_to_me(*origin, R)
    for lat, lon in [(-89.4, 31.0), (-89.6, -150.0), (-90.0, 0.0)]:
        point = geographic_to_me(lat, lon, 900.0, R)
        local = me_to_local_enu(point, origin[0], origin[1], origin_me)
        assert math.dist(local_enu_to_me(local, origin[0], origin[1], origin_me), point) <= tol
        # Distanța se păstrează (transformare rigidă).
        assert math.hypot(*local) == pytest.approx(math.dist(point, origin_me), abs=tol)
    vector = (3.0, -4.0, 12.0)
    assert enu_to_me(me_to_enu(vector, -10.0, 20.0), -10.0, 20.0) == pytest.approx(vector)


def test_horizon_drop_on_sphere_is_negative_elevation() -> None:
    # Un punct de pe sferă aflat la 10 km se vede sub planul local: curbura este inclusă.
    observer = geographic_to_me(-89.0, 0.0, 0.0, R)
    target = geographic_to_me(-89.0 + math.degrees(10_000.0 / R), 0.0, 0.0, R)
    local = me_to_local_enu(target, -89.0, 0.0, observer)
    _, elevation = az_el_from_enu(local)
    assert elevation == pytest.approx(-math.degrees(10_000.0 / R) / 2.0, rel=1e-6)
