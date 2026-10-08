"""
End-to-end tests for the server: login security, DLP blocking, AI flow
(with a FAKE Gemini, so no internet or API key is needed), incidents and
the admin dashboard.  Run with:  python -m pytest -v
"""

import os
import sys
import time

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import ai_assistant  # noqa: E402
import app as shieldchat  # noqa: E402
import database  # noqa: E402

CARD_MSG = "Hi Bob, here is the client card: Visa: 4485 3647 3952 7352 Expires: 2/2009"


@pytest.fixture
def env(tmp_path, monkeypatch):
    """Fresh database per test, plus logged-in Alice, Bob and Admin."""
    monkeypatch.setattr(database, "DB_PATH", str(tmp_path / "test.db"))
    database.init_db()
    shieldchat.approved_texts.clear()
    shieldchat._last_client_incident.clear()
    clients = {}
    for name, pw in [("alice", "Alice@123"), ("bob", "Bob@123"), ("admin", "Admin@123")]:
        http = shieldchat.app.test_client()
        http.post("/login", data={"email": f"{name}@shieldcorp.com", "password": pw})
        sock = shieldchat.socketio.test_client(shieldchat.app, flask_test_client=http)
        clients[name] = (http, sock)
    return clients


def fake_ai(result, calls):
    """Return a stand-in for analyse_message that records every call."""
    def _fake(text):
        calls.append(text)
        return result
    return _fake


def incidents(env):
    http, _ = env["admin"]
    return http.get("/api/admin/summary").get_json()["incidents"]


def send(env, who, text, to=2):
    _, sock = env[who]
    return sock.emit("send_message", {"to": to, "text": text}, callback=True)


def test_card_blocked_and_never_sent_to_ai(env, monkeypatch):
    calls = []
    monkeypatch.setattr(ai_assistant, "analyse_message", fake_ai(None, calls))
    reply = send(env, "alice", CARD_MSG)
    assert reply["status"] == "blocked" and reply["layer"] == 1
    assert "Visa" in reply["findings"][0]["label"]
    assert calls == []                                  # raw message never reached the AI
    assert "4485" not in reply["masked_text"]
    inc = incidents(env)[0]
    assert inc["type"] == "CARD" and "4485" not in inc["details"]
    # The admin's browser got a live push.
    assert any(e["name"] == "incident" for e in env["admin"][1].get_received())


def test_send_masked_version_delivers(env, monkeypatch):
    calls = []
    monkeypatch.setattr(ai_assistant, "analyse_message", fake_ai(None, calls))
    masked = send(env, "alice", CARD_MSG)["masked_text"]
    env["bob"][1].get_received()
    assert send(env, "alice", masked)["status"] == "sent"
    got = [e for e in env["bob"][1].get_received() if e["name"] == "new_message"]
    assert got and got[0]["args"][0]["text"] == masked


def test_ai_unavailable_still_sends(env, monkeypatch):
    monkeypatch.setattr(ai_assistant, "analyse_message", fake_ai(None, []))
    reply = send(env, "alice", "Hi Bob, meeting at 3?")
    assert reply == {"status": "sent", "ai_unavailable": True}


def test_rude_message_gets_suggestion_then_suggestion_sends(env, monkeypatch):
    calls = []
    result = {"is_unprofessional": True, "tone": "aggressive",
              "suggestion": "Could you please share the report when possible?",
              "sensitive_detected": False, "sensitive_reason": ""}
    monkeypatch.setattr(ai_assistant, "analyse_message", fake_ai(result, calls))
    reply = send(env, "alice", "Send me the report now, why are you always so slow?")
    assert reply["status"] == "tone"
    assert send(env, "alice", reply["suggestion"])["status"] == "sent"
    assert len(calls) == 1          # the AI's own suggestion is not re-checked


def test_ai_sensitive_blocked_and_logged(env, monkeypatch):
    result = {"is_unprofessional": False, "tone": "professional", "suggestion": "",
              "sensitive_detected": True, "sensitive_reason": "Card number written in words"}
    monkeypatch.setattr(ai_assistant, "analyse_message", fake_ai(result, []))
    reply = send(env, "alice", "card is four four eight five ...")
    assert reply["status"] == "blocked" and reply["layer"] == 2
    assert incidents(env)[0]["type"] == "AI_SENSITIVE"


def test_client_incidents(env):
    _, sock = env["alice"]
    sock.emit("client_incident", {"type": "COPY_ATTEMPT"})
    sock.emit("client_incident", {"type": "BULK_PASTE", "length": 450})
    sock.emit("client_incident", {"type": "DROP_TABLE"})       # unknown type ignored
    types = [i["type"] for i in incidents(env)]
    assert types == ["BULK_PASTE", "COPY_ATTEMPT"]


def test_admin_requires_admin_role(env):
    assert env["alice"][0].get("/admin").status_code == 403
    assert env["alice"][0].get("/api/admin/summary").status_code == 403
    assert env["admin"][0].get("/admin").status_code == 200


def test_parse_ai_json_handles_code_fences():
    raw = '```json\n{"is_unprofessional": true, "tone": "rude", "suggestion": "Please...", ' \
          '"sensitive_detected": false, "sensitive_reason": ""}\n```'
    assert ai_assistant.parse_ai_json(raw)["tone"] == "rude"
    assert ai_assistant.parse_ai_json("not json") is None


def test_ai_timeout_returns_none(monkeypatch):
    monkeypatch.setattr(ai_assistant, "_get_client", lambda: object())
    monkeypatch.setattr(ai_assistant, "_call_gemini", lambda m: time.sleep(8))
    monkeypatch.setattr(ai_assistant, "AI_TIMEOUT_SECONDS", 1)
    start = time.time()
    assert ai_assistant.analyse_message("hello") is None
    assert time.time() - start < 3
