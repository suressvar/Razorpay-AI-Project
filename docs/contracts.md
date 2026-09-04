# Recovery Autopilot — Domain Contracts Specification

This document formally specifies the shared domain contracts, controlled enumerations, and validation invariants used across Recovery Autopilot.

---

## 1. Controlled Enumerations

### `FailureCategory`
Classifies the diagnostic cause of payment failure:
- `INSUFFICIENT_FUNDS`: Customer account lacked sufficient funds at scheduled charge time.
- `BANK_TIMEOUT`: Issuing bank or gateway network timeout during mandate processing.
- `EXPIRED_CARD`: Card instrument validity has lapsed.
- `MANDATE_REVOKED`: Recurring e-mandate was cancelled by the customer or bank.
- `LIMIT_EXCEEDED`: Daily/monthly transaction ceiling reached.
- `NETWORK_FAILURE`: Transient network or 3D-Secure transport failure.
- `CUSTOMER_ACTION_REQUIRED`: Mandate re-authentication or OTP step required.
- `UNKNOWN_FAILURE`: Unrecognized gateway error code. Always escalates to `HUMAN_REVIEW`.

### `RecoveryAction`
Controlled set of recovery interventions. Arbitrary commands or arbitrary tool calls are strictly forbidden:
- `WAIT_FOR_RETRY`: Pause and wait before scheduling an automated gateway charge retry.
- `SEND_PAYMENT_LINK`: Generate an on-demand Razorpay test payment link with immutable amount.
- `REQUEST_METHOD_UPDATE`: Prompt customer to add an alternate card or UPI autopay instrument.
- `SEND_REMINDER`: Send an informative reminder without generating a new instrument.
- `HUMAN_REVIEW`: Escalate case to merchant operations queue.
- `STOP`: Terminate recovery lifecycle (e.g. on opt-out, successful payment, or exhaustion).

### `CaseStatus`
State machine lifecycle statuses:
- `NEW`: Ingested payment failure, awaiting diagnosis.
- `DIAGNOSING`: AI model is formulating a root-cause diagnosis and proposal.
- `AWAITING_POLICY`: Proposal formulated, awaiting deterministic guardrail check.
- `SCHEDULED`: Approved action queued with delay timer.
- `AWAITING_APPROVAL`: High-value or low-confidence proposal held for human sign-off.
- `ACTION_IN_PROGRESS`: Adapter is executing the approved recovery action.
- `MONITORING`: Action executed, waiting for payment outcome signal.
- `PROMISED_TO_PAY`: Customer acknowledged and promised payment by a specific date.
- `RECOVERED`: Payment succeeded; terminal success state.
- `EXHAUSTED`: Maximum attempts reached without recovery; terminal failure state.
- `OPTED_OUT`: Customer requested stop; terminal stopped state.
- `STOPPED`: Manually cancelled or paused by operator; terminal state.
- `ERROR`: Unrecoverable system or adapter failure.

---

## 2. Core Entities

### `PaymentContext`
Immutable snapshot of the payment failure event:
- `payment_id`: Razorpay payment identifier.
- `subscription_id`: Subscription identifier.
- `amount_inr`: Exact billing amount in INR (strictly positive, immutable).
- `failure_category`: Controlled `FailureCategory`.
- `failure_code` & `failure_reason`: Raw gateway details.
- `payment_method`: `CARD`, `UPI`, `NETBANKING`, or `NACH`.
- `customer_segment`: `ENTERPRISE`, `GROWTH`, `SMB`, or `STARTER`.
- `previous_failures`: Non-negative counter of prior failed charges.
- `previous_contacts`: Non-negative counter of customer touches.
- `bank_degraded`: Boolean indicating bank downtime status.
- `opted_out`: Boolean indicating communication opt-out.

### `RecoveryProposal`
Structured AI output:
- `action`: `RecoveryAction` (strictly validated against enum).
- `confidence`: Float bounded between `0.0` and `1.0`.
- `delay_minutes`: Integer bounded between `0` and `10080` (max 7 days).
- `reason_codes`: List of uppercase string codes justifying the choice.
- `explanation`: Human-readable rationale.
- `customer_message`: Optional customer draft text.
- `requires_human_approval`: Boolean flag if AI requests human sign-off.
- **Strict Prohibition**: Extra fields are forbidden (`extra="forbid"`). The model cannot pass amounts, URLs, or external tool names.

### `PolicyDecision`
Deterministic safety evaluation:
- `allowed`: Boolean indicating whether action is permitted.
- `approved_action`: Final approved `RecoveryAction`.
- `modified_delay_minutes`: Optional delay override by policy.
- `reason_codes`: List of policy rule results (e.g. `RULE_AMOUNT_THRESHOLD_EXCEEDED`).
- `requires_human_review`: Boolean flag mandating human sign-off.
- `block_reason`: Detailed explanation if blocked.

### `PaymentCase`
Aggregate root entity containing the case identifier, immutable `PaymentContext`, current `CaseStatus`, proposals, decisions, execution results, and final `PaymentOutcome`.
