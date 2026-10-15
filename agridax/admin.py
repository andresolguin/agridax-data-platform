from __future__ import annotations

import hashlib
import time

from psycopg import sql

from .config import PROJECT_ROOT, Settings
from .database import connect
from .raw_contract import raw_schema_issues


def wait_ready(timeout_seconds: int = 90) -> None:
    """TCP + authenticated admin query + complete base RAW schema, with a deadline."""
    settings = Settings.load()
    if not 1 <= timeout_seconds <= 600:
        raise ValueError('Readiness timeout must be 1 through 600 seconds')
    deadline = time.monotonic() + timeout_seconds
    last = "not connected"
    while time.monotonic() < deadline:
        try:
            import psycopg
            params = settings.connection_params("admin")
            params["connect_timeout"] = max(1, min(settings.connect_timeout, int(deadline - time.monotonic())))
            remaining_ms = max(1, int((deadline - time.monotonic()) * 1000))
            params['options'] += f' -c statement_timeout={remaining_ms}'
            with psycopg.connect(**params) as conn:
                issues = raw_schema_issues(conn)
                if not issues:
                    return
                last = 'RAW schema is missing/incompatible: ' + ', '.join(issues[:5]) + '; apply the documented initialization/migration'
        except psycopg.Error as exc:
            last = type(exc).__name__
        time.sleep(min(0.25, max(0, deadline - time.monotonic())))
    raise RuntimeError(f"Database readiness timed out after {timeout_seconds}s: {last}")


def initialize_database(*, create_raw: bool = False) -> None:
    """Explicit admin-only initialization / checked migrations; never a volume reset."""
    settings = Settings.load()
    settings.validate_all()
    with connect("admin", autocommit=True) as conn:
        if not conn.execute("select pg_try_advisory_lock(8142026, 1)").fetchone()[0]:
            raise RuntimeError("Cannot initialize while another release holds the writer lock")
        try:
            if create_raw:
                conn.execute((PROJECT_ROOT / "infra/postgres/init/001_create_raw_schema.sql").read_text())
            with conn.transaction():
                for role in ("ingest", "dbt", "publish", "reader"):
                    user, password = settings.credentials(role)
                    existing=conn.execute('select rolsuper,rolcreatedb,rolcreaterole,rolreplication,rolbypassrls from pg_roles where rolname=%s',(user,)).fetchone()
                    memberships=conn.execute('select count(*) from pg_auth_members m join pg_roles r on r.oid=m.member where r.rolname=%s',(user,)).fetchone()[0]
                    if (existing and any(existing)) or memberships:
                        raise RuntimeError(f'Existing workload role {user} has elevated attributes/memberships; explicit admin review is required')
                    if not conn.execute("select 1 from pg_roles where rolname=%s", (user,)).fetchone():
                        conn.execute(sql.SQL("create role {} login").format(sql.Identifier(user)))
                    conn.execute(sql.SQL(
                        "alter role {} login nosuperuser nocreatedb nocreaterole noreplication nobypassrls password {}"
                    ).format(sql.Identifier(user), sql.Literal(password)))
                    conn.execute(sql.SQL("alter role {} set timezone to 'UTC'").format(sql.Identifier(user)))
                    conn.execute(sql.SQL("alter role {} set lock_timeout to {}").format(sql.Identifier(user),sql.Literal(f"{settings.lock_timeout_seconds}s")))
                    conn.execute(sql.SQL("alter role {} set statement_timeout to {}").format(sql.Identifier(user),sql.Literal(f"{settings.statement_timeout_seconds}s")))
                conn.execute("create schema if not exists ops")
                conn.execute("create table if not exists ops.schema_migrations ("
                             "version text primary key, sha256 text not null, applied_at timestamptz not null default clock_timestamp())")
                for path in sorted((PROJECT_ROOT / "infra/postgres/migrations").glob("*.sql")):
                    digest = hashlib.sha256(path.read_bytes()).hexdigest()
                    applied = conn.execute("select sha256 from ops.schema_migrations where version=%s", (path.name,)).fetchone()
                    if applied:
                        if applied[0] != digest:
                            raise RuntimeError(f"Applied migration changed: {path.name}; add a new migration")
                    else:
                        conn.execute(path.read_text())
                        conn.execute("insert into ops.schema_migrations(version,sha256) values(%s,%s)", (path.name,digest))
                grant_roles(conn, settings)
        finally:
            conn.execute("select pg_advisory_unlock(8142026, 1)")


