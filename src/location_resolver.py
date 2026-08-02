import json
from pathlib import Path
from urllib.parse import parse_qs, urlparse
from .db import connection

CONFIG_FILE = Path(__file__).resolve().parent.parent / "config" / "locations.json"


def normalize_location_code(code):
    """Turn a scanned managed QR URL into its stored location code."""
    if not code:
        return ""
    normalized = code.strip()
    try:
        parsed = urlparse(normalized)
        qr_id = parsed.path.removeprefix("/q/") if parsed.path.startswith("/q/") else ""
        if qr_id.isdigit():
            with connection() as conn:
                record = conn.execute("SELECT location_code FROM location_qrcodes WHERE id = ?", (int(qr_id),)).fetchone()
            if record:
                return record["location_code"]
        embedded_location = parse_qs(parsed.query).get("location", [""])[0]
        if embedded_location:
            return embedded_location.strip()
    except ValueError:
        pass
    return normalized


def resolve_location(code):
    """Return a configured or manager-created QR location."""
    normalized = normalize_location_code(code)
    if not normalized:
        return None
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
