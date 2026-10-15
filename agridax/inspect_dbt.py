"""Inspection commands with the same private dotenv/profile contract as releases."""
from __future__ import annotations

import argparse
import os
import subprocess
import uuid

from .config import PROJECT_ROOT, Settings, integer
from .pipeline import DBT_PROJECT, dbt_executable


def main() -> None:
    parser = argparse.ArgumentParser(description='dbt inspection; never establishes publication eligibility')
    parser.add_argument('command', choices=['debug', 'parse', 'compile', 'test', 'ls', 'source-freshness'])
    parser.add_argument('arguments', nargs=argparse.REMAINDER)
    args = parser.parse_args()
    forbidden = {'--profiles-dir', '--project-dir', '--target', '-t', '--profile',
                 '--target-path', '--log-path', '--store-failures', '--store-failures-as'}
    if any(value.split('=', 1)[0] in forbidden for value in args.arguments):
        parser.error('Profile/paths and failure materialization are controlled by the inspection wrapper')
    settings = Settings.load()
    settings.connection_params('dbt')
    integer('DBT_THREADS', 4, 1, 32)
    command = ['source', 'freshness'] if args.command == 'source-freshness' else [args.command]
    inspection = DBT_PROJECT / 'target/inspection' / str(uuid.uuid4())
    invocation = [dbt_executable(), *command, '--project-dir', str(DBT_PROJECT),
                  '--profiles-dir', str(DBT_PROJECT), '--target', 'dev',
                  '--log-path', str(DBT_PROJECT / 'logs/inspection')]
    if args.command != 'debug':
        invocation += ['--target-path', str(inspection)]
    env = dict(os.environ, DBT_SEND_ANONYMOUS_USAGE_STATS='false', DBT_STORE_FAILURES='false')
    completed = subprocess.run([*invocation, *args.arguments], cwd=PROJECT_ROOT, env=env, check=False)
    raise SystemExit(completed.returncode)


if __name__ == '__main__':
    main()
