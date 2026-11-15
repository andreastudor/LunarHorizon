"""Comparația cu referințele Horizons arhivate (T-01, T-02) și diferența dintre profiluri (T-03).

T-01: acceptare 0,001°, diagnostic 0,00001° pe setul fix (confirmate de astronomi, comunicat de
utilizator); T-02/T-03 neschimbate. Acordul cu Horizons compară două implementări JPL (DE440s local,
DE441 la Horizons), nu observații independente, și nu validează coordonatele siturilor sau DEM-ul.
"""

import json
from collections.abc import Iterator

import numpy as np
import pytest
import spiceypy

from lunarhorizon.astro import horizons
from lunarhorizon.astro.bodies import ObserverSite, body_direction, body_direction_et
from lunarhorizon.astro.kernels import (
    DEFAULT_KERNEL_DIR,
    SPICE_LOCK,
    LoadedProfile,
    activate,
    load_profile,
)
from lunarhorizon.astro.reference import (
    PROPOSED_TOLERANCES,
    REFERENCE_DIR,
    T01_ACCEPTANCE_DEG,
    T01_DIAGNOSTIC_DEG,
    ReferenceCase,
    compare_direction,
    compare_vector,
    load_cases,
    separation_deg,
)
from lunarhorizon.core.conventions import APPARENT_CORRECTION
from lunarhorizon.core.coords import enu_from_az_el

pytestmark = [
    pytest.mark.kernels,
    pytest.mark.skipif(
        not (DEFAULT_KERNEL_DIR / "de440s.bsp").is_file(),
        reason="kernelurile lipsesc; rulați scripts/download_kernels.py",
    ),
]
CASES = load_cases()
VALIDATION_CASES = [c for c in CASES if not c.diagnostic]


@pytest.fixture(scope="module")
def de440() -> Iterator[LoadedProfile]:
    profile = load_profile("de440_me421")
    yield profile


@pytest.mark.parametrize("correction", ["LT+S", "CN+S"])
@pytest.mark.parametrize("body", ["sun", "earth"])
@pytest.mark.parametrize("case", VALIDATION_CASES, ids=[c.case_id for c in VALIDATION_CASES])
def test_apparent_direction_and_range_match_horizons(
    de440: LoadedProfile, case: ReferenceCase, body: str, correction: str
) -> None:
    result = compare_direction(de440, case, body, correction)  # type: ignore[arg-type]
    assert result.separation_deg <= T01_ACCEPTANCE_DEG
    assert abs(result.distance_diff_km) <= PROPOSED_TOLERANCES["T-02_distance_km"]
    if correction == APPARENT_CORRECTION:
        # Diagnostic T-01 pe setul fix versionat (configurația implicită, compatibilă).
        assert result.separation_deg <= T01_DIAGNOSTIC_DEG


def test_d02_default_apparent_correction_is_cn_s_everywhere() -> None:
    from lunarhorizon.astro import bodies
    from lunarhorizon.simulation import idealized

    assert APPARENT_CORRECTION == "CN+S"
    assert bodies.DEFAULT_APPARENT_CORRECTION == APPARENT_CORRECTION
    assert not hasattr(idealized, "APPARENT_CORRECTION") or (
        idealized.APPARENT_CORRECTION == APPARENT_CORRECTION
    )
    assert T01_ACCEPTANCE_DEG == 1e-3 and T01_DIAGNOSTIC_DEG == 1e-5


CNS_ARCHIVE = REFERENCE_DIR.parent / "cns_review_2026_11_14"


@pytest.mark.parametrize("body", ["sun", "earth"])
def test_cns_review_cases_rerun_in_the_current_engine(de440: LoadedProfile, body: str) -> None:
    """Cele 10 comparații ale pachetului, cu exact intrările cererilor (inclusiv microsecundele)."""
    cases = json.loads((CNS_ARCHIVE / "cases.json").read_text(encoding="utf-8"))["cases"]
    assert len(cases) == 5
    for case in cases:
        site = ObserverSite(
            case["latitude_deg"], case["longitude_deg"], case["surface_height_m"], 2.0
        )
        document = json.loads((CNS_ARCHIVE / case["references"][body]).read_text(encoding="utf-8"))
        raw = json.dumps(document["response"]).encode("utf-8")
        reference = horizons.parse_observer(horizons.result_text(raw))
        with SPICE_LOCK:
            et = spiceypy.str2et(case["utc"].rstrip("Z").replace("T", " ") + " UTC")
        calc = body_direction_et(de440, site, body, et, case["utc"])  # type: ignore[arg-type]
        assert calc.correction == "CN+S"
        ref_unit = np.array(enu_from_az_el(reference.azimuth_deg, reference.elevation_deg))
        separation = separation_deg(np.array(calc.direction_enu), ref_unit)
        assert separation <= T01_ACCEPTANCE_DEG
        assert separation <= T01_DIAGNOSTIC_DEG


@pytest.mark.parametrize("body", ["sun", "earth"])
def test_geometric_icrf_vectors_match_horizons(de440: LoadedProfile, body: str) -> None:
    case = next(c for c in CASES if "vectors" in c.queries)
    result = compare_vector(de440, case, body)  # type: ignore[arg-type]
    assert result.vector_diff_km <= PROPOSED_TOLERANCES["T-02_vector_km"]


def test_exact_pole_diagnostic_is_recorded(de440: LoadedProfile) -> None:
    # Diagnostic (D-03/D-18): nu este un criteriu T-01; verifică doar că rezultatul este definit.
    case = next(c for c in CASES if c.diagnostic)
    for body in ("sun", "earth"):
        result = compare_direction(de440, case, body, APPARENT_CORRECTION)
        assert np.isfinite(result.separation_deg)


def test_profile_difference_t03(de440: LoadedProfile) -> None:
    de421 = load_profile("de421")
    try:
        for case in CASES:
            for body in ("sun", "earth"):
                a = body_direction(de440, case.site, body, case.utc)
                b = body_direction(de421, case.site, body, case.utc)
                separation = separation_deg(np.array(a.direction_enu), np.array(b.direction_enu))
                assert separation <= PROPOSED_TOLERANCES["T-03_separation_deg"]
    finally:
        activate(de440)
