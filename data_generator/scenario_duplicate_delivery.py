from __future__ import annotations

from datetime import datetime

import psycopg

from agridax.database import fixture_transaction
from agridax.fixtures import ingestion_clock


SCENARIO_BATCH_ID = "DUPLICATE_DELIVERY_01"
SOURCE_SYSTEM = "field_ops"
SOURCE_EVENT_ID = "OPS_1002"


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


def insert_duplicate_delivery(
    conn: psycopg.Connection,
    scenario_time: datetime,
) -> None:
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
            select
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
                %s as ingested_at,
                %s as source_batch_id
            from raw.field_events
            where source_system = %s
              and source_event_id = %s
            order by ingested_at asc, raw_record_id asc
            limit 1
            """,
            (
                scenario_time,
                SCENARIO_BATCH_ID,
                SOURCE_SYSTEM,
                SOURCE_EVENT_ID,
            ),
        )

        if cur.rowcount != 1:
            raise RuntimeError(
                f"Expected exactly one source event to duplicate for "
                f"{SOURCE_SYSTEM}:{SOURCE_EVENT_ID}."
            )


def main() -> None:

    with fixture_transaction() as conn:
        scenario_time = ingestion_clock(conn)
        if scenario_already_loaded(conn):
            print(
                f"Scenario {SCENARIO_BATCH_ID} is already loaded. "
                "No rows were inserted."
            )
            return

        insert_duplicate_delivery(conn, scenario_time)
        conn.commit()

        print(f"Loaded scenario: {SCENARIO_BATCH_ID}")
        print(f"Inserted duplicate physical delivery for {SOURCE_EVENT_ID}")
        print(f"Duplicate ingested at: {scenario_time.isoformat()}")
        print("Logical event key remains unchanged.")
        print(
            "Expected behavior: RAW count increases, trusted downstream "
            "count does not."
        )


if __name__ == "__main__":
    main()
