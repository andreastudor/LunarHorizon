"""Catalogul E04: validare structurală, tipuri de poziții, trasabilitate și legătura cu E03.

Testele sunt offline. Ele NU dovedesc că pozițiile sunt corecte fizic: verificarea științifică este
în docs/VALIDARE.md §7 și în scripts/verify_catalog_sources.py (rețea).
"""

import copy
import json
import math
import re
from typing import Any

import pytest
from jsonschema import Draft202012Validator
from pydantic import ValidationError

from lunarhorizon.astro.reference import load_cases
from lunarhorizon.catalog import DEFAULT_CATALOG_PATH, get_site, load_catalog, planned_target_of
from lunarhorizon.contracts.catalog import Catalog, Site
from lunarhorizon.contracts.export import build_schema, document_schema
from lunarhorizon.core.conventions import REFERENCE_RADIUS_M, SUPPORTED_FRAMES
from lunarhorizon.core.coords import geographic_to_me, normalize_longitude_deg
from tests.support import REPO_ROOT, read_json

CATALOG = load_catalog()
RAW = read_json(DEFAULT_CATALOG_PATH)
APOLLO_IDS = [f"apollo{n}_lm" for n in (11, 12, 14, 15, 16, 17)]
PDS_ZIP_SHA256 = "f0145e0b8871053f3358c599d356a5af05db70e4da2fe8c91264e84b98e4408b"
# Diferența maximă admisă între poziția adoptată și o coroborare, în metri. Nu este o toleranță
# științifică: detectează un conflict între surse, care ar trebui investigat, nu mediat.
CORROBORATION_BOUND_M = 100.0


def _distance_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    a = geographic_to_me(lat1, lon1, 0.0, REFERENCE_RADIUS_M)
    b = geographic_to_me(lat2, lon2, 0.0, REFERENCE_RADIUS_M)
    return math.dist(a, b)


def _mutated(change: Any) -> dict[str, Any]:
    document: dict[str, Any] = copy.deepcopy(RAW)
    change(document)
    return document


def _site(document: dict[str, Any], site_id: str) -> dict[str, Any]:
    return next(s for s in document["sites"] if s["id"] == site_id)


# --- Structură --------------------------------------------------------------------------------


def test_catalog_validates_for_pydantic_and_json_schema() -> None:
    Catalog.model_validate_json(DEFAULT_CATALOG_PATH.read_text(encoding="utf-8"))
    Draft202012Validator(document_schema(build_schema(), "Catalog")).validate(RAW)


def test_expected_minimal_content() -> None:
    ids = [site.id for site in CATALOG.sites]
    assert len(ids) == len(set(ids)) == 10
    assert all(re.fullmatch(r"[a-z0-9][a-z0-9_.-]{0,63}", i) for i in ids)
    assert set(APOLLO_IDS) <= set(ids)
    assert "blueghost1_lander" in ids  # CLPS
    assert {"im1_odysseus", "im2_athena"}.isdisjoint(ids)
    assert {"chandrayaan3_vikram", "change4_lander"} <= set(ids)  # internațional
    assert {s.country for s in CATALOG.sites} >= {"United States", "India", "China"}


def test_coordinates_and_frames_are_in_domain() -> None:
    for site in CATALOG.sites:
        assert -90.0 <= site.latitude_deg <= 90.0
        assert -180.0 <= site.longitude_deg < 180.0
        assert site.frame_id in SUPPORTED_FRAMES
        assert math.isfinite(site.latitude_deg) and math.isfinite(site.longitude_deg)


def test_reader_returns_the_validated_catalog() -> None:
    assert load_catalog(DEFAULT_CATALOG_PATH) == CATALOG
    assert get_site(CATALOG, "apollo11_lm").mission == "Apollo 11"
    with pytest.raises(KeyError):
        get_site(CATALOG, "inexistent")
    assert all(isinstance(site, Site) for site in CATALOG.sites)


# --- Poziție efectivă, țintă planificată, punct reprezentativ ---------------------------------


