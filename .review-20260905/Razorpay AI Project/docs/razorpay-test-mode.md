# Razorpay Test Mode and Webhook Integration Guide

## 1. Overview

Recovery Autopilot integrates with Razorpay strictly in **Test Mode**. All external credentials, payment identifiers, and customer records operate within safe sandboxes. Real money is never moved, and real customer notifications are never sent.

---

## 2. Supported Razorpay Events

The webhook ingress adapter processes and normalizes the following events:

| Event Name | Domain Mapping | System Action |
| :--- | :--- | :--- |
| `payment.failed` | `PaymentContext` Ingestion | Ingests context, diagnoses failure cause, triggers safety policy. |
| `payment.authorized` | Transient Auth State | Records audit event; waits for capture or settlement. |
| `payment.captured` | Payment Recovery Signal | Resolves case as `RECOVERED`; terminates active recovery workflows. |
| `order.paid` | Order Recovery Signal | Resolves case as `RECOVERED`. |
| `subscription.pending` | Invoice Due | Monitors subscription charge status. |
| `subscription.halted` | Max Failures Reached | Flags subscription for priority intervention or human escalation. |
| `subscription.charged` | Recurring Success | Records successful billing cycle. |

---

## 3. Webhook Signature Verification

Every incoming webhook request MUST include the `X-Razorpay-Signature` header.

### Verification Algorithm
```python
expected_signature = hmac.new(
    RAZORPAY_WEBHOOK_SECRET.encode("utf-8"),
    raw_request_body_bytes,
    hashlib.sha256,
).hexdigest()

is_valid = hmac.compare_digest(expected_signature, header_signature)
```
- **Crucial Security Requirement:** Verification uses the exact raw, unparsed request bytes before any JSON deserialization to prevent formatting and encoding mismatches.
- Invalid signatures immediately return HTTP 400 with no processing or background dispatch.

---

## 4. Test-Mode Payment Link Generation

When the policy engine approves `SEND_PAYMENT_LINK`:
1. The billing amount is extracted **strictly** from the immutable context of the original payment failure.
2. The AI proposal CANNOT supply or modify the amount.
3. An idempotency key is passed (e.g. `plink_{case_id}_{attempt}_{uuid}`).
4. A mock or test payment link is created (`https://rzp.io/i/...`).
5. A simulated WhatsApp / Email notification preview is recorded for dashboard review.

---

## 5. Data Privacy and Redaction

In all logs, persistent audit trails, and API responses:
- Email addresses are masked: `aar***@example.com`
- Phone numbers are masked: `+919****0001`
- Secrets and API keys are never printed, logged, or placed in URL parameters.
