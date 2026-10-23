import json
import re
import asyncio
import logging
import os
import secrets
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal
from uuid import uuid4

from fastapi import Depends, FastAPI, File, Header, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy import select

from .database import (
    AuditEvent, Case, Session, User, db_session, hash_token, init_db,
    password_hash, password_matches, SESSION_TTL, utc_now,
    check_database_connection,
)

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


PROJECT_ROOT = Path(__file__).resolve().parent.parent
FRONTEND_DIST = PROJECT_ROOT / "frontend" / "dist"
ai_logger = logging.getLogger("eko_sahayak.ai")

app = FastAPI(title="Eko Sahayak", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "https://eko-sahayak-ai.netlify.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class CaseInput(BaseModel):
    source: Literal["voice_note", "support", "field_visit", "activity_log"] = "support"
    summary: str = Field(min_length=8, max_length=1200)
    language: Literal["English", "Hindi", "Hinglish"] = "English"
    consent_to_share: bool = False


class CaseStatus(BaseModel):
    status: Literal["new", "in_review", "resolved", "escalated"]


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=80)
    password: str = Field(min_length=1, max_length=200)


class SignupRequest(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    username: str = Field(min_length=3, max_length=80, pattern=r"^[a-zA-Z0-9_.-]+$")
    password: str = Field(min_length=8, max_length=200)


class AiResolution(BaseModel):
    category: str
    priority: Literal["normal", "high", "urgent"]
    owner: str
    root_cause: str
    evidence: list[str]
    next_action: str
    escalation: str
    confidence: float = Field(ge=0, le=1)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


DEMO_USERNAME = os.getenv("EKO_DEMO_USERNAME", "prabal")
DEMO_PASSWORD = os.getenv("EKO_DEMO_PASSWORD", "eko-demo")
def public_user(user: User) -> dict[str, str]:
    return {"id": user.id, "name": user.name, "username": user.username, "role": user.role}


def current_user(authorization: str | None = Header(default=None)) -> dict[str, str]:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Login required")
    token = authorization.split(" ", 1)[1].strip()
    with db_session() as db:
        session = db.scalar(select(Session).where(Session.token_hash == hash_token(token)))
        if not session or session.expires_at.replace(tzinfo=timezone.utc) <= utc_now():
            if session:
                db.delete(session)
            raise HTTPException(status_code=401, detail="Session expired. Please log in again.")
        user = db.get(User, session.user_id)
        if not user:
            raise HTTPException(status_code=401, detail="Login required")
        return public_user(user)


def redact_local(text: str) -> str:
    """Remove common secrets before any optional model call."""
    patterns = (
        (r"\b\d{12}\b", "[REDACTED_ID]"),
        (r"\b\d{10}\b", "[REDACTED_PHONE]"),
        (r"\b(?:otp|pin|password)\s*[:#-]?\s*\d{4,8}\b", "[REDACTED_SECRET]"),
        (r"\b[\w.+-]+@[\w.-]+\.\w+\b", "[REDACTED_EMAIL]"),
    )
    redacted = text
    for pattern, replacement in patterns:
        redacted = re.sub(pattern, replacement, redacted, flags=re.IGNORECASE)
    return redacted


def classify_case(payload: CaseInput, *, note: str | None = None) -> dict:
    """Explainable, offline-safe triage. No external model or PII leaves the device."""
    text = (note or payload.summary).lower()
    if any(word in text for word in ("otp", "pin", "password", "fraud", "scam", "money missing")):
        category, priority, owner = "Safety / fraud risk", "urgent", "Trust & Safety"
        root_cause = "Potential account or payment security issue; the report needs human verification."
        action = "Pause risky activity, preserve the local evidence, and call the Trust & Safety desk."
        escalation = "Escalate immediately. Never request or store an OTP, PIN, or full payment credential."
    elif any(word in text for word in ("failed", "error", "down", "offline", "network")):
        category, priority, owner = "Product / connectivity", "high", "Product Support"
        root_cause = "The task likely failed because of connectivity, a stale session, or a service error."
        action = "Capture the last successful step, retry once on a stable connection, then share the error code."
        escalation = "Escalate after one safe retry or immediately if multiple entrepreneurs report the same failure."
    elif any(word in text for word in ("cash", "settlement", "commission", "payout", "payment")):
        category, priority, owner = "Settlement / payout", "high", "Payments Operations"
        root_cause = "A settlement or commission event is not matching the expected status."
        action = "Verify the transaction reference and last successful settlement before retrying."
        escalation = "Escalate if the reference is missing, money is debited, or the issue is older than 24 hours."
    elif any(word in text for word in ("kyc", "document", "aadhaar", "pan", "verification")):
        category, priority, owner = "KYC / onboarding", "normal", "Onboarding Desk"
        root_cause = "Onboarding is blocked by an incomplete, unreadable, or mismatched document step."
        action = "Ask for the missing step only; guide the entrepreneur through a fresh, well-lit capture."
        escalation = "Escalate when the user cannot complete the step or a mismatch needs manual review."
    else:
        category, priority, owner = "Needs clarification", "normal", "Field Operations"
        root_cause = "There is not enough structured evidence to identify a reliable root cause yet."
        action = "Ask one focused question: what were you trying to do, and what happened instead?"
        escalation = "Keep with the field owner until the missing context is captured."

    case_id = f"EKO-{datetime.now().strftime('%m%d')}-{str(uuid4())[:4].upper()}"
    return {
        "id": case_id,
        "status": "in_review",
        "category": category,
        "priority": priority,
        "owner": owner,
        "root_cause": root_cause,
        "evidence": [
            f"Reported through {payload.source.replace('_', ' ')}",
            f"Language preference: {payload.language}",
            "No external retrieval used; conclusion is based only on the submitted event",
        ],
        "next_action": action,
        "escalation": escalation,
        "confidence": 0.88 if category != "Needs clarification" else 0.58,
        "consent_to_share": payload.consent_to_share,
        "created_at": now_iso(),
        "audit": [
            {"event": "case_received", "detail": "Raw note retained locally for this demo session.", "at": now_iso()},
            {"event": "triage_completed", "detail": "Rule-based classification with explicit evidence.", "at": now_iso()},
        ],
    }


async def classify_with_gemini(payload: CaseInput) -> tuple[dict, str]:
    """Use Gemini for language understanding, while keeping policy decisions local."""
    api_key = os.getenv("GEMINI_API_KEY")
    model = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")
    if not api_key:
        ai_logger.warning("AI provider unavailable: provider=gemini reason=missing_api_key")
        return classify_case(payload), "local_rules_no_key"
    started = time.perf_counter()
    ai_logger.info("AI request started: provider=gemini model=%s source=%s", model, payload.source)
    try:
        from google import genai

        client = genai.Client(api_key=api_key)
        prompt = f"""You are Eko Sahayak, an operations triage assistant.
Return ONLY valid JSON with keys: category, priority, owner, root_cause, evidence,
next_action, escalation, confidence. Use priority normal, high, or urgent.
Use only the redacted report below. Never request secrets. Do not approve payments,
KYC, refunds, or case closure. If evidence is insufficient, use category
"Needs clarification", confidence below 0.65, and ask one focused question.
Report source: {payload.source}
Language: {payload.language}
Redacted report: {redact_local(payload.summary)}"""
        response = await asyncio.to_thread(
            client.models.generate_content,
            model=model,
            contents=prompt,
            config={"response_mime_type": "application/json"},
        )
        model_output = json.loads(response.text)
        if isinstance(model_output.get("evidence"), str):
            model_output["evidence"] = [model_output["evidence"]]
        if not isinstance(model_output.get("escalation"), str):
            model_output["escalation"] = (
                "Escalate to the assigned human owner when evidence is missing or the issue repeats."
                if not model_output.get("escalation")
                else str(model_output["escalation"])
            )
        parsed = AiResolution.model_validate(model_output)
        result = classify_case(payload, note=payload.summary)
        result.update(parsed.model_dump())
        # Local safety policy always wins over model output.
        lower = payload.summary.lower()
        if any(word in lower for word in ("otp", "pin", "password", "fraud", "scam", "money missing")):
            result["category"] = "Safety / fraud risk"
            result["priority"] = "urgent"
            result["owner"] = "Trust & Safety"
            result["escalation"] = "Escalate immediately. Never request or store an OTP, PIN, or full payment credential."
        elif any(word in lower for word in ("failed", "error", "down", "offline", "network")):
            result["category"] = "Product / connectivity"
            result["owner"] = "Product Support"
        elif any(word in lower for word in ("cash", "settlement", "commission", "payout", "payment")):
            result["category"] = "Settlement / payout"
            result["owner"] = "Payments Operations"
        elif any(word in lower for word in ("kyc", "document", "aadhaar", "pan", "verification")):
            result["category"] = "KYC / onboarding"
            result["owner"] = "Onboarding Desk"
        elif result["confidence"] < 0.65:
            result["category"] = "Needs clarification"
            result["owner"] = "Field Operations"
        result["evidence"] = [*result["evidence"], "Gemini response validated against the typed resolution contract"]
        result["audit"] = [
            {"event": "case_received", "detail": "Redacted report retained locally for this demo session.", "at": now_iso()},
            {"event": "ai_triage_completed", "detail": "Gemini JSON validated; local safety policy applied.", "at": now_iso()},
        ]
        ai_logger.info(
            "AI request succeeded: provider=gemini model=%s duration_ms=%d validation=passed",
            model,
            round((time.perf_counter() - started) * 1000),
        )
        return result, "gemini"
    except Exception as error:
        ai_logger.exception(
            "AI request failed: provider=gemini model=%s duration_ms=%d error=%s",
            model,
            round((time.perf_counter() - started) * 1000),
            type(error).__name__,
        )
        result = classify_case(payload)
        result["audit"].append({"event": "ai_fallback", "detail": f"Gemini unavailable; deterministic rules used ({type(error).__name__}).", "at": now_iso()})
        return result, "local_rules_fallback"


async def classify_with_openrouter(payload: CaseInput) -> tuple[dict, str]:
    """Use OpenRouter chat completions while preserving the local safety boundary."""
    api_key = os.getenv("OPENROUTER_API_KEY")
    model = os.getenv("OPENROUTER_MODEL", "nvidia/nemotron-3.5-super-vl:free")
    if not api_key:
        ai_logger.warning("AI provider unavailable: provider=openrouter reason=missing_api_key")
        return classify_case(payload), "local_rules_no_key"
    started = time.perf_counter()
    ai_logger.info("AI request started: provider=openrouter model=%s source=%s", model, payload.source)
    try:
        import httpx

        prompt = f"""You are Eko Sahayak, an operations triage assistant.
Return ONLY valid JSON with keys: category, priority, owner, root_cause, evidence,
next_action, escalation, confidence. Use priority normal, high, or urgent.
Evidence must be a JSON array of strings. Escalation must be a string.
Use only the redacted report below. Never request secrets. Do not approve payments,
KYC, refunds, or case closure. If evidence is insufficient, use category
"Needs clarification", confidence below 0.65, and ask one focused question.
Report source: {payload.source}
Language: {payload.language}
Redacted report: {redact_local(payload.summary)}"""
        async with httpx.AsyncClient(timeout=35) as client:
            response = await client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "http://localhost:8000",
                    "X-Title": "Eko Sahayak",
                },
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.1,
                    "response_format": {"type": "json_object"},
                },
            )
            response.raise_for_status()
            body = response.json()
        content = body["choices"][0]["message"]["content"]
        if isinstance(content, list):
            content = "".join(part.get("text", "") for part in content if isinstance(part, dict))
        model_output = json.loads(content)
        if isinstance(model_output.get("evidence"), str):
            model_output["evidence"] = [model_output["evidence"]]
        if not isinstance(model_output.get("escalation"), str):
            model_output["escalation"] = "Escalate to the assigned human owner when evidence is missing or the issue repeats."
        parsed = AiResolution.model_validate(model_output)
        result = classify_case(payload)
        result.update(parsed.model_dump())
        lower = payload.summary.lower()
        if any(word in lower for word in ("otp", "pin", "password", "fraud", "scam", "money missing")):
            result["category"] = "Safety / fraud risk"
            result["priority"] = "urgent"
            result["owner"] = "Trust & Safety"
            result["escalation"] = "Escalate immediately. Never request or store an OTP, PIN, or full payment credential."
        elif any(word in lower for word in ("failed", "error", "down", "offline", "network")):
            result["category"] = "Product / connectivity"
            result["owner"] = "Product Support"
        elif any(word in lower for word in ("cash", "settlement", "commission", "payout", "payment")):
            result["category"] = "Settlement / payout"
            result["owner"] = "Payments Operations"
        elif any(word in lower for word in ("kyc", "document", "aadhaar", "pan", "verification")):
            result["category"] = "KYC / onboarding"
            result["owner"] = "Onboarding Desk"
        elif result["confidence"] < 0.65:
            result["category"] = "Needs clarification"
            result["owner"] = "Field Operations"
        result["evidence"] = [*result["evidence"], "OpenRouter response validated against the typed resolution contract"]
        result["audit"] = [
            {"event": "case_received", "detail": "Redacted report retained locally for this demo session.", "at": now_iso()},
            {"event": "ai_triage_completed", "detail": "OpenRouter JSON validated; local safety policy applied.", "at": now_iso()},
        ]
        ai_logger.info(
            "AI request succeeded: provider=openrouter model=%s duration_ms=%d validation=passed",
            model,
            round((time.perf_counter() - started) * 1000),
        )
        return result, "openrouter"
    except Exception as error:
        status_code = getattr(getattr(error, "response", None), "status_code", "none")
        ai_logger.exception(
            "AI request failed: provider=openrouter model=%s duration_ms=%d status=%s error=%s",
            model,
            round((time.perf_counter() - started) * 1000),
            status_code,
            type(error).__name__,
        )
        result = classify_case(payload)
        result["audit"].append({"event": "ai_fallback", "detail": f"OpenRouter unavailable; deterministic rules used ({type(error).__name__}).", "at": now_iso()})
        return result, "local_rules_fallback"


