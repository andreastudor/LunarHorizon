"""Fixture-uri pytest comune: toleranțele T-04 / T-05."""

import pytest

from lunarhorizon.core.reference_vectors import TOLERANCES


@pytest.fixture(scope="session")
def tolerances() -> dict[str, dict[str, float]]:
    return TOLERANCES
