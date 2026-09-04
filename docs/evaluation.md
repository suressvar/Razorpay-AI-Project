# Recovery Autopilot — Evaluation and Simulation Methodology

## 1. Overview and Objective

The evaluation system provides a reproducible, statistically rigorous benchmark measuring the incremental revenue lift of **Recovery Autopilot** compared to a fixed-rule baseline strategy across 500 deterministic synthetic subscription failure cases.

---

## 2. Synthetic Dataset Generation

### Deterministic Seed Control
All cases are deterministically generated using Python's standard random generator with a configurable seed (default: `seed=42`). Re-running generation always produces the identical scenario sequence.

### Failure Category Distribution
The dataset models realistic recurring billing failure patterns:
- **Insufficient Funds (28%)**: Customer balance depleted at billing time.
- **Bank Gateway Timeout (18%)**: Transient issuing bank switch latency.
- **Expired Card (14%)**: Card instrument validity lapsed.
- **Mandate Revoked (10%)**: Mandate cancelled by bank or user.
- **Limit Exceeded (10%)**: Card or account velocity ceiling reached.
- **Network Failure (10%)**: Transient TLS / communication drops.
- **Customer Action Required (6%)**: 3D-Secure / OTP step required.
- **Unknown Failure (4%)**: Unrecognized upstream error codes.

### Synthetic PII Compliance
To ensure complete safety and privacy compliance, no real merchant or cardholder data is ever generated or used:
- Names are generated from synthetic pools (e.g. `Test Aarav Sharma`).
- Emails strictly follow `user_XXXX@synthetic-test.example.com`.
- Phone numbers follow the reserved range `+9198000XXXXX`.
- Amounts reflect realistic subscription plans (₹499 to ₹48,000 across Starter, SMB, Growth, and Enterprise tiers).

---

## 3. Simulation Physics and Assumptions

The outcome simulator (`OutcomeSimulator`) models realistic recovery dynamics without secretly favoring the AI:

1. **Transient Infrastructure Failures (`BANK_TIMEOUT`, `NETWORK_FAILURE`)**:
   - `WAIT_FOR_RETRY` achieves **86–88% recovery** with **0 customer contacts**.
   - Sending a payment link achieves ~70% recovery, but incurs unnecessary customer contact and friction.
2. **Expired Cards (`EXPIRED_CARD`)**:
   - `WAIT_FOR_RETRY` has **0% recovery probability** (retrying an expired card is mathematically futile).
   - `REQUEST_METHOD_UPDATE` achieves **74% recovery**.
3. **Insufficient Funds (`INSUFFICIENT_FUNDS`)**:
   - Near salary dates (1st–5th of month), waiting or delayed payment links achieve **65–72% recovery**.
   - Generic reminders sent immediately achieve only **40% recovery**.
4. **Mandate Revocation & Customer Action**:
   - `SEND_PAYMENT_LINK` allows direct ad-hoc payment settlement (**68–78% recovery**).
5. **Contact Fatigue Penalty**:
   - Each previous contact attempt applies an 8% cumulative penalty to response likelihood, modeling customer spam fatigue.
6. **Safety Violation Penalties**:
   - Contacting an opted-out user or violating frequency caps results in an immediate safety violation flag and 0% recovery.

---

## 4. Fixed-Rule Baseline Definition

```text
Wait 24 hours → send one generic reminder → stop after limit
```

*Important Notice:* This baseline models a typical naive merchant automation script, **NOT** Razorpay's proprietary internal production retry systems.

---

## 5. Metrics and Statistical Methodology

1. **Total INR Recovered**: Cumulative gross revenue collected from recovered cases.
2. **Recovery Rate (%)**: Proportion of failed subscription charges successfully collected.
3. **Incremental Lift**: Difference in recovered revenue and recovery rate over baseline.
4. **Contacts Per Recovered Case**: Efficiency metric calculating customer touchpoints needed per win.
5. **Unnecessary Contacts Avoided**: Count of customer notifications spared through intelligent waiting.
6. **Safety Violations**: Count of guardrail violations (must remain 0).
7. **Bootstrap 95% Confidence Intervals**: Empirical bootstrap sampling (1,000 iterations) providing rigorous statistical bounds.

---

## 6. Execution Commands

```bash
# Generate 500 deterministic synthetic cases
python scripts/generate_dataset.py --count 500 --seed 42

# Execute benchmark evaluation and output dashboard
python scripts/run_evaluation.py --size 500 --seed 42
```