def test_planned_target_and_actual_position_are_distinct_linked_entries() -> None:
    actual = get_site(CATALOG, "chandrayaan3_vikram")
    planned = get_site(CATALOG, "chandrayaan3_planned_target")
    assert (actual.position_kind, planned.position_kind) == ("actual", "planned_target")
    assert (actual.status, planned.status) == ("landed", "planned")
    assert actual.mission_status == planned.mission_status == "landed"
    assert planned_target_of(CATALOG, actual) == planned
    assert planned_target_of(CATALOG, planned) == actual
    separation = _distance_m(
        actual.latitude_deg, actual.longitude_deg, planned.latitude_deg, planned.longitude_deg
    )
    assert 100.0 < separation < 2000.0  # ținta și poziția efectivă nu sunt același punct


def test_named_only_targets_are_not_invented_as_coordinates() -> None:
    for site_id in ("blueghost1_lander",):
        site = get_site(CATALOG, site_id)
        assert site.planned_target_note is not None
        assert "coordonate numerice" in site.planned_target_note
        assert site.related_site_id is None  # nu există intrare numerică pentru țintă
    planned = [s.id for s in CATALOG.sites if s.position_kind == "planned_target"]
    assert planned == ["chandrayaan3_planned_target"]


def test_no_region_or_representative_point_is_presented_as_a_landing() -> None:
    for site in CATALOG.sites:
        assert site.geometry_type == "point"
        assert site.position_kind != "representative_point"
        assert site.region is None


# --- Zero, necunoscut ------------------------------------------------------------------------


def test_unknown_is_null_not_zero() -> None:
    for site in CATALOG.sites:
        assert site.horizontal_uncertainty_m != 0.0
        for source in site.position_sources:
            assert source.published_uncertainty_m != 0.0
    planned = get_site(CATALOG, "chandrayaan3_planned_target")
    assert planned.horizontal_uncertainty_m is None
    assert planned.elevation_m is None and planned.elevation_reference is None
    ce4 = get_site(CATALOG, "change4_lander")
    assert ce4.agency is None and ce4.operator is None
    for site in CATALOG.sites:
        assert site.landing_date_utc is None
        assert site.terrain_available is False  # relieful real nu este verificat înainte de E05


# --- Proveniență -----------------------------------------------------------------------------


def test_every_position_has_an_opened_original_with_locator_and_quote() -> None:
    for site in CATALOG.sites:
        primary = site.primary_source()
        assert primary.access == "opened_original"
        assert primary.coordinates is not None
        assert primary.locator and primary.quote and primary.institution and primary.title
        assert primary.accessed_at == site.accessed_at
        assert primary.url == site.source_url
        assert site.position_verification == "verified_at_original"
        assert site.adoption_note


def test_inaccessible_sources_carry_no_coordinates_or_quotes() -> None:
    inaccessible = [
        (site.id, s)
        for site in CATALOG.sites
        for s in site.position_sources
        if s.access != "opened_original"
    ]
    assert [(i, s.url) for i, s in inaccessible] == [
        ("apollo11_lm", "https://doi.org/10.1016/j.icarus.2016.05.011")
    ]
    assert all(s.coordinates is None and s.quote is None for _, s in inaccessible)


def test_pds_product_sources_are_hashed_and_dated() -> None:
    pds_sources = [
        s
        for site in CATALOG.sites
        for s in site.position_sources
        if "OBJECT_ID=" in (s.identifier or "")
    ]
    assert len(pds_sources) == 9  # toate pozițiile efective; ținta ISRO are altă sursă
    assert {s.file_sha256 for s in pds_sources} == {PDS_ZIP_SHA256}
    assert all("2026-08-14" in (s.version_or_update or "") for s in pds_sources)


def test_no_source_claims_a_frame_realization_it_does_not_state() -> None:
    for site in CATALOG.sites:
        for source in site.position_sources:
            assert source.frame_realization_stated is False
        assert "IPOTEZĂ" in site.adoption_note  # adoptarea cadrului MOON_ME_DE440_ME421
        assert "D-10" in site.adoption_note


def test_conventions_declared_by_the_sources_are_recorded() -> None:
    a11 = get_site(CATALOG, "apollo11_lm")
    primary = a11.primary_source()
    assert primary.declared_frame is not None and "GCS_Moon_2000" in primary.declared_frame
    assert primary.coordinates is not None
    assert "1 737 400" in primary.coordinates.frame_description
    table = next(s for s in a11.position_sources if s.used_for == "corroboration" and s.coordinates)
    assert table.declared_frame == "mean Earth/polar axis (ME) system"
    assert table.published == "Published by Mark Robinson on 25 November 2016"


