import secrets
from .db import connection


def create_report(report_type, text_body, location_code=None, location=None, reporter=None):
    location = location or {}
    reporter = reporter or {}
    token = secrets.token_urlsafe(24)
    with connection() as conn:
        cursor = conn.execute(
            """INSERT INTO reports (report_type, text_body, site, department, machine, location_code, reporter_id, reporter_name, public_token)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (report_type, text_body, location.get("site"), location.get("department"), location.get("machine"),
             location_code, reporter.get("device_id"), reporter.get("reporter_name"), token),
        )
        return cursor.lastrowid


def add_file(report_id, file_data):
    with connection() as conn:
        conn.execute("""INSERT INTO report_files (report_id, file_type, local_path, original_filename, mime_type, file_size)
                      VALUES (?, ?, ?, ?, ?, ?)""", (report_id, *file_data))


def get_report(report_id):
    with connection() as conn:
        report = conn.execute("SELECT * FROM reports WHERE id = ?", (report_id,)).fetchone()
        files = conn.execute("SELECT * FROM report_files WHERE report_id = ? ORDER BY id", (report_id,)).fetchall()
    return report, files


def get_report_file(report_id, file_id):
    with connection() as conn:
        return conn.execute("SELECT * FROM report_files WHERE id = ? AND report_id = ?", (file_id, report_id)).fetchone()
