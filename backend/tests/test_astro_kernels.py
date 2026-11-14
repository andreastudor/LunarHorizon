"""E03 cu kerneluri: acoperire, erori, verificări analitice independente de Horizons."""

import math
from pathlib import Path

import numpy as np
import pytest
import spiceypy

from lunarhorizon.astro.bodies import Body, ObserverSite, body_direction, body_radius_km
from lunarhorizon.astro.kernels import (
    DEFAULT_KERNEL_DIR,
    DEFAULT_MANIFEST_PATH,
    SPICE_LOCK,
    LoadedProfile,
    activate,
    load_profile,
)
from lunarhorizon.astro.timeconv import et_to_utc, utc_to_et
from lunarhorizon.core.coords import wrap_longitude_deg
from lunarhorizon.core.errors import ErrorCode, LunarHorizonError

pytestmark = [
    pytest.mark.kernels,
    pytest.mark.skipif(
        not (DEFAULT_KERNEL_DIR / "de440s.bsp").is_file(),
        reason="kernelurile lipsesc; rulați scripts/download_kernels.py",
    ),
]
UTC = "2026-11-14T12:00:00Z"
SPEED_OF_LIGHT_KM_S = 299792.458


@pytest.fixture(scope="module")
def de440() -> LoadedProfile:
    return load_profile("de440_me421")


def test_coverage_equals_naif_published_summary(de440: LoadedProfile) -> None:
    # aa_summaries.txt (NAIF): de440s.bsp acoperă 1849 DEC 26 00:00:00 - 2150 JAN 22 00:00:00 ET.
    with SPICE_LOCK:
        start = spiceypy.str2et("1849 DEC 26 00:00:00 TDB")
        end = spiceypy.str2et("2150 JAN 22 00:00:00 TDB")
    assert de440.coverage_start_et == pytest.approx(start, abs=1e-3)
    assert de440.coverage_end_et == pytest.approx(end, abs=1e-3)


@pytest.mark.parametrize("utc", ["1849-01-01T00:00:00Z", "2150-06-01T00:00:00Z"])
def test_outside_coverage_is_rejected_with_limits(de440: LoadedProfile, utc: str) -> None:
    site = ObserverSite(0.0, 0.0, 0.0, 2.0)
    with pytest.raises(LunarHorizonError) as info:
        body_direction(de440, site, "sun", utc)
    assert info.value.code == ErrorCode.OUT_OF_EPHEMERIS_COVERAGE
    assert info.value.context["coverage_start_utc"].startswith("1849-12-25T23:59")


def test_de421_profile_has_its_own_narrower_coverage(de440: LoadedProfile) -> None:
    de421 = load_profile("de421")
    try:
        assert de421.coverage_end_utc.startswith("2050-12-31")
        with pytest.raises(LunarHorizonError):
            body_direction(de421, ObserverSite(0.0, 0.0, 0.0, 2.0), "earth", "2060-01-01T00:00:00Z")
    finally:
        activate(de440)


def test_missing_or_altered_kernels_are_refused(tmp_path: Path) -> None:
    with pytest.raises(LunarHorizonError) as missing:
        load_profile("de440_me421", kernel_dir=tmp_path)
    assert missing.value.code == ErrorCode.KERNEL_MISSING
    altered_manifest = tmp_path / "kernels.json"
    text = DEFAULT_MANIFEST_PATH.read_text(encoding="utf-8")
    real = text.split('"sha256": "', 1)[1][:64]
    altered_manifest.write_text(text.replace(real, "0" * 64, 1), encoding="utf-8")
    with pytest.raises(LunarHorizonError, match="SHA-256"):
        load_profile("de440_me421", manifest_path=altered_manifest)


def test_utc_et_round_trip_and_leap_second_count(de440: LoadedProfile) -> None:
    et = utc_to_et(UTC, de440)
    assert et_to_utc(et, de440) == UTC
    # ET - UTC = 32.184 s + 37 s intercalate (naif0012, ultima la 2017-01-01), ±0,002 s (TDB-TT).
    with SPICE_LOCK:
        delta = spiceypy.deltet(et, "ET")
    assert delta == pytest.approx(69.184, abs=0.002)


