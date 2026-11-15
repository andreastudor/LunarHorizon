"""Exportul schemei JSON comune (data/schemas/lunarhorizon.schema.json).

Un singur fișier, cu toate definițiile în `$defs` și documentele de nivel superior în `anyOf`.
Din el se generează tipurile TypeScript (frontend/scripts/generate-contract-types.mjs).
JSON Schema descrie structura; regulile dintre câmpuri (de exemplu „null cere un motiv”) sunt
impuse de validatorii Pydantic, deci de backend, care produce rezultatele.
"""

import json
from typing import Any, Final

from pydantic import BaseModel
from pydantic.json_schema import models_json_schema

from lunarhorizon.contracts.catalog import Catalog
from lunarhorizon.contracts.manifests import (
    DemProductManifest,
    KernelManifest,
    TerrainManifest,
    TerrainSample,
)
from lunarhorizon.contracts.scenarios import ScenarioIndex
from lunarhorizon.contracts.service import Coverage, Health, Problem, TerrainStatusReport
from lunarhorizon.contracts.simulation import (
    SimulationAccepted,
    SimulationRequest,
    SimulationResult,
    SimulationStatus,
)
from lunarhorizon.core.conventions import SCHEMA_VERSION

JSON_SCHEMA_DIALECT: Final = "https://json-schema.org/draft/2020-12/schema"

DOCUMENT_MODELS: Final[dict[str, type[BaseModel]]] = {
    "Catalog": Catalog,
    "KernelManifest": KernelManifest,
    "DemProductManifest": DemProductManifest,
    "TerrainManifest": TerrainManifest,
    "TerrainSample": TerrainSample,
    "SimulationRequest": SimulationRequest,
    "SimulationAccepted": SimulationAccepted,
    "SimulationStatus": SimulationStatus,
    "SimulationResult": SimulationResult,
    "ScenarioIndex": ScenarioIndex,
    "Health": Health,
    "Coverage": Coverage,
    "TerrainStatusReport": TerrainStatusReport,
    "Problem": Problem,
}


def build_schema() -> dict[str, Any]:
    _, top = models_json_schema(
        [(model, "validation") for model in DOCUMENT_MODELS.values()],
        ref_template="#/$defs/{model}",
    )
    definitions = top["$defs"]
    missing = [name for name in DOCUMENT_MODELS if name not in definitions]
    if missing:
        raise RuntimeError(f"definiții lipsă în schemă: {missing}")
    return {
        "$schema": JSON_SCHEMA_DIALECT,
        "title": "LunarHorizonContracts",
        "description": (
            "Contractele de date LunarHorizon. Generat din backend/lunarhorizon/contracts; "
            "nu se editează manual (scripts/generate_contracts.py)."
        ),
        "x-schema-version": SCHEMA_VERSION,
        "anyOf": [{"$ref": f"#/$defs/{name}"} for name in DOCUMENT_MODELS],
        "$defs": dict(sorted(definitions.items())),
    }


def document_schema(root: dict[str, Any], name: str) -> dict[str, Any]:
    """Schema de validare pentru un singur tip de document, cu definițiile comune."""
    return {"$schema": JSON_SCHEMA_DIALECT, "$ref": f"#/$defs/{name}", "$defs": root["$defs"]}


def dumps(document: Any) -> str:
    return json.dumps(document, indent=2, ensure_ascii=False) + "\n"
