import secrets
from .db import connection


def create_report(report_type, text_body, location_code=None, location=None, reporter=None):
    location = location or {}
    reporter = reporter or {}
    token = secrets.token_urlsafe(24)
    with connection() as conn:
        query = """INSERT INTO reports (report_type, text_body, site, department, machine, location_code, reporter_id, reporter_name, reporter_device_label, public_token)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"""
        if conn.dialect == "postgres":
            query += " RETURNING id"
        cursor = conn.execute(
            query,
            (report_type, text_body, location.get("site"), location.get("department"), location.get("machine"),
             location_code, reporter.get("device_id"), reporter.get("reporter_name"), reporter.get("device_label"), token),
        )
        return cursor.fetchone()["id"] if conn.dialect == "postgres" else cursor.lastrowid


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


def list_reports(status=None):
    with connection() as conn:
        if status and status != "all":
            return conn.execute("SELECT * FROM reports WHERE status = ? ORDER BY created_at DESC", (status,)).fetchall()
        return conn.execute("SELECT * FROM reports ORDER BY created_at DESC").fetchall()


def update_report_workflow(report_id, status, assigned_to, review_note):
    with connection() as conn:
        conn.execute(
            """UPDATE reports SET status=?, assigned_to=?, assigned_at=CASE WHEN ? <> '' THEN CURRENT_TIMESTAMP ELSE assigned_at END,
               review_note=?, updated_at=CURRENT_TIMESTAMP WHERE id=?""",
            (status, assigned_to, assigned_to, review_note, report_id),
        )


def get_messages(report_id):
    with connection() as conn:
        return conn.execute("SELECT * FROM report_messages WHERE report_id = ? ORDER BY created_at", (report_id,)).fetchall()


def add_message(report_id, author_name, author_role, body):
    with connection() as conn:
        conn.execute("INSERT INTO report_messages (report_id, author_name, author_role, body) VALUES (?, ?, ?, ?)",
                     (report_id, author_name, author_role, body))
    if author_role in {"manager", "technician"}:
        from .push_notifications import notify_reporter
        report, _ = get_report(report_id)
        notify_reporter(report, "PLASTOPIL — עדכון לקריאה", f"יש עדכון חדש לקריאה #{report_id}.")