@pytest.mark.parametrize("target", ["SUN", "EARTH"])
def test_body_is_at_zenith_from_its_sub_point(de440: LoadedProfile, target: str) -> None:
    """Independent de Horizons: din punctul sub-corp, direcția geometrică este radială."""
    et = utc_to_et(UTC, de440)
    with SPICE_LOCK:
        point, _, _ = spiceypy.subpnt(
            "INTERCEPT/ELLIPSOID", "MOON", et, de440.frame_id, "NONE", target
        )
        _, lon, lat = spiceypy.reclat(point)
    site = ObserverSite(math.degrees(lat), math.degrees(lon), 0.0, 0.0)
    body: Body = "sun" if target == "SUN" else "earth"
    zenith = body_direction(de440, site, body, UTC, "NONE")
    assert zenith.elevation_deg == pytest.approx(90.0, abs=1e-6)
    antipode = ObserverSite(
        -site.latitude_deg, wrap_longitude_deg(site.longitude_deg + 180.0), 0.0, 0.0
    )
    nadir = body_direction(de440, antipode, body, UTC, "NONE")
    assert nadir.elevation_deg == pytest.approx(-90.0, abs=1e-6)


def test_observer_state_matches_alternative_spice_path(de440: LoadedProfile) -> None:
    """spkcpo (observator fix) = spkpos(corp față de Lună) - poziția observatorului, pentru NONE."""
    site = ObserverSite(-89.5, 45.0, 1500.0, 2.0)
    et = utc_to_et(UTC, de440)
    observer_km = np.array(site.position_me_m()) / 1000.0
    bodies: tuple[tuple[Body, str], ...] = (("sun", "SUN"), ("earth", "EARTH"))
    for body, name in bodies:
        with SPICE_LOCK:
            moon_to_body, _ = spiceypy.spkpos(name, et, de440.frame_id, "NONE", "MOON")
        direct = body_direction(de440, site, body, UTC, "NONE")
        expected = np.asarray(moon_to_body) - observer_km
        assert direct.distance_km == pytest.approx(float(np.linalg.norm(expected)), abs=1e-6)
        assert direct.light_time_s == pytest.approx(
            direct.distance_km / SPEED_OF_LIGHT_KM_S, rel=1e-12
        )


def test_angular_radius_uses_kernel_radii(de440: LoadedProfile) -> None:
    site = ObserverSite(0.0, 0.0, 0.0, 2.0)
    for body in ("sun", "earth"):
        direction = body_direction(de440, site, body, UTC)
        expected = math.degrees(math.asin(body_radius_km(body, de440) / direction.distance_km))
        assert direction.angular_radius_deg == pytest.approx(expected, rel=1e-12)
    assert body_radius_km("sun", de440) == 695700.0  # pck00011.tpc


def test_pole_convention_rotates_azimuth_with_longitude(de440: LoadedProfile) -> None:
    """D-03 (provizoriu): la pol, longitudinea dată fixează nordul; elevația nu depinde de ea."""
    pole0 = body_direction(de440, ObserverSite(-90.0, 0.0, 0.0, 2.0), "sun", UTC)
    pole90 = body_direction(de440, ObserverSite(-90.0, 90.0, 0.0, 2.0), "sun", UTC)
    assert pole0.azimuth_convention == "pole_meridian"
    assert pole0.elevation_deg == pytest.approx(pole90.elevation_deg, abs=1e-12)
    assert pole0.azimuth_deg is not None and pole90.azimuth_deg is not None
    assert (pole0.azimuth_deg - pole90.azimuth_deg) % 360.0 == pytest.approx(90.0, abs=1e-9)


def test_aberration_size_is_physically_plausible(de440: LoadedProfile) -> None:
    """Între direcția geometrică și cea aparentă a Soarelui: aberație de ordinul v/c ≈ 0,0057°."""
    site = ObserverSite(0.0, 0.0, 0.0, 2.0)
    geometric = np.array(body_direction(de440, site, "sun", UTC, "NONE").direction_enu)
    apparent = np.array(body_direction(de440, site, "sun", UTC, "LT+S").direction_enu)
    separation = math.degrees(math.acos(min(1.0, float(geometric @ apparent))))
    assert 0.002 < separation < 0.01
