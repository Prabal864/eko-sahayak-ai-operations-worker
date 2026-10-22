# Eko Sahayak — Implementation Notes

## AI Provider

The active provider is OpenRouter. Configuration is stored in `.env` and excluded from source control:

```env
AI_PROVIDER=openrouter
OPENROUTER_API_KEY=replace-with-your-key
OPENROUTER_MODEL=nvidia/nemotron-3.5-super-vl:free
```

The provider can be changed without changing the frontend contract. Gemini remains available as an optional backend provider through `AI_PROVIDER=gemini`.

## Prompts, Rules, Logic, or Agent Instructions Used

This section directly documents the prompt, rules, logic, and agent
instructions used by the worker, as requested in the assignment email.

### Agent instruction

The provider receives only the redacted report and is instructed to follow
this bounded workflow:

```text
You are Eko Sahayak, an operations triage assistant.
Return ONLY valid JSON with keys: category, priority, owner, root_cause,
evidence, next_action, escalation, confidence.
Use priority normal, high, or urgent.
Use only the redacted report below.
Never request secrets.
Do not approve payments, KYC, refunds, or case closure.
If evidence is insufficient, use category "Needs clarification",
confidence below 0.65, and ask one focused question.
```

The application validates the returned JSON and applies local safety rules
after the provider response. The model cannot override those safety rules.

### Prompt contract

The model receives a redacted operational report and is instructed to return only JSON with:

```json
{
  "category": "string",
  "priority": "normal | high | urgent",
  "owner": "string",
  "root_cause": "string",
  "evidence": ["string"],
  "next_action": "string",
  "escalation": "string",
  "confidence": 0.0
}
```

The prompt instructs the model to use `Needs clarification` and confidence below `0.65` when evidence is insufficient, never request secrets, and never approve payments, KYC, refunds, or closure.

## Local Rules

Local rules recognize:

- Fraud, scams, OTP, PIN, password, and missing-money language
- Payment, payout, settlement, commission, and cash language
- KYC and document language
- Connectivity, network, offline, error, and failure language

Connectivity signals take precedence over business-domain signals when both appear. Vague reports remain clarification cases.

## PII Redaction

The prototype redacts common patterns for long numeric identifiers, ten-digit phone numbers, secret labels with numeric values, and email addresses before the provider request. This is a prototype guardrail, not a complete PII detector.

## APIs

| Method | Endpoint | Purpose |
| --- | --- | --- |
| GET | `/api/health` | Service health |
| GET | `/api/cases` | Cases and summary counts |
| POST | `/api/analyze` | Analyze and create a case |
| PATCH | `/api/cases/{case_id}` | Update human workflow status |
| GET | `/api/audit` | Retrieve audit events |

Swagger documentation is available at `/docs`.

## Provider Metadata

Every analyzed case records one of:

- `openrouter`
- `gemini`
- `local_rules_fallback`
- `local_rules_no_key`

This makes provider use visible to the operator and evaluator.

## Tool/API Usage

- React and React DOM for the frontend
- Vite for frontend development/build
- FastAPI for the backend
- Pydantic for typed contracts
- OpenRouter Chat Completions API for optional AI analysis
- Python dotenv for local environment configuration

No CRM, payment, KYC, WhatsApp, or external retrieval system is connected in the current version.
