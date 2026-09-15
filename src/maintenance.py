from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from .db import connection

OUTCOMES = {"in_progress", "fixed", "not_fixed", "waiting_parts"}


def _day_bounds():
    local = datetime.now(ZoneInfo("Asia/Jerusalem"))
    start = local.replace(hour=0, minute=0, second=0, microsecond=0).astimezone(timezone.utc)
    end = start + timedelta(days=1)
    return local.date().isoformat(), start, end


def _bound(conn, value):
    return value if conn.dialect == "postgres" else value.strftime("%Y-%m-%d %H:%M:%S")


def list_journal(user=None, status="all", include_archived=False):
    clauses = [] if include_archived else ["r.archived_at IS NULL"]
    params = []
    if status == "open":
        clauses.append("r.status <> 'resolved'")
    elif status == "closed":
        clauses.append("r.status = 'resolved'")
    if user and user["role"] == "technician":
        clauses.append("r.assigned_to = ?")
        params.append(user["display_name"])
    where = " WHERE " + " AND ".join(clauses) if clauses else ""
    query = """SELECT r.*, (SELECT COUNT(*) FROM maintenance_actions a WHERE a.report_id=r.id) action_count,
             (SELECT a.outcome FROM maintenance_actions a WHERE a.report_id=r.id ORDER BY a.id DESC LIMIT 1) last_outcome
             FROM reports r""" + where + " ORDER BY CASE WHEN r.status='resolved' THEN 1 ELSE 0 END, r.updated_at DESC, r.id DESC"
    with connection() as conn:
        return conn.execute(query, params).fetchall()


def dashboard_snapshot():
    day, start, end = _day_bounds()
    with connection() as conn:
        start, end = _bound(conn, start), _bound(conn, end)
        totals = conn.execute("""SELECT
          COUNT(*) total,
          SUM(CASE WHEN status <> 'resolved' THEN 1 ELSE 0 END) open_count,
          SUM(CASE WHEN status = 'resolved' THEN 1 ELSE 0 END) closed_count,
          SUM(CASE WHEN status <> 'resolved' AND report_type='safety_near_miss' THEN 1 ELSE 0 END) open_safety,
          SUM(CASE WHEN status <> 'resolved' AND report_type='maintenance_request' THEN 1 ELSE 0 END) open_maintenance
          FROM reports WHERE archived_at IS NULL""").fetchone()
        new_today = conn.execute("SELECT COUNT(*) n FROM reports WHERE archived_at IS NULL AND created_at >= ? AND created_at < ?", (start, end)).fetchone()["n"]
        work_today = conn.execute("SELECT COUNT(*) n FROM maintenance_actions WHERE created_at >= ? AND created_at < ?", (start, end)).fetchone()["n"]
        fixed_today = conn.execute("SELECT COUNT(*) n FROM maintenance_actions WHERE outcome='fixed' AND created_at >= ? AND created_at < ?", (start, end)).fetchone()["n"]
        waiting = conn.execute("""SELECT COUNT(*) n FROM reports r WHERE r.archived_at IS NULL AND r.status <> 'resolved'
          AND (SELECT outcome FROM maintenance_actions a WHERE a.report_id=r.id ORDER BY a.id DESC LIMIT 1)='waiting_parts'""").fetchone()["n"]
    return {"day": day, "total": totals["total"] or 0, "open": totals["open_count"] or 0,
            "closed": totals["closed_count"] or 0, "open_safety": totals["open_safety"] or 0,
            "open_maintenance": totals["open_maintenance"] or 0, "new_today": new_today,
            "work_today": work_today, "fixed_today": fixed_today, "waiting_parts": waiting}


def add_action(report_id, user, outcome, work_done, parts="", knowledge_note="", root_cause=""):
    if outcome not in OUTCOMES or not work_done.strip():
        raise ValueError("יש לבחור תוצאת טיפול ולתאר את העבודה")
    with connection() as conn:
        query = """INSERT INTO maintenance_actions
          (report_id,author_user_id,author_name,outcome,work_done,parts,knowledge_note,root_cause)
          VALUES (?,?,?,?,?,?,?,?)"""
        if conn.dialect == "postgres": query += " RETURNING id"
        cursor = conn.execute(query, (report_id, user["id"], user["display_name"], outcome,
                                      work_done, parts, knowledge_note, root_cause))
        action_id = cursor.fetchone()["id"] if conn.dialect == "postgres" else cursor.lastrowid
        conn.execute("UPDATE reports SET updated_at=CURRENT_TIMESTAMP WHERE id=?", (report_id,))
        return action_id


