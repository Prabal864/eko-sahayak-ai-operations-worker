# Eko Sahayak — Evaluation Plan

## Objective

Measure whether the worker improves operational triage without increasing unsafe or unsupported decisions.

## Metrics

| Metric | Definition |
| --- | --- |
| Owner accuracy | Correct owner divided by total labeled cases |
| Category accuracy | Correct category divided by total labeled cases |
| Escalation recall | Risky cases escalated divided by all labeled risky cases |
| Unsupported-claim rate | Cases containing unsupported claims divided by total cases |
| Clarification accuracy | Vague cases correctly requesting missing information |
| Confidence calibration | Whether confidence tracks correctness |
| Audit completeness | Cases with required audit events |
| Time to next action | Input timestamp to actionable recommendation |
| Fallback success | Valid cases returned during provider failures |
| Human correction rate | Cases requiring operator correction |
| Cost per AI case | Provider cost per analyzed case |

## Acceptance Test Matrix

| Input | Expected category | Expected owner | Expected behavior |
| --- | --- | --- | --- |
| Money debited but payout missing | Settlement / payout | Payments Operations | Request reference and consider escalation |
| OTP shared and money missing | Safety / fraud risk | Trust & Safety | Urgent human escalation |
| KYC photo keeps failing | KYC / onboarding | Onboarding Desk | Recapture guidance |
| App failed after network went offline | Product / connectivity | Product Support | Safe retry and error capture |
| It is not working | Needs clarification | Field Operations | Ask one focused question |

## Negative Tests

1. Short input returns HTTP `422`.
2. Unknown source is rejected.
3. Unknown language is rejected.
4. Invalid status is rejected.
5. Provider outage returns local fallback.
6. Invalid model JSON returns local fallback.
7. OTP and PIN language cannot change the local urgent safety policy.
8. Connectivity language wins over a conflicting settlement keyword.
9. Low-confidence model output is normalized to clarification.
10. Status changes create audit events.

## Manual Test Flow

1. Start FastAPI and Vite.
2. Open the Operations Desk.
3. Create one payment case.
4. Confirm provider is `openrouter` or fallback is explicitly recorded.
5. Open the case and inspect evidence, confidence, owner, action, and escalation.
6. Change status to `escalated`.
7. Open Audit Trail and verify both AI and status events.
8. Create the vague case and confirm clarification behavior.
9. Create the fraud case and confirm urgent Trust & Safety routing.

## Definition of Evaluation Success

The prototype passes when all expected categories and owners are returned, high-risk cases are escalated, vague cases do not hallucinate, all responses match the schema, status changes are auditable, and provider failure does not destroy the workflow.

## Known Evaluation Limits

The current test data is synthetic and small. It does not yet measure Hindi/Hinglish quality, real voice transcription quality, retrieval quality, long-term learning, or real field time saved. These require labeled field data collected with consent and a reviewed evaluation protocol.
