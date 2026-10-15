from __future__ import annotations

from datetime import datetime, timedelta

import psycopg

from agridax.database import fixture_transaction
from agridax.fixtures import ingestion_clock


SCENARIO_BATCH_ID = "POST_FIELD_STATE_EVENT_01"
SOURCE_SYSTEM = "field_ops"
SOURCE_EVENT_ID = "OPS_1004"
FIELD_ID = "FIELD_AR_001_A"
FIELD_STATE_BATCH_ID = "FIELD_STATE_CHANGE_01"


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


def get_changed_state_effective_from(
    conn: psycopg.Connection,
) -> datetime:
    with conn.cursor() as cur:
        cur.execute(
            """
            select effective_from
            from raw.fields
            where field_id = %s
              and source_batch_id = %s
            order by raw_record_id desc
            limit 1
            """,
            (FIELD_ID, FIELD_STATE_BATCH_ID),
        )
        row = cur.fetchone()

    if row is None:
        raise RuntimeError(
            "Field-state change scenario must be loaded before "
            "the post-change event scenario."
        )

    return row[0]


def insert_post_change_event(
    conn: psycopg.Connection,
    field_state_effective_from: datetime,
) -> datetime:
    event_timestamp = field_state_effective_from + timedelta(minutes=15)
    source_updated_at = event_timestamp + timedelta(minutes=1)
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
                'EVT_0005',
                %s,
                %s,
                %s,
                'irrigation',
                %s,
                12.5,
                'mm',
                '{"zone": "north"}'::jsonb,
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

    return event_timestamp


def main() -> None:

    with fixture_transaction() as conn:
        if scenario_already_loaded(conn):
            print(
                f"Scenario {SCENARIO_BATCH_ID} is already loaded. "
                "No rows were inserted."
            )
            return

        effective_from = get_changed_state_effective_from(conn)
        event_timestamp = insert_post_change_event(conn, effective_from)
        conn.commit()

        print(f"Loaded scenario: {SCENARIO_BATCH_ID}")
        print(f"Inserted {SOURCE_EVENT_ID} for {FIELD_ID}")
        print(f"Event time: {event_timestamp.isoformat()}")
        print("Expected historical crop_type: soy")


if __name__ == "__main__":
    main()