# --- Normalizări și coroborări ---------------------------------------------------------------


def test_adopted_values_are_the_normalized_original() -> None:
    for site in CATALOG.sites:
        assert site.original_coordinates is not None
        assert site.latitude_deg == pytest.approx(site.original_coordinates.latitude_deg, abs=1e-9)
        assert site.longitude_deg == pytest.approx(
            normalize_longitude_deg(site.original_coordinates.longitude_deg), abs=1e-9
        )
    # Domeniul 0-360 din tabelul LROC 2016 se normalizează la valoarea din produsul actual.
    for site_id, lon360 in (("apollo12_lm", 336.5781), ("apollo14_lm", 342.52806)):
        site = get_site(CATALOG, site_id)
        table = next(
            s
            for s in site.position_sources
            if s.coordinates and s.coordinates.longitude_deg > 180.0
        )
        assert table.coordinates is not None
        assert table.coordinates.longitude_deg == lon360
        assert normalize_longitude_deg(lon360) == pytest.approx(site.longitude_deg, abs=1e-9)


def test_corroborating_sources_agree_within_the_documented_bound() -> None:
    worst: dict[str, float] = {}
    for site in CATALOG.sites:
        for source in site.position_sources:
            if source.used_for != "corroboration" or source.coordinates is None:
                continue
            lon = normalize_longitude_deg(source.coordinates.longitude_deg)
            distance = _distance_m(
                site.latitude_deg, site.longitude_deg, source.coordinates.latitude_deg, lon
            )
            worst[site.id] = max(worst.get(site.id, 0.0), distance)
            assert distance <= CORROBORATION_BOUND_M, (site.id, source.url, distance)
    assert worst["apollo11_lm"] < 0.01  # aceeași valoare în produs și în tabelul din 2016


def test_differences_between_sources_are_kept_not_averaged() -> None:
    site = get_site(CATALOG, "chandrayaan3_vikram")
    values = {s.coordinates.longitude_deg for s in site.position_sources if s.coordinates}
    assert values == {32.3187, 32.32}  # ambele păstrate; poziția adoptată este a produsului
    assert site.longitude_deg == 32.3187
    ce4 = get_site(CATALOG, "change4_lander")
    assert {s.published_uncertainty_m for s in ce4.position_sources} == {10.0, 13.0}
    assert ce4.horizontal_uncertainty_m == 10.0


def test_elevation_is_traceable_to_the_published_radius() -> None:
    for site in CATALOG.sites:
        if site.elevation_m is not None:
            assert site.elevation_reference and "RADIUS" in site.elevation_reference
    assert get_site(CATALOG, "apollo11_lm").elevation_m == pytest.approx(-1926.289, abs=1e-9)


# --- Apollo 11 și E03 ------------------------------------------------------------------------


def test_apollo11_position_matches_the_e03_reference_cases() -> None:
    a11 = get_site(CATALOG, "apollo11_lm")
    cases = {c.case_id: c for c in load_cases()}
    for case_id in ("a11_dem", "a11_catalog"):
        site = cases[case_id].site
        assert site.latitude_deg == a11.latitude_deg == 0.67416
        assert site.longitude_deg == a11.longitude_deg == 23.47314
    # Înălțimile de suprafață ale cazurilor E03 diferă de altitudinea din catalog cu < 1 m;
    # cazurile E03 nu se modifică (sunt intrări de test documentate, nu valori din catalog).
    assert a11.elevation_m is not None
    assert abs(cases["a11_catalog"].site.surface_height_m - a11.elevation_m) < 1.0
    assert abs(cases["a11_dem"].site.surface_height_m - a11.elevation_m) < 1.0


# --- Selecția demonstrativă (D-07) -----------------------------------------------------------


def test_demo_selection_is_unconfirmed_and_candidates_are_documented() -> None:
    selection = CATALOG.demo_site_selection
    assert selection.decision_id == "D-07"
    assert selection.status == "unconfirmed"
    assert selection.confirmed_site_ids == []
    assert selection.candidates == []
    assert "Shackleton Connecting Ridge" in " ".join(e.label for e in selection.excluded)
    assert "studiu termic" in " ".join(e.reason for e in selection.excluded)


# --- Respingerea datelor invalide ------------------------------------------------------------


def _rejects(change: Any) -> None:
    with pytest.raises(ValidationError):
        Catalog.model_validate_json(json.dumps(_mutated(change)))