def add_discussion(report_id, user, body):
    with connection() as conn:
        conn.execute("INSERT INTO maintenance_discussion (report_id,author_user_id,author_name,body) VALUES (?,?,?,?)",
                     (report_id, user["id"], user["display_name"], body))


def add_event(report_id, user, event_type, detail=""):
    with connection() as conn:
        conn.execute("INSERT INTO maintenance_events (report_id,actor_user_id,actor_name,event_type,detail) VALUES (?,?,?,?,?)",
                     (report_id, user["id"], user["display_name"], event_type, detail))


def get_case_history(report_id):
    with connection() as conn:
        actions = conn.execute("SELECT * FROM maintenance_actions WHERE report_id=? ORDER BY id DESC", (report_id,)).fetchall()
        discussion = conn.execute("SELECT * FROM maintenance_discussion WHERE report_id=? ORDER BY id", (report_id,)).fetchall()
        events = conn.execute("SELECT * FROM maintenance_events WHERE report_id=? ORDER BY id", (report_id,)).fetchall()
    return actions, discussion, events


def search_knowledge(term=""):
    term = term.strip()[:120]
    with connection() as conn:
        query = """SELECT a.*, r.machine, r.department, r.location_code, r.text_body,
             r.report_type FROM maintenance_actions a JOIN reports r ON r.id=a.report_id
             WHERE r.archived_at IS NULL AND a.knowledge_note <> ''"""
        params = []
        if term:
            query += " AND (a.knowledge_note LIKE ? OR a.root_cause LIKE ? OR a.work_done LIKE ? OR r.machine LIKE ? OR r.text_body LIKE ?)"
            params = [f"%{term}%"] * 5
        return conn.execute(query + " ORDER BY a.created_at DESC, a.id DESC LIMIT 100", params).fetchall()


def archive_report(report_id, user):
    with connection() as conn:
        conn.execute("UPDATE reports SET archived_at=CURRENT_TIMESTAMP, archived_by=?, updated_at=CURRENT_TIMESTAMP WHERE id=? AND archived_at IS NULL",
                     (user["display_name"], report_id))
    add_event(report_id, user, "archived")


def restore_report(report_id, user):
    with connection() as conn:
        conn.execute("UPDATE reports SET archived_at=NULL, archived_by=NULL, updated_at=CURRENT_TIMESTAMP WHERE id=? AND archived_at IS NOT NULL", (report_id,))
    add_event(report_id, user, "restored")


def receipt_state(report_id, user_id):
    with connection() as conn:
        return conn.execute("SELECT viewed_at, acknowledged_at FROM case_receipts WHERE report_id=? AND staff_user_id=?",
                            (report_id, user_id)).fetchone()


def mark_receipt(report_id, user, acknowledge=False):
    with connection() as conn:
        existing = conn.execute("SELECT viewed_at, acknowledged_at FROM case_receipts WHERE report_id=? AND staff_user_id=?",
                                (report_id, user["id"])).fetchone()
        if not existing:
            conn.execute("INSERT INTO case_receipts (report_id,staff_user_id,viewed_at) VALUES (?,?,CURRENT_TIMESTAMP)",
                         (report_id, user["id"]))
            recorded = True
        else:
            recorded = False
        if acknowledge and (not existing or not existing["acknowledged_at"]):
            conn.execute("UPDATE case_receipts SET acknowledged_at=CURRENT_TIMESTAMP WHERE report_id=? AND staff_user_id=?",
                         (report_id, user["id"]))
            recorded = True
    if recorded:
        add_event(report_id, user, "acknowledged" if acknowledge else "viewed", "התיק אושר לטיפול" if acknowledge else "התיק נצפה")
    return receipt_state(report_id, user["id"])
