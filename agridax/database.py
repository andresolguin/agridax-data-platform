from __future__ import annotations

from contextlib import contextmanager
import sys

import psycopg

from .config import Settings

LOCK_NAMESPACE = 8142026
PIPELINE_LOCK = 1
RAW_LOCK = 2
RAW_TABLES = ("farms", "fields", "field_events", "weather_observations", "sustainability_practices")


def connect(role: str = "ingest", *, autocommit: bool = False):
    settings = Settings.load()
    # Operational connections run few control queries; explicit no-cache is also pooler compatible.
    conn = psycopg.connect(**settings.connection_params(role), autocommit=autocommit,prepare_threshold=None)
    with conn.cursor() as cur:
        cur.execute("select set_config('timezone', 'UTC', false)")
        cur.execute("select set_config('lock_timeout', %s, false)", (f"{settings.lock_timeout_seconds}s",))
        cur.execute("select set_config('statement_timeout', %s, false)", (f"{settings.statement_timeout_seconds}s",))
    if not autocommit:
        conn.commit()
    return conn


@contextmanager
def ingestion_transaction():
    """Take the shared ingestion boundary before assigning timestamps / checking fixtures."""
    with connect("ingest") as conn:
        conn.execute("select pg_advisory_xact_lock_shared(%s, %s)", (LOCK_NAMESPACE, RAW_LOCK))
        yield conn


@contextmanager
def fixture_transaction():
    """Serialize repository fixtures as well as taking the RAW ingestion boundary."""
    with ingestion_transaction() as conn:
        conn.execute("select pg_advisory_xact_lock(%s, 3)", (LOCK_NAMESPACE,))
        yield conn


@contextmanager
def single_writer(conn):
    """One coordinator for build + validation + promotion; fail immediately on contention."""
    acquired = []
    try:
        for key in (PIPELINE_LOCK, RAW_LOCK):
            ok = conn.execute("select pg_try_advisory_lock(%s, %s)", (LOCK_NAMESPACE, key)).fetchone()[0]
            if not ok:
                raise RuntimeError("Another release or ingestion transaction is active; retry after it completes")
            acquired.append(key)
        yield
    finally:
        if not conn.closed and not conn.broken:
            try:
                for key in reversed(acquired):
                    conn.execute("select pg_advisory_unlock(%s, %s)", (LOCK_NAMESPACE, key))
            except psycopg.Error:
                # Closing the session releases its locks; preserve any original COMMIT failure.
                conn.close()
                print('Writer connection failed during lock cleanup; connection closed. Reconcile the run/release marker if needed.',file=sys.stderr)
