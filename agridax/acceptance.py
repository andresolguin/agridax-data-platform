"""Reproducible acceptance tests. Resets are limited to explicit disposable databases."""
from __future__ import annotations

import argparse
import json
import os
import shutil
import socket
import subprocess
import tempfile
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

import psycopg
from psycopg import sql

from . import acceptance_fixtures as f
from .admin import initialize_database,wait_ready
from .config import PROJECT_ROOT, Settings
from .database import connect, fixture_transaction, single_writer
from .pipeline import dbt_executable, run_pipeline
from .preflight import check_tree
from .publication import MART_KEYS, publish_marts
from .time_contract import backfill_range
from .fixtures import fixture_clock


class Suite:
    def __init__(self, embedded: bool = False):
        self.embedded=embedded
        self.records=[]
        self.output=PROJECT_ROOT/'dbt/agridax/target/acceptance_results.json'
        self.output.parent.mkdir(parents=True,exist_ok=True)
        self.anchor=fixture_clock()

    def record(self,name,result='PASS',detail=None):
        self.records.append({'name':name,'result':result,'detail':detail})
        self.output.write_text(json.dumps({'scope':'embedded diagnostic; NOT native acceptance' if self.embedded else 'native PostgreSQL acceptance','records':self.records},indent=2,default=str))
        print(f'ACCEPTANCE {result}: {name}',flush=True)

    def expect(self,name,actual,expected):
        if actual != expected:
            self.record(name,'FAIL',{'actual':actual,'expected':expected})
            raise AssertionError(f'{name}: expected {expected!r}, received {actual!r}')
        self.record(name,detail=actual)

    def query(self,query,params=(),role='dbt'):
        with connect(role) as conn:
            return conn.execute(query,params).fetchall()

    def fails(self,name,action,*,exception=RuntimeError,message=None,sqlstate=None):
        try:
            action()
        except exception as exc:
            if message is not None and message not in str(exc):
                self.record(name,'FAIL','Failure did not match the expected cause')
                raise AssertionError(f'{name}: unexpected failure cause') from exc
            if sqlstate is not None and getattr(exc,'sqlstate',None) != sqlstate:
                self.record(name,'FAIL','Failure did not match the expected SQLSTATE')
                raise AssertionError(f'{name}: unexpected SQLSTATE') from exc
            self.record(name,detail={'exception':type(exc).__name__,'expected_cause':message,'sqlstate':getattr(exc,'sqlstate',None)})
        else:
            self.record(name,'FAIL','Expected failure did not occur')
            raise AssertionError(name)

    def release(self,**kwargs):
        return run_pipeline(**kwargs)

    def expected_failed_tests(self,name,expected):
        run_id=self.query("select run_id::text from ops.pipeline_runs where status='failed' order by started_at desc limit 1")[0][0]
        artifact=json.loads((self.output.parent/'runs'/run_id/'build/run_results.json').read_text())
        actual={r['unique_id'] for r in artifact['results'] if r['status'] in ('fail','error')}
        self.expect(name,actual,set(expected))

    def published(self):
        result={}
        for mart in MART_KEYS:
            q=sql.SQL("select count(*),md5(coalesce(string_agg(to_jsonb(t)::text,E'\\n' order by to_jsonb(t)::text),'')) from {} t").format(sql.Identifier('published',mart))
            with connect('publish') as conn:
                count,digest=conn.execute(q).fetchone()
                oid=conn.execute('select to_regclass(%s)::oid',(f'published.{mart}',)).fetchone()[0]
            result[mart]=[count,digest,oid]
        return result

    def reset(self):
        with connect('admin',autocommit=True) as conn:
            actual,version=conn.execute('select current_database(),version()').fetchone()
            if self.embedded:
                if 'PGlite' not in version:
                    raise RuntimeError('Embedded diagnostic flag is valid only for PGlite')
            elif not actual.startswith('agridax_acceptance_') or conn.info.server_version//10000 != 16:
                raise RuntimeError('Native acceptance requires PostgreSQL16 and an agridax_acceptance_* database')
            self.record('engine_scope',detail=version)
            # Explicit isolated acceptance reset; NEVER a bootstrap/publication operation.
            for schema in ('published','analytics','snapshots','ops','raw'):
                conn.execute(sql.SQL('drop schema if exists {} cascade').format(sql.Identifier(schema)))
        initialize_database(create_raw=True)
        self.record('isolated_empty_database_initialized')

    def compile_bounds(self):
        from .pipeline import DBT_PROJECT
        base=[dbt_executable(),'compile','--project-dir',str(DBT_PROJECT),'--profiles-dir',str(DBT_PROJECT),
              '--select','stg_field_event_winners','stg_weather_observation_winners']
        start='2026-01-01T00:00:00Z';end='2026-01-02T00:00:00Z'
        cases=[('utc',{'backfill_start':start,'backfill_end':end},False,True),
               ('offset',{'backfill_start':'2026-01-01T09:00:00-03:00','backfill_end':'2026-01-01T13:30:00+01:00'},False,True),
               ('missing_end',{'backfill_start':start},False,False),
               ('missing_start',{'backfill_end':end},False,False),
               ('equal',{'backfill_start':start,'backfill_end':start},False,False),
               ('reversed',{'backfill_start':end,'backfill_end':start},False,False),
               ('malformed',{'backfill_start':'not-a-timestamp','backfill_end':end},False,False),
               ('missing_zone',{'backfill_start':'2026-01-01T00:00:00','backfill_end':end},False,False),
               ('sql_literal',{'backfill_start':start+"';select 1;--",'backfill_end':end},False,False),
               ('full_refresh',{'backfill_start':start,'backfill_end':end},True,False)]
        for name,variables,full,success in cases:
            cmd=base+['--vars',json.dumps(variables)]
            if full: cmd+=['--full-refresh']
            result=subprocess.run(cmd,cwd=PROJECT_ROOT,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
            log=self.output.parent/f'compile_{name}.log';log.write_text(result.stdout)
            self.expect('compile_bounds_'+name,result.returncode==0,success)

    def native_checks(self):
        if self.embedded:
            self.record('native_login_role_isolation','NOT RUN','PGlite socket does not implement independent authenticated sessions')
            self.record('native_writer_ingest_reader_concurrency','NOT RUN','Single PGlite backend cannot reproduce native sessions/locks/MVCC readers')
            return
        settings=Settings.load()
        for role in ['ingest','dbt','publish','reader']:
            with connect(role) as conn:
                self.expect('authenticated_role_'+role,conn.execute('select current_user').fetchone()[0],settings.credentials(role)[0])
                self.expect('restricted_role_'+role,conn.execute('select rolsuper,rolcreatedb,rolcreaterole,rolreplication,rolbypassrls from pg_roles where rolname=current_user').fetchone(),(False,False,False,False,False))
        wrong=settings.connection_params('reader');wrong['password']=uuid.uuid4().hex
        def bad_login():
            with psycopg.connect(**wrong):
                pass
        self.fails('bad_password_rejected',bad_login,exception=psycopg.OperationalError,message='password authentication failed')
        def execute_transaction(conn,statement):
            with conn.transaction():
                conn.execute(statement)
        with connect('reader') as reader:
            for statement in ['select * from raw.fields','delete from published.dim_fields','insert into ops.releases(release_id,evidence,candidate_fingerprints) values(gen_random_uuid(),\'{}\',\'{}\')']:
                self.fails('reader_forbidden_'+statement.split()[0],lambda:execute_transaction(reader,statement),exception=psycopg.errors.InsufficientPrivilege,sqlstate='42501')
        with connect('ingest') as ingester:
            self.fails('ingester_cannot_update_raw',lambda:execute_transaction(ingester,"update raw.fields set field_name='forbidden'"),exception=psycopg.errors.InsufficientPrivilege,sqlstate='42501')
        with connect('publish',autocommit=True) as first, single_writer(first):
            self.fails('second_writer_refused',lambda:run_pipeline(),message='Another release or ingestion transaction is active')
            with connect('ingest') as second:
                second.execute("set local lock_timeout='100ms'")
                self.fails('ingestion_boundary_timeout',lambda:execute_transaction(second,'select pg_advisory_xact_lock_shared(8142026,2)'),exception=psycopg.errors.LockNotAvailable,sqlstate='55P03')
        self.record('native_single_writer_and_ingestion_lock')
        before=self.query('select count(*) from published.fct_field_events',role='reader')[0][0]
        with fixture_transaction() as conn:
            f.event(conn,'READER_COHORT',self.anchor,occurred=self.anchor-timedelta(hours=1))
        with connect('reader',autocommit=True) as reader:
            with reader.transaction():
                reader.execute('set transaction isolation level repeatable read read only')
                self.expect('reader_initial_release',reader.execute('select count(*) from published.fct_field_events').fetchone()[0],before)
                self.release()
                self.expect('reader_pins_old_release',reader.execute('select count(*) from published.fct_field_events').fetchone()[0],before)
        self.expect('new_reader_sees_new_release',self.query('select count(*) from published.fct_field_events',role='reader'),[(before+1,)])

    def run(self):
        os.environ['AGRIDAX_FIXTURE_ANCHOR']=self.anchor.isoformat()
        self.reset()
        wait_ready(5)
        self.record('authenticated_tcp_complete_raw_contract')
        with connect('admin') as conn:
            conn.execute('alter table raw.weather_observations rename column wind_speed_kmh to acceptance_missing_column')
        try:
            self.fails('incompatible_raw_readiness_rejected',lambda:wait_ready(1),message='raw.weather_observations.wind_speed_kmh')
        finally:
            with connect('admin') as conn:
                conn.execute('alter table raw.weather_observations rename column acceptance_missing_column to wind_speed_kmh')
        self.expect('source_preflight',check_tree(),[])
        self.fails('first_run_backfill_rejected',lambda:self.release(backfill_start='2026-01-01T00:00:00Z',backfill_end='2026-01-02T00:00:00Z'),exception=ValueError,message='Bounded backfill requires existing canonical targets')
        self.fails('empty_source_freshness_blocks_release',self.release,message='dbt source freshness failed')
        self.expect('empty_source_has_no_release',self.query('select count(*) from ops.releases',role='publish'),[(0,)])
        self.release(seed_baseline=True)
        self.expect('baseline_raw_counts',self.query("select (select count(*) from raw.farms),(select count(*) from raw.fields),(select count(*) from raw.field_events),(select count(*) from raw.weather_observations),(select count(*) from raw.sustainability_practices)"),[(3,4,4,4,4)])
        self.expect('baseline_fact_events',self.query('select count(*) from analytics.fct_field_events'),[(4,)])
        baseline=self.published()
        before_raw=self.query('select max(ingested_at),count(*) from raw.weather_observations')
        self.fails('freshness_override_error',lambda:self.release(dbt_vars={'weather_freshness_warn_minutes':1,'weather_freshness_error_minutes':2}),message='dbt source freshness failed')
        self.expect('freshness_does_not_mutate_raw',self.query('select max(ingested_at),count(*) from raw.weather_observations'),before_raw)
        self.expect('freshness_failure_preserves_release',self.published(),baseline)
        self.release(seed_baseline=True)
        self.expect('idempotent_rerun_data_and_oid',self.published(),baseline)
        self.expect('idempotent_snapshot',self.query('select count(*) from snapshots.snap_fields'),[(4,)])
        from dotenv import dotenv_values
        clean_env=dict(os.environ)
        for key in dotenv_values(os.environ.get('AGRIDAX_ENV_FILE',PROJECT_ROOT/'.env')):
            clean_env.pop(key,None)
        with tempfile.TemporaryDirectory() as folder:
            inspected=subprocess.run([os.sys.executable,'-m','agridax.inspect_dbt','debug'],cwd=folder,env=clean_env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
        (self.output.parent/'inspection_debug.log').write_text(inspected.stdout)
        self.expect('inspection_debug_from_dotenv_outside_root',inspected.returncode,0)

        from data_generator import scenario_source_correction,scenario_duplicate_delivery,scenario_late_arrival,scenario_invalid_record,scenario_publication_candidate
        scenario_source_correction.main();scenario_source_correction.main();self.release()
        scenario_duplicate_delivery.main();scenario_duplicate_delivery.main();self.release()
        self.expect('repository_correction_then_old_retry',self.query("select count(*),sum(quantity) from analytics.fct_field_events where source_system='field_ops' and source_event_id='OPS_1002'"),[(1,Decimal(3000))])
        before=self.published()
        for scenario in [scenario_late_arrival,scenario_invalid_record,scenario_publication_candidate]:
            scenario.main();scenario.main()
        self.release(skip_publish=True)
        self.expect('repository_late_arrival',self.query("select quantity from analytics.fct_field_events where source_event_id='OPS_1005'"),[(Decimal('7.5'),)])
        self.expect('repository_invalid_observable',self.query("select rejection_reason from analytics.quarantine_field_events where source_event_id='OPS_INVALID_1007'"),[('invalid_unit_for_irrigation',)])
        self.expect('repository_invalid_not_in_fact',self.query("select count(*) from analytics.fct_field_events where source_event_id='OPS_INVALID_1007'"),[(0,)])
        self.expect('repository_candidate_waits_for_promotion',self.published(),before)
        self.expect('repository_fixture_reruns_no_duplicate_batches',self.query("select source_batch_id,count(*) from raw.field_events where source_batch_id in ('SOURCE_CORRECTION_01','DUPLICATE_DELIVERY_01','LATE_ARRIVAL_01','INVALID_RECORD_01','PUBLICATION_CANDIDATE_01') group by source_batch_id order by source_batch_id"),[('DUPLICATE_DELIVERY_01',1),('INVALID_RECORD_01',1),('LATE_ARRIVAL_01',1),('PUBLICATION_CANDIDATE_01',1),('SOURCE_CORRECTION_01',1)])
        self.release()
        self.compile_bounds()

        a=self.anchor;old=a-timedelta(minutes=40);newer=a-timedelta(minutes=30)
        with fixture_transaction() as conn:
            f.event(conn,'F2',a-timedelta(hours=2),occurred=a-timedelta(hours=1),ingested=old,quantity=10,payload={'version':'v1'})
            event_winner=f.event(conn,'F2',a-timedelta(hours=1),occurred=a-timedelta(hours=1),ingested=newer,quantity=20,payload={'version':'v2'})
            f.weather(conn,'WX_F2_1',a-timedelta(hours=2),observed=a-timedelta(hours=7),ingested=old,rain=1)
            weather_winner=f.weather(conn,'WX_F2_2',a-timedelta(hours=1),observed=a-timedelta(hours=7),ingested=newer,rain=2)
        self.release(full_refresh=True)
        checkpoint=self.query("select stream,processed_through from ops.processing_checkpoints order by stream")
        self.expect('processing_full_scan_counts_physical_deliveries',self.query("select stream,rows_in_window,changed_keys,lower_bound is null from ops.processing_scans where run_id=(select last_run_id from ops.processing_checkpoints where stream='field_events') order by stream"),[('field_events',11,8,True),('weather_observations',6,5,True)])
        with fixture_transaction() as conn:
            f.event(conn,'F2',a-timedelta(hours=2),occurred=a-timedelta(hours=1),quantity=10,payload={'version':'stale'})
            f.weather(conn,'WX_F2_RETRY',a-timedelta(hours=2),observed=a-timedelta(hours=7),rain=1)
        self.release()
        self.expect('stale_event_full_identity',self.query("select raw_record_id,quantity,event_payload->>'version' from analytics.stg_field_events where source_event_id='F2'"),[(event_winner,Decimal(20),'v2')])
        self.expect('stale_weather_full_identity',self.query('select raw_record_id,rainfall_mm from analytics.stg_weather_observations where observed_at=%s and field_id=%s',(a-timedelta(hours=7),'FIELD_AR_001_A')),[(weather_winner,Decimal(2))])
        self.expect('non_winner_advances_processing',self.query("select processed_through from ops.processing_checkpoints where stream='field_events'")[0][0]>checkpoint[0][1],True)
        self.expect('processing_normal_lower_uses_previous_checkpoint',self.query("select lower_bound from ops.processing_scans where run_id=(select last_run_id from ops.processing_checkpoints where stream='field_events') and stream='field_events'"),[(checkpoint[0][1]-timedelta(seconds=Settings.load().lookback_seconds),)])
        checkpoint=self.query('select stream,processed_through from ops.processing_checkpoints order by stream')
        self.release(backfill_start=(old-timedelta(seconds=1)).isoformat(),backfill_end=(old+timedelta(seconds=1)).isoformat())
        self.expect('backfill_preserves_winner',self.query("select quantity from analytics.stg_field_events where source_event_id='F2'"),[(Decimal(20),)])
        self.expect('backfill_does_not_rewind_or_advance_checkpoint',self.query('select stream,processed_through from ops.processing_checkpoints order by stream'),checkpoint)
        self.expect('processing_backfill_counts_raw_losing_revision',self.query("select stream,rows_in_window,changed_keys,is_backfill from ops.processing_scans where run_id=(select run_id from ops.pipeline_runs where run_kind='backfill' order by started_at desc limit 1) order by stream"),[('field_events',1,1,True),('weather_observations',1,1,True)])
        with fixture_transaction() as conn:
            f.event(conn,'F2',None,occurred=a-timedelta(hours=1),quantity=10)
            f.weather(conn,'WX_F2_UNDATED',None,observed=a-timedelta(hours=7),rain=1)
        self.release()
        self.expect('undated_does_not_replace_dated_event',self.query("select quantity from analytics.stg_field_events where source_event_id='F2'"),[(Decimal(20),)])
        self.expect('undated_does_not_replace_dated_weather',self.query('select rainfall_mm from analytics.stg_weather_observations where observed_at=%s',(a-timedelta(hours=7),)),[(Decimal(2),)])

        with fixture_transaction() as conn:
            invalid_id=f.event(conn,'F2',a-timedelta(minutes=30),occurred=a-timedelta(hours=1),unit='kg')
            invalid_weather=f.weather(conn,'WX_F2_INVALID',a-timedelta(minutes=30),observed=a-timedelta(hours=7),humidity=150)
        self.release()
        self.expect('valid_to_invalid_event',self.query("select count(*) from analytics.stg_field_events where source_event_id='F2'"),[(0,)])
        self.expect('invalid_winner_retained',self.query('select raw_record_id,rejection_reason from analytics.stg_field_event_winners where source_event_id=%s',('F2',)),[(invalid_id,'invalid_unit_for_irrigation')])
        self.expect('valid_to_invalid_weather',self.query('select count(*) from analytics.stg_weather_observations where observed_at=%s',(a-timedelta(hours=7),)),[(0,)])
        with fixture_transaction() as conn:
            recovered=f.event(conn,'F2',a-timedelta(minutes=15),occurred=a-timedelta(hours=1),quantity=30)
            f.weather(conn,'WX_F2_RECOVER',a-timedelta(minutes=15),observed=a-timedelta(hours=7),rain=2)
        self.release()
        self.expect('invalid_to_valid_event',self.query("select raw_record_id,quantity from analytics.stg_field_events where source_event_id='F2'"),[(recovered,Decimal(30))])
        self.expect('physical_quarantine_history',self.query('select count(*) from analytics.quarantine_field_events where raw_record_id=%s',(invalid_id,)),[(1,)])
        self.expect('weather_recovery_retains_physical_quarantine',self.query('select count(*) from analytics.quarantine_weather_observations where raw_record_id=%s',(invalid_weather,)),[(1,)])

        expected_reasons=[]
        with fixture_transaction() as conn:
            for number,(attrs,reason) in enumerate([({'event_id':' '},'missing_event_id'),({'source':' '},'missing_source_system'),({'field':' '},'missing_field_id'),({'quantity':-1},'negative_quantity'),({'quantity':f.NAN},'non_finite_quantity'),({'event_id':'\t'},'missing_event_id'),({'source':'\t\n'},'missing_source_system')]):
                rid=f.event(conn,f'INVALID_{number}',a,occurred=a-timedelta(hours=1),**attrs)
                expected_reasons.append((rid,reason))
            rid=f.event(conn,' ',a,occurred=a-timedelta(hours=1),event_id='BLANK_LOGICAL_ID');expected_reasons.append((rid,'missing_source_event_id'))
            rid=f.event(conn,'\t',a,occurred=a-timedelta(hours=1),event_id='WHITESPACE_LOGICAL_ID');expected_reasons.append((rid,'missing_source_event_id'))
            weather_reasons=[]
            for number,(attrs,reason) in enumerate([({'humidity':150},'invalid_humidity_pct'),({'humidity':-1},'invalid_humidity_pct'),({'rain':-5},'negative_rainfall'),({'wind':-3},'negative_wind_speed'),({'temperature':f.NAN},'non_finite_temperature'),({'rain':f.NAN},'non_finite_rainfall'),({'wind':f.NAN},'non_finite_wind_speed'),({'source':'\n'},'missing_source_system')]):
                rid=f.weather(conn,f'INVALID_WX_{number}',a,observed=a-timedelta(hours=8,minutes=number),**attrs);weather_reasons.append((rid,reason))
            zero_day=(a-timedelta(days=3)).replace(hour=12,minute=0,second=0)
            f.event(conn,'ZERO',a,occurred=zero_day,quantity=0)
            weather_day=(a-timedelta(days=2)).replace(hour=12,minute=0,second=0)
            f.weather(conn,'WEATHER_ONLY',a,observed=weather_day,field='FIELD_AR_001_B',rain=0,temperature=None,humidity=None,wind=None)
            utc_boundary=(a-timedelta(days=5)).replace(hour=0,minute=0,second=0)
            f.event(conn,'UTC_BEFORE',a,occurred=utc_boundary-timedelta(microseconds=1),field='FIELD_BR_001_A',quantity=7)
            f.event(conn,'UTC_AT',a,occurred=utc_boundary.astimezone(timezone(timedelta(hours=-3))),field='FIELD_BR_001_A',quantity=0)
        self.release()
        for rid,reason in expected_reasons:
            self.expect('event_quarantine_'+str(rid),self.query('select rejection_reason from analytics.quarantine_field_events where raw_record_id=%s',(rid,)),[(reason,)])
            self.expect('invalid_event_not_in_fact_'+str(rid),self.query('select count(*) from analytics.fct_field_events e join raw.field_events r on lower(trim(r.source_system))=e.source_system and trim(r.source_event_id)=e.source_event_id where r.raw_record_id=%s',(rid,)),[(0,)])
        for rid,reason in weather_reasons:
            self.expect('weather_quarantine_'+str(rid),self.query('select rejection_reason from analytics.quarantine_weather_observations where raw_record_id=%s',(rid,)),[(reason,)])
        self.expect('zero_vs_missing_weather',self.query('select irrigation_mm,rainfall_mm,has_activity_data,has_weather_data,data_completeness_status from analytics.fct_field_daily_performance where field_id=%s and business_date=%s',('FIELD_AR_001_A',zero_day.date())),[(Decimal(0),None,True,False,'activity_only')])
        self.expect('weather_zero_and_null_measurement',self.query('select rainfall_mm,avg_temperature_c,irrigation_mm,has_activity_data,has_weather_data,data_completeness_status from analytics.fct_field_daily_performance where field_id=%s and business_date=%s',('FIELD_AR_001_B',weather_day.date())),[(Decimal(0),None,None,False,True,'weather_only')])
        self.expect('business_date_uses_utc_boundary',self.query('select business_date,irrigation_mm from analytics.fct_field_daily_performance where field_id=%s and business_date in (%s,%s) order by business_date',('FIELD_BR_001_A',(utc_boundary-timedelta(days=1)).date(),utc_boundary.date())),[((utc_boundary-timedelta(days=1)).date(),Decimal(7)),(utc_boundary.date(),Decimal(0))])

        from data_generator import scenario_field_state_change,scenario_post_change_event,scenario_harvest_event
        scenario_field_state_change.main();scenario_post_change_event.main();scenario_harvest_event.main()
        self.release()
        self.expect('post_state_event',self.query("select crop_type_at_event from analytics.fct_field_events where source_event_id='OPS_1004'"),[('soy',)])
        effective,revision=self.query("select effective_from,updated_at from raw.fields where source_batch_id='FIELD_STATE_CHANGE_01'")[0]
        with fixture_transaction() as conn:
            f.state(conn,field='FIELD_AR_001_A',effective=effective,revision=revision,crop='corn')
            f.event(conn,'BEFORE_BOUNDARY',a,occurred=effective-timedelta(microseconds=1))
            f.event(conn,'AT_BOUNDARY',a,occurred=effective)
            f.state(conn,field='FIELD_AR_001_A',effective=a+timedelta(days=2),revision=a,crop='future_crop')
        self.release()
        self.expect('same_update_current_correction',self.query("select crop_type from analytics.dim_fields where field_id='FIELD_AR_001_A'"),[('corn',)])
        self.expect('temporal_half_open_boundary',self.query("select source_event_id,crop_type_at_event from analytics.fct_field_events where source_event_id in ('BEFORE_BOUNDARY','AT_BOUNDARY') order by source_event_id"),[('AT_BOUNDARY','corn'),('BEFORE_BOUNDARY','wheat')])
        self.expect('corrected_historical_context',self.query("select crop_type_at_event from analytics.fct_field_events where source_event_id='OPS_1004'"),[('corn',)])
        self.expect('snapshot_observation_is_aware',self.query("select pg_typeof(warehouse_observed_at)::text,pg_typeof(dbt_valid_from)::text,warehouse_observed_at=dbt_valid_from,warehouse_observed_at>updated_at from snapshots.snap_fields where field_id='FIELD_AR_001_A' and dbt_valid_to is null"),[('timestamp with time zone','timestamp with time zone',True,True)])
        observations=self.query("select count(*),max(dbt_valid_from) from snapshots.snap_fields where field_id='FIELD_AR_001_A'")
        with fixture_transaction() as conn:
            retry_state=f.state(conn,field='FIELD_AR_001_A',effective=effective,revision=revision,crop='corn')
        self.release()
        self.expect('physical_field_retry_is_current',self.query("select raw_record_id from analytics.stg_fields where field_id='FIELD_AR_001_A'"),[(retry_state,)])
        self.expect('ingestion_only_retry_does_not_version_snapshot',self.query("select count(*),max(dbt_valid_from) from snapshots.snap_fields where field_id='FIELD_AR_001_A'"),observations)
        original_effective,original_revision=self.query("select effective_from,updated_at from raw.fields where field_id='FIELD_AR_001_A' and source_batch_id='BASELINE_01'")[0]
        prior_release=self.published()
        for number,(label,area) in enumerate([('zero',Decimal(0)),('nan',f.NAN)],1):
            with fixture_transaction() as conn:
                f.state(conn,field='FIELD_AR_001_A',effective=original_effective,revision=original_revision+timedelta(seconds=number),crop='wheat',area=area)
            self.fails('historical_area_'+label+'_blocks_release',self.release,message='dbt build failed')
            self.expected_failed_tests('historical_area_'+label+'_specific_test',{'test.agridax.test_field_history_positive_intervals'})
            self.expect('historical_area_'+label+'_preserves_release',self.published(),prior_release)
        with fixture_transaction() as conn:
            f.state(conn,field='FIELD_AR_001_A',effective=original_effective,revision=original_revision+timedelta(seconds=3),crop='wheat',area=Decimal('120.50'))
            f.event(conn,'BEFORE_FIRST_STATE',a,occurred=original_effective-timedelta(microseconds=1))
        self.fails('event_before_first_state_blocks_release',self.release,message='dbt build failed')
        self.expected_failed_tests('unmatched_temporal_state_specific_test',{'test.agridax.test_int_field_events_with_history_all_matched'})
        self.expect('unmatched_temporal_state_preserves_release',self.published(),prior_release)
        with fixture_transaction() as conn:
            f.event(conn,'BEFORE_FIRST_STATE',a+timedelta(seconds=1),occurred=original_effective+timedelta(microseconds=1))
        self.release()
        self.expect('first_harvest_metrics',self.query("select harvest_quantity,abs(yield_kg_per_hectare-3485.4771784232365145)<0.000000001,abs(cycle_duration_days-0.08333333333333333333)<0.000000001,crop_type_at_planting from analytics.fct_crop_cycles where planting_source_event_id='OPS_1001'"),[(Decimal(420000),True,True,'wheat')])
        planted,harvested=self.query("select planted_at,harvested_at from analytics.fct_crop_cycles where planting_source_event_id='OPS_1001'")[0]
        with fixture_transaction() as conn:
            f.event(conn,'ADDITIONAL_HARVEST',a,occurred=harvested+timedelta(minutes=5),kind='harvest',unit='kg',quantity=100000)
            f.event(conn,'ORPHAN_HARVEST',a,occurred=planted-timedelta(hours=1),kind='harvest',unit='kg',quantity=100)
            f.event(conn,'PLANT_B1',a,occurred=a-timedelta(hours=3),field='FIELD_AR_001_B',kind='planting',unit='ha',quantity=1)
            f.event(conn,'PLANT_B2',a,occurred=a-timedelta(hours=2),field='FIELD_AR_001_B',kind='planting',unit='ha',quantity=1)
        self.release()
        self.expect('first_harvest_not_total_production',self.query("select harvest_quantity from analytics.fct_crop_cycles where planting_source_event_id='OPS_1001'"),[(Decimal(420000),)])
        self.expect('harvest_reconciliation_statuses',self.query("select source_event_id,assignment_status from analytics.int_harvest_cycle_assignment where source_event_id in ('ADDITIONAL_HARVEST','ORPHAN_HARVEST') order by source_event_id"),[('ADDITIONAL_HARVEST','additional_harvest'),('ORPHAN_HARVEST','before_first_planting')])
        self.expect('superseded_and_open_cycles',self.query("select planting_source_event_id,crop_cycle_status from analytics.fct_crop_cycles where field_id='FIELD_AR_001_B' order by planting_source_event_id"),[('PLANT_B1','superseded'),('PLANT_B2','open')])
        old_release=self.published()
        with fixture_transaction() as conn:
            f.event(conn,'SIMULTANEOUS',a,occurred=a-timedelta(hours=2),field='FIELD_AR_001_B',kind='planting',unit='ha',quantity=1)
        self.fails('ambiguous_simultaneous_plantings_rejected',self.release,message='dbt build failed')
        self.expected_failed_tests('simultaneous_plantings_specific_test_failed',{'test.agridax.test_no_simultaneous_plantings'})
        self.expect('invalid_pairing_preserves_release',self.published(),old_release)
        with fixture_transaction() as conn:
            f.event(conn,'SIMULTANEOUS',a+timedelta(seconds=1),occurred=a-timedelta(hours=2)+timedelta(minutes=1),field='FIELD_AR_001_B',kind='planting',unit='ha',quantity=1)
        self.release()

        with connect('admin') as conn:
            conn.execute("create view published.acceptance_view as select source_event_id,quantity from published.fct_field_events")
            conn.execute("create index acceptance_field_idx on published.fct_field_events(field_id)")
            conn.execute("comment on table published.fct_field_events is 'acceptance metadata'")
            conn.execute("alter table published.fct_field_events add constraint acceptance_quantity check(quantity>=0)")
        previous=self.published()
        self.fails('publication_rollback_after_copy2',lambda:self.release(simulate_failure_after_copy=2),message='TEST ONLY: simulated publication failure after copy 2')
        self.expect('rollback_all_five_marts_data_oid',self.published(),previous)
        self.release()
        self.expect('successful_promotion_preserves_objects',self.published(),previous)
        self.expect('published_metadata_preserved',self.query("select to_regclass('published.acceptance_view') is not null,to_regclass('published.acceptance_field_idx') is not null,obj_description('published.fct_field_events'::regclass)='acceptance metadata',exists(select 1 from pg_constraint where conname='acceptance_quantity')",role='publish'),[(True,True,True,True)])
        self.expect('reader_select_grant',self.query("select has_table_privilege(%s,'published.fct_field_events','SELECT')",(Settings.load().credentials('reader')[0],),role='publish'),[(True,)])
        with connect('admin') as conn:
            conn.execute("create function published.acceptance_change() returns trigger language plpgsql as $$ begin if new.source_event_id='F2' then new.quantity:=new.quantity+1; end if; return new; end $$")
            conn.execute('create trigger acceptance_change before insert on published.fct_field_events for each row execute function published.acceptance_change()')
        try:
            self.fails('consumer_trigger_changed_copy_rejected',self.release,message='Published content differs from the validated candidate')
            self.expect('consumer_trigger_failure_preserves_release',self.published(),previous)
        finally:
            with connect('admin') as conn:
                conn.execute('drop trigger acceptance_change on published.fct_field_events')
                conn.execute('drop function published.acceptance_change()')

        accepted=self.published()
        real_publish=publish_marts
        def tamper(conn,run_id,**kwargs):
            with connect('dbt') as editor:
                editor.execute("update analytics.fct_field_events set quantity=quantity+1 where source_event_id='F2'")
            return real_publish(conn,run_id,**kwargs)
        with patch('agridax.pipeline.publish_marts',tamper):
            self.fails('candidate_tamper_rejected',self.release,message='Candidate changed after validation')
        self.expect('tamper_preserves_release',self.published(),accepted)
        self.release()
        unused=self.release(skip_publish=True)
        with connect('publish',autocommit=True) as conn:
            self.fails('stale_validation_without_live_writer_refused',lambda:publish_marts(conn,unused),message='Publication lost its single-writer' if self.embedded else 'Publication requires the live coordinator')
        standalone=subprocess.run([os.sys.executable,'scripts/publish_marts.py'],cwd=PROJECT_ROOT,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
        self.expect('standalone_publisher_refused',standalone.returncode!=0 and b'Standalone publication is refused' in standalone.stdout,True)
        unmanaged=subprocess.run([dbt_executable(),'build','--project-dir','dbt/agridax','--profiles-dir','dbt/agridax'],cwd=PROJECT_ROOT,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
        self.expect('unmanaged_dbt_mutation_refused',unmanaged.returncode!=0 and b'a managed run is required' in unmanaged.stdout,True)

        canonical=self.query('select to_jsonb(t)::text from analytics.stg_field_event_winners t order by raw_record_id')
        weather_canonical=self.query('select to_jsonb(t)::text from analytics.stg_weather_observation_winners t order by raw_record_id')
        facts=self.query('select to_jsonb(t)::text from analytics.fct_field_events t order by source_system,source_event_id')
        with connect('admin') as conn:
            conn.execute('drop schema analytics cascade')
            conn.execute('drop schema snapshots cascade')
        initialize_database()
        self.release(full_refresh=True)
        self.expect('raw_rebuild_canonical_equivalence',self.query('select to_jsonb(t)::text from analytics.stg_field_event_winners t order by raw_record_id'),canonical)
        self.expect('raw_rebuild_weather_canonical_equivalence',self.query('select to_jsonb(t)::text from analytics.stg_weather_observation_winners t order by raw_record_id'),weather_canonical)
        self.expect('raw_rebuild_historical_fact_equivalence',self.query('select to_jsonb(t)::text from analytics.fct_field_events t order by source_system,source_event_id'),facts)
        with connect('admin') as conn:
            conn.execute('truncate analytics.stg_field_event_winners,analytics.stg_weather_observation_winners')
        self.release()
        self.expect('empty_targets_recover_without_checkpoint_reset',self.query('select to_jsonb(t)::text from analytics.stg_field_event_winners t order by raw_record_id'),canonical)
        self.expect('empty_weather_target_recovery',self.query('select to_jsonb(t)::text from analytics.stg_weather_observation_winners t order by raw_record_id'),weather_canonical)
        self.expect('processing_empty_target_preserves_full_scan_evidence',self.query("select count(*) from ops.processing_scans where run_id=(select last_run_id from ops.processing_checkpoints where stream='field_events') and lower_bound is null"),[(2,)])
        self.native_checks()
        previous=self.published()
        with fixture_transaction() as conn:
            f.event(conn,'FUTURE_INGESTION',a,occurred=a,ingested=a+timedelta(days=1))
        self.fails('future_ingestion_metadata_blocks_release',self.release,message='future ingestion timestamps')
        self.expect('future_metadata_preserves_release',self.published(),previous)
        self.record('functional_suite_complete',detail={'native_sql_acceptance':not self.embedded,'full_bootstrap_acceptance':not self.embedded and not any(r['result']=='NOT RUN' for r in self.records) and any(r['name']=='powershell_existing_volume_rerun' for r in self.records)})


def docker_run():
    if not shutil.which('docker'):
        raise RuntimeError('Docker is unavailable; clean-volume native acceptance was not executed')
    project='agridax_acceptance_'+uuid.uuid4().hex[:12]
    with socket.socket() as reservation:
        reservation.bind(('127.0.0.1',0));port=reservation.getsockname()[1]
    from secrets import token_urlsafe
    with tempfile.TemporaryDirectory(prefix='agridax_acceptance_') as folder:
        env_file=Path(folder)/'.env'
        template=(PROJECT_ROOT/'.env.example').read_text().replace('POSTGRES_PORT=5432',f'POSTGRES_PORT={port}').replace('POSTGRES_DB=agridax','POSTGRES_DB='+project)
        for role in ['ADMIN','INGEST','DBT','PUBLISH','READER']: template=template.replace('REPLACE_'+role+'_PASSWORD',token_urlsafe(32))
        env_file.write_text(template);env_file.chmod(0o600)
        from dotenv import dotenv_values
        previous=dict(os.environ)
        os.environ.update({k:v for k,v in dotenv_values(env_file).items() if v is not None})
        os.environ['AGRIDAX_ENV_FILE']=str(env_file)
        compose=['docker','compose','--project-name',project,'--env-file',str(env_file),'-f',str(PROJECT_ROOT/'docker-compose.yml')]
        try:
            subprocess.run(compose+['config','--quiet'],check=True)
            subprocess.run(compose+['up','-d','--wait','--wait-timeout','120'],check=True)
            suite=Suite()
            shell=shutil.which('pwsh') or shutil.which('powershell')
            if shell:
                bootstrap=[shell,'-NoProfile','-ExecutionPolicy','Bypass','-File',str(PROJECT_ROOT/'scripts/bootstrap.ps1'),'-EnvironmentFile',str(env_file),'-ComposeProject',project,'-PythonExecutable',os.sys.executable]
                subprocess.run(bootstrap,check=True)
                suite.record('powershell_clean_volume_bootstrap')
                subprocess.run(bootstrap,check=True)
                suite.record('powershell_existing_volume_rerun')
            else:
                suite.record('powershell_bootstrap','NOT RUN','PowerShell executable unavailable; Python native path is tested separately')
            suite.run()
            if any(record['result']=='NOT RUN' for record in suite.records):
                raise RuntimeError('Full Docker/PowerShell acceptance is incomplete; inspect acceptance_results.json')
        finally:
            subprocess.run(compose+['down','--volumes','--remove-orphans'],check=False)
            os.environ.clear();os.environ.update(previous)


def main():
    parser=argparse.ArgumentParser(description='Acceptance on an isolated disposable database; no Git actions')
    parser.add_argument('--docker',action='store_true',help='Create/test/remove only a uniquely named isolated Compose project/volume')
    parser.add_argument('--existing-disposable',action='store_true')
    parser.add_argument('--allow-reset',action='store_true',help='Explicitly reset schemas in the verified disposable database')
    parser.add_argument('--embedded-diagnostic',action='store_true',help='Selected SQL behavior only; never counts as native acceptance')
    args=parser.parse_args()
    if args.docker:
        if args.existing_disposable or args.embedded_diagnostic: parser.error('Docker mode cannot be combined with another mode')
        docker_run()
    elif args.existing_disposable and args.allow_reset:
        Suite(args.embedded_diagnostic).run()
    else:
        parser.error('Choose --docker or --existing-disposable --allow-reset')


if __name__=='__main__': main()
