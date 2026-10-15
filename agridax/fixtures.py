from __future__ import annotations

import os
from datetime import datetime, timezone

from .time_contract import parse_timestamp


def fixture_clock(conn=None) -> datetime:
    """Explicit clock for generated fixtures. Never modify timestamps already in RAW."""
    if os.environ.get("AGRIDAX_FIXTURE_ANCHOR"):
        anchor = parse_timestamp(os.environ["AGRIDAX_FIXTURE_ANCHOR"],"AGRIDAX_FIXTURE_ANCHOR")
    else:
        anchor = datetime.now(timezone.utc)
    anchor = anchor.replace(microsecond=0)
    if anchor < datetime(2024,2,1,tzinfo=timezone.utc):
        raise ValueError("Fixture anchor must be after the fixed master creation dates (2024-02-01 UTC)")
    if conn and anchor > conn.execute("select clock_timestamp()").fetchone()[0]:
        raise ValueError("Fixture anchor cannot be in the future")
    return anchor


def ingestion_clock(conn) -> datetime:
    """New physical fixture deliveries receive database time after the ingestion lock."""
    return conn.execute("select clock_timestamp()").fetchone()[0]
