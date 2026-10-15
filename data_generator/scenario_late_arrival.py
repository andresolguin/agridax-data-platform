from __future__ import annotations

from datetime import datetime, timedelta

import psycopg

from agridax.database import fixture_transaction
from agridax.fixtures import fixture_clock, ingestion_clock


SCENARIO_BATCH_ID = "LATE_ARRIVAL_01"
SOURCE_SYSTEM = "field_ops"
SOURCE_EVENT_ID = "OPS_1005"
FIELD_ID = "FIELD_AR_002_A"


def scenario_already_loaded(conn: psycopg.Connection) -> bool:
    with conn.cursor() as cur:
        cur.execute(
            """
            select exists (
                select 1
                from raw.field_events
                where source_system = %s
                  and source_event_id = %s
            )
            """,
            (SOURCE_SYSTEM, SOURCE_EVENT_ID),
        )
        return bool(cur.fetchone()[0])


def insert_late_arrival(
    conn: psycopg.Connection,
    scenario_time: datetime,
) -> datetime:
    event_timestamp = scenario_time - timedelta(days=1, hours=2)
    source_updated_at = event_timestamp + timedelta(minutes=1)
    ingested_at = ingestion_clock(conn)

    with conn.cursor() as cur:
        cur.execute(
            """
            insert into raw.field_events (
                event_id,
                source_system,
                source_event_id,
                field_id,
                event_type,
                event_timestamp,
                quantity,
                unit,
                event_payload,
                source_updated_at,
                ingested_at,
                source_batch_id
            )
            values (
                'EVT_0006',
                %s,
                %s,
                %s,
                'irrigation',
                %s,
                7.5,
                'mm',
                '{"zone": "central", "delivery": "delayed"}'::jsonb,
                %s,
                %s,
                %s
            )
            """,
            (
                SOURCE_SYSTEM,
                SOURCE_EVENT_ID,
                FIELD_ID,
                event_timestamp,
                source_updated_at,
                ingested_at,
                SCENARIO_BATCH_ID,
            ),
        )
    return ingested_at


def main() -> None:

    with fixture_transaction() as conn:
        scenario_time = fixture_clock(conn)
        if scenario_already_loaded(conn):
            print(
                f"Scenario {SCENARIO_BATCH_ID} is already loaded. "
                "No rows were inserted."
            )
            return

        ingested_at = insert_late_arrival(conn, scenario_time)
        conn.commit()

        event_timestamp = scenario_time - timedelta(days=1, hours=2)

        print(f"Loaded scenario: {SCENARIO_BATCH_ID}")
        print(f"Inserted {SOURCE_EVENT_ID} for {FIELD_ID}")
        print(f"Event time:    {event_timestamp.isoformat()}")
        print(f"Ingested time: {ingested_at.isoformat()}")
        print(
            "Expected behavior: incremental processing must capture "
            "the late event despite its older business timestamp."
        )


if __name__ == "__main__":
    main()
