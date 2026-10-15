import os
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from agridax.config import ConfigurationError, Settings, load_environment
from agridax.time_contract import backfill_range, parse_timestamp
from agridax.preflight import inspect_content
from agridax.database import single_writer
from agridax.publication import CommitOutcomeUnknown
import psycopg


class BackfillTests(unittest.TestCase):
    def test_valid_utc(self):
        lower,upper=backfill_range('2026-01-01T00:00:00Z','2026-01-02T00:00:00+00:00')
        self.assertEqual(lower,datetime(2026,1,1,tzinfo=timezone.utc))
        self.assertEqual((upper-lower).days,1)

    def test_valid_non_utc(self):
        lower,upper=backfill_range('2026-01-01T09:00:00-03:00','2026-01-01T13:30:00+01:00')
        self.assertEqual(lower.hour,12)
        self.assertEqual((upper-lower).total_seconds(),1800)

    def test_reject_ranges(self):
        a='2026-01-01T00:00:00Z';b='2026-01-02T00:00:00Z'
        for kwargs in [(a,a,False),(b,a,False),(a,None,False),(None,b,False),(a,b,True)]:
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError): backfill_range(*kwargs)

    def test_reject_calendar_timezone_and_sql(self):
        for value in ['not-a-timestamp','2026-01-01T00:00:00','2026-02-30T00:00:00Z',"2026-01-01T00:00:00Z'; select 1; --",'2026-01-01T00:00:00.1234567Z','2026-01-01T00:00:00+24:00']:
            with self.subTest(value=value), self.assertRaises(ValueError): parse_timestamp(value)


class ConfigurationTests(unittest.TestCase):
    def test_quoted_values_and_process_precedence(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'.env'
            path.write_text('POSTGRES_PASSWORD="quoted # value"\nPOSTGRES_HOST=file-host\n')
            with patch.dict(os.environ,{'AGRIDAX_ENV_FILE':str(path),'POSTGRES_HOST':'process-host'},clear=True):
                load_environment()
                self.assertEqual(os.environ['POSTGRES_PASSWORD'],'quoted # value')
                self.assertEqual(Settings.load().host,'process-host')

    def test_empty_process_value_does_not_fall_back(self):
        with patch.dict(os.environ,{'AGRIDAX_ENV_FILE':'/nonexistent','POSTGRES_HOST':''},clear=True):
            with self.assertRaises(ConfigurationError): Settings.load()

    def test_ports(self):
        for value in ['0','65536','abc','-1',' 5432 ','']:
            with patch.dict(os.environ,{'AGRIDAX_ENV_FILE':'/nonexistent','POSTGRES_PORT':value},clear=True):
                with self.subTest(value=value),self.assertRaises(ConfigurationError): Settings.load()

    def test_secret_detection_does_not_print_values(self):
        issues=inspect_content('private.cfg',b'POSTGRES_PASSWORD=unit_test_literal\n')
        self.assertTrue(issues)
        self.assertNotIn('unit_test_literal','\n'.join(issues))
        self.assertEqual(inspect_content('.env.example',b'POSTGRES_PASSWORD=REPLACE_ADMIN_PASSWORD\n'),[])


class FailureReportingTests(unittest.TestCase):
    def test_lock_cleanup_preserves_commit_uncertainty(self):
        class BrokenCleanup:
            closed=False
            broken=False
            def execute(self,query,params):
                if 'unlock' in query:
                    raise psycopg.OperationalError('Injected connection loss during cleanup')
                return self
            def fetchone(self):
                return (True,)
            def close(self):
                self.closed=True
        connection=BrokenCleanup()
        with self.assertRaises(CommitOutcomeUnknown):
            with single_writer(connection):
                raise CommitOutcomeUnknown('Injected unknown COMMIT result')
        self.assertTrue(connection.closed)


if __name__=='__main__': unittest.main()
