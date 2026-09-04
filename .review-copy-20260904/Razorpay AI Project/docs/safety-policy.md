# Recovery Autopilot — Safety Policy and Workflow Governance

## 1. Fundamental Safety Principle

```text
AI proposes → deterministic policy approves → executor acts
```

The AI intelligence layer operates strictly as an advisory diagnostic agent. It has zero capability to execute actions, modify financial amounts, or contact customers directly. All decisions must pass through deterministic, auditable, and testable Python policy guardrails.

---

## 2. Guardrails Specification

| Rule Code | Guardrail Name | Policy Boundary | Action on Breach |
| :--- | :--- | :--- | :--- |
| `RULE_CUSTOMER_OPTED_OUT` | Opt-Out Enforcement | Customer marked `opted_out = True` | Action overridden to `STOP`. Zero communication sent. |
| `RULE_MAX_ATTEMPTS_EXCEEDED`| Frequency Ceiling | Maximum 3 contact attempts per recovery lifecycle | Action overridden to `STOP`. Terminal state transition to `EXHAUSTED`. |
| `RULE_HIGH_VALUE_THRESHOLD` | High-Value Safety Gate | Invoice amount ≥ INR 15,000 | Case held in `AWAITING_APPROVAL`. Manual operator confirmation required. |
| `RULE_UNKNOWN_FAILURE_CATEGORY` | Anomaly Guard | Failure category is `UNKNOWN_FAILURE` | Case held in `AWAITING_APPROVAL`. Automated customer actions blocked. |
| `RULE_LOW_CONFIDENCE` | Uncertainty Gate | Model confidence score < 0.70 | Case held in `AWAITING_APPROVAL`. Human operator reviews evidence. |
| `RULE_EXPIRED_CARD_NO_RETRY`| Invalid Action Block | Card expired + `WAIT_FOR_RETRY` proposed | Overridden to `REQUEST_METHOD_UPDATE` to avoid futile retries. |
| `RULE_PAYMENT_AMOUNT_IMMUTABLE`| Amount Lock | Context billing amount is frozen | AI proposal schema rejects any attempt to inject new amounts. |

---

## 3. State Machine Transition Table

```text
┌───────────────────────┬────────────────────────────────────────────────────────────────────────┐
│ Current Status        │ Permitted Target Statuses                                              │
├───────────────────────┼────────────────────────────────────────────────────────────────────────┤
│ NEW                   │ DIAGNOSING, STOPPED, OPTED_OUT, ERROR                                  │
│ DIAGNOSING            │ AWAITING_POLICY, ERROR, STOPPED                                        │
│ AWAITING_POLICY       │ SCHEDULED, AWAITING_APPROVAL, ACTION_IN_PROGRESS, OPTED_OUT, STOPPED   │
│ SCHEDULED             │ ACTION_IN_PROGRESS, RECOVERED, OPTED_OUT, STOPPED, ERROR               │
│ AWAITING_APPROVAL     │ SCHEDULED, ACTION_IN_PROGRESS, STOPPED, RECOVERED, OPTED_OUT, ERROR    │
│ ACTION_IN_PROGRESS    │ MONITORING, RECOVERED, ERROR, STOPPED                                  │
│ MONITORING            │ RECOVERED, EXHAUSTED, PROMISED_TO_PAY, DIAGNOSING, OPTED_OUT, STOPPED  │
│ PROMISED_TO_PAY       │ MONITORING, RECOVERED, EXHAUSTED, OPTED_OUT, STOPPED, ERROR            │
│ RECOVERED (Terminal)  │ [None - Terminal Success]                                              │
│ EXHAUSTED (Terminal)  │ [None - Terminal Abandonment]                                          │
│ OPTED_OUT (Terminal)  │ [None - Terminal Stop]                                                 │
│ STOPPED (Terminal)    │ [None - Terminal Stop]                                                 │
│ ERROR                 │ DIAGNOSING (Operator Retry Only)                                       │
└───────────────────────┴────────────────────────────────────────────────────────────────────────┘
```

Any attempt to execute an unlisted transition raises an `IllegalStateTransitionError` and immediately records an `ILLEGAL_TRANSITION_BLOCKED` audit event.

---

## 4. Stop Conditions

The recovery lifecycle terminates immediately when:
1. **Payment Succeeded**: Ingestion of `payment.captured` or `order.paid` transitions case directly to `RECOVERED`.
2. **Customer Opt-Out**: Customer replies with opt-out keyword or toggles mandate cancellation; case transitions to `OPTED_OUT`.
3. **Attempt Exhaustion**: Reaching 3 contact attempts without recovery transitions case to `EXHAUSTED`.
4. **Manual Cancellation**: Merchant operator clicks Reject or Cancel in the dashboard; case transitions to `STOPPED`.
