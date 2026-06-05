from datetime import UTC, datetime, timedelta

from sdlc.utils.time import format_iso, human_delta, now_utc, parse_timespec


def test_now_utc_has_utc_tz():
    n = now_utc()
    assert n.tzinfo is not None
    assert n.tzinfo == UTC


def test_format_iso_ends_with_z():
    dt = datetime(2024, 1, 15, 10, 30, 0, tzinfo=UTC)
    result = format_iso(dt)
    assert result.endswith("Z")
    assert result == "2024-01-15T10:30:00Z"


def test_parse_timespec_1d():
    result = parse_timespec("1d")
    expected = now_utc() - timedelta(days=1)
    diff = abs((result - expected).total_seconds())
    assert diff < 5


def test_parse_timespec_7d():
    result = parse_timespec("7d")
    expected = now_utc() - timedelta(days=7)
    diff = abs((result - expected).total_seconds())
    assert diff < 5


def test_human_delta_just_now():
    dt = now_utc() - timedelta(seconds=10)
    result = human_delta(dt)
    assert result == "just now"


def test_human_delta_ago():
    dt = now_utc() - timedelta(hours=3)
    result = human_delta(dt)
    assert "ago" in result
