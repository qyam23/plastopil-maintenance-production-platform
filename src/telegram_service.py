import logging
import os
import requests

TYPE_META = {
    "safety_near_miss": ("⚠️", "דיווח בטיחות חדש"),
    "maintenance_request": ("🔧", "קריאת אחזקה חדשה"),
    "process_quality": ("📊", "דיווח איכות / תהליך חדש"),
}


def notify(report):
    if os.getenv("TELEGRAM_ENABLED", "0") != "1":
        return False
    token, chat_id = os.getenv("TELEGRAM_BOT_TOKEN"), os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        logging.warning("Telegram is enabled but credentials are missing")
        return False
    icon, title = TYPE_META.get(report["report_type"], ("📣", "דיווח חדש"))
    base_url = os.getenv("PUBLIC_BASE_URL", "").rstrip("/")
    location = "\n".join(part for part in [report["site"], report["department"], report["machine"]] if part)
    reporter_line = ""
    if report["report_type"] == "safety_near_miss" and report["reporter_name"]:
        reporter_line = f"\n👤 מדווח: {report['reporter_name']}"
    text = f"{icon} {title}\n\n📍 {location or 'ללא מיקום מזוהה'}{reporter_line}\n🕒 {report['created_at']}\n\n📝 {report['text_body'] or 'ללא טקסט'}"
    payload = {"chat_id": chat_id, "text": text}
    if base_url:
        payload["reply_markup"] = {"inline_keyboard": [[{"text": "פתח קריאה", "url": f"{base_url}/report/{report['id']}?token={report['public_token']}"}]]}
    try:
        response = requests.post(f"https://api.telegram.org/bot{token}/sendMessage", json=payload, timeout=10)
        response.raise_for_status()
        return True
    except requests.RequestException:
        logging.exception("Telegram notification failed for report %s", report["id"])
        return False
