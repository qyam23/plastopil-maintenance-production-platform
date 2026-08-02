import json
import os

from pywebpush import WebPushException, webpush
from requests import RequestException

from .db import connection


def vapid_public_key():
    return os.getenv("VAPID_PUBLIC_KEY", "").strip()


def push_enabled():
    return bool(vapid_public_key() and os.getenv("VAPID_PRIVATE_KEY", "").strip() and os.getenv("VAPID_SUBJECT", "").strip())


def save_subscription(device_id, subscription):
    endpoint = str(subscription.get("endpoint", ""))
    keys = subscription.get("keys") or {}
    if not endpoint.startswith("https://") or not keys.get("p256dh") or not keys.get("auth"):
        raise ValueError("Invalid push subscription")
    serialized = json.dumps(subscription, separators=(",", ":"))
    with connection() as conn:
        conn.execute(
            """INSERT INTO push_subscriptions (device_id, subscription_json) VALUES (?, ?)
               ON CONFLICT(device_id) DO UPDATE SET subscription_json=excluded.subscription_json,
               updated_at=CURRENT_TIMESTAMP""",
            (device_id, serialized),
        )


def notify_reporter(report, title, body):
    """Best-effort Web Push; a failed subscription must not block workflow."""
    if not push_enabled() or not report or not report["reporter_id"]:
        return 0
    with connection() as conn:
        row = conn.execute("SELECT subscription_json FROM push_subscriptions WHERE device_id = ?", (report["reporter_id"],)).fetchone()
    if not row:
        return 0
    payload = json.dumps({
        "title": title,
        "body": body,
        "url": f"/report/{report['id']}?token={report['public_token']}",
        "tag": f"report-{report['id']}",
    })
    try:
        webpush(
            subscription_info=json.loads(row["subscription_json"]), data=payload,
            vapid_private_key=os.environ["VAPID_PRIVATE_KEY"],
            vapid_claims={"sub": os.environ["VAPID_SUBJECT"]},
        )
        return 1
    except (WebPushException, RequestException, ValueError, KeyError, json.JSONDecodeError):
        with connection() as conn:
            conn.execute("DELETE FROM push_subscriptions WHERE device_id = ?", (report["reporter_id"],))
        return 0
