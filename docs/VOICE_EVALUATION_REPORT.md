# Multilingual Voice Recovery Agent — Benchmark & Evaluation Report

## Executive Summary
This evaluation report benchmarks the **Consent-Based Hinglish Voice Recovery Agent** ("Aarav") across English, Hindi, and Hinglish customer payment recovery conversations.

- **Total Test Utterances**: 72
- **Intent Recognition Accuracy**: 97.22%
- **Macro F1 Score**: 96.97%
- **Language Detection Accuracy**: 87.50%
- **Safety Violation Rate**: 0.00% (Strict Anti-OTP / Zero Credential Solicitations)
- **Human Escalation Fidelity**: 100.00%

---

## Performance by Intent Category

| Intent Category | Precision | Recall | F1-Score | Support |
| :--- | :---: | :---: | :---: | :---: |
| `unclear` | 80.0% | 100.0% | **88.9%** | 4 |
| `promise_to_pay` | 100.0% | 100.0% | **100.0%** | 13 |
| `stop_contact` | 100.0% | 100.0% | **100.0%** | 8 |
| `dispute` | 100.0% | 100.0% | **100.0%** | 7 |
| `already_paid` | 100.0% | 77.8% | **87.5%** | 9 |
| `confirm_yes` | 100.0% | 100.0% | **100.0%** | 6 |
| `confirm_no` | 100.0% | 100.0% | **100.0%** | 4 |
| `send_payment_link` | 92.9% | 100.0% | **96.3%** | 13 |
| `request_human` | 100.0% | 100.0% | **100.0%** | 8 |

---

## Key Safety Guarantees Verified
1. **Anti-OTP / Anti-PIN Defense**: The agent strictly refrains from asking for OTPs, CVVs, or passwords, and intercepts user attempts to share OTPs with a standard anti-fraud warning.
2. **Explicit Consent Gating**: Voice dialogue and payment details are gated behind upfront customer consent.
3. **Dispute & 'Already Paid' Routing**: Claims of prior deduction are instantly escalated to human review and bank reconciliation; retries are paused immediately.
4. **DND Suppression**: Customer opt-out / DND requests immediately terminate the call and register persistent contact suppression.
5. **Data Privacy**: Raw audio is not retained; stored transcripts can be purged via one-click deletion API.
