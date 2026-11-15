"""Contractele de date: schema la zi, fixture-uri, mutații, zero / necunoscut / necalculat."""

import copy
import json
import re
from collections.abc import Callable, Iterator
from typing import Any

import pytest
from jsonschema import Draft202012Validator
from pydantic import ValidationError

from lunarhorizon.contracts.export import DOCUMENT_MODELS, build_schema, document_schema, dumps
from lunarhorizon.contracts.simulation import SimulationRequest, SimulationResult
from lunarhorizon.core.conventions import UNIT_SUFFIXES
from lunarhorizon.core.errors import HTTP_STATUS, ErrorCode
from lunarhorizon.core.reference_vectors import build_reference_vectors
from tests.support import CONTRACT_FIXTURES, SCHEMA_PATH, VECTORS_PATH, read_json

Document = dict[str, Any]
FIXTURES: dict[str, Document] = {
    name: doc
    for name, doc in read_json(CONTRACT_FIXTURES / "synthetic_valid_documents.json").items()
    if not name.startswith("_")
}
SCHEMA = read_json(SCHEMA_PATH)

# Câmpuri numerice fără sufix de unitate, permise explicit.
UNITLESS_NUMERIC_FIELDS = {
    "status": "statusul HTTP din application/problem+json (RFC 9457)",
    "level": "indexul nivelului de detaliu",
    "coordinates": "pozițiile GeoJSON [longitudine, latitudine] în grade",
    "nodata_value": "valoarea-santinelă brută din raster",
    "loc": "calea câmpului invalid (nume și indici), nu o mărime",
}


def _normalized(text: str) -> str:
    return text.replace("\r\n", "\n")


def test_schema_file_is_up_to_date() -> None:
    assert _normalized(SCHEMA_PATH.read_text(encoding="utf-8")) == dumps(build_schema())


def test_reference_vectors_are_up_to_date() -> None:
    expected = dumps(build_reference_vectors())
    assert _normalized(VECTORS_PATH.read_text(encoding="utf-8")) == expected


def test_every_document_type_has_a_fixture() -> None:
    assert set(FIXTURES) == set(DOCUMENT_MODELS)


@pytest.mark.parametrize("name", sorted(DOCUMENT_MODELS))
def test_fixture_valid_for_pydantic_and_json_schema(name: str) -> None:
    document = FIXTURES[name]
    DOCUMENT_MODELS[name].model_validate_json(json.dumps(document))
    Draft202012Validator(document_schema(SCHEMA, name)).validate(document)


def test_validation_normalizes_time_and_longitude() -> None:
    request = SimulationRequest.model_validate_json(json.dumps(FIXTURES["SimulationRequest"]))
    assert request.start_utc == "2030-01-01T00:00:00Z"
    custom = request.sites[1]
    assert custom.custom.longitude_deg == -0.5  # type: ignore[union-attr]


def _mutate(name: str, change: Callable[[Document], None]) -> Document:
    document = copy.deepcopy(FIXTURES[name])
    change(document)
    return document


def _set(path: str, value: Any) -> Callable[[Document], None]:
    def change(document: Document) -> None:
        *parents, last = path.split(".")
        target: Any = document
        for key in parents:
            target = target[int(key)] if key.isdigit() else target[key]
        if last.isdigit():
            target[int(last)] = value
        else:
            target[last] = value

    return change


def _delete(path: str) -> Callable[[Document], None]:
    def change(document: Document) -> None:
        *parents, last = path.split(".")
        target: Any = document
        for key in parents:
            target = target[int(key)] if key.isdigit() else target[key]
        del target[last]

    return change


