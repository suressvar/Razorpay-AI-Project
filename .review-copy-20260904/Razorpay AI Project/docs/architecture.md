# Recovery Autopilot — Architecture Specification

## 1. Executive Summary

**Recovery Autopilot** is an autonomous, safety-bounded subscription recovery agent designed for Razorpay merchants. When recurring subscription charges fail, merchants typically rely on blunt cron retries or spam customer notifications, causing payment fatigue, involuntary churn, and merchant revenue loss.

Recovery Autopilot solves this by:
1. Ingesting failed payment signals and webhooks.
2. Diagnosing the underlying root cause with an AI model (Gemini 3.7 Flash or local Ollama).
3. Formulating a bounded recovery proposal.
4. Subjecting every proposal to a deterministic policy guardrail.
5. Safely executing only policy-approved actions in test mode.
6. Proving incremental recovery lift against a fixed-rule baseline via deterministic simulation.

---

## 2. Core Architectural Boundary

```text
       ┌───────────────┐
       │ AI Model      │  Proposes bounded intervention (action, confidence, delay, reason)
       └───────┬───────┘
               │  Strictly typed Pydantic RecoveryProposal (NO execution privilege)
               ▼
       ┌───────────────┐
       │ Deterministic │  Validates limits, frequency caps, amount thresholds & customer state
       │ Safety Policy │
       └───────┬───────┘
               │  PolicyDecision: ALLOWED, ADJUSTED, BLOCKED, or ESCALATED TO HUMAN
               ▼
       ┌───────────────┐
       │ Safe Executor │  Executes approved test-mode Razorpay / simulated notification
       └───────────────┘
```

### Safety Invariants

The AI model **MUST NEVER**:
- **Directly call Razorpay or any financial API.** All execution happens strictly through sandboxed, policy-gated adapters.
- **Change payment amounts.** Billing amounts are immutable properties of the original failed payment context.
- **Circumvent contact limits.** A maximum of 3 contacts per recovery lifecycle and minimum 24-hour spacing are enforced deterministically.
- **Approve its own high-value actions.** Any case exceeding `HUMAN_REVIEW_THRESHOLD_INR` (default: ₹15,000) or with confidence below `MIN_CONFIDENCE_THRESHOLD` (0.70) mandates manual human operator sign-off.
- **Process real customer PII in development or simulation.** Synthetic PII masks are enforced across all demo and evaluation flows.

---

## 3. Component Overview

| Layer | Responsibility | Technology |
| :--- | :--- | :--- |
| **Domain Layer** | Typed models, controlled enums, and immutability invariants | Pydantic v2 |
| **Model Layer** | Root-cause diagnosis, structured action proposal, message drafting | Gemini 3.7 Flash / Ollama / FakeProvider |
| **Policy Layer** | Deterministic guardrails, business rules, threshold checks | Pure Python state validation engine |
| **Workflow Layer** | Case state machine (`NEW` to `RECOVERED` / `STOPPED`) | Pure Python state machine |
| **Integration Layer** | Razorpay test mode SDK, HMAC webhook verification, simulated notification bus | `razorpay`, `httpx`, HMAC SHA256 |
| **Application Layer** | REST API, async database persistence, Celery background tasks | FastAPI, SQLAlchemy 2.0 (async), Celery, Redis |
| **Frontend Layer** | Real-time recovery dashboard, human-review queue, evaluation analytics | React, TypeScript, Vite, Tailwind CSS, Recharts |

---

## 4. Configuration Matrix

The application is controlled by typed environment variables defined in `recovery_autopilot.config.Settings`:

| Variable | Default | Purpose |
| :--- | :--- | :--- |
| `ENVIRONMENT` | `development` | Deployment environment flag |
| `DATABASE_URL` | `sqlite+aiosqlite:///./recovery_autopilot.db` | Storage URI (PostgreSQL or SQLite) |
| `REDIS_URL` | `redis://localhost:6379/0` | Celery broker and result backend |
| `USE_IN_PROCESS_WORKER` | `true` | Allows zero-dependency local execution without Celery/Redis |
| `MODEL_PROVIDER` | `fake` | Model provider: `gemini`, `ollama`, or `fake` |
| `GEMINI_MODEL` | `gemini-3.7-flash` | Primary cloud model target |
| `OLLAMA_MODEL` | `qwen3:8b` | Optional local model target |
| `RAZORPAY_KEY_ID` | `rzp_test_simulation_key` | Razorpay test mode API key |
| `RAZORPAY_WEBHOOK_SECRET` | `rzp_whsec_simulation_key` | HMAC SHA256 secret for webhook verification |
| `SYNTHETIC_MODE` | `true` | Enforces mock customer data and sandboxed calls |
| `HUMAN_REVIEW_THRESHOLD_INR`| `15000.0` | Mandates human sign-off for invoice amounts ≥ ₹15,000 |
| `MIN_CONFIDENCE_THRESHOLD` | `0.70` | Mandates human sign-off if AI confidence < 70% |
| `MAX_CONTACT_ATTEMPTS` | `3` | Absolute contact ceiling per recovery case |
| `MIN_HOURS_BETWEEN_CONTACTS`| `24` | Contact spacing cooldown |
