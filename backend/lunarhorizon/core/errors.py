"""Codurile de eroare stabile ale aplicației (docs/API.md §6)."""

from collections.abc import Mapping
from enum import StrEnum
from typing import Final


class ErrorCode(StrEnum):
    VALIDATION_ERROR = "VALIDATION_ERROR"
    TOO_MANY_SITES = "TOO_MANY_SITES"
    INTERVAL_TOO_LONG = "INTERVAL_TOO_LONG"
    UNSUPPORTED_FRAME = "UNSUPPORTED_FRAME"
    OUT_OF_EPHEMERIS_COVERAGE = "OUT_OF_EPHEMERIS_COVERAGE"
    OUT_OF_DEM_COVERAGE = "OUT_OF_DEM_COVERAGE"
    SIMULATION_NOT_FOUND = "SIMULATION_NOT_FOUND"
    KERNEL_MISSING = "KERNEL_MISSING"
    TERRAIN_DATA_MISSING = "TERRAIN_DATA_MISSING"
    PRECOMPUTED_NOT_AVAILABLE = "PRECOMPUTED_NOT_AVAILABLE"
    INTERNAL_ERROR = "INTERNAL_ERROR"


# Statusul HTTP implicit. OUT_OF_DEM_COVERAGE folosește 404 la GET /api/terrain/manifest.
# PRECOMPUTED_NOT_AVAILABLE apare numai în sursa de date statică a frontendului.
HTTP_STATUS: Final[dict[ErrorCode, int | None]] = {
    ErrorCode.VALIDATION_ERROR: 422,
    ErrorCode.TOO_MANY_SITES: 422,
    ErrorCode.INTERVAL_TOO_LONG: 422,
    ErrorCode.UNSUPPORTED_FRAME: 422,
    ErrorCode.OUT_OF_EPHEMERIS_COVERAGE: 422,
    ErrorCode.OUT_OF_DEM_COVERAGE: 422,
    ErrorCode.SIMULATION_NOT_FOUND: 404,
    ErrorCode.KERNEL_MISSING: 503,
    ErrorCode.TERRAIN_DATA_MISSING: 503,
    ErrorCode.PRECOMPUTED_NOT_AVAILABLE: None,
    ErrorCode.INTERNAL_ERROR: 500,
}


class LunarHorizonError(Exception):
    """Eroare cu cod stabil. `context` poartă câmpuri suplimentare ale `Problem` (de exemplu
    `coverage_start_utc` și `coverage_end_utc` pentru OUT_OF_EPHEMERIS_COVERAGE)."""

    def __init__(
        self, code: ErrorCode, detail: str, context: Mapping[str, str] | None = None
    ) -> None:
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail
        self.context: dict[str, str] = dict(context or {})
