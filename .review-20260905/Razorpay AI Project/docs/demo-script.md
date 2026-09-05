# Recovery Autopilot — 5-Minute Judge Demo Script

> **Goal:** Show a working end-to-end AI recovery flow in ≤ 5 minutes with real API calls, live metrics, and a human approval action.

---

## Setup (Before Demo — 2 min)

```bash
# Terminal 1: Start backend
python -m uvicorn recovery_autopilot.main:app --host 0.0.0.0 --port 8000 --app-dir backend/src

# Terminal 2: Start frontend
cd frontend && npm run dev

# Open http://localhost:5173 in browser
```

---

## Step 1 — Overview Dashboard (30 sec)

**Navigate to:** http://localhost:5173

**Say:** "This is Recovery Autopilot — an AI-powered system that recovers failed Razorpay subscription payments autonomously, with strict safety guardrails."

**Click: "Seed Demo Data"** → Point to:
- 50 synthetic cases being seeded with realistic failure scenarios
- Instant KPI metrics updating (total cases, recovered, awaiting review)
- Live audit stream showing real-time AI activity

---

## Step 2 — Cases List (45 sec)

**Navigate to:** Cases (left sidebar)

**Show filters:** Filter by `INSUFFICIENT_FUNDS` category. Point to:
- Filterable table with case status, failure category, amount, contact count
- Status badges showing the AI state machine in action (NEW → DIAGNOSING → AWAITING_POLICY → SCHEDULED)

**Click any case** to drill into CaseDetail.

---

## Step 3 — Case Deep-Dive (60 sec)

**On CaseDetail page, point to:**

1. **Customer Context** — synthetic but realistic: `cust_syn_xxxxx`, masked email, segment
2. **AI Diagnosis** (blue card):
   - Proposed action (e.g. `SEND_PAYMENT_LINK`)
   - Confidence score with color-coded bar
   - AI explanation text
3. **Safety Policy Decision** (green/red card):
   - 9 rules evaluated deterministically
   - Decision: APPROVED or BLOCKED
   - Human review flag if amount ≥ ₹15,000
4. **Audit Trail** — chronological events: WEBHOOK → AI → POLICY → EXECUTOR

**Say:** "Notice: The AI proposed the action, but it only executes after the safety policy approves it. The AI has no direct write access."

---

## Step 4 — Human Review Queue (60 sec)

**Navigate to:** Human Review (left sidebar)

**Show:** Cases awaiting operator approval (amount ≥ ₹15,000 or confidence < 70%)

**Point to the policy guardrail banner:** "Cases reach this queue when: amount ≥ ₹15,000 · confidence < 70% · unknown failure."

**Demo: Click "Approve" on any case:**
1. Confirmation modal shows the proposed action and amount
2. Click "Confirm Approval" → Watch the case disappear from queue
3. Navigate back to Cases → find case now in `ACTION_IN_PROGRESS` status

---

## Step 5 — Evaluation Benchmark (90 sec)

**Navigate to:** Evaluation (left sidebar)

**Say:** "The real question for any AI recovery system is: does it actually perform better than just running a fixed rule? Let's run a 500-case deterministic simulation."

**Click "Run Evaluation"** (100 or 500 cases)

**Wait ~10-30 seconds, then show:**

1. **Safety Certificate** — "Zero safety violations across 500 simulated cases ✓"
2. **KPI Cards:**
   - AI Recovery Rate: ~74% vs Baseline: ~19% → **+55 percentage points**
   - Incremental INR: ₹5,00,000+ additional recovered
   - Contacts Avoided: 100+ unnecessary contacts saved
3. **Category Breakdown Chart** — AI dramatically outperforms baseline on INSUFFICIENT_FUNDS, BANK_TIMEOUT
4. **Radar Chart** — AI performance profile vs baseline

---

## Step 6 — Simulate Live Webhook (30 sec)

**Navigate back to Overview**, click **"Simulate Webhook"**

**Say:** "This sends a synthetic `payment.failed` webhook event, just like Razorpay would in production — with HMAC signature verification."

**Show:** New case appears in Cases list, audit stream updates with new event.

---

## Key Talking Points

| Point | Evidence |
|---|---|
| **Safety-first design** | 9 deterministic guardrails run before every action |
| **AI proposes, policy approves** | Architecture invariant enforced at code level |
| **Test-mode only** | Zero real customer contacts, all links test-mode |
| **Measurable lift** | +55pp recovery rate vs fixed-rule baseline |
| **Human in the loop** | High-value/low-confidence cases require operator approval |
| **Zero configuration** | SQLite + fake AI, runs in 2 commands |

---

## Fallback Plan

If Gemini API is unavailable, the `fake` provider runs deterministic expert heuristics that **still outperform the baseline** — the demo works entirely offline.

```bash
# Force fake provider
MODEL_PROVIDER=fake python -m uvicorn recovery_autopilot.main:app ...
```
