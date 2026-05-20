# app/routers/waitlist.py
import re
import logging
from fastapi import APIRouter
from fastapi.responses import JSONResponse, HTMLResponse, Response

from ..models.database import SessionLocal, WaitlistEntry

logger = logging.getLogger(__name__)
router = APIRouter()

_EMAIL_RE = re.compile(r'^[^\s@]+@[^\s@]+\.[^\s@]+$')

_CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
}


@router.options("/api/waitlist")
def waitlist_preflight():
    """Handle CORS preflight from kitabiai.com."""
    return Response(status_code=200, headers=_CORS_HEADERS)


@router.post("/api/waitlist")
def join_waitlist(data: dict):
    """Save name + email to the waitlist. Duplicate emails are accepted silently."""
    email = (data.get("email") or "").strip().lower()
    name  = (data.get("name")  or "").strip()
    source = (data.get("source") or "unknown").strip()

    if not email or not _EMAIL_RE.match(email):
        return JSONResponse({"ok": False, "error": "invalid_email"}, status_code=400, headers=_CORS_HEADERS)

    db = SessionLocal()
    try:
        exists = db.query(WaitlistEntry).filter_by(email=email).first()
        if not exists:
            db.add(WaitlistEntry(name=name, email=email, source=source))
            db.commit()
            logger.info(f"Waitlist: new signup — {email} ({source})")
    except Exception as e:
        db.rollback()
        logger.error(f"Waitlist insert failed: {e}")
        return JSONResponse({"ok": False, "error": "server_error"}, status_code=500, headers=_CORS_HEADERS)
    finally:
        db.close()

    return JSONResponse({"ok": True}, headers=_CORS_HEADERS)


@router.get("/admin/waitlist", response_class=HTMLResponse)
def admin_waitlist():
    """Admin view — table of all waitlist signups."""
    db = SessionLocal()
    try:
        entries = db.query(WaitlistEntry).order_by(WaitlistEntry.created_at.desc()).all()
    finally:
        db.close()

    rows = "".join(
        f"<tr><td>{e.id}</td><td>{e.name or '—'}</td><td>{e.email}</td>"
        f"<td>{e.source or '—'}</td><td>{e.created_at.strftime('%Y-%m-%d %H:%M') if e.created_at else '—'}</td></tr>"
        for e in entries
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<title>Waitlist — KitabiAI</title>
<style>
  body {{ font-family: system-ui, sans-serif; padding: 32px; background: #fdfaf7; color: #1c1410; }}
  h1 {{ color: #c76a2d; margin-bottom: 8px; }}
  .count {{ color: #6b5d4d; margin-bottom: 24px; }}
  table {{ border-collapse: collapse; width: 100%; background: #fff; border-radius: 12px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,.08); }}
  th {{ background: #c76a2d; color: #fff; padding: 12px 16px; text-align: left; font-size: 13px; }}
  td {{ padding: 10px 16px; border-bottom: 1px solid #e8d8c8; font-size: 14px; }}
  tr:last-child td {{ border-bottom: none; }}
  tr:hover td {{ background: #fdf5ef; }}
  .back {{ display: inline-block; margin-bottom: 20px; color: #c76a2d; text-decoration: none; font-size: 14px; }}
</style>
</head>
<body>
  <a class="back" href="/admin">← Back to Admin</a>
  <h1>Waitlist Signups</h1>
  <p class="count">{len(entries)} subscriber{'s' if len(entries) != 1 else ''}</p>
  <table>
    <thead><tr><th>#</th><th>Name</th><th>Email</th><th>Source</th><th>Date</th></tr></thead>
    <tbody>{rows if rows else '<tr><td colspan="5" style="text-align:center;color:#999;padding:24px">No signups yet.</td></tr>'}</tbody>
  </table>
</body>
</html>"""
