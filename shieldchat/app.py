"""
app.py - ShieldChat web server (Flask routes + Socket.IO real-time events).

Run with:  python app.py   then open http://localhost:5000
"""

import os
from datetime import datetime, timedelta
from functools import wraps

from dotenv import load_dotenv
from flask import Flask, abort, jsonify, redirect, render_template, request, session, url_for
from flask_socketio import SocketIO, emit, join_room
from werkzeug.security import check_password_hash

import ai_assistant
import dlp
from database import get_db, init_db

load_dotenv()  # read settings (SECRET_KEY, GEMINI_API_KEY ...) from the .env file

app = Flask(__name__)
# SECRET_KEY signs the session cookie. If someone knew it they could forge a
# login cookie, so it lives in .env (not in code) and must be long and random.
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY") or os.urandom(32).hex()
# HttpOnly: JavaScript cannot read the session cookie, so an XSS bug could not steal it.
app.config["SESSION_COOKIE_HTTPONLY"] = True
# SameSite=Lax: the browser does not send our cookie on requests started by
# other websites, which blocks most cross-site request forgery (CSRF).
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
# SESSION_COOKIE_SECURE (HTTPS-only cookie) should be True in production.
# It stays False here only because the local demo runs on plain http://localhost.
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(hours=8)  # one working day

# async_mode="threading" works on plain Windows Python (no eventlet/gevent needed).
socketio = SocketIO(app, async_mode="threading")

# user_id -> number of open browser tabs, used for the green "online" dot.
online_users = {}

# user_id -> recent message texts the server has already cleared (see on_send_message).
approved_texts = {}

ALLOWED_DOMAIN = "@shieldcorp.com"   # only company accounts may sign in
MAX_FAILED_ATTEMPTS = 5              # wrong passwords allowed before lockout
LOCKOUT_MINUTES = 2                  # how long the account stays locked


def now_iso():
    """Current local time as a short ISO string, e.g. 2026-10-05T14:30:00."""
    return datetime.now().isoformat(timespec="seconds")


def log_incident(user_email, incident_type, details=""):
    """Save a security incident and push it live to any open admin dashboard."""
    # 'details' must only ever contain MASKED values or descriptions, never the
    # raw card/Aadhaar/etc. The incident log is read by people and may be backed
    # up or exported; storing the raw value would itself be a data leak.
    created = now_iso()
    conn = get_db()
    conn.execute(
        "INSERT INTO dlp_incidents (user_email, type, details, created_at) VALUES (?, ?, ?, ?)",
        (user_email[:120], incident_type, details[:500], created),
    )
    conn.commit()
    conn.close()
    socketio.emit(
        "incident",
        {"user_email": user_email, "type": incident_type, "details": details, "created_at": created},
        to="admins",
    )


def login_required(view):
    """Decorator: send the visitor to the login page if they are not signed in."""
    @wraps(view)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapper


# ---------------------------------------------------------------- pages


