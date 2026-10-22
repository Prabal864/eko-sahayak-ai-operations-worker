from fastapi.testclient import TestClient
from uuid import uuid4
import os

from backend.main import app


client = TestClient(app)
TEST_USERNAME = os.getenv("EKO_DEMO_USERNAME", "prabal")
TEST_PASSWORD = os.getenv("EKO_DEMO_PASSWORD", "eko-demo")


def auth_headers():
    response = client.post("/api/auth/login", json={"username": TEST_USERNAME, "password": TEST_PASSWORD})
    assert response.status_code == 200
    token = response.json()["token"]
    return {"Authorization": "Bearer " + token}


def analyze(summary: str, source: str = "support"):
    response = client.post(
        "/api/analyze",
        headers=auth_headers(),
        json={
            "source": source,
            "summary": summary,
            "language": "English",
            "consent_to_share": False,
        },
    )
    assert response.status_code == 200
    return response.json()


def test_health():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["database"]["connected"] is True
    assert response.json()["database"]["type"] in {"sqlite", "postgresql"}


def test_dashboard_requires_login():
    response = client.get("/api/cases")
    assert response.status_code == 401


def test_login_and_logout():
    response = client.post("/api/auth/login", json={"username": TEST_USERNAME, "password": TEST_PASSWORD})
    assert response.status_code == 200
    token = response.json()["token"]
    headers = {"Authorization": "Bearer " + token}
    assert client.get("/api/auth/me", headers=headers).status_code == 200
    assert client.post("/api/auth/logout", headers=headers).status_code == 200
    assert client.get("/api/auth/me", headers=headers).status_code == 401


def test_signup_creates_account_and_session():
    username = f"new_operator_{uuid4().hex[:8]}"
    response = client.post(
        "/api/auth/signup",
        json={"name": "New Operator", "username": username, "password": "safe-demo-password"},
    )
    assert response.status_code == 200
    headers = {"Authorization": "Bearer " + response.json()["token"]}
    assert response.json()["user"]["username"] == username
    assert "password_hash" not in response.json()["user"]
    assert client.get("/api/auth/me", headers=headers).status_code == 200


def test_signup_rejects_duplicate_username():
    response = client.post(
        "/api/auth/signup",
        json={"name": "Duplicate", "username": TEST_USERNAME, "password": "safe-demo-password"},
    )
    assert response.status_code == 409


def test_voice_transcription_requires_login():
    response = client.post(
        "/api/voice/transcribe",
        files={"audio": ("voice.webm", b"audio", "audio/webm")},
    )
    assert response.status_code == 401


def test_voice_transcription_reports_missing_provider_configuration(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    response = client.post(
        "/api/voice/transcribe",
        headers=auth_headers(),
        files={"audio": ("voice.webm", b"audio", "audio/webm")},
    )
    assert response.status_code == 503


def test_payment_routes_to_payments_operations():
    result = analyze("Settlement is missing after a successful customer payment.")
    assert result["category"] == "Settlement / payout"
    assert result["owner"] == "Payments Operations"


def test_fraud_risk_overrides_other_signals():
    result = analyze("The agent shared an OTP and money is now missing.")
    assert result["category"] == "Safety / fraud risk"
    assert result["priority"] == "urgent"
    assert result["owner"] == "Trust & Safety"


def test_connectivity_precedes_settlement_signal():
    result = analyze("The device is offline and settlement is not visible yet.")
    assert result["category"] == "Product / connectivity"
    assert result["owner"] == "Product Support"


def test_vague_report_requests_clarification():
    result = analyze("It is not working for the entrepreneur.")
    assert result["category"] == "Needs clarification"
    assert result["status"] == "in_review"
    assert result["confidence"] < 0.7


def test_invalid_input_is_rejected():
    response = client.post(
        "/api/analyze",
        json={"source": "support", "summary": "short"},
    )
    assert response.status_code == 401


def test_status_update_adds_audit_event():
    result = analyze("KYC document upload is blocked on the onboarding screen.")
    case_id = result["id"]
    response = client.patch(
        f"/api/cases/{case_id}",
        headers=auth_headers(),
        json={"status": "escalated"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "escalated"
    assert response.json()["audit"][-1]["event"] == "status_changed"