# (document, mutație, respinsă și de JSON Schema?)  — regulile între câmpuri sunt numai în Pydantic.
INVALID_CASES: list[tuple[str, str, Callable[[Document], None], bool]] = [
    ("SimulationRequest", "timp fără zonă", _set("start_utc", "2030-01-01T00:00:00"), True),
    ("SimulationRequest", "secundă intercalară", _set("end_utc", "2016-12-31T23:59:60Z"), False),
    ("SimulationRequest", "alias de cadru", _set("frame_id", "MOON_ME"), True),
    ("SimulationRequest", "IAU_MOON", _set("frame_id", "IAU_MOON"), True),
    ("SimulationRequest", "cinci situri", _set("sites", [{"site_id": "a"}] * 5), True),
    (
        "SimulationRequest",
        "sfârșit înainte de început",
        _set("end_utc", "2029-12-31T00:00:00Z"),
        False,
    ),
    ("SimulationRequest", "longitudine 360", _set("sites.1.custom.longitude_deg", 360.0), True),
    ("SimulationRequest", "latitudine 91", _set("sites.1.custom.latitude_deg", 91.0), True),
    ("SimulationRequest", "înălțime negativă", _set("observer_height_m", -1.0), True),
    ("SimulationRequest", "câmp necunoscut", _set("elevation", 1.0), True),
    ("SimulationRequest", "număr ca text", _set("observer_height_m", "2"), True),
    ("SimulationRequest", "panou nerezervat", _set("panel", {"tilt_deg": 10.0}), True),
    ("Catalog", "id duplicat", _set("sites.2.id", "synthetic_point_a"), False),
    ("Catalog", "longitudine nenormalizată", _set("sites.0.longitude_deg", 190.0), True),
    ("Catalog", "altitudine fără referință", _set("sites.0.elevation_m", 12.0), False),
    ("Catalog", "regiune fără punct reprezentativ", _set("sites.2.position_kind", "actual"), False),
    ("Catalog", "poligon deschis", _set("sites.2.region.coordinates.0.4", [-120.0, -88.2]), False),
    ("Catalog", "URL lipsă", _delete("sites.0.source_url"), True),
    (
        "TerrainManifest",
        "exagerare implicită 2",
        _set("vertical.exaggeration_default_factor", 2),
        True,
    ),
    ("TerrainManifest", "cale absolută", _set("lods.0.heights_path", "/etc/lod0.f32"), True),
    ("TerrainManifest", "cale cu ..", _set("lods.0.heights_path", "../lod0.f32"), True),
    ("SimulationStatus", "eșec fără eroare", _set("error", None), False),
    ("Health", "degradat fără motiv", _set("issues", []), False),
    ("Problem", "cod necunoscut", _set("code", "SOMETHING_ELSE"), True),
    ("SimulationResult", "seria cu lungimi diferite", _set("series.0.sun.visible", [True]), False),
    ("SimulationResult", "azimut 360", _set("series.0.sun.azimuth_deg.0", 360.0), True),
    (
        "SimulationResult",
        "cadru diferit în proveniență",
        _set("provenance.frame_id", "MOON_ME_DE421"),
        False,
    ),
    ("SimulationResult", "orizont idealizat nenul", _set("horizon.0.elevation_deg.1", 0.5), False),
    (
        "SimulationResult",
        "pas azimutal care nu divide 360",
        _set("horizon.0.azimuth_step_deg", 7.0),
        False,
    ),
]


@pytest.mark.parametrize(
    ("name", "label", "change", "schema_rejects"),
    INVALID_CASES,
    ids=[f"{case[0]}:{case[1]}" for case in INVALID_CASES],
)
def test_invalid_documents_are_rejected(
    name: str, label: str, change: Callable[[Document], None], schema_rejects: bool
) -> None:
    document = _mutate(name, change)
    with pytest.raises(ValidationError):
        DOCUMENT_MODELS[name].model_validate_json(json.dumps(document))
    schema_errors = list(Draft202012Validator(document_schema(SCHEMA, name)).iter_errors(document))
    assert bool(schema_errors) == schema_rejects, label


# --- Zero, necunoscut, necalculat -----------------------------------------------------------------


def _result(document: Document) -> SimulationResult:
    return SimulationResult.model_validate_json(json.dumps(document))