@app.route("/", methods=["GET"])
def index():
    """Home: go to the chat if logged in, otherwise to the login page."""
    return redirect(url_for("chat") if "user_id" in session else url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    """Show the login form and check the email/password on submit."""
    if request.method == "GET":
        return render_template("login.html", error=None)

    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")

    # 1) Domain restriction: simulates "internal employees only". Checked on
    #    the server, because anything checked only in the browser can be bypassed.
    if not email.endswith(ALLOWED_DOMAIN):
        log_incident(email or "(blank)", "FAILED_LOGIN", "Non-company email domain rejected")
        return render_template(
            "login.html", error="Access denied: only ShieldCorp employees (@shieldcorp.com) can sign in."
        )

    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()

    if not user:
        conn.close()
        log_incident(email, "FAILED_LOGIN", "Unknown account")
        return render_template("login.html", error="Invalid email or password.")

    # 2) Lockout check BEFORE looking at the password, so a locked account
    #    cannot keep being guessed (this is what stops brute-force attacks).
    if user["locked_until"] and user["locked_until"] > now_iso():
        conn.close()
        wait = datetime.fromisoformat(user["locked_until"]) - datetime.now()
        seconds = max(1, int(wait.total_seconds()))
        return render_template(
            "login.html",
            error=f"Account locked after {MAX_FAILED_ATTEMPTS} failed attempts. Try again in {seconds} seconds.",
        )

    # 3) Password check. check_password_hash hashes the typed password and
    #    compares hashes; the real password is never stored or compared in plain text.
    if not check_password_hash(user["password_hash"], password):
        attempts = user["failed_attempts"] + 1
        if attempts >= MAX_FAILED_ATTEMPTS:
            locked_until = (datetime.now() + timedelta(minutes=LOCKOUT_MINUTES)).isoformat(timespec="seconds")
            conn.execute(
                "UPDATE users SET failed_attempts = 0, locked_until = ? WHERE id = ?", (locked_until, user["id"])
            )
            conn.commit()
            conn.close()
            log_incident(email, "FAILED_LOGIN", f"Wrong password (attempt {attempts}/{MAX_FAILED_ATTEMPTS})")
            log_incident(email, "LOCKOUT", f"Account locked for {LOCKOUT_MINUTES} minutes")
            return render_template(
                "login.html",
                error=f"Too many failed attempts. Account locked for {LOCKOUT_MINUTES} minutes.",
            )
        conn.execute("UPDATE users SET failed_attempts = ? WHERE id = ?", (attempts, user["id"]))
        conn.commit()
        conn.close()
        log_incident(email, "FAILED_LOGIN", f"Wrong password (attempt {attempts}/{MAX_FAILED_ATTEMPTS})")
        # Same message for "unknown user" and "wrong password" so the form does
        # not reveal which emails exist. (The lockout message does reveal it;
        # that is the usual trade-off for giving users a clear lockout notice.)
        return render_template("login.html", error="Invalid email or password.")

    # Success: reset the failed-attempt counter.
    conn.execute("UPDATE users SET failed_attempts = 0, locked_until = NULL WHERE id = ?", (user["id"],))
    conn.commit()
    conn.close()

    session.clear()  # fresh session on login (prevents session fixation)
    session.permanent = True
    session["user_id"] = user["id"]
    session["email"] = user["email"]
    session["name"] = user["name"]
    session["role"] = user["role"]
    return redirect(url_for("admin") if user["role"] == "admin" else url_for("chat"))


@app.route("/logout")
def logout():
    """Forget the session and return to the login page."""
    session.clear()
    return redirect(url_for("login"))


@app.route("/chat")
@login_required
def chat():
    """Main WhatsApp-style chat screen."""
    return render_template("chat.html", me=session)


# ---------------------------------------------------------------- JSON APIs


@app.route("/api/contacts")
@login_required
def api_contacts():
    """List every other user, with an online flag, for the left-hand panel."""
    conn = get_db()
    rows = conn.execute(
        "SELECT id, name, email FROM users WHERE id != ? ORDER BY name", (session["user_id"],)
    ).fetchall()
    conn.close()
    return jsonify([
        {"id": r["id"], "name": r["name"], "email": r["email"], "online": r["id"] in online_users}
        for r in rows
    ])


@app.route("/api/messages/<int:other_id>")
@login_required
def api_messages(other_id):
    """Return the conversation history between me and one contact."""
    me = session["user_id"]
    conn = get_db()
    rows = conn.execute(
        """SELECT sender_id, receiver_id, text, created_at FROM messages
           WHERE (sender_id = ? AND receiver_id = ?) OR (sender_id = ? AND receiver_id = ?)
           ORDER BY id""",
        (me, other_id, other_id, me),
    ).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


# ---------------------------------------------------------------- Socket.IO events


@socketio.on("connect")
def on_connect():
    """A browser opened a live connection; refuse it if not logged in."""
    if "user_id" not in session:
        return False  # rejects the socket connection
    uid = session["user_id"]
    # Each user gets a private "room"; messages for them are sent to that room,
    # so every tab they have open receives them, and nobody else does.
    join_room(f"user_{uid}")
    if session.get("role") == "admin":
        join_room("admins")  # receives live incident pushes for the dashboard
    online_users[uid] = online_users.get(uid, 0) + 1
    emit("presence", {"user_id": uid, "online": True}, broadcast=True)


@socketio.on("disconnect")
def on_disconnect(*args):
    """A tab closed; mark the user offline once their last tab is gone."""
    uid = session.get("user_id")
    if uid is None:
        return
    online_users[uid] = online_users.get(uid, 1) - 1
    if online_users[uid] <= 0:
        online_users.pop(uid, None)
        emit("presence", {"user_id": uid, "online": False}, broadcast=True)


def _approve(uid, text):
    """Remember a text the server has already cleared for this user (keeps the last 20)."""
    texts = approved_texts.setdefault(uid, [])
    texts.append(text)
    del texts[:-20]


def _deliver(sender, receiver, text):
    """Store a message in SQLite and push it to both people's browsers."""
    created = now_iso()
    conn = get_db()
    # Parameterised query ("?" placeholders): the message text is passed as
    # data, never glued into the SQL string, so it cannot inject SQL commands.
    conn.execute(
        "INSERT INTO messages (sender_id, receiver_id, text, created_at) VALUES (?, ?, ?, ?)",
        (sender, receiver, text, created),
    )
    conn.commit()
    conn.close()
    msg = {"sender_id": sender, "receiver_id": receiver, "text": text, "created_at": created}
    socketio.emit("new_message", msg, to=f"user_{receiver}")
    socketio.emit("new_message", msg, to=f"user_{sender}")  # sender's other tabs too


@socketio.on("send_message")
def on_send_message(data):
    """Check a message with DLP (Layer 1) and AI (Layer 2), then send, block or suggest a rewrite."""
    if "user_id" not in session:
        return {"status": "error", "error": "Not logged in"}

    sender = session["user_id"]
    email = session["email"]
    text = str(data.get("text", "")).strip()[:2000]
    try:
        receiver = int(data.get("to"))
    except (TypeError, ValueError):
        return {"status": "error", "error": "Bad receiver"}
    if not text:
        return {"status": "error", "error": "Empty message"}
    conn = get_db()
    receiver_exists = conn.execute("SELECT 1 FROM users WHERE id = ?", (receiver,)).fetchone()
    conn.close()
    if receiver == sender or not receiver_exists:
        return {"status": "error", "error": "Bad receiver"}

    # ---------- LAYER 1: local pattern + checksum DLP ----------
    # Runs on the SERVER for every message, whatever the browser claims,
    # because anything enforced only in JavaScript can be bypassed.
    findings = dlp.scan(text)
    if findings:
        public = dlp.public_findings(findings)
        for f in public:
            # Only the MASKED value is logged (see log_incident for why).
            log_incident(email, f["type"], f"{f['label']}: {f['masked_value']}")
        masked = dlp.mask_text(text, findings)
        _approve(sender, masked)  # the server made this version, so it is safe to send
        # The raw text is NOT sent to Gemini: sensitive data never leaves our server.
        return {"status": "blocked", "layer": 1, "findings": public, "masked_text": masked}

    # ---------- LAYER 2: Gemini tone + contextual DLP ----------
    # Skipped only for texts this server already approved: our own masked
    # version, an AI suggestion, or an original the user chose to send after
    # seeing the tone hint (that text was already checked by the AI once).
    ai_unavailable = False
    if text not in approved_texts.get(sender, []):
        result = ai_assistant.analyse_message(text)
        if result is None:
            # FAIL-OPEN for tone: AI is down/slow/no key -> send anyway.
            # Layer 1 above has already run, so pattern DLP is still enforced.
            ai_unavailable = True
        elif result["sensitive_detected"]:
            reason = result["sensitive_reason"] or "Sensitive information detected by AI"
            log_incident(email, "AI_SENSITIVE", f"AI Layer 2: {reason}")
            return {
                "status": "blocked",
                "layer": 2,
                "findings": [{
                    "type": "AI_SENSITIVE",
                    "label": "Sensitive information (detected by AI)",
                    "masked_value": "(value not shown)",
                    "reason": reason,
                }],
                "masked_text": None,  # AI gives no exact positions, so no masked version
            }
        elif result["is_unprofessional"] and result["suggestion"]:
            # Tone problems are NOT blocked; we only suggest a better wording.
            _approve(sender, text)
            _approve(sender, result["suggestion"])
            return {"status": "tone", "tone": result["tone"], "suggestion": result["suggestion"], "original": text}

    _deliver(sender, receiver, text)
    return {"status": "sent", "ai_unavailable": ai_unavailable}


# Browser-reported events we accept, and how often (seconds) per user/type.
CLIENT_INCIDENT_TYPES = {"COPY_ATTEMPT", "BULK_PASTE"}
_last_client_incident = {}


@socketio.on("client_incident")
def on_client_incident(data):
    """Log a copy attempt or bulk paste reported by the browser (Phase 5)."""
    if "user_id" not in session:
        return
    kind = str(data.get("type", ""))
    if kind not in CLIENT_INCIDENT_TYPES:
        return  # only accept known types, so the log cannot be filled with junk
    # Simple rate limit: at most one incident of each type per user every 3 seconds.
    key = (session["user_id"], kind)
    now = datetime.now()
    if key in _last_client_incident and (now - _last_client_incident[key]).total_seconds() < 3:
        return
    _last_client_incident[key] = now
    if kind == "COPY_ATTEMPT":
        details = "Tried to copy/cut/right-click chat messages"
    else:
        # We log only the SIZE of the paste, never its content.
        size = int(data.get("length", 0) or 0)
        details = f"Pasted {size} characters into the message box"
    log_incident(session["email"], kind, details)


# ---------------------------------------------------------------- Admin dashboard (Phase 6)


def admin_required(view):
    """Decorator: allow only the Security Admin role; everyone else gets 403 Forbidden."""
    # The check happens on the SERVER. Hiding a link in the UI is not security:
    # anyone can type /admin in the address bar.
    @wraps(view)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        if session.get("role") != "admin":
            abort(403)
        return view(*args, **kwargs)
    return wrapper


@app.route("/admin")
@admin_required
def admin():
    """Security Admin dashboard page."""
    return render_template("admin.html", me=session)


@app.route("/api/admin/summary")
@admin_required
def api_admin_summary():
    """Numbers for the dashboard cards plus the latest 100 incidents."""
    today = datetime.now().strftime("%Y-%m-%d")
    dlp_types = ("CARD", "AADHAAR", "PAN", "BANK_ACCOUNT", "IFSC", "AI_SENSITIVE")
    conn = get_db()

    def count(sql, params=()):
        return conn.execute(sql, params).fetchone()[0]

    stats = {
        "total_messages": count("SELECT COUNT(*) FROM messages"),
        # One blocked message can have several findings (e.g. PAN + Aadhaar),
        # all logged with the same user and timestamp, so count those pairs.
        "dlp_blocks_today": count(
            "SELECT COUNT(DISTINCT user_email || created_at) FROM dlp_incidents WHERE type IN"
            f" ({','.join('?' * len(dlp_types))}) "
            "AND substr(created_at, 1, 10) = ?",
            (*dlp_types, today),
        ),
        "copy_attempts": count("SELECT COUNT(*) FROM dlp_incidents WHERE type = 'COPY_ATTEMPT'"),
        "failed_logins": count("SELECT COUNT(*) FROM dlp_incidents WHERE type = 'FAILED_LOGIN'"),
        "locked_accounts": count("SELECT COUNT(*) FROM users WHERE locked_until > ?", (now_iso(),)),
    }
    incidents = [
        dict(r) for r in conn.execute(
            "SELECT created_at, user_email, type, details FROM dlp_incidents ORDER BY id DESC LIMIT 100"
        )
    ]
    conn.close()
    return jsonify({"stats": stats, "incidents": incidents})


if __name__ == "__main__":
    init_db()
    print("ShieldChat running on http://localhost:5000")
    if not os.getenv("GEMINI_API_KEY"):
        print("Note: GEMINI_API_KEY not set - AI features off, DLP Layer 1 still active.")
    # allow_unsafe_werkzeug lets the built-in dev server run with Socket.IO.
    # Fine for a local demo; a real deployment would use a production server.
    socketio.run(app, host="127.0.0.1", port=5000, debug=False, allow_unsafe_werkzeug=True)
