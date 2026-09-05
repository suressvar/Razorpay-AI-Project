# Razorpay Recovery Autopilot

Recovery Autopilot is an automated payment recovery engine built for subscription merchants using Razorpay. It detects recurring payment failures, diagnoses root causes, proposes policy-bounded recovery actions, and reconciles subsequent payments into an immutable recovery ledger.

This project addresses revenue loss caused by failed recurring transactions, such as bank timeouts, card expirations, and mandate revocations. It aligns with the objectives of Track 03 (AI Revenue Recovery) by replacing indiscriminate retries and generic email blasts with adaptive, guardrailed workflows. This repository is an independent Buildathon entry and is not officially affiliated with or endorsed by Razorpay.

---

## The Problem

Recurring billing failures in India represent a major operational friction. Subscription renewals frequently fail due to banking gateway timeouts, insufficient balances around billing dates, expired cards, or mandate cancellations under Reserve Bank of India e-mandate regulations.

Standard merchant systems either retry cards repeatedly at fixed intervals or broadcast generic reminder emails. Blind retries often fail when a card is expired or funds are absent, incurring gateway fees and triggering fraud rate limits. Generic emails suffer from low open rates and lack contextual explanations.

For an illustrative example: an annual subscription payment of 4,999 INR that fails at 03:00 due to a scheduled bank downtime should not be retried five times until the subscription halts. A more effective approach pauses retries during the downtime, re-attempts the charge when the bank recovers, or offers an instant Unified Payments Interface (UPI) payment link during business hours.

---

## How the Application Works

The recovery workflow follows seven structured steps:

1. **Ingest Failure Event**: The system receives a `payment.failed` webhook. Raw body signature is verified using HMAC-SHA256, and the event is written to a durable database queue within 50 milliseconds.
2. **Correlate Payment Context**: A background worker leases the job and matches the case using exact identifiers across payment ID, subscription ID, order ID, or customer ID.
3. **Diagnose Root Cause**: The system classifies the failure into established categories, including bank timeout, insufficient funds, expired card, or customer action required.
4. **Propose Recovery Action**: An action plan is generated, such as smart retrying, sending a localized payment link, or initiating a voice follow-up.
5. **Enforce Safety Guardrails**: The proposed intervention passes through a deterministic policy engine that checks Do Not Disturb (DND) status, enforces minimum cooling-off intervals, and caps contact attempts at three. High-value cases (15,000 INR and above) are routed to a human review queue.
6. **Execute Intervention**: Once approved, the system generates an idempotent Razorpay test-mode payment link or dispatches a simulated notification.
7. **Reconcile and Update Ledger**: When a `payment.captured` or `order.paid` webhook arrives, the system validates the amount and marks the case as recovered. Revenue is only credited to the ledger after explicit gateway capture confirmation; generated payment links are never counted as recovered revenue.

---

## What AI Does and What Code Controls

Language models and deterministic code handle strictly separated responsibilities:

- **Language Model Tasks**: A configured language model (OpenAI, Gemini, or Ollama) analyzes failure codes and interaction history to summarize diagnostic evidence and draft customer explanations.
- **Deterministic Code Tasks**: The `SafetyPolicyEngine` controls financial rules, retry cooldowns, contact frequency limits, amount tolerances, and execution permissions. The model has no write access to the database and cannot directly call payment gateway APIs.
- **Human Approval Requirements**: Cases involving financial discrepancies, amounts exceeding 15,000 INR, or unknown failure codes require explicit human operator approval through the review dashboard.
- **Handling Model Uncertainty**: If an external model call fails, times out, or returns an unparseable response, the system automatically falls back to a deterministic, rule-based decision tree.

---

## Implemented Features

