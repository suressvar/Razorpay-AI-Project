# 5-Minute Buildathon Demonstration Pitch Script
## Autonomous Subscription Recovery for Razorpay

**Audience**: Buildathon Judges, Payment Operations Leads, FinTech Architects  
**Target Duration**: 5 minutes (300 seconds)  
**Tone**: Honest, technically grounded, evidence-backed, production-architected.  
**Execution Environment**: Razorpay Test Mode (`rzp_test_...`) & Isolated Synthetic Laboratory. *(Live customer calls and real bank charges strictly disabled).*

---

### Phase 1: The Problem & Ingestion Evidence (0:00 – 0:45)

**Visual**: Navigate to `http://localhost:5173/cases` -> Click on Case `case_001` or run a simulated webhook failure from Dashboard (`http://localhost:5173/`).

**Presenter Script**:
> "Subscription and recurring mandate failures are a silent revenue leak for Indian SaaS and subscription merchants. In India, RBI recurring e-mandates, bank card network limits, and UPI timeouts create unique failure modes that generic email blasts fail to recover.
> 
> Here on our **Payment Recovery Dashboard**, we see a real-time event ingested directly from Razorpay: a ₹4,999 annual subscription renewal for customer Priya Sharma failed with error `BAD_REQUEST_PAYMENT_TIMED_OUT`.
>
> Notice the telemetry: the system preserves exact event IDs (`evt_...`), the linked subscription reference (`sub_...`), and customer contact history without exposing unmasked PII."

---

### Phase 2: Agent Diagnosis & Guardrailed Policy Decision (0:45 – 1:30)

**Visual**: Navigate to Case Detail page (`http://localhost:5173/cases/{case_id}`) -> View **Autonomous Diagnosis** and **Policy Guardrails**.

**Presenter Script**:
> "Instead of blindly firing an instant retry—which risks triggering bank rate limits or harassing the customer—the Autopilot initiates a structured diagnosis.
> 
> The AI Model analyzes the failure category, previous failure count, time-of-day, and proximity to salary settlement dates. It proposes a targeted recovery intervention: `SEND_PAYMENT_LINK` with an interactive voice follow-up.
> 
> But crucial to our architecture: **the LLM is never given direct write access or API authorization**. Every proposal must pass through our deterministic `SafetyPolicyEngine`. The policy engine enforces:
> 1. Customer DND status and explicit opt-outs.
> 2. Cooldown windows (minimum 12 hours between contacts).
> 3. Maximum contact attempts (capped at 3).
> 4. Financial thresholds: cases exceeding ₹15,000 are automatically diverted to our **Human Review Queue** for four-eyes approval."

---

### Phase 3: Multilingual Voice Recovery Conversation (1:30 – 2:30)

**Visual**: Click **Voice Recovery Agent** on the Case page or test in the Copilot / Voice Lab (`http://localhost:5173/copilot`).

**Presenter Script**:
> "Now let's demonstrate customer contact. In India, multilingual conversational recovery yields significantly higher response rates than emails.
> 
> We support 7 Indian languages: English, Hindi, Kannada, Tamil, Telugu, Marathi, and Bengali.
> 
> Let's listen to genuine speech synthesis generated via Microsoft Edge Neural voice (`hi-IN-MadhurNeural`), and genuine local multilingual speech recognition powered by local int8 Whisper:
> 
> *(Audio speaks)*: *'Namaste Priya ji. Hum Merchant Services se bol rahe hain. Aapka ₹4,999 ka subscription payment bank timeout ki wajah se complete nahi ho paya. Kya hum aapke registered mobile par WhatsApp UPI link share karein?'*
> 
> If the customer interrupts: the audio halts immediately via our server-side interrupt state machine.
> 
> When the customer confirms: *'Haan, link bhej dijiye'*, our conversational state machine strictly binds that affirmative answer to the active proposal. A generic 'yes' never approves an unproposed action, and credentials or URLs are never read aloud."

---

### Phase 4: Razorpay Test-Mode Execution & Deduplicated Idempotency (2:30 – 3:15)

**Visual**: Click **Approve Action** (or auto-execution) -> Show generated Razorpay Payment Link (`https://rzp.io/i/...`).

**Presenter Script**:
> "Once approved, the action executor dispatches to the gateway.
> 
> We operate in genuine **Razorpay Test Mode** using typed SDK adapters. Notice the generated payment link: `https://rzp.io/i/test_...`.
> 
> Notice how we handle network timeouts and retries: we persist an atomic `OperationKeyRecord`. If a network glitch occurs or an operator clicks twice, the system reconciles with Razorpay's API and returns the existing link without double-creating payment links or double-charging the customer."

---

### Phase 5: Webhook Reconciliation, Recovery Ledger & Audit (3:15 – 4:00)

**Visual**: Navigate to **Developer Settings** (`http://localhost:5173/settings`) -> Dispatch Simulated Webhook `payment.captured` for the payment ID -> Navigate to Case Ledger / Audit Stream.

**Presenter Script**:
> "When the customer pays the link, Razorpay posts a `payment.captured` or `order.paid` webhook event.
> 
> We unified all entry points—direct webhooks, async queue workers, and batch reconciliations—behind a single **Unified Event Processor**.
> 
> Key reliability guarantees:
> 1. **Stable Deduplication**: Provider event IDs and SHA-256 fallback hashes prevent double-processing.
> 2. **Financial Recovery Ledger**: Every confirmed rupee is logged in an immutable `recovery_ledger` table with unique constraint on `provider_payment_id`. An authorization event alone is never counted as captured revenue.
> 3. **Out-of-Order Handling**: If a payment capture arrives before the failure event finishes processing, the pending recovery job is immediately cancelled, preventing redundant customer outreach."

---

### Phase 6: Reproducible Evidence & Benchmark Lab (4:00 – 5:00)

**Visual**: Navigate to **Benchmark & Evaluation Lab** (`http://localhost:5173/evaluation`).

**Presenter Script**:
> "Finally, let's look at scientific evaluation. We reject vanity benchmarks and hard-coded recovery claims.
> 
> Our evaluation suite runs on a versioned 500-scenario dataset (`Dataset v2.1.0`) with an 80/20 train and held-out test split. The agent is evaluated with ground-truth labels completely hidden.
> 
> Across 500 paired scenarios:
> - **Autopilot Recovery Rate**: **69.4%** (95% Bootstrap CI: [65.6%, 73.4%]) versus **17.2%** for the fixed-rule baseline — a net lift of **+52.2%**.
> - **Action Decision Accuracy**: **98.4%** match with domain-expert safe interventions.
> - **Escalation Precision**: **100.0%** (zero spurious human review escalations).
> - **Policy Violations**: **0** — strictly zero DND or contact breaches across all test runs.
> 
> Every single metric displayed links directly to reproducible artifact files: `docs/evaluation/ai_benchmark_report.md` and `data/scenarios/evaluation_results.json`.
> 
> Any judge can clone this repository, run `pytest`, and reproduce these exact numbers in 30 seconds.
> 
> Thank you, and we welcome your questions!"
