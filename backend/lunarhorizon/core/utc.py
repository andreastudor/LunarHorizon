"""Momente de timp UTC în ISO 8601 (docs/SPEC_FIZICA.md §2).

Format acceptat: `YYYY-MM-DDTHH:MM:SS[.fff](Z|±HH:MM)`; fracțiunile au cel mult 3 cifre
(milisecunde), precizia comună cu frontendul. Un offset explicit se convertește în UTC;
lipsa zonei este o eroare.
Forma canonică este în UTC, cu `Z`, fără zerouri finale în fracțiune.

Secunda intercalară `:60` este respinsă explicit: `datetime` nu o poate reprezenta. Conversia spre
timpul SPICE (ET) se face numai prin SPICE, la etapa E03.
"""

import re
from datetime import UTC, datetime, timedelta, timezone
from typing import Final, Literal

UTC_INPUT_PATTERN: Final = r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d{1,3})?(Z|[+-]\d{2}:\d{2})$"
_PARSE = re.compile(
    r"(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})(?:\.(\d{1,3}))?(Z|[+-]\d{2}:\d{2})?"
)

UtcErrorReason = Literal[
    "invalid_format",
    "missing_timezone",
    "invalid_offset",
    "invalid_date",
    "leap_second_unsupported",
]
IntervalErrorReason = Literal["end_not_after_start"]


class UtcParseError(ValueError):
    def __init__(self, reason: UtcErrorReason, text: str) -> None:
        super().__init__(f"{reason}: {text!r}")
        self.reason: UtcErrorReason = reason
        self.text = text


class IntervalError(ValueError):
    def __init__(self, reason: IntervalErrorReason, start_utc: str, end_utc: str) -> None:
        super().__init__(f"{reason}: {start_utc} -> {end_utc}")
        self.reason: IntervalErrorReason = reason


def parse_utc(text: str) -> datetime:
    """Întoarce un `datetime` conștient de zonă, în UTC, cu precizie de milisecundă."""
    match = _PARSE.fullmatch(text)
    if match is None:
        raise UtcParseError("invalid_format", text)
    year, month, day, hour, minute, second, fraction, zone = match.groups()
    if zone is None:
        raise UtcParseError("missing_timezone", text)
    if second == "60":
        raise UtcParseError("leap_second_unsupported", text)

    offset_min = 0
    if zone != "Z":
        offset_h, offset_m = int(zone[1:3]), int(zone[4:6])
        if offset_h > 23 or offset_m > 59:
            raise UtcParseError("invalid_offset", text)
        offset_min = (offset_h * 60 + offset_m) * (-1 if zone[0] == "-" else 1)

    millisecond = int((fraction or "0").ljust(3, "0"))
    try:
        local = datetime(
            int(year),
            int(month),
            int(day),
            int(hour),
            int(minute),
            int(second),
            millisecond * 1000,
            tzinfo=timezone(timedelta(minutes=offset_min)),
        )
        return local.astimezone(UTC)
    except (ValueError, OverflowError) as exc:
        raise UtcParseError("invalid_date", text) from exc


def format_utc(moment: datetime) -> str:
    """Forma canonică UTC; rotunjește la cea mai apropiată milisecundă."""
    if moment.tzinfo is None:
        raise ValueError("format_utc cere un datetime cu zonă")
    rounded = (moment + timedelta(microseconds=500)).astimezone(UTC)
    millisecond = rounded.microsecond // 1000
    base = (
        f"{rounded.year:04d}-{rounded.month:02d}-{rounded.day:02d}"
        f"T{rounded.hour:02d}:{rounded.minute:02d}:{rounded.second:02d}"
    )
    if millisecond == 0:
        return f"{base}Z"
    return f"{base}.{f'{millisecond:03d}'.rstrip('0')}Z"


def canonical_utc(text: str) -> str:
    return format_utc(parse_utc(text))


def parse_utc_interval(start_utc: str, end_utc: str) -> tuple[datetime, datetime]:
    start, end = parse_utc(start_utc), parse_utc(end_utc)
    if end <= start:
        raise IntervalError("end_not_after_start", start_utc, end_utc)
    return start, end
