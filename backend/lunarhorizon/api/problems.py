"""Erorile în format `application/problem+json` (RFC 9457; docs/API.md §6)."""

from collections.abc import Sequence
from typing import Any

from lunarhorizon.contracts.service import FieldError, Problem
from lunarhorizon.core.errors import HTTP_STATUS, ErrorCode, LunarHorizonError

PROBLEM_MEDIA_TYPE = "application/problem+json"

TITLES: dict[ErrorCode, str] = {
    ErrorCode.VALIDATION_ERROR: "Cerere invalidă",
    ErrorCode.TOO_MANY_SITES: "Prea multe situri",
    ErrorCode.INTERVAL_TOO_LONG: "Interval prea lung",
    ErrorCode.UNSUPPORTED_FRAME: "Cadru neacceptat",
    ErrorCode.OUT_OF_EPHEMERIS_COVERAGE: "În afara acoperirii efemeridelor",
    ErrorCode.OUT_OF_DEM_COVERAGE: "Teren DEM indisponibil",
    ErrorCode.SIMULATION_NOT_FOUND: "Simulare necunoscută",
    ErrorCode.KERNEL_MISSING: "Kerneluri indisponibile",
    ErrorCode.TERRAIN_DATA_MISSING: "Date de teren lipsă",
    ErrorCode.PRECOMPUTED_NOT_AVAILABLE: "Scenariu precalculat indisponibil",
    ErrorCode.INTERNAL_ERROR: "Eroare internă",
}


def problem_type(code: ErrorCode) -> str:
    return f"urn:lunarhorizon:problem:{code.value.lower().replace('_', '-')}"


def make_problem(
    code: ErrorCode,
    detail: str,
    *,
    status: int | None = None,
    context: dict[str, str] | None = None,
    field_errors: list[FieldError] | None = None,
) -> Problem:
    extra = context or {}
    return Problem(
        type=problem_type(code),
        title=TITLES[code],
        status=status if status is not None else HTTP_STATUS[code],
        detail=detail,
        code=code,
        field_errors=field_errors,
        coverage_start_utc=extra.get("coverage_start_utc"),
        coverage_end_utc=extra.get("coverage_end_utc"),
    )


def from_error(error: LunarHorizonError, *, status: int | None = None) -> Problem:
    return make_problem(error.code, error.detail, status=status, context=error.context)


def internal_problem() -> Problem:
    """Eroare generică: fără detalii interne în răspuns (jurnalul serverului păstrează cauza)."""
    return make_problem(ErrorCode.INTERNAL_ERROR, "Eroare internă; vezi jurnalul serverului.")


def from_validation_errors(errors: Sequence[dict[str, Any]]) -> Problem:
    """Problema 422 construită din erorile Pydantic ale cererii."""
    field_errors = [
        FieldError(
            loc=[part if isinstance(part, int) else str(part) for part in error["loc"]],
            message=str(error.get("msg") or "valoare invalidă"),
        )
        for error in errors
    ]
    code = ErrorCode.VALIDATION_ERROR
    for error in errors:
        loc = tuple(error["loc"])
        if error.get("type") == "too_long" and loc[-1:] == ("sites",):
            code = ErrorCode.TOO_MANY_SITES
            break
        if loc[-1:] == ("frame_id",) and error.get("type") == "literal_error":
            code = ErrorCode.UNSUPPORTED_FRAME
            break
    summary = "; ".join(
        f"{'.'.join(str(part) for part in error['loc'])}: {error.get('msg')}"
        for error in errors[:5]
    )
    return make_problem(code, summary or "cerere invalidă", field_errors=field_errors)
