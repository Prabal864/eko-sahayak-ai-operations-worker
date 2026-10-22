# Eko Sahayak — Assignment Submission Document

## Project Name

**Eko Sahayak — AI Operations & Resolution Worker**

## Assignment Direction

This project combines the email's:

- Micro-Entrepreneur RCA / Operations Worker
- Support Resolution Worker
- Device-Constrained AI Worker

The worker accepts an operational report and produces a structured, explainable, human-reviewed resolution case.

## Goal

Reduce the time from an unstructured field or support report to a safe, owned next action. The intended business improvement is faster routing, more consistent triage, safer escalation, and better operational visibility.

## User

The primary user is a field operator or support team member helping a micro-entrepreneur or MSME. Secondary users are Payments Operations, Product Support, Onboarding, Trust & Safety, and operations managers.

## System

The worker operates inside this larger workflow:

```text
Capture → Minimize → Triage → Review → Act → Verify → Resolve or Escalate
```

The bounded responsibility of Eko Sahayak is **capture to a structured resolution recommendation and human handoff**.

## Inputs

- Support issue
- Field visit note
- Activity log
- Voice-note transcript
- Language preference: English, Hindi, or Hinglish
- Source type
- Optional consent to share a non-identifying summary

The current version accepts text. Audio recording and speech-to-text are planned for the next version.

## Outputs

- Case ID
- Category
- Priority
- Likely owner
- Root cause or clarification requirement
- Evidence used
- Recommended next action
- Escalation path
- Confidence score
- Workflow status
- Provider metadata
- Audit events

## Decisions

The worker can recommend classification, priority, owner, root cause, evidence, next action, clarification questions, and escalation. It cannot make consequential business decisions without a human.

## Constraints

The worker must not move money, approve KYC, approve refunds, request OTPs/PINs/passwords, close risky cases, contact customers without approval, or present low-confidence guesses as facts.

## Device Constraint

The design targets low-end laptops, shared desktops, and mobile browsers with unreliable connectivity, small screens, low digital comfort, and local-language needs. The deterministic fallback requires no model download and keeps the basic workflow usable when the AI provider is unavailable.

## Definition of Done

A case is complete when it has a clear owner, action, evidence, confidence, escalation rule, human decision, final status, and audit record. A risky or uncertain case is not complete merely because a model returned text.

## Privacy / DPDP Design

Raw notes should remain local wherever possible. OTPs, PINs, passwords, full payment credentials, identity numbers, and unnecessary personal data must not be shared. The prototype redacts common PII patterns before the OpenRouter request, captures sharing consent separately, and records only non-identifying operational metadata in audit events.

Production work still required includes encryption at rest, retention and deletion, access controls, consent expiry, data-subject rights, purpose limitation, and provider data-processing review.

## Escalation

Stop and ask a human when the report indicates fraud, OTP/PIN exposure, missing money, payment risk, KYC mismatch, repeated failures, multiple affected users, missing evidence, invalid AI output, or low confidence.

## Success Metrics

- Time to assigned owner
- Time to recommended next action
- Correct owner-routing rate
- Safety/payment escalation recall
- Unsupported-claim rate
- Clarification accuracy
- Confidence calibration
- Audit completeness
- Human correction rate
- AI cost per case
- Fallback success rate

## Current Autonomous Capabilities

The current version can redact common PII, call OpenRouter, validate structured JSON, normalize categories, assign priority and owner, create a case, recommend an action, record confidence, write audit events, and use local rules when the provider fails.

## Human-Led Responsibilities

Humans confirm root cause, gather sensitive evidence safely, contact the entrepreneur, move money, approve KYC or refunds, escalate fraud, and close consequential cases.

## Intentional Failure Scenario

Input:

```text
It is not working.
```

Expected behavior:

- Category: Needs clarification
- Low confidence
- Field Operations owner
- One focused question
- No invented root cause

## Next Version

Add SQLite persistence, local speech-to-text, approved-procedure retrieval, formal evaluation dashboards, human feedback capture, consent expiry, deletion workflows, and calibrated confidence.

## Submission Positioning

> Eko Sahayak is a local-first, explainable AI Operations and Resolution Worker inspired by Eko's Micro-Entrepreneur RCA / Operations Worker and Support Resolution Worker directions. It converts unstructured operational reports into safe, auditable, human-reviewed next actions.
