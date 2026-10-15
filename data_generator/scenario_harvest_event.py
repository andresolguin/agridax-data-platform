from __future__ import annotations

from datetime import datetime, timedelta

import psycopg

from agridax.database import fixture_transaction
from agridax.fixtures import ingestion_clock


SCENARIO_BATCH_ID = "HARVEST_EVENT_01"
SOURCE_SYSTEM = "field_ops"
SOURCE_EVENT_ID = "OPS_1006"
FIELD_ID = "FIELD_AR_001_A"
PLANTING_SOURCE_SYSTEM = "field_ops"
PLANTING_SOURCE_EVENT_ID = "OPS_1001"


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


def get_planting_timestamp(conn: psycopg.Connection) -> datetime:
    with conn.cursor() as cur:
        cur.execute(
            """
            select event_timestamp
            from raw.field_events
            where source_system = %s
              and source_event_id = %s
              and field_id = %s
              and event_type = 'planting'
            order by ingested_at asc, raw_record_id asc
            limit 1
            """,
            (
                PLANTING_SOURCE_SYSTEM,
                PLANTING_SOURCE_EVENT_ID,
                FIELD_ID,
            ),
        )
        row = cur.fetchone()

    if row is None:
        raise RuntimeError(
            f"Planting event {PLANTING_SOURCE_SYSTEM}:{PLANTING_SOURCE_EVENT_ID} "
            f"was not found for {FIELD_ID}."
        )

    return row[0]


def insert_harvest_event(
    conn: psycopg.Connection,
    planting_timestamp: datetime,
) -> datetime:
    harvest_timestamp = planting_timestamp + timedelta(hours=2)
    source_updated_at = harvest_timestamp + timedelta(minutes=2)
    ingested_at = ingestion_clock(conn)

    if ingested_at <= source_updated_at:
        raise RuntimeError("Fixture anchor/source revision ordering is invalid; future ingestion is not synthesized")

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
                'EVT_0007',
                %s,
                %s,
                %s,
                'harvest',
                %s,
                420000.0,
                'kg',
                '{"quality_grade": "A"}'::jsonb,
                %s,
                %s,
                %s
            )
            """,
            (
                SOURCE_SYSTEM,
                SOURCE_EVENT_ID,
                FIELD_ID,
                harvest_timestamp,
                source_updated_at,
                ingested_at,
                SCENARIO_BATCH_ID,
            ),
        )

    return harvest_timestamp


def main() -> None:

    with fixture_transaction() as conn:
        if scenario_already_loaded(conn):
            print(
                f"Scenario {SCENARIO_BATCH_ID} is already loaded. "
                "No rows were inserted."
            )
            return

        planting_timestamp = get_planting_timestamp(conn)
        harvest_timestamp = insert_harvest_event(conn, planting_timestamp)
        conn.commit()

        print(f"Loaded scenario: {SCENARIO_BATCH_ID}")
        print(f"Inserted {SOURCE_EVENT_ID} for {FIELD_ID}")
        print(f"Planting time: {planting_timestamp.isoformat()}")
        print(f"Harvest time:  {harvest_timestamp.isoformat()}")
        print("Harvest quantity: 420000 kg")
        print("Expected behavior: the open crop cycle closes with this harvest.")


if __name__ == "__main__":
    main()
