"""Vectorii de test comuni Python ↔ TypeScript (tests/vectors/conventions.json).

Intrările sunt fixate aici. Ieșirile așteptate sunt calculate de implementarea Python din `core`
(sursa „python-reference”) și servesc testului de concordanță din frontend (toleranța T-05).
Implementarea Python este verificată separat, prin proprietăți independente: dus-întors, PROJ,
cazuri analitice (backend/tests/).

Fișierul se regenerează cu `scripts/generate_contracts.py`; un test verifică că este la zi.
"""

from typing import Any, Final

from lunarhorizon.core import conventions as conv
from lunarhorizon.core.coords import (
    CoordinateError,
    az_el_from_enu,
    enu_basis,
    geographic_to_me,
    me_to_local_enu,
    normalize_longitude_deg,
    validate_latitude_deg,
)
from lunarhorizon.core.projection import SouthPolarStereographic
from lunarhorizon.core.utc import UtcParseError, canonical_utc

# Toleranțele de implementare (docs/VALIDARE.md §2). Verifică aritmetica, nu fizica.
TOLERANCES: Final[dict[str, dict[str, float]]] = {
    "T-04": {"angle_deg": 1e-9, "length_m": 1e-6},
    "T-05": {"angle_deg": 1e-9, "length_m": 1e-6, "unit_vector": 1e-12, "scale_factor": 1e-12},
}

UTC_VALID: Final = [
    "2026-11-14T12:00:00Z",
    "2026-11-14T12:00:00.5Z",
    "2026-11-14T12:00:00.120Z",
    "2026-11-14T12:00:00.001Z",
    "2026-11-14T14:30:00+02:00",
    "2026-11-14T08:30:00-03:30",
    "2026-11-14T23:59:59.999-00:01",
    "2028-02-29T00:00:00Z",
    "2026-01-01T01:00:00+01:00",
    "1999-12-31T23:59:59Z",
    "0099-06-15T12:00:00Z",
]
UTC_INVALID: Final = [
    "2026-11-14T12:00:00",
    "2026-11-14 12:00:00Z",
    "2026-11-14T12:00Z",
    "2026-11-14T12:00:00.1234Z",
    "2026-11-14T12:00:00z",
    "2026-11-14",
    "2026-02-29T00:00:00Z",
    "2026-13-01T00:00:00Z",
    "2026-11-14T24:00:00Z",
    "2026-11-14T12:60:00Z",
    "2016-12-31T23:59:60Z",
    "2026-11-14T12:00:00+24:00",
    "2026-11-14T12:00:00+02:60",
    "0000-01-01T00:00:00Z",
    "9999-12-31T23:30:00-01:00",
    "0001-01-01T00:30:00+01:00",
    " 2026-11-14T12:00:00Z",
]

LONGITUDE_INPUTS: Final = [
    0.0,
    -180.0,
    180.0,
    179.999999,
    -179.999999,
    359.5,
    270.0,
    -0.0,
    90.0,
    359.999999999,
    360.0,
    -180.0001,
    400.0,
]
LATITUDE_INVALID: Final = [90.0000001, -90.5, 180.0]

GEOGRAPHIC_POINTS: Final = [
    (0.0, 0.0, 0.0),
    (0.0, 90.0, 0.0),
    (0.0, -90.0, 0.0),
    (0.0, -180.0, 0.0),
    (90.0, 0.0, 0.0),
    (-90.0, 0.0, 0.0),
    (-90.0, 135.0, 1500.0),
    (-89.9, 179.999999, -2500.0),
    (-89.9, -179.999999, -2500.0),
    (-87.5, 45.0, 1200.0),
    (-85.0, -120.0, 6000.0),
    (23.4, 3.6, -1800.0),
    (-12.75, -77.3, 250.0),
]
AZ_EL_ENU: Final = [
    (0.0, 1.0, 0.0),
    (1.0, 0.0, 0.0),
    (0.0, -1.0, 0.0),
    (-1.0, 0.0, 0.0),
    (-1e-12, 1.0, 0.0),
    (1.0, 1.0, 1.0),
    (0.0, 0.0, 1.0),
    (0.0, 0.0, -1.0),
    (-3.0, -4.0, 0.5),
]
STEREO_POINTS: Final = [
    (-90.0, 0.0),
    (-89.0, 0.0),
    (-87.0, 90.0),
    (-88.5, -135.0),
    (-80.0, 179.999999),
    (-80.0, -179.999999),
    (-60.0, 45.0),
    (-89.99, 270.0 - 360.0),
]
LOCAL_ENU_CASES: Final = [
    ((-89.5, 0.0, 1000.0), (-89.4, 10.0, 1500.0)),
    ((-87.0, 45.0, 0.0), (-87.0, 45.01, 0.0)),
    ((-90.0, 0.0, 0.0), (-89.99, 90.0, 100.0)),
    ((-88.0, 179.99, 200.0), (-88.0, -179.99, 200.0)),
]


