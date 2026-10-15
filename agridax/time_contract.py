from __future__ import annotations

import re
from datetime import datetime, timezone

ISO_TIMESTAMP = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|[+-]\d{2}:\d{2})$"
)


def parse_timestamp(value: str, name: str = "timestamp") -> datetime:
    """Supported ISO-8601 subset: seconds, explicit offset, microsecond precision."""
    if not isinstance(value, str) or not ISO_TIMESTAMP.fullmatch(value):
        raise ValueError(f"{name} must be ISO-8601 with seconds and explicit Z or ±HH:MM offset")
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{name} is not a valid calendar timestamp") from exc
    if result.utcoffset() is None:
        raise ValueError(f"{name} must have a timezone")
    return result.astimezone(timezone.utc)


def backfill_range(start: str | None, end: str | None, full_refresh: bool = False):
    if (start is None) != (end is None):
        raise ValueError("Both backfill_start and backfill_end are required")
    if start is None:
        return None
    lower = parse_timestamp(start, "backfill_start")
    upper = parse_timestamp(end, "backfill_end")
    if lower >= upper:
        raise ValueError("backfill_start must be strictly earlier than backfill_end")
    if full_refresh:
        raise ValueError("Bounded backfill cannot be combined with --full-refresh")
    return lower, upper