SEED_CASES = [
    {
        "id": "EKO-1018-7F2A", "status": "escalated", "category": "Settlement / payout",
        "priority": "urgent", "owner": "Payments Operations",
        "root_cause": "Settlement is not matching the expected status after a completed transaction.",
        "evidence": ["Field note from 10:42 AM", "Transaction reference is available locally"],
        "next_action": "Verify the reference with Payments Operations before any retry.",
        "escalation": "Escalated because money was debited and the issue is older than 24 hours.",
        "confidence": 0.94, "consent_to_share": True, "created_at": "2026-10-21T10:42:00+05:30",
        "audit": [{"event": "escalated", "detail": "Human review required for money movement.", "at": "2026-10-21T10:45:00+05:30"}],
    },
    {
        "id": "EKO-1018-6B11", "status": "in_review", "category": "KYC / onboarding",
        "priority": "normal", "owner": "Onboarding Desk",
        "root_cause": "The document capture step is incomplete or unreadable.",
        "evidence": ["Voice note transcribed locally", "No identity number stored"],
        "next_action": "Guide the entrepreneur through a fresh, well-lit document capture.",
        "escalation": "Escalate when a mismatch needs manual review.",
        "confidence": 0.82, "consent_to_share": False, "created_at": "2026-10-21T09:18:00+05:30",
        "audit": [{"event": "triage_completed", "detail": "PII minimized before analysis.", "at": "2026-10-21T09:18:03+05:30"}],
    },
    {
        "id": "EKO-1017-2D09", "status": "resolved", "category": "Product / connectivity",
        "priority": "high", "owner": "Product Support",
        "root_cause": "A stale session caused the first attempt to fail on an unreliable connection.",
        "evidence": ["Retry succeeded once", "No repeated incident in the last hour"],
        "next_action": "Close after confirming the entrepreneur can complete the task.",
        "escalation": "Reopen if the issue repeats for more than one user.",
        "confidence": 0.91, "consent_to_share": False, "created_at": "2026-10-17T14:11:00+05:30",
        "audit": [{"event": "resolved", "detail": "Closed after a safe retry.", "at": "2026-10-17T14:18:00+05:30"}],
    },
]