def _utc_section() -> dict[str, Any]:
    valid = [{"input": text, "canonical": canonical_utc(text)} for text in UTC_VALID]
    invalid = []
    for text in UTC_INVALID:
        try:
            canonical_utc(text)
        except UtcParseError as exc:
            invalid.append({"input": text, "reason": exc.reason})
        else:
            raise AssertionError(f"intrare marcată invalidă, dar acceptată: {text!r}")
    return {"valid": valid, "invalid": invalid}


def _longitude_section() -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    for value in LONGITUDE_INPUTS:
        try:
            cases.append({"input": value, "output": normalize_longitude_deg(value)})
        except CoordinateError as exc:
            cases.append({"input": value, "error": exc.reason})
    return cases


def _latitude_invalid_section() -> list[dict[str, Any]]:
    cases = []
    for value in LATITUDE_INVALID:
        try:
            validate_latitude_deg(value)
        except CoordinateError as exc:
            cases.append({"input": value, "error": exc.reason})
        else:
            raise AssertionError(f"latitudine marcată invalidă, dar acceptată: {value!r}")
    return cases


def build_reference_vectors() -> dict[str, Any]:
    radius = conv.REFERENCE_RADIUS_M
    projection = SouthPolarStereographic()
    return {
        "description": (
            "Vectori de test comuni Python și TypeScript. Intrări fixate în "
            "backend/lunarhorizon/core/reference_vectors.py; ieșiri calculate de implementarea "
            "Python. Nu sunt valori validate fizic. "
            "Se regenerează cu scripts/generate_contracts.py."
        ),
        "source": "python-reference",
        "schema_version": conv.SCHEMA_VERSION,
        "conventions": {
            "reference_radius_m": radius,
            "supported_frames": list(conv.SUPPORTED_FRAMES),
            "default_frame": conv.DEFAULT_FRAME,
            "rejected_frame_aliases": list(conv.REJECTED_FRAME_ALIASES),
            "longitude_output_range_deg": [-180.0, 180.0],
            "longitude_input_range_deg": [-180.0, 360.0],
            "unit_suffixes": list(conv.UNIT_SUFFIXES),
            "provisional_decisions": conv.PROVISIONAL_DECISIONS,
            "polar_stereographic": {
                "proj4": projection.to_proj4(),
                "status": projection.status,
            },
        },
        "tolerances": TOLERANCES,
        "utc": _utc_section(),
        "longitude_normalization": _longitude_section(),
        "latitude_invalid": _latitude_invalid_section(),
        "geographic_to_me": [
            {
                "latitude_deg": lat,
                "longitude_deg": lon,
                "height_m": h,
                "me_m": list(geographic_to_me(lat, lon, h, radius)),
            }
            for lat, lon, h in GEOGRAPHIC_POINTS
        ],
        "enu_basis": [
            {
                "latitude_deg": lat,
                "longitude_deg": lon,
                "east": list(basis[0]),
                "north": list(basis[1]),
                "up": list(basis[2]),
            }
            for lat, lon, _ in GEOGRAPHIC_POINTS
            for basis in [enu_basis(lat, lon)]
        ],
        "az_el": [
            {
                "enu": list(vector),
                "azimuth_deg": az_el[0],
                "elevation_deg": az_el[1],
            }
            for vector in AZ_EL_ENU
            for az_el in [az_el_from_enu(vector)]
        ],
        "polar_stereographic": [
            {
                "latitude_deg": lat,
                "longitude_deg": lon,
                "x_m": xy[0],
                "y_m": xy[1],
                "scale_factor": projection.scale(lat),
            }
            for lat, lon in STEREO_POINTS
            for xy in [projection.forward(lat, lon)]
        ],
        "local_enu": [
            {
                "origin": {"latitude_deg": o[0], "longitude_deg": o[1], "height_m": o[2]},
                "point": {"latitude_deg": p[0], "longitude_deg": p[1], "height_m": p[2]},
                "enu_m": list(
                    me_to_local_enu(
                        geographic_to_me(p[0], p[1], p[2], radius),
                        o[0],
                        o[1],
                        geographic_to_me(o[0], o[1], o[2], radius),
                    )
                ),
            }
            for o, p in LOCAL_ENU_CASES
        ],
    }
