# Eko Sahayak — Privacy and DPDP Design

## Privacy Principle

Collect the minimum information needed to route and resolve an operational issue. Keep personal and sensitive data local unless an approved purpose, consent, and operational need exist.

## Data Classification

| Data | Handling |
| --- | --- |
| Operational summary | Minimize and redact before AI call |
| Raw voice note | Keep local in a future voice version |
| OTP, PIN, password | Never request or share |
| Full payment credentials | Never request or share |
| Identity numbers | Avoid; redact when detected |
| Phone/email | Redact unless explicitly required and approved |
| Category, owner, priority | May be used as non-identifying operational metadata |
| Aggregated resolution metrics | May flow to Eko for improvement |

## Consent

Consent to share a non-identifying summary is a separate field from using the worker locally. The UI shows whether consent exists. Production must record purpose, timestamp, scope, expiry, and withdrawal.

## AI Boundary

Only a redacted operational report is sent to the configured AI provider. The model receives no direct authority to execute payment, KYC, refund, customer-contact, or closure actions.

## Retention

The prototype keeps state in memory for the demo. A production implementation must define:

- Maximum retention duration
- Automated deletion
- Case-specific deletion
- Audit retention
- Backup deletion
- Consent expiry
- Data export and access request handling

## Security Controls Needed for Production

- TLS for all network traffic
- Encryption at rest
- Secret manager instead of local `.env`
- Role-based access
- Operator authentication
- Rate limiting
- Provider allow-list
- Prompt-injection controls
- Structured output validation
- Audit access monitoring
- Incident response process

## Threats Considered

- Accidental PII entry
- Prompt injection in field notes
- Hallucinated root causes
- Provider outage
- Unauthorized status updates
- Over-sharing audit data
- Model output that attempts a prohibited action

## Safe Defaults

- Local rules remain available if AI fails.
- Low confidence produces clarification.
- High-risk language triggers human escalation.
- Audit events record provider and fallback use.
- Secrets are excluded from source control.

## Important Limitation

The current redaction is pattern-based and should not be treated as complete DPDP compliance. A production version requires a reviewed data inventory, threat model, retention policy, access model, legal review, and provider agreement.
