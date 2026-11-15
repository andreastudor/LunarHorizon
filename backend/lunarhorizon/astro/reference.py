"""Comparația motorului cu referințele Horizons arhivate (docs/VALIDARE.md §3).

Criteriul principal pentru direcții este separarea unghiulară dintre versori,
ε = atan2(|a x b|, a · b), stabilă și lângă zenit, unde azimutul nu este bine condiționat.
Se raportează separat ΔA (cu trecerea peste 0°/360°), Δe și diferența de distanță.
Pentru vectori: ‖v_calc - v_ref‖ în km, la momentul TDB raportat de Horizons.
"""

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final

import numpy as np

from lunarhorizon.astro import horizons
from lunarhorizon.astro.bodies import (
    Body,
    ObserverSite,
    body_direction,
    body_vector_icrf_km,
)
from lunarhorizon.astro.kernels import REPO_ROOT, LoadedProfile
from lunarhorizon.core.conventions import Correction
from lunarhorizon.core.coords import enu_from_az_el

REFERENCE_DIR: Final = REPO_ROOT / "data" / "reference" / "horizons"
J2000_JD: Final = 2451545.0
SECONDS_PER_DAY: Final = 86400.0

# Pragurile T-01, T-02, T-03 (docs/VALIDARE.md §2, D-12). Sunt praguri de acord între implementări
# JPL, nu acuratețe fizică. T-02 (0,1 km) și T-03 (0,001°) au fost confirmate de astronomi
# (comunicat, 2026-11-14). Pragul pentru vectori (T-02_vector_km) rămâne cel propus. Numele
# dicționarului este istoric; pentru T-01 se folosesc constantele de mai jos.
# T-01: acceptare la separare <= 0,001° pentru configurații compatibile (observator, epocă, cadru,
# corecție) — confirmată de astronomi, comunicată de utilizator în conversația din 2026-11-15.
# Diagnostic: o separare > 0,00001° pe setul fix versionat de referințe se semnalează și se
# investighează separat, chiar dacă T-01 trece. Nu schimbă T-02/T-03.
T01_ACCEPTANCE_DEG: Final = 1e-3
T01_DIAGNOSTIC_DEG: Final = 1e-5

PROPOSED_TOLERANCES: Final[dict[str, float]] = {
    "T-01_separation_deg": 1e-3,
    "T-02_distance_km": 0.1,
    "T-02_vector_km": 0.1,
    "T-03_separation_deg": 1e-3,
}


@dataclass(frozen=True)
class ReferenceCase:
    case_id: str
    matrix_id: str
    purpose: str
    site: ObserverSite
    utc: str
    queries: tuple[str, ...]
    diagnostic: bool


@dataclass(frozen=True)
class DirectionComparison:
    case_id: str
    body: Body
    correction: Correction
    profile_id: str
    calc_azimuth_deg: float | None
    calc_elevation_deg: float
    ref_azimuth_deg: float
    ref_elevation_deg: float
    azimuth_diff_deg: float | None
    elevation_diff_deg: float
    separation_deg: float
    calc_distance_km: float
    ref_distance_km: float
    distance_diff_km: float
    diagnostic: bool


@dataclass(frozen=True)
class VectorComparison:
    case_id: str
    body: Body
    profile_id: str
    jd_tdb: float
    calc_vector_km: tuple[float, float, float]
    ref_vector_km: tuple[float, float, float]
    vector_diff_km: float
    separation_deg: float


def load_cases(path: Path = REFERENCE_DIR / "cases.json") -> list[ReferenceCase]:
    raw = json.loads(path.read_text(encoding="utf-8"))["cases"]
    return [
        ReferenceCase(
            case_id=c["case_id"],
            matrix_id=c["matrix_id"],
            purpose=c["purpose"],
            site=ObserverSite(
                c["latitude_deg"], c["longitude_deg"], c["surface_height_m"], c["observer_height_m"]
            ),
            utc=c["utc"],
            queries=tuple(c["queries"]),
            diagnostic=bool(c["diagnostic"]),
        )
        for c in raw
    ]


def archived_text(case_id: str, body: Body, kind: str) -> str:
    raw = (REFERENCE_DIR / case_id / f"{body}_{kind}.response.json").read_bytes()
    return horizons.result_text(raw)


def separation_deg(a: np.ndarray, b: np.ndarray) -> float:
    return math.degrees(math.atan2(float(np.linalg.norm(np.cross(a, b))), float(np.dot(a, b))))


def wrap_deg(angle: float) -> float:
    return (angle + 180.0) % 360.0 - 180.0


def compare_direction(
    profile: LoadedProfile, case: ReferenceCase, body: Body, correction: Correction
) -> DirectionComparison:
    reference = horizons.parse_observer(archived_text(case.case_id, body, "observer"))
    calc = body_direction(profile, case.site, body, case.utc, correction)
    ref_unit = np.array(enu_from_az_el(reference.azimuth_deg, reference.elevation_deg))
    calc_unit = np.array(calc.direction_enu)
    calc_unit = calc_unit / np.linalg.norm(calc_unit)
    return DirectionComparison(
        case_id=case.case_id,
        body=body,
        correction=correction,
        profile_id=profile.profile_id,
        calc_azimuth_deg=calc.azimuth_deg,
        calc_elevation_deg=calc.elevation_deg,
        ref_azimuth_deg=reference.azimuth_deg,
        ref_elevation_deg=reference.elevation_deg,
        azimuth_diff_deg=(
            None if calc.azimuth_deg is None else wrap_deg(calc.azimuth_deg - reference.azimuth_deg)
        ),
        elevation_diff_deg=calc.elevation_deg - reference.elevation_deg,
        separation_deg=separation_deg(calc_unit, ref_unit),
        calc_distance_km=calc.distance_km,
        ref_distance_km=reference.range_km,
        distance_diff_km=calc.distance_km - reference.range_km,
        diagnostic=case.diagnostic,
    )


def compare_vector(profile: LoadedProfile, case: ReferenceCase, body: Body) -> VectorComparison:
    reference = horizons.parse_vectors(archived_text(case.case_id, body, "vectors"))
    et = (reference.jd_tdb - J2000_JD) * SECONDS_PER_DAY
    calc = body_vector_icrf_km(profile, case.site, body, et, "NONE")
    ref = np.array(reference.position_km)
    return VectorComparison(
        case_id=case.case_id,
        body=body,
        profile_id=profile.profile_id,
        jd_tdb=reference.jd_tdb,
        calc_vector_km=(float(calc[0]), float(calc[1]), float(calc[2])),
        ref_vector_km=reference.position_km,
        vector_diff_km=float(np.linalg.norm(calc - ref)),
        separation_deg=separation_deg(calc / np.linalg.norm(calc), ref / np.linalg.norm(ref)),
    )


def header_summary(case_id: str, body: Body, kind: str = "observer") -> dict[str, Any]:
    return horizons.header_facts(archived_text(case_id, body, kind))
