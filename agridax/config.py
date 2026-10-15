from __future__ import annotations

import argparse
import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ROLE_USERS = {
    "admin": "POSTGRES_USER",
    "ingest": "INGEST_USER",
    "dbt": "DBT_USER",
    "publish": "PUBLISH_USER",
    "reader": "READER_USER",
}
ROLE_PASSWORDS = {
    "admin": "POSTGRES_PASSWORD",
    "ingest": "INGEST_PASSWORD",
    "dbt": "DBT_ENV_SECRET_PASSWORD",
    "publish": "PUBLISH_PASSWORD",
    "reader": "READER_PASSWORD",
}
DEFAULT_USERS = {
    "admin": "agridax_admin", "ingest": "agridax_ingest",
    "dbt": "agridax_transform", "publish": "agridax_publish",
    "reader": "agridax_reader",
}


class ConfigurationError(ValueError):
    pass


def load_environment() -> Path:
    """Process environment wins, including empty values (which validation rejects)."""
    path = Path(os.environ.get("AGRIDAX_ENV_FILE", PROJECT_ROOT / ".env"))
    load_dotenv(path, override=False, encoding="utf-8")
    return path


def required(name: str, default: str | None = None) -> str:
    value = os.environ.get(name, default)
    if value is None or not value.strip():
        raise ConfigurationError(f"Missing or empty configuration: {name}")
    return value


def integer(name: str, default: int, minimum: int, maximum: int) -> int:
    value = required(name, str(default))
    if not value.isascii() or not value.isdecimal():
        raise ConfigurationError(f"{name} must be an integer")
    number = int(value)
    if not minimum <= number <= maximum:
        raise ConfigurationError(f"{name} must be between {minimum} and {maximum}")
    return number


@dataclass(frozen=True)
class Settings:
    host: str
    port: int
    database: str
    connect_timeout: int
    lock_timeout_seconds: int
    statement_timeout_seconds: int
    lookback_seconds: int

    @classmethod
    def load(cls) -> "Settings":
        load_environment()
        return cls(
            host=required("POSTGRES_HOST", "127.0.0.1"),
            port=integer("POSTGRES_PORT", 5432, 1, 65535),
            database=required("POSTGRES_DB", "agridax"),
            connect_timeout=integer("CONNECT_TIMEOUT_SECONDS", 5, 1, 30),
            lock_timeout_seconds=integer("LOCK_TIMEOUT_SECONDS", 10, 1, 120),
            statement_timeout_seconds=integer("STATEMENT_TIMEOUT_SECONDS", 300, 1, 3600),
            lookback_seconds=integer("INGESTION_LOOKBACK_SECONDS", 300, 0, 86400),
        )

    def credentials(self, role: str) -> tuple[str, str]:
        if role not in ROLE_USERS:
            raise ConfigurationError(f"Unknown role: {role}")
        user = required(ROLE_USERS[role], DEFAULT_USERS[role])
        password = required(ROLE_PASSWORDS[role])
        if password.lower() in {"change_me", "changeme", "password"} or password.upper().startswith("REPLACE_"):
            raise ConfigurationError(f"Replace the example value for {ROLE_PASSWORDS[role]}")
        return user, password

    def connection_params(self, role: str = "ingest") -> dict:
        user, password = self.credentials(role)
        return {
            "host": self.host, "port": self.port, "dbname": self.database,
            "user": user, "password": password, "connect_timeout": self.connect_timeout,
            "options": "-c timezone=UTC", "application_name": f"agridax_{role}",
        }

    def validate_all(self) -> None:
        integer("DBT_THREADS",4,1,32)
        users = [self.credentials(role)[0] for role in ROLE_USERS]
        if len(set(users)) != len(users):
            raise ConfigurationError("Admin and workload roles must have distinct users")
        for user in users:
            if len(user.encode("utf-8")) > 63:
                raise ConfigurationError("PostgreSQL role names must fit 63 bytes")


def get_connection_params(role: str = "ingest") -> dict:
    return Settings.load().connection_params(role)


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate configuration without printing secrets")
    parser.parse_args()
    settings = Settings.load()
    settings.validate_all()
    print("Configuration valid; secrets omitted.")


if __name__ == "__main__":
    main()
