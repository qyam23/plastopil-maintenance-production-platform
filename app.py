import hmac
import os
import secrets
import time
from collections import defaultdict, deque
from functools import wraps
from pathlib import Path
from flask import Flask, abort, flash, jsonify, redirect, render_template, request, send_file, send_from_directory, session, url_for
from werkzeug.urls import urlsplit
from src.auth import authenticate, get_user, seed_initial_users
from src.qrcodes import create_qrcode, get_qrcode, list_qrcodes, make_qr_png
from dotenv import load_dotenv
from src.db import init_db
from src.location_resolver import resolve_location
from src.reporter_devices import get_device, save_device
from src.reports import add_file, add_message, create_report, get_messages, get_report, get_report_file, list_reports, update_report_workflow
from src.storage import delete_stored, save_upload, validate_upload
from src.telegram_service import notify

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")
app = Flask(__name__)
secret_key = os.getenv("SECRET_KEY")
if not secret_key:
    raise RuntimeError("SECRET_KEY must be set in .env before starting the server")
app.config["SECRET_KEY"] = secret_key
app.config["MAX_CONTENT_LENGTH"] = int(os.getenv("MAX_CONTENT_LENGTH", 52428800))
init_db()
seed_initial_users()

REPORT_TYPES = {"safety_near_miss", "maintenance_request", "process_quality"}
WORKFLOW_STATUSES = {"new", "reviewed", "assigned", "in_progress", "resolved"}
RATE_BUCKETS = defaultdict(deque)


def rate_limit(limit, seconds=60):
    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            key = f"{view.__name__}:{request.remote_addr or 'unknown'}"; now = time.monotonic(); bucket = RATE_BUCKETS[key]
            while bucket and bucket[0] <= now - seconds: bucket.popleft()
            if len(bucket) >= limit:
                return jsonify({"error": "יותר מדי בקשות. נסו שוב בעוד דקה."}), 429
            bucket.append(now)
            return view(*args, **kwargs)
        return wrapped
    return decorator


def staff_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        user = get_user(session.get("user_id"))
        if not user:
            return redirect(url_for("login", next=request.full_path))
        session["display_name"], session["role"] = user["display_name"], user["role"]
        return view(*args, **kwargs)
    return wrapped


def manager_required(view):
    @wraps(view)
    @staff_required
    def wrapped(*args, **kwargs):
        if session.get("role") != "manager": abort(403)
        return view(*args, **kwargs)
    return wrapped


def binding_token():
    if "device_binding" not in session:
        session["device_binding"] = secrets.token_urlsafe(24)
    return session["device_binding"]


def report_authorized(report):
    supplied = request.args.get("token", "")
    return bool(supplied and report and hmac.compare_digest(supplied, report["public_token"]))


