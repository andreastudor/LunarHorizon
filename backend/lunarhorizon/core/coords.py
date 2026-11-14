"""Coordonate pe Lună și cadrul local al observatorului (docs/SPEC_FIZICA.md §3.2 și §4).

- Latitudine planetocentrică în [-90, 90]; longitudine pozitivă spre est, normalizată în
  [-180, 180). La intrare se acceptă și [0, 360).
- Cartezian ME în metri: r = (R_ref + h) · u(lat, lon), pe sfera de referință (raza: decizia D-05).
- Baza locală E, N, U; azimut de la nord spre est în [0, 360); elevație față de planul
  perpendicular pe direcția radială.
- La |lat| = 90°, „nordul” este direcția spre meridianul longitudinii date
  (convenție provizorie, decizia D-03).

Funcțiile lucrează cu vectori ai cadrului ME fără a ști de efemeride: cadrul exact (D-01) este
o etichetă a datelor, nu o transformare aplicată aici.
"""

import math
from typing import Literal

from lunarhorizon.core.units import deg_to_rad, rad_to_deg

Vec3 = tuple[float, float, float]
CoordinateErrorReason = Literal[
    "not_finite",
    "latitude_out_of_range",
    "longitude_out_of_range",
    "zero_vector",
]
AzimuthConvention = Literal["standard", "pole_meridian"]


class CoordinateError(ValueError):
    def __init__(self, reason: CoordinateErrorReason, value: object) -> None:
        super().__init__(f"{reason}: {value!r}")
        self.reason: CoordinateErrorReason = reason


def validate_latitude_deg(latitude_deg: float) -> float:
    if not math.isfinite(latitude_deg):
        raise CoordinateError("not_finite", latitude_deg)
    if not -90.0 <= latitude_deg <= 90.0:
        raise CoordinateError("latitude_out_of_range", latitude_deg)
    return float(latitude_deg)


def normalize_longitude_deg(longitude_deg: float) -> float:
    """Acceptă [-180, 360) și întoarce valoarea echivalentă din [-180, 180)."""
    if not math.isfinite(longitude_deg):
        raise CoordinateError("not_finite", longitude_deg)
    if not -180.0 <= longitude_deg < 360.0:
        raise CoordinateError("longitude_out_of_range", longitude_deg)
    return wrap_longitude_deg(longitude_deg)


def wrap_longitude_deg(longitude_deg: float) -> float:
    """Aduce orice longitudine finită în [-180, 180); pentru valori calculate, nu pentru intrări."""
    if not math.isfinite(longitude_deg):
        raise CoordinateError("not_finite", longitude_deg)
    return ((longitude_deg + 180.0) % 360.0) - 180.0


def azimuth_convention(latitude_deg: float) -> AzimuthConvention:
    return "pole_meridian" if abs(latitude_deg) == 90.0 else "standard"


def unit_vector(latitude_deg: float, longitude_deg: float) -> Vec3:
    lat, lon = deg_to_rad(latitude_deg), deg_to_rad(longitude_deg)
    return (math.cos(lat) * math.cos(lon), math.cos(lat) * math.sin(lon), math.sin(lat))


def geographic_to_me(
    latitude_deg: float, longitude_deg: float, height_m: float, radius_m: float
) -> Vec3:
    ux, uy, uz = unit_vector(latitude_deg, longitude_deg)
    r = radius_m + height_m
    return (r * ux, r * uy, r * uz)


def me_to_geographic(point_m: Vec3, radius_m: float) -> tuple[float, float, float]:
    """Întoarce (lat_deg, lon_deg, înălțime_m). Exact pe axa polară, longitudinea este 0."""
    x, y, z = point_m
    latitude_deg = rad_to_deg(math.atan2(z, math.hypot(x, y)))
    longitude_deg = wrap_longitude_deg(rad_to_deg(math.atan2(y, x)))
    return latitude_deg, longitude_deg, math.hypot(x, y, z) - radius_m


def enu_basis(latitude_deg: float, longitude_deg: float) -> tuple[Vec3, Vec3, Vec3]:
    lat, lon = deg_to_rad(latitude_deg), deg_to_rad(longitude_deg)
    sin_lat, cos_lat = math.sin(lat), math.cos(lat)
    sin_lon, cos_lon = math.sin(lon), math.cos(lon)
    east = (-sin_lon, cos_lon, 0.0)
    north = (-sin_lat * cos_lon, -sin_lat * sin_lon, cos_lat)
    up = (cos_lat * cos_lon, cos_lat * sin_lon, sin_lat)
    return east, north, up


def _dot(a: Vec3, b: Vec3) -> float:
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def me_to_enu(vector_me: Vec3, latitude_deg: float, longitude_deg: float) -> Vec3:
    """Componentele (e, n, u) ale unui vector ME în baza locală din (lat, lon)."""
    east, north, up = enu_basis(latitude_deg, longitude_deg)
    return (_dot(vector_me, east), _dot(vector_me, north), _dot(vector_me, up))


def enu_to_me(vector_enu: Vec3, latitude_deg: float, longitude_deg: float) -> Vec3:
    east, north, up = enu_basis(latitude_deg, longitude_deg)
    e, n, u = vector_enu
    return (
        e * east[0] + n * north[0] + u * up[0],
        e * east[1] + n * north[1] + u * up[1],
        e * east[2] + n * north[2] + u * up[2],
    )


def az_el_from_enu(vector_enu: Vec3) -> tuple[float, float]:
    """Azimut în [0, 360) de la nord spre est și elevație în [-90, 90], în grade."""
    e, n, u = vector_enu
    length = math.hypot(e, n, u)
    if length == 0.0:
        raise CoordinateError("zero_vector", vector_enu)
    azimuth_deg = rad_to_deg(math.atan2(e, n))
    if azimuth_deg < 0.0:
        azimuth_deg += 360.0
    if azimuth_deg >= 360.0:
        azimuth_deg = 0.0
    elevation_deg = rad_to_deg(math.asin(max(-1.0, min(1.0, u / length))))
    return azimuth_deg, elevation_deg


def enu_from_az_el(azimuth_deg: float, elevation_deg: float) -> Vec3:
    """Versorul direcției: d = sin(az)cos(el)·E + cos(az)cos(el)·N + sin(el)·U."""
    az, el = deg_to_rad(azimuth_deg), deg_to_rad(elevation_deg)
    return (math.sin(az) * math.cos(el), math.cos(az) * math.cos(el), math.sin(el))


def me_to_local_enu(
    point_me: Vec3, origin_latitude_deg: float, origin_longitude_deg: float, origin_me: Vec3
) -> Vec3:
    """Poziția unui punct față de o origine locală, în metri, pe baza E, N, U din origine."""
    offset = (point_me[0] - origin_me[0], point_me[1] - origin_me[1], point_me[2] - origin_me[2])
    return me_to_enu(offset, origin_latitude_deg, origin_longitude_deg)


def local_enu_to_me(
    point_enu: Vec3, origin_latitude_deg: float, origin_longitude_deg: float, origin_me: Vec3
) -> Vec3:
    dx, dy, dz = enu_to_me(point_enu, origin_latitude_deg, origin_longitude_deg)
    return (origin_me[0] + dx, origin_me[1] + dy, origin_me[2] + dz)
