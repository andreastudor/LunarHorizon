"""Căi comune pentru teste (schema, vectorii și fixture-urile din afara backendului)."""

import json
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
VECTORS_PATH = REPO_ROOT / "tests" / "vectors" / "conventions.json"
SCHEMA_PATH = REPO_ROOT / "data" / "schemas" / "lunarhorizon.schema.json"
CONTRACT_FIXTURES = REPO_ROOT / "tests" / "fixtures" / "contracts"


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))