@app.get("/")
def welcome(): return render_template("welcome.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user = authenticate(request.form.get("username", "").strip(), request.form.get("password", ""))
        if user:
            session.clear(); session["user_id"] = user["id"]; session["display_name"] = user["display_name"]; session["role"] = user["role"]
            destination = request.form.get("next", "")
            if destination.startswith("/") and not destination.startswith("//"):
                return redirect(destination)
            return redirect(url_for("manage_dashboard"))
        flash("שם משתמש או סיסמה אינם נכונים", "error")
    return render_template("login.html", next=request.args.get("next", ""))


@app.post("/logout")
def logout():
    session.clear()
    return redirect(url_for("welcome"))

@app.get("/start")
def start(): return render_template("start.html")

@app.get("/scan")
def scan(): return render_template("scan.html")

@app.get("/report/new")
def report_new():
    code = request.args.get("location", "").strip()
    return render_template("report_form.html", location_code=code, location=resolve_location(code) if code else None)


@app.post("/api/reporter-devices")
@rate_limit(12)
def reporter_device_save():
    payload = request.get_json(silent=True) or {}
    device_id = str(payload.get("device_id", "")).strip(); reporter_name = str(payload.get("reporter_name", "")).strip(); device_label = str(payload.get("device_label", "")).strip()
    if not (8 <= len(device_id) <= 80 and 2 <= len(reporter_name) <= 80 and len(device_label) <= 80):
        return jsonify({"error": "פרטי המדווח אינם תקינים"}), 400
    try: save_device(device_id, reporter_name, device_label, binding_token())
    except PermissionError: return jsonify({"error": "המכשיר משויך להפעלה אחרת. הזינו זיהוי חדש."}), 403
    return jsonify({"device_id": device_id, "reporter_name": reporter_name, "device_label": device_label})


@app.post("/report/new")
@rate_limit(20)
def report_create():
    report_type = request.form.get("report_type", "")
    code = request.form.get("location_code", "").strip(); text_body = request.form.get("text_body", "").strip()
    uploads = [upload for upload in request.files.getlist("attachments") if upload and upload.filename]
    if report_type not in REPORT_TYPES:
        flash("יש לבחור סוג דיווח לפני השליחה", "error"); return redirect(url_for("report_new", location=code))
    if not text_body and not uploads:
        flash("יש להוסיף טקסט או קובץ אחד לפחות", "error"); return redirect(url_for("report_new", location=code))
    try:
        for upload in uploads: validate_upload(upload)
    except ValueError as error:
        flash(str(error), "error"); return redirect(url_for("report_new", location=code))
    reporter = get_device(request.form.get("device_id", "").strip(), binding_token())
    if not reporter:
        flash("יש לשמור את פרטי המדווח לפני שליחת דיווח", "error"); return redirect(url_for("report_new", location=code))
    report_id = create_report(report_type, text_body, code or None, resolve_location(code), dict(reporter))
    try:
        for upload in uploads:
            stored = save_upload(upload)
            try: add_file(report_id, stored)
            except Exception:
                delete_stored(stored[1]); raise
    except Exception:
        flash("לא הצלחנו לשמור את הקבצים. הדיווח נשמר ללא הקבצים שלא הושלמו.", "error")
    report, _ = get_report(report_id); notify(report)
    return redirect(url_for("report_success", report_id=report_id, token=report["public_token"]))


@app.get("/report/success/<int:report_id>")
def report_success(report_id):
    report, _ = get_report(report_id)
    if not report or not report_authorized(report): abort(404)
    return render_template("report_success.html", report_id=report_id, token=report["public_token"])


@app.get("/report/<int:report_id>")
def report_detail(report_id):
    report, files = get_report(report_id)
    if not report or not report_authorized(report): abort(404)
    return render_template("report_detail.html", report=report, files=files, messages=get_messages(report_id), token=report["public_token"])


@app.post("/report/<int:report_id>/messages")
def reporter_message(report_id):
    report, _ = get_report(report_id)
    if not report or not report_authorized(report): abort(404)
    body = request.form.get("body", "").strip()
    if 1 <= len(body) <= 1000:
        add_message(report_id, report["reporter_name"] or "מדווח", "reporter", body)
    return redirect(url_for("report_detail", report_id=report_id, token=report["public_token"]))


@app.get("/manage")
@staff_required
def manage_dashboard():
    reports = list_reports(request.args.get("status", "all"))
    if session.get("role") == "technician":
        reports = [report for report in reports if report["assigned_to"] == session.get("display_name")]
    return render_template("manage.html", reports=reports, active_status=request.args.get("status", "all"))


@app.route("/manage/qr", methods=["GET", "POST"])
@manager_required
def manage_qrcodes():
    if request.method == "POST":
        name = request.form.get("name", "").strip()[:120]
        description = request.form.get("description", "").strip()[:500]
        location_code = request.form.get("location_code", "").strip().upper()[:120]
        if not name or not location_code:
            flash("יש להזין שם וקוד מיקום", "error")
        else:
            try:
                create_qrcode(name, description, location_code)
                flash("קוד QR נוצר ומוכן להדפסה", "success")
                return redirect(url_for("manage_qrcodes"))
            except Exception:
                flash("קוד המיקום כבר קיים. בחרו קוד שונה", "error")
    return render_template("manage_qr.html", codes=list_qrcodes())


@app.get("/manage/qr/<int:qr_id>/image.png")
@staff_required
def qrcode_image(qr_id):
    record = get_qrcode(qr_id)
    if not record: abort(404)
    target = url_for("report_from_qr", qr_id=record["id"], _external=True)
    return send_file(make_qr_png(target), mimetype="image/png", download_name=f"{record['location_code']}.png")


@app.get("/q/<int:qr_id>")
def report_from_qr(qr_id):
    """Compact destination encoded in printable QR labels."""
    record = get_qrcode(qr_id)
    if not record: abort(404)
    return redirect(url_for("report_new", location=record["location_code"]))


@app.get("/manage/qr/<int:qr_id>/print")
@manager_required
def qrcode_print(qr_id):
    record = get_qrcode(qr_id)
    if not record: abort(404)
    return render_template("print_qr.html", record=record)


@app.get("/manage/report/<int:report_id>")
@staff_required
def manage_report(report_id):
    report, files = get_report(report_id)
    if not report: abort(404)
    if session.get("role") == "technician" and report["assigned_to"] != session.get("display_name"): abort(403)
    return render_template("manage_report.html", report=report, files=files, messages=get_messages(report_id))


@app.post("/manage/report/<int:report_id>/workflow")
@manager_required
def manage_workflow(report_id):
    status = request.form.get("status", "new")
    if status not in WORKFLOW_STATUSES: abort(400)
    update_report_workflow(report_id, status, request.form.get("assigned_to", "").strip()[:80], request.form.get("review_note", "").strip()[:1000])
    return redirect(url_for("manage_report", report_id=report_id))


@app.post("/manage/report/<int:report_id>/messages")
@staff_required
def manager_message(report_id):
    report, _ = get_report(report_id)
    if not report: abort(404)
    if session.get("role") == "technician" and report["assigned_to"] != session.get("display_name"): abort(403)
    body = request.form.get("body", "").strip(); author = session.get("display_name", "מוקד אחזקה")
    if 1 <= len(body) <= 1000:
        add_message(report_id, author or "מוקד אחזקה", "manager", body)
    return redirect(url_for("manage_report", report_id=report_id))


@app.get("/report/<int:report_id>/files/<int:file_id>")
def report_file(report_id, file_id):
    report, _ = get_report(report_id)
    file = get_report_file(report_id, file_id)
    if not report or not file or not report_authorized(report): abort(404)
    path = Path(file["local_path"])
    return send_from_directory(BASE_DIR / "uploads", str(path.relative_to("uploads")).replace("\\", "/"), mimetype=file["mime_type"])


@app.errorhandler(413)
def too_large(error):
    flash("הקבצים גדולים מדי לשליחה", "error")
    return redirect(request.referrer or url_for("report_new"))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "8010")), debug=False)
