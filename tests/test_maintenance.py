"""Run maintenance workflow against an isolated local database, not user data."""
import os
import sys
import tempfile
import io
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ["DATABASE_URL"] = ""
os.environ["SECRET_KEY"] = "test-maintenance-secret"
os.environ["ADMIN_USERNAME"] = "test_manager"
os.environ["ADMIN_DISPLAY_NAME"] = "Test Manager"
os.environ["ADMIN_PASSWORD"] = "maintenance-test-manager"
os.environ["TECHNICIAN_USERNAME"] = "test_technician"
os.environ["TECHNICIAN_DISPLAY_NAME"] = "Test Technician"
os.environ["TECHNICIAN_PASSWORD"] = "maintenance-test-technician"

import src.db as db

tmp = tempfile.TemporaryDirectory()
db.DB_PATH = Path(tmp.name) / "reports.db"
import app as application
from src.reports import get_report


def run():
    worker = application.app.test_client()
    manager = application.app.test_client()
    technician = application.app.test_client()
    device = {"device_id": "isolated-maintenance-device", "reporter_name": "Test Worker", "device_label": "Test phone"}
    assert worker.post("/api/reporter-devices", json=device).status_code == 200
    submitted = worker.post("/report/new", data={"report_type": "maintenance_request", "text_body": "Gear motor makes noise", "device_id": device["device_id"]})
    assert submitted.status_code == 302
    report_id = int(urlparse(submitted.headers["Location"]).path.rsplit("/", 1)[1])
    token = parse_qs(urlparse(submitted.headers["Location"]).query)["token"][0]
    assert manager.post("/login", data={"username": "test_manager", "password": "maintenance-test-manager"}).status_code == 302
    assert technician.post("/login", data={"username": "test_technician", "password": "maintenance-test-technician"}).status_code == 302
    assert manager.get("/manage/journal").status_code == 200
    assert manager.get("/manage/maintenance-dashboard").status_code == 200
    assert technician.get("/manage/maintenance-dashboard").status_code == 403
    assert technician.get(f"/manage/report/{report_id}").status_code == 403
    assert manager.post(f"/manage/report/{report_id}/workflow", data={"status": "assigned", "assigned_to": "Test Technician", "review_note": "Check motor"}).status_code == 302
    assert technician.get(f"/manage/report/{report_id}").status_code == 200
    assert technician.post(f"/manage/report/{report_id}/workflow", data={"status": "resolved"}).status_code == 403
    assert technician.post(f"/manage/report/{report_id}/archive").status_code == 403
    action = technician.post(f"/manage/report/{report_id}/actions", data={"outcome": "waiting_parts", "work_done": "Checked the gearbox and found a worn gear", "parts": "Replacement gear", "knowledge_note": "Check motor coupling first", "root_cause": "Worn gear", "work_attachments": (io.BytesIO(b"\xff\xd8\xff\xe0test-work-image"), "repair.jpg")}, content_type="multipart/form-data")
    assert action.status_code == 302
    assert "Check motor coupling first" in technician.get("/manage/knowledge").get_data(as_text=True)
    assert "Replacement gear" in technician.get(f"/manage/report/{report_id}").get_data(as_text=True)
    assert "מצורף לעבודה: repair.jpg" in technician.get(f"/manage/report/{report_id}").get_data(as_text=True)
    assert manager.get("/manage/maintenance-dashboard").get_data(as_text=True).count("פתוחות שממתינות לחלפים") == 1
    assert technician.post(f"/manage/report/{report_id}/discussion", data={"body": "Check voltage before restart"}).status_code == 302
    assert "Check voltage before restart" in technician.get(f"/manage/report/{report_id}").get_data(as_text=True)
    assert "Check voltage before restart" not in worker.get(f"/report/{report_id}?token={token}").get_data(as_text=True)
    assert manager.get(f"/manage/report/{report_id}/case").status_code == 200
    receipt = manager.post(f"/manage/report/{report_id}/case/receipt", data={"action": "view"})
    assert receipt.status_code == 200 and receipt.get_json()["viewed_at"]
    receipt = manager.post(f"/manage/report/{report_id}/case/receipt", data={"action": "acknowledge"})
    assert receipt.status_code == 200 and receipt.get_json()["acknowledged_at"]
    assert technician.post(f"/manage/report/{report_id}/archive").status_code == 403
    assert manager.post(f"/manage/report/{report_id}/archive").status_code == 302
    assert not get_report(report_id)[0]["archived_at"]
    assert manager.post(f"/manage/report/{report_id}/workflow", data={"status": "resolved", "assigned_to": "Test Technician", "review_note": "Closed after final test"}).status_code == 302
    assert manager.post(f"/manage/report/{report_id}/archive").status_code == 302
    assert get_report(report_id)[0]["archived_at"]
    assert f"קריאה #{report_id}" not in manager.get("/manage/journal").get_data(as_text=True)
    assert manager.post(f"/manage/report/{report_id}/restore").status_code == 302
    assert not get_report(report_id)[0]["archived_at"]
    assert f"קריאה #{report_id}" in manager.get("/manage/journal").get_data(as_text=True)
    print("Maintenance tests passed")


if __name__ == "__main__":
    try: run()
    finally: tmp.cleanup()
