# 🚀 Recovery Autopilot — Razorpay Buildathon

> **Autonomous, safety-bounded subscription payment recovery agent for Razorpay**

Recovery Autopilot detects failed subscription payments, diagnoses their root cause using Gemini AI, proposes bounded recovery interventions, validates every action through deterministic safety guardrails, and proves measurable incremental revenue recovery against a fixed-rule baseline.

---

## Architecture

```
AI proposes → deterministic policy approves → executor acts
```

The AI **never** has direct write access to Razorpay, cannot alter payment amounts, cannot bypass contact frequency limits, and cannot self-approve high-value actions.

```
Razorpay Webhooks / Synthetic Engine
           ↓
  Payment Case (NEW → DIAGNOSING)
           ↓
   Agent 3: Gemini AI Diagnosis
           ↓
   Agent 4: Safety Policy Engine
    ┌──────┴───────┐
  APPROVED      HUMAN REVIEW
    ↓               ↓ (Dashboard)
   Agent 5: Safe Razorpay Adapter
    (test-mode payment links, mock notifications)
           ↓
   Agent 6: Persistence & Audit Trail
           ↓
   Agent 7: React Dashboard
```

---

## Quick Start (Zero Dependencies)

The entire system runs locally with **SQLite** and the **fake/deterministic AI provider** — no PostgreSQL, Redis, or Gemini API key required.

### 1. Backend

```bash
# Install Python dependencies
python -m pip install uv
python -m uv pip install --system fastapi uvicorn pydantic pydantic-settings sqlalchemy aiosqlite httpx google-genai razorpay

# Start the API server
python -m uvicorn recovery_autopilot.main:app \
  --host 0.0.0.0 --port 8000 --app-dir backend/src

# API docs available at:
# http://localhost:8000/docs
```

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
# Open http://localhost:5173
```

### 3. Seed & Demo

```bash
# Seed 50 synthetic cases
curl -X POST http://localhost:8000/demo/seed \
  -H "Content-Type: application/json" \
  -d '{"count": 50, "seed": 42}'

# Run 500-case evaluation benchmark
curl -X POST http://localhost:8000/demo/run-evaluation \
  -H "Content-Type: application/json" \
  -d '{"size": 500, "seed": 42}'

# Simulate a payment failure webhook
curl -X POST http://localhost:8000/demo/simulate-webhook \
  -H "Content-Type: application/json" \
  -d '{"event_type": "payment.failed", "category": "INSUFFICIENT_FUNDS", "amount_inr": 3499}'
```

---

## Model Provider Configuration

Set `MODEL_PROVIDER` in your `.env` file:

| Provider | Value | Requirements |
|---|---|---|
| **Fake (default)** | `fake` | None — deterministic heuristic |
| **Google Gemini** | `gemini` | `GEMINI_API_KEY` |
| **Ollama/Qwen3** | `ollama` | Local Ollama + `OLLAMA_MODEL=qwen3:8b` |

---

## Safety Guardrails (Non-Negotiable)

All 9 rules are **deterministic** and run **before** any AI action executes:

| Rule | Condition | Outcome |
|---|---|---|
| 1 | Customer opted out | STOP immediately |
| 2 | Already recovered | STOP immediately |
| 3 | ≥ 3 contacts OR < 24h gap | Block / delay |
| 4 | Amount ≥ ₹15,000 | Escalate to Human Review |
| 5 | `UNKNOWN_FAILURE` category | Escalate to Human Review |
| 6 | AI confidence < 70% | Escalate to Human Review |
| 7 | Duplicate payment link active | Block |
| 8 | Amount mismatch attempt | Block |
| 9 | Duplicate in-flight intervention | Block |

---

## Evaluation Results (500 cases, seed=42)

| Metric | AI Autopilot | Fixed Baseline | Lift |
|---|---|---|---|
| Recovery Rate | ~74% | ~19% | **+55pp** |
| Safety Violations | **0** | — | ✓ |
| Incremental INR | ₹5,00,000+ | — | — |
| Unnecessary Contacts | Avoided 100+ | — | ✓ |

> Bootstrap 95% confidence intervals available in `/metrics/evaluation` response.

---

## Project Structure

```
.
├── backend/
│   ├── src/recovery_autopilot/
│   │   ├── config.py               # Pydantic Settings
│   │   ├── domain/                 # Enums + typed models
│   │   ├── synthetic/              # 500-case generator
│   │   ├── evaluation/             # Simulation + metrics
│   │   ├── model_providers/        # Gemini / Ollama / Fake
│   │   ├── agents/                 # Diagnosis + proposal agents
│   │   ├── policies/               # Safety guardrails
│   │   ├── workflows/              # State machine
│   │   ├── integrations/           # Razorpay adapter + notifications
│   │   ├── persistence/            # SQLAlchemy + repository
│   │   ├── api/                    # FastAPI routes
│   │   ├── services/               # Orchestrator
│   │   └── main.py                 # FastAPI app
│   └── tests/                      # 53 tests
├── frontend/
│   └── src/
│       ├── pages/                  # Overview, Cases, CaseDetail, HumanReview, Evaluation
│       ├── components/             # Badge, Card, KpiCard
│       ├── api.ts                  # Type-safe API client
│       └── types.ts                # Shared TypeScript types
├── docs/
│   ├── architecture.md
│   ├── contracts.md
│   ├── evaluation.md
│   ├── safety-policy.md
│   └── razorpay-test-mode.md
├── scripts/
│   ├── generate_dataset.py
│   └── run_evaluation.py
├── docker-compose.yml
└── .env.example
```

---

## Running Tests

```bash
# Backend (53 tests)
python -m pytest backend/tests/ -v

# Frontend TypeScript check
cd frontend && npx tsc --noEmit

# Code quality
python -m ruff check backend/src/
```

---

## Docker Compose (Full Stack)

```bash
cp .env.example .env
# Set GEMINI_API_KEY in .env if using Gemini provider
docker compose up -d
```

Services:
- `backend` at port 8000
- `frontend` at port 5173
- `postgres` at port 5432
- `redis` at port 6379

---

## Dashboard Pages

| Page | URL | Description |
|---|---|---|
| Overview | `/` | KPIs, recovery trend chart, live audit stream |
| Cases | `/cases` | Filter & search all payment cases |
| Case Detail | `/cases/:id` | AI diagnosis, policy decision, audit trail |
| Human Review | `/review` | Approve/reject high-value cases |
| Evaluation | `/evaluation` | 500-case benchmark, charts, incremental lift |

---

## API Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/health` | Service health check |
| GET | `/metrics/summary` | Live KPI metrics |
| GET | `/metrics/evaluation` | Benchmark results |
| GET | `/cases` | List cases (filter by status/category) |
| GET | `/cases/{id}` | Case detail |
| GET | `/cases/{id}/audit` | Audit trail |
| GET | `/cases/{id}/notifications` | Simulated notifications |
| POST | `/cases/{id}/approve` | Human approval |
| POST | `/cases/{id}/reject` | Human rejection |
| POST | `/demo/seed` | Seed synthetic cases |
| POST | `/demo/run-evaluation` | Run benchmark |
| POST | `/demo/simulate-webhook` | Simulate payment event |
| POST | `/webhooks/razorpay` | Razorpay webhook receiver |
