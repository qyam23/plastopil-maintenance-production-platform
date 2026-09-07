"""Restore the local SQLite copy into an external PostgreSQL database.

Example (PowerShell):
  python scripts/restore_sqlite_to_postgres.py --database-url $env:DATABASE_URL

The script is deliberately idempotent: it never deletes from the destination
and can therefore be run again after a connection failure.
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

import psycopg

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.db import POSTGRES_SCHEMA  # noqa: E402


TABLES = (
    ("users", "id"),
    ("reporter_devices", "device_id"),
    ("location_qrcodes", "id"),
    ("reports", "id"),
    ("report_files", "id"),
    ("report_messages", "id"),
    ("push_subscriptions", "device_id"),
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Restore the local report database to PostgreSQL.")
    parser.add_argument("--database-url", required=True, help="Target PostgreSQL connection string (for example from Neon).")
    parser.add_argument("--source", type=Path, default=ROOT / "data" / "reports.db", help="SQLite source database path.")
    return parser.parse_args()


def create_schema(connection: psycopg.Connection) -> None:
    for statement in POSTGRES_SCHEMA:
        connection.execute(statement)
    for statement in (
        "ALTER TABLE reports ADD COLUMN IF NOT EXISTS public_token TEXT",
        "ALTER TABLE reports ADD COLUMN IF NOT EXISTS assigned_to TEXT",
        "ALTER TABLE reports ADD COLUMN IF NOT EXISTS reporter_device_label TEXT",
        "ALTER TABLE reports ADD COLUMN IF NOT EXISTS assigned_at TIMESTAMPTZ",
        "ALTER TABLE reports ADD COLUMN IF NOT EXISTS review_note TEXT",
        "ALTER TABLE reporter_devices ADD COLUMN IF NOT EXISTS binding_token TEXT",
        "CREATE INDEX IF NOT EXISTS idx_report_files_report_id ON report_files(report_id)",
        "CREATE INDEX IF NOT EXISTS idx_reports_status ON reports(status)",
        "CREATE INDEX IF NOT EXISTS idx_report_messages_report_id ON report_messages(report_id)",
    ):
        connection.execute(statement)


def source_columns(connection: sqlite3.Connection, table: str) -> list[str]:
    return [row[1] for row in connection.execute(f"PRAGMA table_info({table})")]


def target_columns(connection: psycopg.Connection, table: str) -> set[str]:
    return {
        row[0]
        for row in connection.execute(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_schema = 'public' AND table_name = %s",
            (table,),
        )
    }


def copy_table(source: sqlite3.Connection, target: psycopg.Connection, table: str, key: str) -> int:
    columns = [name for name in source_columns(source, table) if name in target_columns(target, table)]
    if not columns:
        return 0
    quoted_columns = ", ".join(columns)
    placeholders = ", ".join("%s" for _ in columns)
    statement = f"INSERT INTO {table} ({quoted_columns}) VALUES ({placeholders}) ON CONFLICT ({key}) DO NOTHING"
    count = 0
    for row in source.execute(f"SELECT {quoted_columns} FROM {table}"):
        target.execute(statement, tuple(row))
        count += 1
    return count


def reset_sequences(target: psycopg.Connection) -> None:
    for table in ("users", "location_qrcodes", "reports", "report_files", "report_messages"):
        target.execute(
            "SELECT setval(pg_get_serial_sequence(%s, 'id'), "
            "COALESCE((SELECT MAX(id) FROM " + table + "), 1), true)",
            (table,),
        )


def main() -> None:
    args = parse_args()
    if not args.source.is_file():
        raise SystemExit(f"SQLite source not found: {args.source}")
    with sqlite3.connect(args.source) as source, psycopg.connect(args.database_url) as target:
        create_schema(target)
        total = 0
        for table, key in TABLES:
            copied = copy_table(source, target, table, key)
            total += copied
            print(f"{table}: {copied} rows read")
        reset_sequences(target)
        target.commit()
    print(f"Restore complete: {total} rows read from {args.source.name}.")


if __name__ == "__main__":
    main()
