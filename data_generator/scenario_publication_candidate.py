from __future__ import annotations

from datetime import datetime, timedelta

import psycopg

from agridax.database import fixture_transaction
from agridax.fixtures import fixture_clock, ingestion_clock


SCENARIO_BATCH_ID = "PUBLICATION_CANDIDATE_01"
SOURCE_SYSTEM = "field_ops"
SOURCE_EVENT_ID = "OPS_1008"
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


def insert_publication_candidate(
    conn: psycopg.Connection,
    scenario_time: datetime,
) -> None:
    event_time = scenario_time - timedelta(minutes=5)

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
                'pesticide',
                %s,
                24.0,
                'kg',
                jsonb_build_object(
                    'scenario', %s::text,
                    'note', 'valid event used to verify safe publication'
                ),
                %s,
                %s,
                %s
            )
            ''',
            (
                "EVT_1008",
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

        insert_publication_candidate(conn, scenario_time)
        conn.commit()

        print(f"Loaded scenario: {SCENARIO_BATCH_ID}")
        print(f"Inserted valid event: {SOURCE_EVENT_ID}")
        print(f"Field: {FIELD_ID}")
        print("Event type: pesticide")
        print("Quantity: 24.0 kg")
        print(
            "Expected behavior: analytics changes after dbt build, while published "
            "remains on the previous release until an atomic publication succeeds."
        )


if __name__ == "__main__":
    main()