init_db(SEED_CASES, DEMO_USERNAME, DEMO_PASSWORD)


def case_dict(db, case: Case) -> dict:
    events = db.scalars(select(AuditEvent).where(AuditEvent.case_id == case.id).order_by(AuditEvent.id)).all()
    return {
        "id": case.id, "status": case.status, "category": case.category, "priority": case.priority,
        "owner": case.owner, "root_cause": case.root_cause, "evidence": case.evidence,
        "next_action": case.next_action, "escalation": case.escalation, "confidence": case.confidence,
        "consent_to_share": case.consent_to_share, "created_at": case.created_at.isoformat(),
        **({"provider": case.provider} if case.provider else {}),
        "audit": [{"event": event.event, "detail": event.detail, "at": event.at.isoformat()} for event in events],
    }


def create_session(db, user: User) -> tuple[str, dict[str, str]]:
    token = secrets.token_urlsafe(32)
    db.add(Session(token_hash=hash_token(token), user_id=user.id, expires_at=utc_now() + SESSION_TTL))
    return token, public_user(user)


@app.get("/")
async def root():
    react_index = FRONTEND_DIST / "index.html"
    if not react_index.exists():
        raise HTTPException(status_code=503, detail="React build not found. Run npm run build in frontend.")
    return FileResponse(react_index)

