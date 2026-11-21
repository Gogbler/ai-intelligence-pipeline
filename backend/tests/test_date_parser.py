"""Unit tests for Date Normalization and 24-Hour Freshness Checking."""

from datetime import datetime, timedelta, timezone
from app.utils.date_parser import (
    parse_relative_date,
    normalize_to_iso,
    is_within_24_hours,
)


def test_parse_relative_date():
    ref = datetime(2026, 11, 21, 12, 0, 0, tzinfo=timezone.utc)

    # 2 hours ago
    dt = parse_relative_date("2 hours ago", base_time=ref)
    assert dt == datetime(2026, 11, 21, 10, 0, 0, tzinfo=timezone.utc)

    # 45 minutes ago
    dt = parse_relative_date("45 mins ago", base_time=ref)
    assert dt == datetime(2026, 11, 21, 11, 15, 0, tzinfo=timezone.utc)

    # 1 day ago
    dt = parse_relative_date("1 day ago", base_time=ref)
    assert dt == datetime(2026, 11, 20, 12, 0, 0, tzinfo=timezone.utc)

    # Yesterday
    dt = parse_relative_date("yesterday", base_time=ref)
    assert dt == datetime(2026, 11, 20, 12, 0, 0, tzinfo=timezone.utc)

    # Just now
    dt = parse_relative_date("just now", base_time=ref)
    assert dt == ref


def test_normalize_to_iso():
    # RFC 2822 RSS format
    rss_date = "Sat, 21 Nov 2026 10:00:00 +0000"
    iso = normalize_to_iso(rss_date)
    assert iso == "2026-11-21T10:00:00+00:00"

    # Unix timestamp
    ts = 1732183200
    iso_ts = normalize_to_iso(ts)
    assert "2024" in iso_ts or "2025" in iso_ts or "2026" in iso_ts

    # Relative date normalization
    iso_rel = normalize_to_iso("3 hours ago")
    assert iso_rel is not None
    assert "T" in iso_rel


def test_is_within_24_hours():
    now = datetime.now(timezone.utc)

    # 2 hours ago -> Fresh
    fresh_iso = (now - timedelta(hours=2)).isoformat()
    assert is_within_24_hours(fresh_iso, reference_time=now) is True

    # 23 hours ago -> Fresh
    borderline_fresh = (now - timedelta(hours=23)).isoformat()
    assert is_within_24_hours(borderline_fresh, reference_time=now) is True

    # 26 hours ago -> Not fresh
    stale_iso = (now - timedelta(hours=26)).isoformat()
    assert is_within_24_hours(stale_iso, reference_time=now) is False

    # 5 days ago -> Not fresh
    old_iso = (now - timedelta(days=5)).isoformat()
    assert is_within_24_hours(old_iso, reference_time=now) is False

    # Invalid string -> False
    assert is_within_24_hours("not_a_date") is False
