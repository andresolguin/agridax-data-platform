"""Parameterized adversarial fixtures. Only the acceptance runner uses these records."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from psycopg.types.json import Jsonb

from .fixtures import ingestion_clock


def event(conn, key: str, revision: datetime | None, *, quantity=10, unit='mm',
          field='FIELD_AR_001_A', kind='irrigation', occurred: datetime,
          ingested: datetime | None = None, source='acceptance', event_id=None, payload=None):
    return conn.execute(
        "insert into raw.field_events(event_id,source_system,source_event_id,field_id,event_type,"
        "event_timestamp,quantity,unit,event_payload,source_updated_at,ingested_at,source_batch_id) "
        "values(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) returning raw_record_id",
        (event_id if event_id is not None else key,source,key,field,kind,occurred,quantity,unit,
         Jsonb(payload or {'fixture':key}),revision,ingested or ingestion_clock(conn),'ACCEPTANCE')
    ).fetchone()[0]


def weather(conn, key: str, revision: datetime | None, *, observed: datetime,
            field='FIELD_AR_001_A', rain=1, humidity=60, wind=3, temperature=20,
            ingested: datetime | None = None, source='acceptance'):
    return conn.execute(
        "insert into raw.weather_observations(observation_id,field_id,observed_at,temperature_c,"
        "rainfall_mm,humidity_pct,wind_speed_kmh,source_system,source_updated_at,ingested_at,source_batch_id) "
        "values(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) returning raw_record_id",
        (key,field,observed,temperature,rain,humidity,wind,source,revision,ingested or ingestion_clock(conn),'ACCEPTANCE')
    ).fetchone()[0]


def state(conn, *, field: str, effective: datetime, revision: datetime, crop: str,
          area=None, ingested: datetime | None = None):
    row=conn.execute(
        "insert into raw.fields(field_id,farm_id,field_name,area_hectares,crop_type,soil_type,"
        "irrigation_type,status,created_at,effective_from,updated_at,ingested_at,source_batch_id,source_file_name) "
        "select field_id,farm_id,field_name,coalesce(%s,area_hectares),%s,soil_type,irrigation_type,"
        "status,created_at,%s,%s,%s,'ACCEPTANCE','acceptance_fixture' "
        "from raw.fields where field_id=%s order by raw_record_id limit 1 returning raw_record_id",
        (area,crop,effective,revision,ingested or ingestion_clock(conn),field)
    ).fetchone()
    if not row:
        raise RuntimeError('Acceptance field state requires the repository baseline')
    return row[0]


NAN = Decimal('NaN')