@app.get("/assets/{asset_path:path}")
async def react_asset(asset_path: str):
    asset = FRONTEND_DIST / "assets" / asset_path
    if not asset.is_file():
        raise HTTPException(status_code=404, detail="Asset not found")
    return FileResponse(asset)


@app.get("/eko/health")
async def health():
    database = check_database_connection()
    return {
        "status": "ok" if database["connected"] else "degraded",
        "worker": "eko-sahayak",
        "mode": "local-demo",
        "database": database,
    }


@app.post("/eko/auth/login")
async def login(payload: LoginRequest):
    with db_session() as db:
        user = db.scalar(select(User).where(User.username == payload.username.lower()))
        if not user or not password_matches(payload.password, user.password_hash):
            raise HTTPException(status_code=401, detail="Invalid username or password")
        token, user_data = create_session(db, user)
        return {"token": token, "user": user_data}


@app.post("/eko/auth/signup")
async def signup(payload: SignupRequest):
    username = payload.username.lower()
    with db_session() as db:
        if db.scalar(select(User).where(User.username == username)):
            raise HTTPException(status_code=409, detail="Username already exists")
        user = User(name=payload.name.strip(), username=username, role="Field operations",
                    password_hash=password_hash(payload.password))
        db.add(user)
        db.flush()
        token, user_data = create_session(db, user)
        return {"token": token, "user": user_data}


