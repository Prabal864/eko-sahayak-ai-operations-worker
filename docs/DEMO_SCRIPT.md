# Eko Sahayak — Demo Script and Submission Checklist

## Demo Goal

Show that Eko Sahayak converts an unstructured operational report into a safe, structured, auditable, human-reviewed next action.

## Demo Duration

Three to five minutes.

## Setup

```powershell
cd C:\Users\940pp\PycharmProjects\FastAPIProject2
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --reload
```

In a second terminal:

```powershell
cd C:\Users\940pp\PycharmProjects\FastAPIProject2\frontend
npm run dev
```

Open:

```text
http://127.0.0.1:5173
```

## Recording Sequence

### 1. Introduce the problem

Say:

> Field and support teams often receive short, incomplete operational reports. Eko Sahayak turns those reports into an explainable resolution brief without giving the AI authority over money, KYC, or case closure.

### 2. Show the Operations Desk

Point out:

- Open cases
- Urgent cases
- Resolved cases
- Owner routing
- Case statuses

### 3. Create a Payment Case

Input:

```text
The merchant says a customer paid, but the settlement has not arrived since yesterday.
```

Show:

- Settlement / payout
- Payments Operations
- Root cause
- Evidence
- Next action
- Confidence
- Escalation path

Point out the audit event:

```text
AI Triage Completed
```

### 4. Demonstrate Human Control

Change the case status to `Escalated` and save it. Open the Audit Trail and show the status-change event.

Say:

> The AI recommends. A human decides whether the case is resolved or escalated.

### 5. Demonstrate Intentional Failure

Create:

```text
It is not working.
```

Show:

- Needs clarification
- Low confidence
- Field Operations
- Focused clarification question

Say:

> The worker does not invent a root cause when evidence is missing.

### 6. Demonstrate Safety Escalation

Create:

```text
The entrepreneur shared an OTP and now money is missing.
```

Show:

- Safety / fraud risk
- Urgent priority
- Trust & Safety
- Immediate escalation

### 7. Explain Privacy

Point out:

- PII warning
- Consent checkbox
- Redaction before AI provider call
- Local fallback
- Auditability

### 8. Close

Say:

> Eko Sahayak is a bounded, local-first operations worker. It improves triage speed and consistency while keeping risky decisions human-led.

## Submission Checklist

- [x] Working React frontend
- [x] Working FastAPI backend
- [x] OpenRouter integration
- [x] Structured AI response validation
- [x] Local safety rules
- [x] Local fallback
- [x] Workflow states
- [x] Audit trail
- [x] Privacy design
- [x] Device-constrained design
- [x] Intentional failure scenario
- [x] Evaluation plan
- [ ] Record and attach demo video
- [ ] Add persistent SQLite storage
- [ ] Rotate exposed API key before sharing

## Submission Links to Include

```text
Repository: <GitHub repository URL>
Demo video: <video URL>
Live demo or local run instructions: README.md
Documentation: docs/ASSIGNMENT.md, docs/ARCHITECTURE.md,
docs/IMPLEMENTATION.md, docs/PRIVACY_DPDP.md, docs/EVALUATION.md
```

## Honest Scope Statement

This is a working prototype, not a production deployment. It demonstrates the workflow contract, human safety boundary, provider fallback, privacy intent, and audit design. Persistence, actual voice ingestion, formal field evaluation, and complete production DPDP controls are next-version work.
