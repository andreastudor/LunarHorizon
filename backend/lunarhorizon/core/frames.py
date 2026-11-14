"""Validarea identificatorului de cadru (docs/SPEC_FIZICA.md §3.1, docs/API.md §1)."""

from lunarhorizon.core.conventions import SUPPORTED_FRAMES
from lunarhorizon.core.errors import ErrorCode, LunarHorizonError


def validate_frame_id(frame_id: str) -> str:
    """Acceptă numai numele explicite; `MOON_ME`, `MOON_PA` și `IAU_MOON` sunt respinse."""
    if frame_id not in SUPPORTED_FRAMES:
        raise LunarHorizonError(
            ErrorCode.UNSUPPORTED_FRAME,
            f"Cadrul {frame_id!r} nu este acceptat; cadre acceptate: {', '.join(SUPPORTED_FRAMES)}",
        )
    return frame_id
