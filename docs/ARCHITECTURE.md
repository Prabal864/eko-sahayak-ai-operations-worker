# Eko Sahayak — Architecture and Workflow

## Architecture

```text
React + Vite
    ↓
FastAPI REST API
    ↓
Input validation and PII redaction
    ↓
OpenRouter structured-output request
    ↓
Pydantic response validation
    ↓
Local safety and category normalization
    ↓
Resolution case and audit events
    ↓
Human review and status transition
```

## Components

| Component | Responsibility |
| --- | --- |
| React frontend | Dashboard, intake form, case detail, audit trail |
| Vite | Frontend development server and API proxy |
| FastAPI | API contract, orchestration, validation, workflow state |
| OpenRouter | Optional AI language understanding |
| Local classifier | Explainable fallback and policy enforcement |
| Pydantic | Typed request and AI response validation |
| In-memory store | Prototype case and audit state |

## Workflow States

```text
New → In review → Resolved
              ↘ Escalated
```

`New` is the captured report. `In review` means a structured recommendation exists. `Resolved` and `Escalated` are human decisions.

## Case Lifecycle

1. Operator enters a report.
2. FastAPI validates source, language, length, and consent.
3. Common PII patterns are redacted locally.
4. OpenRouter receives only the minimized prompt.
5. JSON response is validated against the resolution contract.
6. Local safety rules override model output where required.
7. A case and audit events are created.
8. A human reviews and changes status.
9. The audit trail records the status transition.

## Safety Boundary

The AI is advisory. Local policy always wins for fraud, OTP/PIN, missing money, high-risk payments, and low-confidence output. The worker never performs money movement, KYC approval, refunds, or autonomous closure.

## Failure Path

```text
OpenRouter success → Validate → Normalize → Return
OpenRouter error   → Local rules → Record fallback → Return
Invalid input      → HTTP 422
Low confidence     → Needs clarification → Human follow-up
```

## State Strategy

The prototype uses an in-memory list. This keeps the demo lightweight but resets data on restart. The production state store should be SQLite first, with tables for cases, events, consent, feedback, and evaluation runs.
