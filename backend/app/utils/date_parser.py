"""Date Normalization and 24-Hour Freshness Utility.

Handles:
- Relative dates ('2 hours ago', '45m ago', 'yesterday', 'just now')
- Standard ISO-8601 timestamps ('2026-11-21T14:30:00Z')
- RFC 2822 / RSS timestamps ('Sat, 21 Nov 2026 14:30:00 GMT')
- Epoch timestamps (seconds or milliseconds)
- Normalizes all output to UTC ISO-8601 string format
- Strict 24-hour freshness verification
"""

import re
from datetime import datetime, timedelta, timezone
from typing import Optional, Any
import dateutil.parser


def parse_relative_date(date_str: str, base_time: Optional[datetime] = None) -> Optional[datetime]:
    """Parse relative human dates like '2 hours ago', 'yesterday', '15 mins ago'."""
    if not date_str:
        return None

    cleaned = date_str.strip().lower()
    ref = base_time or datetime.now(timezone.utc)

    if cleaned in ("just now", "moments ago", "recently"):
        return ref

    if cleaned == "yesterday":
        return ref - timedelta(days=1)

    if cleaned == "today":
        return ref.replace(hour=0, minute=0, second=0, microsecond=0)

    # Match patterns like: "2 hours ago", "45 mins ago", "1 day ago", "3h ago"
    match = re.search(r"(\d+)\s*(s|sec|second|m|min|minute|h|hr|hour|d|day|w|week)s?\s*ago?", cleaned)
    if match:
        val = int(match.group(1))
        unit = match.group(2)
        if unit in ("s", "sec", "second"):
            return ref - timedelta(seconds=val)
        elif unit in ("m", "min", "minute"):
            return ref - timedelta(minutes=val)
        elif unit in ("h", "hr", "hour"):
            return ref - timedelta(hours=val)
        elif unit in ("d", "day"):
            return ref - timedelta(days=val)
        elif unit in ("w", "week"):
            return ref - timedelta(weeks=val)

    return None


def normalize_to_iso(date_input: Any, base_time: Optional[datetime] = None) -> Optional[str]:
    """Normalize any date representation to standard UTC ISO-8601 string format."""
    if not date_input:
        return None

    ref = base_time or datetime.now(timezone.utc)

    # Already a datetime object
    if isinstance(date_input, datetime):
        dt = date_input
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        else:
            dt = dt.astimezone(timezone.utc)
        return dt.isoformat()

    # Numeric timestamp (int or float)
    if isinstance(date_input, (int, float)):
        # Check if milliseconds vs seconds
        if date_input > 1e11:
            date_input = date_input / 1000.0
        dt = datetime.fromtimestamp(date_input, tz=timezone.utc)
        return dt.isoformat()

    date_str = str(date_input).strip()
    if not date_str:
        return None

    # Check relative date first
    rel_dt = parse_relative_date(date_str, ref)
    if rel_dt:
        return rel_dt.astimezone(timezone.utc).isoformat()

    # Try standard dateutil parser
    try:
        dt = dateutil.parser.parse(date_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        else:
            dt = dt.astimezone(timezone.utc)
        return dt.isoformat()
    except (ValueError, TypeError, OverflowError):
        pass

    return None


def is_within_24_hours(iso_date_str: str, reference_time: Optional[datetime] = None) -> bool:
    """Verify strictly if an ISO date string falls within the last 24 hours."""
    if not iso_date_str:
        return False

    try:
        dt = dateutil.parser.isoparse(iso_date_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        else:
            dt = dt.astimezone(timezone.utc)

        ref = reference_time or datetime.now(timezone.utc)
        cutoff = ref - timedelta(hours=24)
        # Must be between cutoff and ref + small future clock-skew buffer (1 hour)
        return cutoff <= dt <= (ref + timedelta(hours=1))
    except Exception:
        return False