def test_missing_provenance_is_rejected() -> None:
    _rejects(lambda d: _site(d, "apollo11_lm").update(position_sources=[]))
    _rejects(lambda d: _site(d, "apollo11_lm").pop("adoption_note"))
    _rejects(lambda d: _site(d, "apollo11_lm").update(adoption_note=""))


def test_adopted_coordinates_must_equal_the_normalized_original() -> None:
    _rejects(lambda d: _site(d, "apollo12_lm").update(longitude_deg=-23.4))
    _rejects(lambda d: _site(d, "apollo12_lm").update(latitude_deg=-3.0))


def test_verified_position_requires_an_opened_original() -> None:
    def make_inaccessible(d: dict[str, Any]) -> None:
        source = _site(d, "apollo11_lm")["position_sources"][0]
        source.update(access="not_accessible", coordinates=None, quote=None)

    _rejects(make_inaccessible)


def test_uncertainty_must_be_the_published_one() -> None:
    _rejects(lambda d: _site(d, "apollo11_lm").update(horizontal_uncertainty_m=15.0))


def test_planned_target_rules() -> None:
    _rejects(lambda d: _site(d, "chandrayaan3_planned_target").update(status="landed"))
    _rejects(lambda d: _site(d, "chandrayaan3_vikram").update(status="planned"))
    _rejects(lambda d: _site(d, "chandrayaan3_vikram").update(related_site_id=None))
    _rejects(lambda d: _site(d, "chandrayaan3_vikram").update(related_site_id="inexistent"))
    _rejects(lambda d: _site(d, "chandrayaan3_vikram").update(related_site_id="apollo11_lm"))


def test_duplicate_ids_and_unknown_candidates_are_rejected() -> None:
    _rejects(lambda d: _site(d, "apollo12_lm").update(id="apollo11_lm"))
    _rejects(
        lambda d: d["demo_site_selection"]["candidates"].append(
            dict(site_id="inexistent", advantages=["test"], limits=["test"])
        )
    )
    _rejects(
        lambda d: d["demo_site_selection"]["candidates"].append(
            dict(site_id="chandrayaan3_planned_target", advantages=["test"], limits=["test"])
        )
    )


def test_demo_selection_cannot_be_confirmed_without_a_real_choice() -> None:
    selection = "demo_site_selection"
    _rejects(lambda d: d[selection].update(confirmed_site_ids=["im2_athena"]))
    _rejects(lambda d: d[selection].update(status="confirmed", confirmed_site_ids=["im2_athena"]))
    _rejects(
        lambda d: d[selection].update(
            status="confirmed", confirmed_site_ids=["im2_athena", "apollo11_lm"]
        )
    )


def test_unframed_values_and_unknown_fields_are_rejected() -> None:
    _rejects(lambda d: _site(d, "apollo11_lm").update(frame_id="MOON_ME"))
    _rejects(lambda d: _site(d, "apollo11_lm").update(frame_id="IAU_MOON"))
    _rejects(lambda d: _site(d, "apollo11_lm").update(latitude_deg=91.0))
    _rejects(lambda d: _site(d, "apollo11_lm").update(longitude_deg=360.0))
    _rejects(lambda d: _site(d, "apollo11_lm").update(elevation_reference=None))
    _rejects(lambda d: _site(d, "apollo11_lm").update(invented_field=1))


# --- Dovada reverificării la surse (fișier arhivat) -----------------------------------------


def test_source_verification_report_covers_the_catalog_and_has_no_failures() -> None:
    report = read_json(REPO_ROOT / "data" / "catalog" / "source_verification.json")
    # Archived verification predates the user-requested removal; no new network claim.
    assert report["catalog_version"] == "e04-2026-11-14"
    assert CATALOG.catalog_version == "e04-2026-11-14-without-im"
    assert report["summary"]["failures"] == 0
    assert report["summary"]["inaccessible"] == 0
    assert {r["site_id"] for r in report["results"]} == (
        {s.id for s in CATALOG.sites} | {"im1_odysseus", "im2_athena"}
    )
    pds = [x for r in report["results"] for x in r["sources"] if x["kind"] == "pds_product"]
    assert len(pds) == 11 and all(not x["checks"] for x in pds)
    assert report["pds_zip_sha256"] == PDS_ZIP_SHA256
