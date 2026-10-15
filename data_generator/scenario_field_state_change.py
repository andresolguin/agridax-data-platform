from __future__ import annotations

from datetime import datetime, timedelta

import psycopg

from agridax.database import fixture_transaction
from agridax.fixtures import fixture_clock, ingestion_clock


SCENARIO_BATCH_ID = "FIELD_STATE_CHANGE_01"
FIELD_ID = "FIELD_AR_001_A"


def scenario_already_loaded(conn: psycopg.Connection) -> bool:
    with conn.cursor() as cur:
        cur.execute(
            """
            select exists (
                select 1
                from raw.fields
                where source_batch_id = %s
                  and field_id = %s
            )
            """,
            (SCENARIO_BATCH_ID, FIELD_ID),
        )
        return bool(cur.fetchone()[0])


def insert_field_state_change(
    conn: psycopg.Connection,
    scenario_time: datetime,
) -> None:
    effective_from = scenario_time - timedelta(minutes=30)
    updated_at = scenario_time - timedelta(minutes=1)
    ingested_at = ingestion_clock(conn)

    with conn.cursor() as cur:
        cur.execute(
            """
            insert into raw.fields (
                field_id,
                farm_id,
                field_name,
                area_hectares,
                crop_type,
                soil_type,
                irrigation_type,
                status,
                created_at,
                effective_from,
                updated_at,
                ingested_at,
                source_batch_id,
                source_file_name
            )
            select
                field_id,
                farm_id,
                field_name,
                area_hectares,
                'soy' as crop_type,
                soil_type,
                irrigation_type,
                status,
                created_at,
                %s as effective_from,
                %s as updated_at,
                %s as ingested_at,
                %s as source_batch_id,
                'fields_state_change.csv' as source_file_name
            from raw.fields
            where field_id = %s
            order by updated_at desc, ingested_at desc, raw_record_id desc
            limit 1
            """,
            (
                effective_from,
                updated_at,
                ingested_at,
                SCENARIO_BATCH_ID,
                FIELD_ID,
            ),
        )

        if cur.rowcount != 1:
            raise RuntimeError(
                f"Expected exactly one source row for {FIELD_ID}."
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

        insert_field_state_change(conn, scenario_time)
        conn.commit()

        print(f"Loaded scenario: {SCENARIO_BATCH_ID}")
        print(f"{FIELD_ID} crop_type: wheat -> soy")
        print(
            "Business-effective from: "
            f"{(scenario_time - timedelta(minutes=30)).isoformat()}"
        )


if __name__ == "__main__":
    main()