| Feature | Purpose | Current Implementation Status |
| :--- | :--- | :--- |
| Exact Payment Correlation | Matches webhooks across multiple identifiers with zero guessing | Working (Verified by integration tests) |
| Durable Webhook Queue | Database-backed queue with row leasing, bounded retries, and dead-letter storage | Working (Fast-path ACK under 50ms) |
| Deterministic Safety Engine | Enforces DND lists, cooling-off windows, and attempt limits | Working (Zero policy violations across test runs) |
| Operator Review Queue | Four-eyes approval interface for high-value and flagged transactions | Working (Rejects version-mismatched approvals) |
| Support Diagnostic Copilot | Assistant that cross-references payment records and generates links | Working (Interactive in dashboard) |
| Multilingual Speech Engine | Vernacular normalization and voice dialogue state machine | Working (Configured with local fallback) |
| Financial Recovery Ledger | Immutable record of captured funds with unique transaction constraints | Working (Authorizations excluded from captured revenue) |
| Unmatched Webhook Isolation | Quarantines uncorrelatable events to prevent case corruption | Working (Inspectable via dedicated dashboard view) |
| Razorpay Test Mode Client | Integration with Razorpay test APIs using test credentials | Working (Rejects live keys; mock client fallback) |

---

## Voice Recovery

Voice communication can recover subscription failures where digital notifications are overlooked. The voice module implements structured phone conversations for payment confirmation, payment link dispatch, and dispute escalation.

- **Speech Providers**: Speech recognition is supported via Faster-Whisper, and speech synthesis uses Microsoft Edge Neural TTS (`edge-tts`). For environments without external dependencies or network access, the system includes a local mathematical tone generator and browser-based speech synthesis as fallbacks.
- **Supported Languages**: Text normalization, currency phrasing, date vocalization, and banking terminology are configured for English, Hindi, Kannada, Tamil, Telugu, Marathi, and Bengali.
- **Barge-In and Interruptions**: A server-side state machine detects user speech and immediately stops agent audio playback to prevent overlapping dialogue.
- **Limitations**: Native-speaker pronunciation has been validated primarily for Hindi and English. Other regional languages rely on standard acoustic models and dictionary transliterations and have not undergone comprehensive native-speaker quality audits.

---

## Architecture and Technology

| Layer | Technologies Used | Role |
| :--- | :--- | :--- |
| Frontend | React 18, Vite, TypeScript, Ant Design, Tailwind CSS | Operator dashboard, Copilot workbench, and review UI |
| Backend API | Python 3.11+, FastAPI, Uvicorn, Pydantic v2 | REST API endpoints, webhook ingress, and authentication |
| Persistence | SQLite (default), PostgreSQL-ready, SQLAlchemy 2.0 async | Relational storage for cases, queues, audits, and ledgers |
| Workers | In-process asynchronous worker pool | Durable queue polling, job leasing, and retry dispatch |
| AI Integration | Unified adapter (OpenAI, Gemini, Ollama, Heuristic Mock) | Diagnostic reasoning and customer dialogue generation |
| Gateway SDK | Official Razorpay Python SDK | Test-mode link creation and HMAC signature verification |

Incoming webhooks are verified and enqueued in a single database transaction. The background worker leases queue items, correlates them with existing records, evaluates policy guardrails, and dispatches approved actions before updating the ledger.

---

## Running the Project

### Prerequisites
- Python 3.11 or newer
- Node.js 18 or newer

### 1. Backend Setup

```bash
cd backend
pip install -r requirements.txt

# Run automated test suite (136 unit and integration tests)
python -m pytest tests/unit tests/integration

# Start the API server
python -m uvicorn recovery_autopilot.main:app --host 127.0.0.1 --port 8000 --app-dir src
```

The backend starts at `http://127.0.0.1:8000`. Interactive OpenAPI documentation is available at `http://127.0.0.1:8000/docs`.

### 2. Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

The dashboard opens at `http://localhost:5173`.

### 3. Execution Modes
- **Synthetic Mode (Default)**: Runs locally with zero external network dependencies. Payment links and webhook events use deterministic local generators.
- **Genuine Razorpay Test Mode**: Set `PAYMENT_EXECUTION_MODE=razorpay_test` in `.env` along with your `RAZORPAY_KEY_ID` (must begin with `rzp_test_`), `RAZORPAY_KEY_SECRET`, and `RAZORPAY_WEBHOOK_SECRET`. Live merchant keys (`rzp_live_`) are blocked by code validation.

### 4. Optional Docker Compose Setup

For evaluators preferring containerized execution:

```bash
# Build and launch all services (Backend, Frontend, PostgreSQL, Redis)
docker compose up --build -d
```

Access endpoints at `http://localhost:5173` (Frontend UI) and `http://localhost:8000/docs` (Backend API).

