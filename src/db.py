import os
import re
import secrets
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from psycopg.rows import dict_row
import psycopg

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "reports.db"


class DatabaseConnection:
    """Small compatibility layer so local SQLite and Render Postgres use the same app code."""

    def __init__(self, raw, dialect):
        self.raw = raw
        self.dialect = dialect

    def execute(self, statement, parameters=()):
        if self.dialect == "postgres":
            statement = statement.replace("?", "%s")
        return self.raw.execute(statement, parameters)

    def commit(self):
        self.raw.commit()

    def rollback(self):
        self.raw.rollback()

    def close(self):
        self.raw.close()


def database_url():
    return os.getenv("DATABASE_URL", "").strip()


@contextmanager
def connection():
    url = database_url()
    if url:
        raw = psycopg.connect(url, row_factory=dict_row)
        conn = DatabaseConnection(raw, "postgres")
    else:
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        raw = sqlite3.connect(DB_PATH)
        raw.row_factory = sqlite3.Row
        raw.execute("PRAGMA foreign_keys = ON")
        conn = DatabaseConnection(raw, "sqlite")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


SQLITE_SCHEMA = [
    """CREATE TABLE IF NOT EXISTS reports (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      report_type TEXT NOT NULL, text_body TEXT,
      site TEXT, department TEXT, machine TEXT, location_code TEXT,
      status TEXT NOT NULL DEFAULT 'new', reporter_id TEXT, reporter_name TEXT,
      public_token TEXT, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
      updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    )""",
    """CREATE TABLE IF NOT EXISTS report_files (
      id INTEGER PRIMARY KEY AUTOINCREMENT, report_id INTEGER NOT NULL,
      file_type TEXT NOT NULL CHECK(file_type IN ('image','video','audio')),
      local_path TEXT NOT NULL, original_filename TEXT NOT NULL, mime_type TEXT,
      file_size INTEGER NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
      FOREIGN KEY(report_id) REFERENCES reports(id) ON DELETE CASCADE
    )""",
    """CREATE TABLE IF NOT EXISTS reporter_devices (
      device_id TEXT PRIMARY KEY, reporter_name TEXT NOT NULL, device_label TEXT,
      binding_token TEXT, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
      updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    )""",
    """CREATE TABLE IF NOT EXISTS report_messages (
      id INTEGER PRIMARY KEY AUTOINCREMENT, report_id INTEGER NOT NULL,
      author_name TEXT NOT NULL,
      author_role TEXT NOT NULL CHECK(author_role IN ('reporter','manager','technician')),
      body TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
      FOREIGN KEY(report_id) REFERENCES reports(id) ON DELETE CASCADE
    )""",
    """CREATE TABLE IF NOT EXISTS users (
      id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT NOT NULL UNIQUE,
      display_name TEXT NOT NULL, role TEXT NOT NULL CHECK(role IN ('manager','technician')),
      password_hash TEXT NOT NULL, active INTEGER NOT NULL DEFAULT 1,
      created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    )""",
    """CREATE TABLE IF NOT EXISTS location_qrcodes (
      id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, description TEXT,
      location_code TEXT NOT NULL UNIQUE, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    )""",
    """CREATE TABLE IF NOT EXISTS push_subscriptions (
      device_id TEXT PRIMARY KEY, subscription_json TEXT NOT NULL,
      created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
      updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    )""",
]

POSTGRES_SCHEMA = [
    """CREATE TABLE IF NOT EXISTS reports (
      id BIGSERIAL PRIMARY KEY, report_type TEXT NOT NULL, text_body TEXT,
      site TEXT, department TEXT, machine TEXT, location_code TEXT,
      status TEXT NOT NULL DEFAULT 'new', reporter_id TEXT, reporter_name TEXT,
      public_token TEXT, created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
      updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
      assigned_to TEXT, reporter_device_label TEXT, assigned_at TIMESTAMPTZ, review_note TEXT
    )""",
    """CREATE TABLE IF NOT EXISTS report_files (
      id BIGSERIAL PRIMARY KEY, report_id BIGINT NOT NULL REFERENCES reports(id) ON DELETE CASCADE,
      file_type TEXT NOT NULL CHECK(file_type IN ('image','video','audio')),
      local_path TEXT NOT NULL, original_filename TEXT NOT NULL, mime_type TEXT,
      file_size BIGINT NOT NULL, created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
    )""",
    """CREATE TABLE IF NOT EXISTS reporter_devices (
      device_id TEXT PRIMARY KEY, reporter_name TEXT NOT NULL, device_label TEXT,
      binding_token TEXT, created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
      updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
    )""",
    """CREATE TABLE IF NOT EXISTS report_messages (
      id BIGSERIAL PRIMARY KEY, report_id BIGINT NOT NULL REFERENCES reports(id) ON DELETE CASCADE,
      author_name TEXT NOT NULL,
      author_role TEXT NOT NULL CHECK(author_role IN ('reporter','manager','technician')),
      body TEXT NOT NULL, created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
    )""",
    """CREATE TABLE IF NOT EXISTS users (
      id BIGSERIAL PRIMARY KEY, username TEXT NOT NULL UNIQUE, display_name TEXT NOT NULL,
      role TEXT NOT NULL CHECK(role IN ('manager','technician')), password_hash TEXT NOT NULL,
      active INTEGER NOT NULL DEFAULT 1, created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
    )""",
    """CREATE TABLE IF NOT EXISTS location_qrcodes (
      id BIGSERIAL PRIMARY KEY, name TEXT NOT NULL, description TEXT,
      location_code TEXT NOT NULL UNIQUE, created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
    )""",
    """CREATE TABLE IF NOT EXISTS push_subscriptions (
      device_id TEXT PRIMARY KEY, subscription_json TEXT NOT NULL,
      created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
      updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
    )""",
]


