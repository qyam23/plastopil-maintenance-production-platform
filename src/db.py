import secrets
import sqlite3
from contextlib import contextmanager
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "reports.db"


@contextmanager
def connection():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _ensure_column(conn, table, column, definition):
    columns = {row["name"] for row in conn.execute(f"PRAGMA table_info({table})")}
    if column not in columns:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def init_db():
    with connection() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS reports (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          report_type TEXT NOT NULL,
          text_body TEXT,
          site TEXT, department TEXT, machine TEXT, location_code TEXT,
          status TEXT NOT NULL DEFAULT 'new',
          reporter_id TEXT, reporter_name TEXT,
          public_token TEXT,
          created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
          updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS report_files (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          report_id INTEGER NOT NULL,
          file_type TEXT NOT NULL CHECK(file_type IN ('image','video','audio')),
          local_path TEXT NOT NULL, original_filename TEXT NOT NULL,
          mime_type TEXT, file_size INTEGER NOT NULL,
          created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
          FOREIGN KEY(report_id) REFERENCES reports(id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS reporter_devices (
          device_id TEXT PRIMARY KEY,
          reporter_name TEXT NOT NULL, device_label TEXT,
          binding_token TEXT,
          created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
          updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS report_messages (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          report_id INTEGER NOT NULL,
          author_name TEXT NOT NULL,
          author_role TEXT NOT NULL CHECK(author_role IN ('reporter','manager','technician')),
          body TEXT NOT NULL,
          created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
          FOREIGN KEY(report_id) REFERENCES reports(id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS users (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          username TEXT NOT NULL UNIQUE,
          display_name TEXT NOT NULL,
          role TEXT NOT NULL CHECK(role IN ('manager','technician')),
          password_hash TEXT NOT NULL,
          active INTEGER NOT NULL DEFAULT 1,
          created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS location_qrcodes (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          name TEXT NOT NULL,
          description TEXT,
          location_code TEXT NOT NULL UNIQUE,
          created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_report_files_report_id ON report_files(report_id);
        CREATE INDEX IF NOT EXISTS idx_reports_status ON reports(status);
        CREATE INDEX IF NOT EXISTS idx_report_messages_report_id ON report_messages(report_id);
        """)
        _ensure_column(conn, "reports", "public_token", "TEXT")
        _ensure_column(conn, "reports", "assigned_to", "TEXT")
        _ensure_column(conn, "reports", "reporter_device_label", "TEXT")
        _ensure_column(conn, "reports", "assigned_at", "TEXT")
        _ensure_column(conn, "reports", "review_note", "TEXT")
        _ensure_column(conn, "reporter_devices", "binding_token", "TEXT")
        for row in conn.execute("SELECT device_id FROM reporter_devices WHERE binding_token IS NULL OR binding_token = ''"):
            conn.execute("UPDATE reporter_devices SET binding_token = ? WHERE device_id = ?", (secrets.token_urlsafe(24), row["device_id"]))
        for row in conn.execute("SELECT id FROM reports WHERE public_token IS NULL OR public_token = ''"):
            conn.execute("UPDATE reports SET public_token = ? WHERE id = ?", (secrets.token_urlsafe(24), row["id"]))
