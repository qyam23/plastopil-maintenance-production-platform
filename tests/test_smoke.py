import io
import os
import sys
import uuid
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("SECRET_KEY", "test-only-secret-key")
import app as application


DEVICE = {"device_id":f"test-device-{uuid.uuid4()}", "reporter_name":"ישראל ישראלי", "device_label":"טלפון בדיקה"}


def token_from(location):
    return parse_qs(urlparse(location).query)["token"][0]


def run():
    client = application.app.test_client()
    for path in ("/", "/start", "/scan", "/report/new", "/report/new?location=PLASTOPIL-EXTRUSION-LINE14"):
        assert client.get(path).status_code == 200, path
    assert "ללא מיקום מזוהה" in client.get("/report/new?location=UNKNOWN").get_data(as_text=True)
    assert client.post("/api/reporter-devices", json=DEVICE).status_code == 200
    attacker = application.app.test_client()
    assert attacker.post("/api/reporter-devices", json=DEVICE).status_code == 403
    missing = client.post("/report/new", data={"report_type":"maintenance_request", "device_id":DEVICE["device_id"]}, follow_redirects=False)
    assert missing.status_code == 302
    response = client.post("/report/new", data={"report_type":"maintenance_request", "text_body":"בדיקת תקלה", "device_id":DEVICE["device_id"]}, follow_redirects=False)
    assert response.status_code == 302 and "/report/success/" in response.headers["Location"]
    report_id = int(urlparse(response.headers["Location"]).path.rsplit("/", 1)[1]); token = token_from(response.headers["Location"])
    assert client.get(f"/report/{report_id}").status_code == 404
    assert client.get(f"/report/{report_id}?token={token}").status_code == 200
    named = client.post("/report/new", data={"report_type":"safety_near_miss", "text_body":"בדיקת בטיחות", "device_id":DEVICE["device_id"]}, follow_redirects=False)
    named_id = int(urlparse(named.headers["Location"]).path.rsplit("/", 1)[1]); report, _ = application.get_report(named_id)
    assert report["reporter_name"] == "ישראל ישראלי" and report["public_token"]
    photo = client.post("/report/new", data={"report_type":"safety_near_miss", "device_id":DEVICE["device_id"], "attachments":(io.BytesIO(b"\xff\xd8\xff\xe0test-image"), "photo.jpg")}, content_type="multipart/form-data")
    assert photo.status_code == 302
    rejected = client.post("/report/new", data={"report_type":"safety_near_miss", "device_id":DEVICE["device_id"], "attachments":(io.BytesIO(b"not an image"), "bad.jpg")}, content_type="multipart/form-data", follow_redirects=True)
    assert "תוכן הקובץ אינו תואם" in rejected.get_data(as_text=True)
    print("Smoke tests passed")


if __name__ == "__main__": run()
