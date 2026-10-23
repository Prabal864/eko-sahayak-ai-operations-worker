# Eko Sahayak — AI Operations & Resolution Worker

Local-first AI worker for Eko field and support operations. It turns an
operational report into a structured, auditable, human-reviewed next action.

## Repository layout

```text
backend/       FastAPI API, AI adapter, policy rules, environment template
frontend/      React/Vite application
tests/         Backend acceptance tests
sample_data/   Synthetic inputs and expected behavior
knowledge_base/Approved operational guidance used by future retrieval
docs/          Assignment, architecture, privacy, evaluation, and demo docs
```

## Documentation

- [Assignment brief and complete system definition](docs/ASSIGNMENT.md)
- [Architecture and workflow](docs/ARCHITECTURE.md)
- [Prompt, rules, APIs, and tool usage](docs/IMPLEMENTATION.md)
- [Privacy and DPDP design](docs/PRIVACY_DPDP.md)
- [Evaluation plan and test cases](docs/EVALUATION.md)
- [Demo script and submission checklist](docs/DEMO_SCRIPT.md)

Eko Sahayak is a working, local-first FastAPI prototype for bounded operations triage. It turns a field note, support issue, voice-note transcript, or activity event into a structured resolution brief: likely root cause, evidence, impact priority, owner, next action, escalation path, and an auditable workflow state.

## Run it

### FastAPI backend

```powershell
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --reload
```

Create `.env` in the project root from `backend\.env.example`. The backend is
configured for OpenRouter by default through `.env`:
`AI_PROVIDER=openrouter`, `OPENROUTER_API_KEY`, and `OPENROUTER_MODEL`.
OpenRouter is used only to structure the redacted report; local safety rules
override model output, and deterministic rules remain available as a fallback.
Gemini remains supported by setting `AI_PROVIDER=gemini`. Never commit `.env`.

### Docker backend

Build from the repository root using the backend directory as the Docker
context:

```powershell
docker build -f backend\Dockerfile -t eko-sahayak-backend backend
docker run --rm -p 8000:8000 --env-file .env eko-sahayak-backend
```

The image runs as a non-root user and exposes port `8000`. The `.env` file is
passed at runtime and is never copied into the image. For PostgreSQL, keep
`DATABASE_URL` in the runtime environment and ensure the database accepts the
container's network connection. The image uses `requirements-runtime.txt`, so
test dependencies are not installed in production.

### Login

The dashboard requires a backend session. Copy `backend\.env.example` to
`.env`, set `EKO_DEMO_USERNAME` and `EKO_DEMO_PASSWORD`, then sign in with
those credentials. The default local demo credentials are `prabal` / `eko-demo`
when the variables are not configured. Case, audit, and status APIs require a
valid bearer session; health and login remain public. Use **Log out** in the
header or sidebar to invalidate the backend session and clear the browser token.
New operators can use **Sign up** on the login screen. Signup validates the
username and password, hashes the password before storing it, creates a local
session, and opens the dashboard immediately. Accounts, sessions, cases,
and audit events are now persisted with SQLAlchemy. Without `DATABASE_URL`, the
app uses `data\eko_sahayak.db` (SQLite); set `DATABASE_URL` to a PostgreSQL URL
for PostgreSQL deployments. Passwords are PBKDF2-hashed, bearer tokens are
stored only as SHA-256 hashes, and sessions expire after 12 hours.

### Voice input

On **New case**, choose **Add voice note**, allow microphone access, speak the
operational update, and select **Stop recording**. Supported browsers add a
local browser transcript immediately. The recorded audio is also sent to the
authenticated backend for Gemini transcription when `GEMINI_API_KEY` is
configured. If server transcription is unavailable, the browser transcript
or typed note can still be analyzed. Use synthetic data only and never speak
OTPs, PINs, passwords, full account numbers, or unnecessary personal details.

### React frontend

For local development, Vite proxies `/api` requests to the local backend.
Production builds use `https://api.prabalsingh.dev` by default. To override
the API origin, set `VITE_API_BASE_URL` in the frontend environment before
building, for example:

```text
VITE_API_BASE_URL=https://api.prabalsingh.dev
```

The API domain must forward requests to the FastAPI container on port `8000`
and expose the backend health endpoint at
`https://api.prabalsingh.dev/api/health`.

Node.js 20+ is required for the frontend:

```powershell
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`. Vite proxies `/api` requests to FastAPI on port `8000`.

For a single-server production-style run, build the React app and start FastAPI:

```powershell
cd frontend
npm run build
cd ..
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --reload
```

FastAPI serves `frontend/dist` at `http://127.0.0.1:8000` when that build exists.

## System definition

**Goal:** reduce time from an unstructured field report to a safe, owned next action. **User:** field operators and support leads working with micro-entrepreneurs on low-end laptops or shared phones. **System:** capture → triage → act → verify → close/escalate. **Inputs:** a short note, source, language, and optional consent. **Outputs:** explainable classification, evidence, owner, priority, next action, escalation rule, status, and audit event.

The current worker is intentionally deterministic and offline-safe. It can recommend and structure; it cannot move money, approve KYC, contact a customer, or close a risky case autonomously. Safety/fraud, money movement, low confidence, missing evidence, or repeated failures stop the workflow and require a human.

## Privacy, DPDP, and constrained-device design

Raw notes are kept in the demo process and are not sent to a third-party model. The UI explicitly warns against OTPs, PINs, full account numbers, and unnecessary identity details. Sharing consent is captured separately from operational processing, and the UI shows whether a case can be shared. A production version should add on-device redaction, encryption at rest, consent expiry, purpose limitation, retention deletion, access logs, and a user-access/deletion flow.

The interface is responsive, keyboard-friendly, low-bandwidth, and uses plain language. The resolution engine has no model download or external dependency, making it viable as a fallback on a low-end device. An intentional failure scenario is a vague note such as “it is not working”: the worker selects “Needs clarification” with low confidence and asks one focused question rather than hallucinating a cause.

## Evaluation plan

Track: time-to-owned-action, correct owner routing, escalation recall for safety/payment cases, unsupported-claim rate, clarification rate, and percent of cases with a complete audit trail. The fixtures below represent the first evaluation slice:

| Input | Expected behavior |
| --- | --- |
| “Money debited but commission not received” | Payment Operations, high/urgent, verify reference, escalate after 24h |
| “OTP was shared and money is missing” | Trust & Safety, urgent, immediate human escalation |
| “KYC photo keeps failing” | Onboarding Desk, normal, recapture guidance |
| “It is not working” | Needs clarification, low confidence, ask one focused question |

Run the automated acceptance tests from the project root:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

The repository currently has no deployed prototype or video URL. Add the
working demo URL and short video link to `docs/DEMO_SCRIPT.md` before sending
the submission.

## Demo flow

1. Open **Operations desk** and review the seeded queue.
2. Select **New case**, paste the payment or vague-note example, and analyze it.
3. Open the generated case to inspect evidence, confidence, owner, escalation, and status transition.
4. Open **Audit trail** to show traceability.

**Next version:** replace the rule adapter with a small, privacy-reviewed model behind the same typed contract; add local speech-to-text, retrieval over approved operating procedures, calibrated confidence, human feedback, and a replayable evaluation harness.
