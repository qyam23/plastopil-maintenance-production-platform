from .db import connection


def save_device(device_id, reporter_name, device_label, binding_token):
    with connection() as conn:
        existing = conn.execute("SELECT binding_token FROM reporter_devices WHERE device_id = ?", (device_id,)).fetchone()
        if existing and existing["binding_token"] and existing["binding_token"] != binding_token:
            raise PermissionError("המכשיר משויך להפעלה אחרת")
        conn.execute(
            """INSERT INTO reporter_devices (device_id, reporter_name, device_label, binding_token)
               VALUES (?, ?, ?, ?)
               ON CONFLICT(device_id) DO UPDATE SET reporter_name=excluded.reporter_name,
               device_label=excluded.device_label, updated_at=CURRENT_TIMESTAMP""",
            (device_id, reporter_name, device_label or None, binding_token),
        )


def get_device(device_id, binding_token):
    if not device_id or not binding_token:
        return None
    with connection() as conn:
        return conn.execute("SELECT * FROM reporter_devices WHERE device_id = ? AND binding_token = ?", (device_id, binding_token)).fetchone()
