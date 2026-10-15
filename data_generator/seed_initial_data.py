from __future__ import annotations

from datetime import datetime, timedelta, timezone

import psycopg
from agridax.config import get_connection_params
from agridax.database import fixture_transaction
from agridax.fixtures import fixture_clock


BASE_BATCH_ID = "BASELINE_01"


def baseline_already_loaded(conn: psycopg.Connection) -> bool:
    expected = {'farms':3,'fields':4,'field_events':4,'weather_observations':4,'sustainability_practices':4}
    actual = {table: conn.execute(f"select count(*) from raw.{table} where source_batch_id=%s", (BASE_BATCH_ID,)).fetchone()[0] for table in expected}
    if not any(actual.values()):
        return False
    if actual != expected:
        raise RuntimeError("Baseline batch is incomplete or altered; use an isolated acceptance database or the documented recovery path")
    return True


def insert_farms(conn: psycopg.Connection, anchor: datetime) -> None:
    updated_at = anchor - timedelta(minutes=15)
    ingested_at = anchor - timedelta(minutes=10)

    rows = [
        ("FARM_AR_001", "Las Acacias", "AR", "Buenos Aires", "family",
         datetime(2024, 1, 15, 12, 0, tzinfo=timezone.utc),
         updated_at, ingested_at, BASE_BATCH_ID, "farms_baseline.csv"),
        ("FARM_AR_002", "El Ombu", "AR", "Cordoba", "corporate",
         datetime(2023, 8, 1, 9, 0, tzinfo=timezone.utc),
         updated_at, ingested_at, BASE_BATCH_ID, "farms_baseline.csv"),
        ("FARM_BR_001", "Fazenda Horizonte", "BR", "Parana", "cooperative",
         datetime(2022, 11, 20, 14, 0, tzinfo=timezone.utc),
         updated_at, ingested_at, BASE_BATCH_ID, "farms_baseline.csv"),
    ]

    with conn.cursor() as cur:
        cur.executemany(
            """
            insert into raw.farms (
                farm_id, farm_name, country_code, region, owner_type,
                created_at, updated_at, ingested_at,
                source_batch_id, source_file_name
            )
            values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            rows,
        )


def insert_fields(conn: psycopg.Connection, anchor: datetime) -> None:
    effective_from = anchor - timedelta(days=14)
    updated_at = anchor - timedelta(minutes=12)
    ingested_at = anchor - timedelta(minutes=8)

    rows = [
        ("FIELD_AR_001_A", "FARM_AR_001", "North Plot", 120.50, "wheat",
         "loam", "pivot", "active",
         datetime(2024, 1, 15, 12, 10, tzinfo=timezone.utc),
         effective_from, updated_at, ingested_at,
         BASE_BATCH_ID, "fields_baseline.csv"),
        ("FIELD_AR_001_B", "FARM_AR_001", "South Plot", 85.25, "soy",
         "clay_loam", "drip", "active",
         datetime(2024, 1, 15, 12, 12, tzinfo=timezone.utc),
         effective_from, updated_at, ingested_at,
         BASE_BATCH_ID, "fields_baseline.csv"),
        ("FIELD_AR_002_A", "FARM_AR_002", "Central Plot", 160.00, "corn",
         "silt_loam", "pivot", "active",
         datetime(2023, 8, 1, 9, 15, tzinfo=timezone.utc),
         effective_from, updated_at, ingested_at,
         BASE_BATCH_ID, "fields_baseline.csv"),
        ("FIELD_BR_001_A", "FARM_BR_001", "Talhao 01", 210.75, "soy",
         "red_clay", "rainfed", "active",
         datetime(2022, 11, 20, 14, 20, tzinfo=timezone.utc),
         effective_from, updated_at, ingested_at,
         BASE_BATCH_ID, "fields_baseline.csv"),
    ]

    with conn.cursor() as cur:
        cur.executemany(
            """
            insert into raw.fields (
                field_id, farm_id, field_name, area_hectares, crop_type,
                soil_type, irrigation_type, status, created_at, effective_from,
                updated_at, ingested_at, source_batch_id, source_file_name
            )
            values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            rows,
        )