@app.get("/eko/auth/me")
async def me(user: dict[str, str] = Depends(current_user)):
    return {"user": user}


@app.post("/eko/auth/logout")
async def logout(authorization: str | None = Header(default=None)):
    if authorization and authorization.lower().startswith("bearer "):
        with db_session() as db:
            session = db.scalar(select(Session).where(
                Session.token_hash == hash_token(authorization.split(" ", 1)[1].strip())
            ))
            if session:
                db.delete(session)
    return {"ok": True}


@app.post("/eko/voice/transcribe")
async def transcribe_voice(
    audio: UploadFile = File(...),
    _: dict[str, str] = Depends(current_user),
):
    """Transcribe a recorded voice note through Gemini when configured."""
    if audio.content_type not in {"audio/webm", "audio/wav", "audio/mpeg", "audio/mp4", "audio/ogg"}:
        raise HTTPException(status_code=415, detail="Unsupported audio format")
    audio_bytes = await audio.read()
    if not audio_bytes or len(audio_bytes) > 10 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Audio must be between 1 byte and 10 MB")
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise HTTPException(
            status_code=503,
            detail="Server transcription is not configured. Use browser transcription or configure GEMINI_API_KEY.",
        )
    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=api_key)
        prompt = (
            "Transcribe this field operations voice note exactly. Return only the "
            "transcript text, preserving the speaker's language. Do not add explanations."
        )
        response = await asyncio.to_thread(
            client.models.generate_content,
            model=os.getenv("GEMINI_TRANSCRIPTION_MODEL", "gemini-2.5-flash"),
            contents=[prompt, types.Part.from_bytes(data=audio_bytes, mime_type=audio.content_type)],
        )
        transcript = (response.text or "").strip()
        if len(transcript) < 8:
            raise ValueError("empty transcription")
        return {"transcript": transcript, "provider": "gemini"}
    except HTTPException:
        raise
    except Exception as error:
        raise HTTPException(status_code=502, detail=f"Voice transcription failed: {type(error).__name__}")


