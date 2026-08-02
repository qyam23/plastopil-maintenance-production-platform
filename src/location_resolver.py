import json
from pathlib import Path

CONFIG_FILE = Path(__file__).resolve().parent.parent / "config" / "locations.json"


def resolve_location(code):
    """Return a mapped machine location or None for an unknown QR code."""
    if not code:
        return None
    with CONFIG_FILE.open(encoding="utf-8") as file:
        return json.load(file).get(code.strip())
