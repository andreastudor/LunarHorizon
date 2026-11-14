"""Indexul scenariilor precalculate pentru modul offline (docs/API.md §5)."""

from pydantic import Field, model_validator

from lunarhorizon.contracts.common import (
    Contract,
    Identifier,
    NonEmptyText,
    RelativePath,
    SchemaVersion,
    Sha256,
)
from lunarhorizon.contracts.simulation import SimulationRequest


class Scenario(Contract):
    scenario_id: Identifier
    title_ro: NonEmptyText
    title_en: NonEmptyText
    site_ids: list[Identifier] = Field(min_length=1, max_length=4)
    # Cererea exactă pentru care rezultatul a fost precalculat; sursa statică o potrivește exact.
    request: SimulationRequest
    result_path: RelativePath
    terrain_manifest_paths: list[RelativePath]
    result_sha256: Sha256


class ScenarioIndex(Contract):
    schema_version: SchemaVersion
    scenarios: list[Scenario]

    @model_validator(mode="after")
    def _unique_ids(self) -> "ScenarioIndex":
        ids = [s.scenario_id for s in self.scenarios]
        if len(ids) != len(set(ids)):
            raise ValueError("scenario_id trebuie să fie unic")
        return self