def test_zero_is_a_value_and_needs_no_reason() -> None:
    result = _result(FIXTURES["SimulationResult"])
    summary = result.summary[0]
    assert summary.earth_visible_duration_s == 0.0
    assert not [i for i in result.quality.issues if i.field == "summary.earth_visible_duration_s"]


def test_unknown_value_requires_a_reason() -> None:
    def drop_issue(document: Document) -> None:
        issues = document["quality"]["issues"]
        document["quality"]["issues"] = [
            i for i in issues if i["field"] != "summary.sun_visible_fraction"
        ]

    with pytest.raises(ValidationError, match=re.escape("summary.sun_visible_fraction")):
        _result(_mutate("SimulationResult", drop_issue))


def test_unknown_series_sample_requires_a_reason() -> None:
    def unknown(document: Document) -> None:
        _set("series.0.earth.visible.1", None)(document)
        _set("series.0.earth.state.1", "undetermined")(document)
        _set("series.0.earth.state_reason.1", "no_data")(document)

    document = _mutate("SimulationResult", unknown)
    with pytest.raises(ValidationError, match=re.escape("series.earth.visible")):
        _result(document)


def test_undetermined_state_must_match_visible() -> None:
    # „Necunoscut” fără starea `undetermined` (sau invers) este respins: nu se ascunde un null.
    document = _mutate("SimulationResult", _set("series.0.earth.visible.1", None))
    with pytest.raises(ValidationError, match="nu corespund"):
        _result(document)


def test_unknown_is_not_zero() -> None:
    # Înlocuirea lui null cu 0 schimbă sensul: rezultatul rămâne valid, dar nu mai e „necunoscut”.
    document = _mutate("SimulationResult", _set("summary.1.sun_visible_fraction", 0.0))
    assert _result(document).summary[1].sun_visible_fraction == 0.0
    assert _result(FIXTURES["SimulationResult"]).summary[1].sun_visible_fraction is None


def test_not_computed_group_must_be_declared() -> None:
    result = _result(FIXTURES["SimulationResult"])
    assert [(nc.group, nc.site_ref) for nc in result.quality.not_computed] == [("events", "s2")]
    undeclared = _mutate("SimulationResult", _set("quality.not_computed", []))
    with pytest.raises(ValidationError, match="events/s2"):
        _result(undeclared)


def test_group_cannot_be_both_present_and_not_computed() -> None:
    def add_events_for_s2(document: Document) -> None:
        first = copy.deepcopy(document["events"][0])
        first["site_ref"] = "s2"
        document["events"].append(first)

    with pytest.raises(ValidationError, match="events/s2"):
        _result(_mutate("SimulationResult", add_events_for_s2))


# --- Convenții impuse asupra schemei --------------------------------------------------------------


def _numeric(prop: dict[str, Any]) -> bool:
    variants = prop.get("anyOf", [prop])
    for variant in variants:
        if variant.get("type") in ("number", "integer"):
            return True
        if variant.get("type") == "array" and _numeric(variant.get("items", {})):
            return True
    return False


def _properties() -> Iterator[tuple[str, str, dict[str, Any]]]:
    for model, definition in SCHEMA["$defs"].items():
        for field, prop in definition.get("properties", {}).items():
            yield model, field, prop


def test_numeric_fields_carry_a_unit_suffix() -> None:
    offenders = [
        f"{model}.{field}"
        for model, field, prop in _properties()
        if _numeric(prop)
        and not field.endswith(UNIT_SUFFIXES)
        and field not in UNITLESS_NUMERIC_FIELDS
    ]
    assert not offenders, f"câmpuri numerice fără sufix de unitate: {offenders}"


def test_error_codes_are_complete() -> None:
    assert set(HTTP_STATUS) == set(ErrorCode)
    assert SCHEMA["$defs"]["ErrorCode"]["enum"] == [code.value for code in ErrorCode]
