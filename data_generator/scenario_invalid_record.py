from __future__ import annotations

from datetime import datetime, timedelta

import psycopg

from agridax.database import fixture_transaction
from agridax.fixtures import fixture_clock, ingestion_clock


SCENARIO_BATCH_ID = "INVALID_RECORD_01"
SOURCE_SYSTEM = "field_ops"
SOURCE_EVENT_ID = "OPS_INVALID_1007"
FIELD_ID = "FIELD_AR_001_B"


def scenario_already_loaded(conn: psycopg.Connection) -> bool:
    with conn.cursor() as cur:
        cur.execute(
            '''
            select exists (
                select 1
                from raw.field_events
                where source_batch_id = %s
            )
            ''',
            (SCENARIO_BATCH_ID,),
        )
        return bool(cur.fetchone()[0])


def insert_invalid_record(
    conn: psycopg.Connection,
    scenario_time: datetime,
) -> None:
    event_time = scenario_time - timedelta(minutes=10)

    with conn.cursor() as cur:
        cur.execute(
            '''
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
                'irrigation',
                %s,
                12.5,
                'kg',
               jsonb_build_object(
                  'scenario', %s::text,
                  'note', 'intentionally invalid irrigation unit'
            ),
                %s,
                %s,
                %s
            )
            ''',
            (
                "EVT_INVALID_1007",
                SOURCE_SYSTEM,
                SOURCE_EVENT_ID,
                FIELD_ID,
                event_time,
                SCENARIO_BATCH_ID,
                scenario_time,
                ingestion_clock(conn),
                SCENARIO_BATCH_ID,
            ),
        )


def main() -> None:

    with fixture_transaction() as conn:
        scenario_time = fixture_clock(conn)
        if scenario_already_loaded(conn):
            print(
                f"Scenario {SCENARIO_BATCH_ID} is already loaded. "
                "No rows were inserted."
            )
            return

        insert_invalid_record(conn, scenario_time)
        conn.commit()

        print(f"Loaded scenario: {SCENARIO_BATCH_ID}")
        print(f"Inserted structurally valid but business-invalid event: {SOURCE_EVENT_ID}")
        print(f"Field: {FIELD_ID}")
        print("Event type: irrigation")
        print("Quantity: 12.5")
        print("Unit: kg")
        print("Expected rejection reason: invalid_unit_for_irrigation")
        print(
            "Expected behavior: row remains in RAW, appears in quarantine, "
            "and is excluded from trusted downstream models."
        )


if __name__ == "__main__":
    main()
