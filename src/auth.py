import os
from werkzeug.security import check_password_hash, generate_password_hash
from .db import connection


def seed_initial_users():
    users = [
        (os.getenv("ADMIN_USERNAME", ""), os.getenv("ADMIN_DISPLAY_NAME", ""), "manager", os.getenv("ADMIN_PASSWORD", "")),
        (os.getenv("TECHNICIAN_USERNAME", ""), os.getenv("TECHNICIAN_DISPLAY_NAME", ""), "technician", os.getenv("TECHNICIAN_PASSWORD", "")),
    ]
    with connection() as conn:
        for username, display_name, role, password in users:
            if username and display_name and password:
                exists = conn.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone()
                if not exists:
                    conn.execute("INSERT INTO users (username, display_name, role, password_hash) VALUES (?, ?, ?, ?)",
                                 (username, display_name, role, generate_password_hash(password)))


def authenticate(username, password):
    with connection() as conn:
        user = conn.execute("SELECT * FROM users WHERE username = ? AND active = 1", (username,)).fetchone()
    return user if user and check_password_hash(user["password_hash"], password) else None


def get_user(user_id):
    with connection() as conn:
        return conn.execute("SELECT * FROM users WHERE id = ? AND active = 1", (user_id,)).fetchone()