---

## A Short Judge Walkthrough

This five-minute sequence demonstrates the core workflow:

1. **Overview Dashboard (`http://localhost:5173/`)**: View operational KPIs, the real-time recovery ledger, and the chronological audit feed.
2. **Explore Cases (`http://localhost:5173/cases`)**: Filter cases by status or category. Select a case to inspect failure telemetry and historical attempts.
3. **Inspect Case Detail (`http://localhost:5173/cases/:caseId`)**: Review the model diagnosis and the bounded intervention plan. Open the Voice Recovery panel to test interactive voice prompts in English or Hindi.
4. **Verify Safety Policy Gate (`http://localhost:5173/review`)**: View high-value cases held for human approval. Observe that approvals require valid reviewer credentials and are tied to the active action version.
5. **Inspect Unmatched Events (`http://localhost:5173/unmatched`)**: Review quarantined webhook events that failed correlation, ensuring non-matching payloads never corrupt existing recovery records.
6. **Support Copilot (`http://localhost:5173/copilot`)**: Submit a support inquiry (e.g., "Customer reports double deduction on card") to observe multi-step diagnostic reasoning and payment link creation.

---

## Evaluation and Verification

The evaluation pipeline benchmarks Recovery Autopilot against a standard fixed-retry baseline across a versioned 500-scenario dataset (`Dataset v2.1.0`, random seed 42).

```bash
cd backend
python -m pytest tests/integration/test_prompt9_evaluation_benchmark.py
```

### Benchmark Summary (Synthetic Paired Simulation)

| Metric | Recovery Autopilot | Fixed Retry Baseline | Delta | Notes |
| :--- | :--- | :--- | :--- | :--- |
| Overall Recovery Rate | 69.4% (95% CI: [65.6%, 73.4%]) | 17.2% (95% CI: [13.8%, 20.6%]) | +52.2% | Calculated via 1,000 bootstrap iterations |
| Held-Out Test Split Recovery | 75.0% | 15.0% | +60.0% | Evaluated on disjoint 20% test slice (N=100) |
| Action Decision Accuracy | 98.4% | N/A | High alignment | Ground truth optimal action hidden from model |
| Safety Policy Violations | 0 | 43 | Zero violations | Enforced by deterministic policy engine |
| Customer Fatigue Reduction | 1.44 contacts/recovery | 5.89 contacts/recovery | 75% fewer contacts | Unnecessary outreach prevented |

*Note on Methodology: Financial recovery amounts and rates represent simulated outcomes generated under controlled test conditions using category-specific probability curves. They do not represent live merchant financial data.* Detailed logs are preserved in `docs/evaluation/ai_benchmark_report.md` and `data/scenarios/evaluation_results.json`.

---

## Boundaries and Limitations

- **Buildathon Prototype**: This software is a submission prototype. It executes in synthetic simulation or Razorpay test mode; real monetary transactions and customer messaging are disabled.
- **Voice Hardware Requirements**: Full neural voice synthesis and local Whisper transcription require external network access or local PyTorch/audio libraries. In standard environments, the system defaults to browser-based synthesis and mathematical tone mocks.
- **External Webhooks**: Receiving live webhooks from the Razorpay dashboard in local development requires a reverse proxy (such as ngrok) to route traffic to port 8000.

---

## Repository Navigation

- **Pitch and Demo Script**: [`docs/demo-script.md`](docs/demo-script.md)
- **Defect Log and Remediation**: [`docs/qa/defects.md`](docs/qa/defects.md)
- **Automated Verification Results**: [`docs/qa/verification-results.md`](docs/qa/verification-results.md)
- **Feature Matrix and Coverage**: [`docs/qa/feature-matrix.md`](docs/qa/feature-matrix.md)
- **Benchmark Evaluation Report**: [`docs/evaluation/ai_benchmark_report.md`](docs/evaluation/ai_benchmark_report.md)
- **Razorpay Test Mode Guide**: [`docs/TEST_MODE_GUIDE.md`](docs/TEST_MODE_GUIDE.md)
- **Safety Policy Specification**: [`docs/safety-policy.md`](docs/safety-policy.md)
- **Security Threat Model**: [`docs/THREAT_MODEL.md`](docs/THREAT_MODEL.md)