def _ensure_sqlite_column(conn, table, column, definition):
    columns = {row["name"] for row in conn.execute(f"PRAGMA table_info({table})")}
    if column not in columns:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def init_db():
    with connection() as conn:
        for statement in POSTGRES_SCHEMA if conn.dialect == "postgres" else SQLITE_SCHEMA:
            conn.execute(statement)
        for statement in (
            "CREATE INDEX IF NOT EXISTS idx_report_files_report_id ON report_files(report_id)",
            "CREATE INDEX IF NOT EXISTS idx_reports_status ON reports(status)",
            "CREATE INDEX IF NOT EXISTS idx_report_messages_report_id ON report_messages(report_id)",
        ):
            conn.execute(statement)
        if conn.dialect == "sqlite":
            for column, definition in (
                ("public_token", "TEXT"), ("assigned_to", "TEXT"),
                ("reporter_device_label", "TEXT"), ("assigned_at", "TEXT"),
                ("review_note", "TEXT"),
            ):
                _ensure_sqlite_column(conn, "reports", column, definition)
            _ensure_sqlite_column(conn, "reporter_devices", "binding_token", "TEXT")
        else:
            for statement in (
                "ALTER TABLE reports ADD COLUMN IF NOT EXISTS public_token TEXT",
                "ALTER TABLE reports ADD COLUMN IF NOT EXISTS assigned_to TEXT",
                "ALTER TABLE reports ADD COLUMN IF NOT EXISTS reporter_device_label TEXT",
                "ALTER TABLE reports ADD COLUMN IF NOT EXISTS assigned_at TIMESTAMPTZ",
                "ALTER TABLE reports ADD COLUMN IF NOT EXISTS review_note TEXT",
                "ALTER TABLE reporter_devices ADD COLUMN IF NOT EXISTS binding_token TEXT",
            ):
                conn.execute(statement)
        for row in conn.execute("SELECT device_id FROM reporter_devices WHERE binding_token IS NULL OR binding_token = ''"):
            conn.execute("UPDATE reporter_devices SET binding_token = ? WHERE device_id = ?", (secrets.token_urlsafe(24), row["device_id"]))
        for row in conn.execute("SELECT id FROM reports WHERE public_token IS NULL OR public_token = ''"):
            conn.execute("UPDATE reports SET public_token = ? WHERE id = ?", (secrets.token_urlsafe(24), row["id"]))
        # Repair reports submitted by earlier scanner versions that saved the
        # compact QR URL itself instead of the QR location code.
        for report in conn.execute("SELECT id, location_code FROM reports WHERE location_code LIKE ?", ("http%",)):
            raw = report["location_code"]
            try:
                parsed = urlparse(raw)
                match = re.fullmatch(r"/q/(\d+)", parsed.path)
                if match:
                    location = conn.execute("SELECT name, description, location_code FROM location_qrcodes WHERE id = ?", (int(match.group(1)),)).fetchone()
                    if location:
                        conn.execute(
                            "UPDATE reports SET location_code = ?, site = ?, department = ?, machine = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                            (location["location_code"], "PLASTOPIL", location["description"] or "מיקום שנסרק ב־QR", location["name"], report["id"]),
                        )
                        continue
                location_code = parse_qs(parsed.query).get("location", [""])[0].strip()
                if location_code:
                    conn.execute("UPDATE reports SET location_code = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (location_code, report["id"]))
            except ValueError:
                continue
