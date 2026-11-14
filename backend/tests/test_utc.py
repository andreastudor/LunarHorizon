"""Timp UTC (docs/SPEC_FIZICA.md §2)."""

from datetime import UTC, datetime, timedelta, timezone

import pytest

from lunarhorizon.core.utc import (
    IntervalError,
    UtcParseError,
    canonical_utc,
    format_utc,
    parse_utc,
    parse_utc_interval,
)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("2026-11-14T12:00:00Z", "2026-11-14T12:00:00Z"),
        ("2026-11-14T12:00:00.500Z", "2026-11-14T12:00:00.5Z"),
        ("2026-11-14T12:00:00.000Z", "2026-11-14T12:00:00Z"),
        ("2026-11-14T14:30:00+02:00", "2026-11-14T12:30:00Z"),
        ("2026-11-14T08:30:00-03:30", "2026-11-14T12:00:00Z"),
        ("2026-01-01T00:30:00+01:00", "2025-12-31T23:30:00Z"),
        ("2026-11-14T12:00:00-00:00", "2026-11-14T12:00:00Z"),
    ],
)
def test_canonical_form_is_utc_with_z(text: str, expected: str) -> None:
    assert canonical_utc(text) == expected


@pytest.mark.parametrize(
    ("text", "reason"),
    [
        ("2026-11-14T12:00:00", "missing_timezone"),
        ("2026-11-14T12:00:00.25", "missing_timezone"),
        ("2026-11-14", "invalid_format"),
        ("2026-11-14T12:00:00.1234Z", "invalid_format"),
        ("2026-02-30T00:00:00Z", "invalid_date"),
        ("2016-12-31T23:59:60Z", "leap_second_unsupported"),
        ("2026-11-14T12:00:00+24:00", "invalid_offset"),
        ("9999-12-31T23:30:00-01:00", "invalid_date"),
    ],
)
def test_rejections_carry_reason(text: str, reason: str) -> None:
    with pytest.raises(UtcParseError) as info:
        parse_utc(text)
    assert info.value.reason == reason


def test_parse_returns_aware_utc() -> None:
    moment = parse_utc("2026-11-14T14:30:00.25+02:00")
    assert moment.tzinfo is UTC
    assert moment == datetime(2026, 11, 14, 12, 30, 0, 250_000, tzinfo=UTC)


def test_format_rounds_to_millisecond_with_carry() -> None:
    moment = datetime(2026, 11, 14, 12, 0, 59, 999_600, tzinfo=UTC)
    assert format_utc(moment) == "2026-11-14T12:01:00Z"
    assert format_utc(moment.replace(microsecond=120_400)) == "2026-11-14T12:00:59.12Z"


def test_format_converts_offsets_and_rejects_naive() -> None:
    plus_two = timezone(timedelta(hours=2))
    assert format_utc(datetime(2026, 11, 14, 14, 0, tzinfo=plus_two)) == "2026-11-14T12:00:00Z"
    with pytest.raises(ValueError):
        format_utc(datetime(2026, 11, 14, 12, 0))


def test_interval_requires_end_after_start() -> None:
    start, end = parse_utc_interval("2026-11-14T00:00:00Z", "2026-11-14T00:00:00.001Z")
    assert end - start == timedelta(milliseconds=1)
    with pytest.raises(IntervalError):
        parse_utc_interval("2026-11-14T02:00:00+02:00", "2026-11-14T00:00:00Z")
