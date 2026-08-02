import json
from pathlib import Path
from .db import connection

CONFIG_FILE = Path(__file__).resolve().parent.parent / "config" / "locations.json"


def resolve_location(code):
    """Return a configured or manager-created QR location."""
    if not code:
        return None
    normalized = code.strip()
    with CONFIG_FILE.open(encoding="utf-8") as file:
        configured = json.load(file).get(normalized)
    if configured:
        return configured
    with connection() as conn:
        qr_location = conn.execute(
            "SELECT name, description FROM location_qrcodes WHERE location_code = ?",
            (normalized,),
        ).fetchone()
    if not qr_location:
        return None
    return {
        "site": "PLASTOPIL",
        "department": qr_location["description"] or "מיקום שנסרק ב־QR",
        "machine": qr_location["name"],
    }
