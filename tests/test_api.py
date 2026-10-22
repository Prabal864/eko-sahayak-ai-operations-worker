from fastapi.testclient import TestClient

from backend.main import app


client = TestClient(app)


def analyze(summary: str, source: str = "support"):
    response = client.post(
        "/api/analyze",
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
    assert response.status_code == 422


def test_status_update_adds_audit_event():
    result = analyze("KYC document upload is blocked on the onboarding screen.")
    case_id = result["id"]
    response = client.patch(f"/api/cases/{case_id}", json={"status": "escalated"})
    assert response.status_code == 200
    assert response.json()["status"] == "escalated"
    assert response.json()["audit"][-1]["event"] == "status_changed"
