"""Required RAW DDL shape, checked before bootstrap advances to fixtures/dbt."""

RAW_COLUMNS = {
    "farms": {
        "raw_record_id": ("bigint", True),
        "farm_id": ("text", True),
        "farm_name": ("text", True),
        "country_code": ("character(2)", True),
        "region": ("text", False),
        "owner_type": ("text", False),
        "created_at": ("timestamp with time zone", True),
        "updated_at": ("timestamp with time zone", True),
        "ingested_at": ("timestamp with time zone", True),
        "source_batch_id": ("text", False),
        "source_file_name": ("text", False),
    },
    "fields": {
        "raw_record_id": ("bigint", True),
        "field_id": ("text", True),
        "farm_id": ("text", True),
        "field_name": ("text", True),
        "area_hectares": ("numeric(12,2)", True),
        "crop_type": ("text", False),
        "soil_type": ("text", False),
        "irrigation_type": ("text", False),
        "status": ("text", True),
        "created_at": ("timestamp with time zone", True),
        "effective_from": ("timestamp with time zone", True),
        "updated_at": ("timestamp with time zone", True),
        "ingested_at": ("timestamp with time zone", True),
        "source_batch_id": ("text", False),
        "source_file_name": ("text", False),
    },
    "field_events": {
        "raw_record_id": ("bigint", True),
        "event_id": ("text", True),
        "source_system": ("text", True),
        "source_event_id": ("text", True),
        "field_id": ("text", True),
        "event_type": ("text", True),
        "event_timestamp": ("timestamp with time zone", True),
        "quantity": ("numeric(18,4)", False),
        "unit": ("text", False),
        "event_payload": ("jsonb", False),
        "source_updated_at": ("timestamp with time zone", False),
        "ingested_at": ("timestamp with time zone", True),
        "source_batch_id": ("text", False),
    },
    "weather_observations": {
        "raw_record_id": ("bigint", True),
        "observation_id": ("text", True),
        "field_id": ("text", True),
        "observed_at": ("timestamp with time zone", True),
        "temperature_c": ("numeric(6,2)", False),
        "rainfall_mm": ("numeric(10,2)", False),
        "humidity_pct": ("numeric(5,2)", False),
        "wind_speed_kmh": ("numeric(8,2)", False),
        "source_system": ("text", True),
        "source_updated_at": ("timestamp with time zone", False),
        "ingested_at": ("timestamp with time zone", True),
        "source_batch_id": ("text", False),
    },
    "sustainability_practices": {
        "raw_record_id": ("bigint", True),
        "practice_id": ("text", True),
        "field_id": ("text", True),
        "practice_type": ("text", True),
        "status": ("text", True),
        "verified": ("boolean", True),
        "valid_from": ("date", True),
        "valid_to": ("date", False),
        "updated_at": ("timestamp with time zone", True),
        "ingested_at": ("timestamp with time zone", True),
        "source_batch_id": ("text", False),
        "source_file_name": ("text", False),
    },
}


def raw_schema_issues(conn) -> list[str]:
    rows = conn.execute(
        "select c.relname,a.attname,format_type(a.atttypid,a.atttypmod),a.attnotnull,a.attidentity "
        "from pg_attribute a join pg_class c on c.oid=a.attrelid "
        "join pg_namespace n on n.oid=c.relnamespace "
        "where n.nspname='raw' and c.relkind='r' and a.attnum>0 and not a.attisdropped"
    ).fetchall()
    found = {(table, column): (kind, required, identity) for table,column,kind,required,identity in rows}
    issues = []
    for table, columns in RAW_COLUMNS.items():
        for column, expected in columns.items():
            actual = found.get((table,column))
            if actual is None or actual[:2] != expected or (column == "raw_record_id" and actual[2] != "a"):
                issues.append(f"raw.{table}.{column}")
    primary_keys = {table: column for table,column in conn.execute(
        "select c.relname,a.attname from pg_constraint k join pg_class c on c.oid=k.conrelid "
        "join pg_namespace n on n.oid=c.relnamespace join pg_attribute a "
        "on a.attrelid=c.oid and a.attnum=k.conkey[1] "
        "where n.nspname='raw' and k.contype='p' and array_length(k.conkey,1)=1"
    ).fetchall()}
    for table in RAW_COLUMNS:
        if primary_keys.get(table) != 'raw_record_id':
            issues.append(f'raw.{table}.primary_key')
    return issues
