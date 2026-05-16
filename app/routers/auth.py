"""
Admin authentication — login / logout routes and session helpers.

Session is a signed, time-limited cookie (HMAC-SHA256, no extra dependencies).
Credentials are read from settings (ADMIN_USERNAME / ADMIN_PASSWORD / SECRET_KEY).
"""
import hmac
import hashlib
import base64
import json
import time

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from ..core.config import settings

router = APIRouter()

SESSION_COOKIE = "kitabiai_session"
SESSION_HOURS  = 8


# ── Token helpers ─────────────────────────────────────────────────────────────

def _sig(payload_b64: str) -> str:
    return hmac.new(
        settings.SECRET_KEY.encode(),
        payload_b64.encode(),
        hashlib.sha256,
    ).hexdigest()


def create_session_token() -> str:
    payload     = json.dumps({"exp": time.time() + SESSION_HOURS * 3600})
    payload_b64 = base64.urlsafe_b64encode(payload.encode()).decode()
    return f"{payload_b64}.{_sig(payload_b64)}"


def verify_session_token(token: str | None) -> bool:
    if not token:
        return False
    try:
        payload_b64, sig = token.rsplit(".", 1)
        if not hmac.compare_digest(_sig(payload_b64), sig):
            return False
        payload = json.loads(base64.urlsafe_b64decode(payload_b64))
        return payload["exp"] > time.time()
    except Exception:
        return False


# ── Login page HTML ───────────────────────────────────────────────────────────

def _login_html(error: bool = False) -> str:
    error_block = (
        '<div class="error">Incorrect username or password.</div>'
        if error else ""
    )
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>KitabiAI — Admin Login</title>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:ui-sans-serif,system-ui,-apple-system,'Segoe UI',sans-serif;
  background:#fdfaf7;display:flex;align-items:center;justify-content:center;
  min-height:100vh;padding:16px}}
.card{{background:#fff;border:1px solid #e8d8c8;border-radius:20px;
  padding:40px 36px;width:100%;max-width:380px;
  box-shadow:0 4px 24px rgba(199,106,45,.10)}}
.logo{{font-size:28px;text-align:center;margin-bottom:6px}}
h1{{text-align:center;font-size:20px;font-weight:700;color:#1c1410;margin-bottom:28px}}
.error{{background:#fef2f2;border:1px solid #fca5a5;color:#dc2626;
  border-radius:10px;padding:10px 14px;font-size:13px;margin-bottom:20px;text-align:center}}
label{{display:block;font-size:13px;font-weight:600;color:#6b5d4d;margin-bottom:6px}}
input{{width:100%;padding:10px 14px;border:1px solid #e8d8c8;border-radius:10px;
  font-size:14px;outline:none;font-family:inherit;background:#fdfaf7;
  margin-bottom:18px;transition:border-color .15s}}
input:focus{{border-color:#c76a2d}}
button{{width:100%;padding:12px;background:#c76a2d;color:#fff;border:none;
  border-radius:10px;font-size:15px;font-weight:600;cursor:pointer;
  font-family:inherit;transition:background .15s}}
button:hover{{background:#e88d51}}
</style>
</head>
<body>
<div class="card">
  <div class="logo">📚</div>
  <h1>KitabiAI Admin</h1>
  {error_block}
  <form method="POST" action="/admin/login">
    <label for="username">Username</label>
    <input type="text" id="username" name="username" required autofocus autocomplete="username"/>
    <label for="password">Password</label>
    <input type="password" id="password" name="password" required autocomplete="current-password"/>
    <button type="submit">Sign In</button>
  </form>
</div>
</body>
</html>"""


# ── Routes ────────────────────────────────────────────────────────────────────

@router.get("/admin/login", response_class=HTMLResponse)
def login_page(error: int = 0):
    return _login_html(error=bool(error))


@router.post("/admin/login")
def login_submit(
    username: str = Form(...),
    password: str = Form(...),
):
    if (
        hmac.compare_digest(username, settings.ADMIN_USERNAME)
        and hmac.compare_digest(password, settings.ADMIN_PASSWORD)
    ):
        token    = create_session_token()
        response = RedirectResponse("/admin", status_code=303)
        response.set_cookie(
            SESSION_COOKIE,
            token,
            httponly=True,
            max_age=SESSION_HOURS * 3600,
            samesite="lax",
        )
        return response
    return RedirectResponse("/admin/login?error=1", status_code=303)


@router.get("/admin/logout")
def logout():
    response = RedirectResponse("/admin/login", status_code=303)
    response.delete_cookie(SESSION_COOKIE)
    return response
