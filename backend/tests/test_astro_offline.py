"""E03 fără kerneluri: observatorul, azimutul nedefinit, manifestul și arhiva Horizons (D-18)."""

import hashlib
import json
import math

import pytest

from lunarhorizon.astro import horizons
from lunarhorizon.astro.bodies import ObserverSite, az_el_or_undefined
from lunarhorizon.astro.kernels import DEFAULT_MANIFEST_PATH, read_manifest
from lunarhorizon.astro.reference import REFERENCE_DIR, archived_text, load_cases
from lunarhorizon.astro.timeconv import spice_time_string
from lunarhorizon.core.conventions import FRAME_ME_DE440, REFERENCE_RADIUS_M


def test_observer_requires_valid_explicit_values() -> None:
    site = ObserverSite(-89.5, 359.5, -100.0, 2.0)
    assert site.longitude_deg == -0.5
    for bad in [(91.0, 0.0, 0.0, 2.0), (0.0, 0.0, math.nan, 2.0), (0.0, 0.0, 0.0, -1.0)]:
        with pytest.raises(ValueError):
            ObserverSite(*bad)


def test_observer_position_includes_surface_and_observer_heights() -> None:
    site = ObserverSite(0.0, 90.0, -1926.0, 2.0)
    assert site.position_me_m() == pytest.approx((0.0, REFERENCE_RADIUS_M - 1924.0, 0.0), abs=1e-6)


@pytest.mark.parametrize("enu", [(0.0, 0.0, 1.0), (0.0, 0.0, -2.0), (1e-14, 0.0, 1.0)])
def test_azimuth_undefined_at_zenith_and_nadir(enu: tuple[float, float, float]) -> None:
    azimuth, elevation = az_el_or_undefined(enu)
    assert azimuth is None
    assert abs(elevation) == pytest.approx(90.0)


def test_azimuth_defined_away_from_zenith() -> None:
    azimuth, elevation = az_el_or_undefined((1.0, 0.0, 1.0))
    assert azimuth == pytest.approx(90.0)
    assert elevation == pytest.approx(45.0)


def test_spice_time_string_is_utc_iso_without_zone() -> None:
    assert spice_time_string("2026-11-14T14:30:00.25+02:00") == "2026-11-14T12:30:00.250"


def test_kernel_manifest_checksums_were_verified() -> None:
    manifest = read_manifest(DEFAULT_MANIFEST_PATH)
    assert manifest.default_profile == "de440_me421"
    for profile in manifest.profiles:
        assert profile.status == "provisional"
        assert profile.coverage_start_utc is not None
        for kernel in profile.files:
            assert kernel.sha256 is not None and kernel.md5 is not None
            for expected in kernel.expected_checksums:
                actual = kernel.sha256 if expected.algorithm == "sha256" else kernel.md5
                assert actual == expected.value, (kernel.filename, expected.source)
    published = {
        k.filename
        for p in manifest.profiles
        for k in p.files
        for c in k.expected_checksums
        if c.kind == "published_by_source"
    }
    assert {"de440s.bsp", "de421.bsp"} <= published


def test_reference_cases_have_explicit_heights_and_archives() -> None:
    cases = load_cases()
    raw = json.loads((REFERENCE_DIR / "cases.json").read_text(encoding="utf-8"))["cases"]
    assert all(c["height_source"] for c in raw)
    for case in cases:
        for kind in case.queries:
            for body in ("sun", "earth"):
                stem = REFERENCE_DIR / case.case_id / f"{body}_{kind}"
                record = json.loads(stem.with_suffix(".request.json").read_text(encoding="utf-8"))
                raw_bytes = (REFERENCE_DIR / case.case_id / record["response_file"]).read_bytes()
                assert hashlib.sha256(raw_bytes).hexdigest() == record["response_sha256"]
                assert record["http_status"] == 200
                assert record["params"]["SITE_COORD"] == f"'{horizons.site_coord(case.site)}'"


def test_horizons_configuration_matches_project_conventions() -> None:
    """D-18: referința altitudinii, cadrul, longitudinea, refracția, din antetul original."""
    for case in load_cases():
        for body in ("sun", "earth"):
            facts = horizons.header_facts(archived_text(case.case_id, body, "observer"))
            assert "1737.4, 1737.4, 1737.4 km" in facts["Center radii"]
            assert REFERENCE_RADIUS_M == 1737.4 * 1000.0
            assert "MEAN_ME" in facts["Center pole/equ"]
            assert "East-longitude positive" in facts["Center pole/equ"]
            assert "NO (AIRLESS)" in facts["Atmos refraction"]
            assert "DE441" in facts["Target body name"]
    assert FRAME_ME_DE440 == "MOON_ME_DE440_ME421"


def test_horizons_parser_reads_archived_tables() -> None:
    row = horizons.parse_observer(archived_text("a11_dem", "sun", "observer"))
    assert row.utc_calendar == "2026-Nov-14 12:00:00.000"
    assert 0.0 <= row.azimuth_deg < 360.0
    assert row.range_km > 1.4e8
    vector = horizons.parse_vectors(archived_text("a11_catalog", "earth", "vectors"))
    assert 3.5e5 < math.dist((0.0, 0.0, 0.0), vector.position_km) < 4.1e5


def test_horizons_error_payload_is_not_a_result() -> None:
    with pytest.raises(horizons.HorizonsError):
        horizons.result_text(b'{"error": "Bad SITE_COORD"}')
    with pytest.raises(horizons.HorizonsError):
        horizons.result_text(b'{"result": "no table here"}')
