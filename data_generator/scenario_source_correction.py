from __future__ import annotations

from datetime import datetime, timedelta

import psycopg

from agridax.database import fixture_transaction
from agridax.fixtures import fixture_clock, ingestion_clock


SCENARIO_BATCH_ID = "SOURCE_CORRECTION_01"
SOURCE_SYSTEM = "field_ops"
SOURCE_EVENT_ID = "OPS_1002"
FIELD_ID = "FIELD_AR_002_A"


def scenario_already_loaded(conn: psycopg.Connection) -> bool:
    with conn.cursor() as cur:
        cur.execute(
            """
            select exists (
                select 1
                from raw.field_events
                where source_batch_id = %s
            )
            """,
            (SCENARIO_BATCH_ID,),
        )
        return bool(cur.fetchone()[0])


def get_original_event(conn: psycopg.Connection) -> tuple:
    with conn.cursor() as cur:
        cur.execute(
            """
            select
                event_id,
                event_timestamp,
                unit
            from raw.field_events
            where source_system = %s
              and source_event_id = %s
            order by
                ingested_at asc,
                raw_record_id asc
            limit 1
            """,
            (SOURCE_SYSTEM, SOURCE_EVENT_ID),
        )
        row = cur.fetchone()

    if row is None:
        raise RuntimeError(
            f"Original event {SOURCE_SYSTEM}:{SOURCE_EVENT_ID} was not found."
        )

    return row


def insert_source_correction(
    conn: psycopg.Connection,
    scenario_time: datetime,
) -> datetime:
    event_id, event_timestamp, unit = get_original_event(conn)

    source_updated_at = scenario_time - timedelta(minutes=1)
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
                %s,
                %s,
                %s,
                %s,
                'fertilizer',
                %s,
                3000.0,
                %s,
                '{"product": "NPK", "correction_reason": "source quantity correction"}'::jsonb,
                %s,
                %s,
                %s
            )
            """,
            (
                event_id,
                SOURCE_SYSTEM,
                SOURCE_EVENT_ID,
                FIELD_ID,
                event_timestamp,
                unit,
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

        ingested_at = insert_source_correction(conn, scenario_time)
        conn.commit()

        print(f"Loaded scenario: {SCENARIO_BATCH_ID}")
        print(f"Corrected logical event: {SOURCE_EVENT_ID}")
        print("Original fertilizer quantity: 3200 kg")
        print("Corrected fertilizer quantity: 3000 kg")
        print(f"Correction ingested at: {ingested_at.isoformat()}")
        print(
            "Expected behavior: trusted downstream models keep one logical "
            "event and use the corrected quantity."
        )


if __name__ == "__main__":
    main()