def insert_field_events(conn: psycopg.Connection, anchor: datetime) -> None:
    event_times = [
        anchor - timedelta(hours=4),
        anchor - timedelta(hours=3),
        anchor - timedelta(hours=2),
        anchor - timedelta(hours=1),
    ]

    rows = [
        ("EVT_0001", "field_ops", "OPS_1001", "FIELD_AR_001_A", "planting",
         event_times[0], 120.50, "ha", '{"seed_variety": "wheat_a1"}',
         event_times[0] + timedelta(minutes=2),
         anchor - timedelta(minutes=30), BASE_BATCH_ID),
        ("EVT_0002", "irrigation_controller", "IRR_2001", "FIELD_AR_001_B", "irrigation",
         event_times[1], 18.40, "mm", '{"zone": "south"}',
         event_times[1] + timedelta(minutes=1),
         anchor - timedelta(minutes=20), BASE_BATCH_ID),
        ("EVT_0003", "field_ops", "OPS_1002", "FIELD_AR_002_A", "fertilizer",
         event_times[2], 3200.0, "kg", '{"product": "NPK"}',
         event_times[2] + timedelta(minutes=5),
         anchor - timedelta(minutes=10), BASE_BATCH_ID),
        ("EVT_0004", "field_ops", "OPS_1003", "FIELD_BR_001_A", "soil_measurement",
         event_times[3], 6.2, "ph", '{"depth_cm": 20}',
         event_times[3] + timedelta(minutes=5),
         anchor - timedelta(minutes=2), BASE_BATCH_ID),
    ]

    with conn.cursor() as cur:
        cur.executemany(
            """
            insert into raw.field_events (
                event_id, source_system, source_event_id, field_id, event_type,
                event_timestamp, quantity, unit, event_payload,
                source_updated_at, ingested_at, source_batch_id
            )
            values (%s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s, %s, %s)
            """,
            rows,
        )


def insert_weather(conn: psycopg.Connection, anchor: datetime) -> None:
    observed_at = anchor - timedelta(hours=1)
    source_updated_at = anchor - timedelta(minutes=5)
    ingested_at = anchor - timedelta(minutes=4)

    rows = [
        ("WX_0001", "FIELD_AR_001_A", observed_at, 18.2, 0.0, 68.0, 14.5,
         "weather_provider_a", source_updated_at, ingested_at, BASE_BATCH_ID),
        ("WX_0002", "FIELD_AR_001_B", observed_at, 18.6, 0.0, 66.0, 13.8,
         "weather_provider_a", source_updated_at, ingested_at, BASE_BATCH_ID),
        ("WX_0003", "FIELD_AR_002_A", observed_at, 23.1, 0.0, 52.0, 18.2,
         "weather_provider_a", source_updated_at, ingested_at, BASE_BATCH_ID),
        ("WX_0004", "FIELD_BR_001_A", observed_at, 26.4, 1.8, 81.0, 9.4,
         "weather_provider_b", source_updated_at, ingested_at, BASE_BATCH_ID),
    ]

    with conn.cursor() as cur:
        cur.executemany(
            """
            insert into raw.weather_observations (
                observation_id, field_id, observed_at, temperature_c,
                rainfall_mm, humidity_pct, wind_speed_kmh, source_system,
                source_updated_at, ingested_at, source_batch_id
            )
            values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            rows,
        )


def insert_sustainability_practices(
    conn: psycopg.Connection, anchor: datetime
) -> None:
    updated_at = anchor - timedelta(minutes=12)
    ingested_at = anchor - timedelta(minutes=6)
    valid_from = (anchor - timedelta(days=120)).date()

    rows = [
        ("PRACTICE_001", "FIELD_AR_001_A", "crop_rotation", "active", True,
         valid_from, None, updated_at, ingested_at,
         BASE_BATCH_ID, "sustainability_baseline.csv"),
        ("PRACTICE_002", "FIELD_AR_001_B", "water_efficiency", "active", True,
         valid_from, None, updated_at, ingested_at,
         BASE_BATCH_ID, "sustainability_baseline.csv"),
        ("PRACTICE_003", "FIELD_AR_002_A", "reduced_tillage", "active", False,
         valid_from, None, updated_at, ingested_at,
         BASE_BATCH_ID, "sustainability_baseline.csv"),
        ("PRACTICE_004", "FIELD_BR_001_A", "cover_crop", "active", True,
         valid_from, None, updated_at, ingested_at,
         BASE_BATCH_ID, "sustainability_baseline.csv"),
    ]

    with conn.cursor() as cur:
        cur.executemany(
            """
            insert into raw.sustainability_practices (
                practice_id, field_id, practice_type, status, verified,
                valid_from, valid_to, updated_at, ingested_at,
                source_batch_id, source_file_name
            )
            values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            rows,
        )


def load_baseline() -> bool:
    with fixture_transaction() as conn:
        if baseline_already_loaded(conn):
            print(
                f"Baseline batch {BASE_BATCH_ID} is already loaded. "
                "No rows were inserted."
            )
            return False

        anchor = fixture_clock(conn)

        insert_farms(conn, anchor)
        insert_fields(conn, anchor)
        insert_field_events(conn, anchor)
        insert_weather(conn, anchor)
        insert_sustainability_practices(conn, anchor)

        conn.commit()

        print(f"Loaded baseline batch: {BASE_BATCH_ID}")
        print(f"Reference time (UTC): {anchor.isoformat()}")
        print("raw.farms: 3 rows")
        print("raw.fields: 4 rows")
        print("raw.field_events: 4 rows")
        print("raw.weather_observations: 4 rows")
        print("raw.sustainability_practices: 4 rows")
        return True


def main() -> None:
    load_baseline()


if __name__ == "__main__":
    main()
