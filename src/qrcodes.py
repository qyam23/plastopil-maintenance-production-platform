from io import BytesIO
import qrcode
from qrcode.constants import ERROR_CORRECT_H
from .db import connection


def create_qrcode(name, description, location_code):
    with connection() as conn:
        query = "INSERT INTO location_qrcodes (name, description, location_code) VALUES (?, ?, ?)"
        if conn.dialect == "postgres":
            query += " RETURNING id"
        cursor = conn.execute(query,
                              (name, description or None, location_code))
        return cursor.fetchone()["id"] if conn.dialect == "postgres" else cursor.lastrowid


def list_qrcodes():
    with connection() as conn:
        return conn.execute("SELECT * FROM location_qrcodes ORDER BY created_at DESC").fetchall()


def get_qrcode(qr_id):
    with connection() as conn:
        return conn.execute("SELECT * FROM location_qrcodes WHERE id = ?", (qr_id,)).fetchone()


def make_qr_png(url):
    image = qrcode.make(url, error_correction=ERROR_CORRECT_H, box_size=12, border=4)
    output = BytesIO(); image.save(output, format="PNG"); output.seek(0)
    return output