@app.get("/eko/cases")
async def list_cases(user: dict[str, str] = Depends(current_user)):
    with db_session() as db:
        rows = db.scalars(select(Case).where(Case.user_id == user["id"]).order_by(Case.created_at.desc())).all()
        cases = [case_dict(db, case) for case in rows]
        return {"cases": cases, "summary": {"open": sum(c["status"] in ("new", "in_review", "escalated") for c in cases),
                                            "urgent": sum(c["priority"] == "urgent" for c in cases),
                                            "resolved": sum(c["status"] == "resolved" for c in cases)}}


@app.post("/eko/analyze")
async def analyze(payload: CaseInput, user: dict[str, str] = Depends(current_user)):
    provider_name = os.getenv("AI_PROVIDER", "openrouter").lower()
    if provider_name == "gemini":
        result, provider = await classify_with_gemini(payload)
    else:
        result, provider = await classify_with_openrouter(payload)
    result["provider"] = provider
    ai_logger.info("AI decision recorded: case_id=%s provider=%s", result["id"], provider)
    with db_session() as db:
        db.add(Case(id=result["id"], user_id=user["id"], status=result["status"], category=result["category"],
                    priority=result["priority"], owner=result["owner"], root_cause=result["root_cause"],
                    evidence=result["evidence"], next_action=result["next_action"], escalation=result["escalation"],
                    confidence=result["confidence"], consent_to_share=result["consent_to_share"],
                    provider=provider, created_at=datetime.fromisoformat(result["created_at"])))
        db.flush()
        for event in result["audit"]:
            db.add(AuditEvent(case_id=result["id"], user_id=user["id"], event=event["event"],
                              detail=event["detail"], at=datetime.fromisoformat(event["at"])))
        db.flush()
        return case_dict(db, db.get(Case, result["id"]))


@app.patch("/eko/cases/{case_id}")
async def update_case(case_id: str, payload: CaseStatus, user: dict[str, str] = Depends(current_user)):
    with db_session() as db:
        case = db.scalar(select(Case).where(Case.id == case_id, Case.user_id == user["id"]))
        if not case:
            raise HTTPException(status_code=404, detail="Case not found")
        previous = case.status
        case.status = payload.status
        db.add(AuditEvent(case_id=case.id, user_id=user["id"], event="status_changed",
                          detail=f"{previous} → {payload.status}", at=utc_now()))
        db.flush()
        return case_dict(db, case)


@app.get("/eko/audit")
async def audit(user: dict[str, str] = Depends(current_user)):
    with db_session() as db:
        events = db.scalars(select(AuditEvent).where(AuditEvent.user_id == user["id"]).order_by(AuditEvent.id)).all()
        return {"events": [{"case_id": event.case_id, "event": event.event, "detail": event.detail,
                            "at": event.at.isoformat()} for event in events]}