def grant_roles(conn, settings: Settings) -> None:
    unsafe_owner = conn.execute(
        "select n.nspname,c.relname from pg_class c join pg_namespace n on n.oid=c.relnamespace "
        "join pg_roles r on r.oid=c.relowner where n.nspname in ('raw','ops') "
        "and c.relkind in ('r','S') and r.rolname<>current_user"
    ).fetchall()
    if unsafe_owner:
        raise RuntimeError('RAW/ops ownership differs from the initializing admin; explicit ownership migration is required')
    users = {role: sql.Identifier(settings.credentials(role)[0]) for role in ("ingest", "dbt", "publish", "reader")}
    for schema in ("analytics", "snapshots", "published"):
        conn.execute(sql.SQL("create schema if not exists {}").format(sql.Identifier(schema)))
        owner = users["publish" if schema == "published" else "dbt"]
        conn.execute(sql.SQL("alter schema {} owner to {}").format(sql.Identifier(schema), owner))
    conn.execute("revoke create on schema public from public")
    conn.execute("revoke all on schema raw, ops, analytics, snapshots, published from public")
    for schema in ('raw','ops','published'):
        conn.execute(sql.SQL('revoke all on all tables in schema {} from public').format(sql.Identifier(schema)))
    conn.execute('revoke all on all sequences in schema raw from public')
    for user in users.values():
        conn.execute(sql.SQL('revoke all on schema public,raw,ops,analytics,snapshots,published from {}').format(user))
        for schema in ['raw','ops','published']:
            conn.execute(sql.SQL('revoke all on all tables in schema {} from {}').format(sql.Identifier(schema),user))
        conn.execute(sql.SQL('revoke all on all sequences in schema raw from {}').format(user))
    conn.execute(sql.SQL("grant usage, create on schema analytics, snapshots to {}").format(users["dbt"]))
    conn.execute(sql.SQL("grant usage, create on schema published to {}").format(users["publish"]))
    conn.execute(sql.SQL("grant usage on schema raw to {}, {}").format(users["ingest"], users["dbt"]))
    conn.execute(sql.SQL("grant select, insert on all tables in schema raw to {}").format(users["ingest"]))
    conn.execute(sql.SQL("grant usage on all sequences in schema raw to {}").format(users["ingest"]))
    conn.execute(sql.SQL("grant select on all tables in schema raw to {}").format(users["dbt"]))
    conn.execute(sql.SQL("grant usage on schema ops to {}, {}, {}, {}").format(*users.values()))
    conn.execute(sql.SQL("grant select on ops.schema_migrations, ops.processing_checkpoints, ops.processing_scans, ops.pipeline_runs to {}, {}").format(users["dbt"],users["publish"]))
    conn.execute(sql.SQL("grant select, insert, update on ops.pipeline_runs to {}").format(users["publish"]))
    conn.execute(sql.SQL("grant select, insert on ops.releases to {}").format(users["publish"]))
    conn.execute(sql.SQL("grant select on ops.releases to {}").format(users["reader"]))
    conn.execute(sql.SQL("grant execute on function ops.assert_managed_run(uuid) to {}").format(users["dbt"]))
    conn.execute(sql.SQL("grant execute on function ops.record_processing_scan(uuid,text,timestamptz,timestamptz,bigint,bigint,boolean) to {}").format(users["dbt"]))
    conn.execute(sql.SQL("grant usage on schema analytics to {}").format(users["publish"]))
    conn.execute(sql.SQL("grant select on all tables in schema analytics to {}").format(users["publish"]))
    conn.execute(sql.SQL("grant select, insert, delete on all tables in schema published to {}").format(users["publish"]))
    conn.execute(sql.SQL("alter default privileges for role {} in schema analytics grant select on tables to {}").format(users["dbt"],users["publish"]))
    conn.execute(sql.SQL("grant usage on schema published to {}").format(users["reader"]))
    conn.execute(sql.SQL("grant select on all tables in schema published to {}").format(users["reader"]))
    conn.execute(sql.SQL("alter default privileges for role {} in schema published grant select on tables to {}").format(users["publish"],users["reader"]))
    from .publication import MART_KEYS
    for mart in MART_KEYS:
        if conn.execute("select to_regclass(%s)", (f"published.{mart}",)).fetchone()[0]:
            conn.execute(sql.SQL("alter table {} owner to {}").format(sql.Identifier('published',mart),users['publish']))
