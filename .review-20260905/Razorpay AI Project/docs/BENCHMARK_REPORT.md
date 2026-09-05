# Recovery Autopilot — Benchmark Evidence Report

## Executive Summary
- **Dataset Size**: 10 subscription failure scenarios
- **Random Seed**: `42`
- **Recovery Autopilot Revenue Recovered**: **₹25,407.44**
- **Fixed Retry Baseline Revenue Recovered**: **₹11,168.81**
- **Net Incremental Lift**: **+₹14,238.63** (+70.00 percentage points)
- **Safety Policy Violations**: **0** (Zero Violation Guarantee)
- **Unnecessary Customer Contacts Avoided**: **4**

---

## Strategy Comparison & 95% Confidence Intervals

| Metric | Recovery Autopilot | Fixed Retry Baseline | Incremental Delta |
| :--- | :--- | :--- | :--- |
| **Recovery Rate** | **80.00%** | 10.00% | **+70.00%** |
| **95% Bootstrap CI** | `[60.0%, 100.0%]` | `[0.0%, 30.0%]` | Non-overlapping |
| **Total Revenue** | **₹25,407.44** | ₹11,168.81 | **+₹14,238.63** |
| **Median Time to Recovery** | **4.0 hrs** | 22.0 hrs | Faster resolution |
| **Contacts / Recovered Case** | **0.75** | 10.00 | Reduced fatigue |
| **Safety Violations** | **0** | 1 | Verified Safe |

---

## Performance by Failure Category

| Failure Category | Cases | Autopilot Rate | Baseline Rate | Rate Lift | Autopilot Recovered | Baseline Recovered |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `BANK_TIMEOUT` | 2 | **50.0%** | 0.0% | `+50.0%` | ₹1,032 | ₹0 |
| `EXPIRED_CARD` | 2 | **100.0%** | 0.0% | `+100.0%` | ₹2,459 | ₹0 |
| `INSUFFICIENT_FUNDS` | 2 | **50.0%** | 50.0% | `+0.0%` | ₹11,169 | ₹11,169 |
| `LIMIT_EXCEEDED` | 1 | **100.0%** | 0.0% | `+100.0%` | ₹3,369 | ₹0 |
| `MANDATE_REVOKED` | 1 | **100.0%** | 0.0% | `+100.0%` | ₹708 | ₹0 |
| `NETWORK_FAILURE` | 2 | **100.0%** | 0.0% | `+100.0%` | ₹6,670 | ₹0 |

---

## Methodology & Safety Principles
1. **Zero Ground-Truth Label Leakage**: Inference pipeline only observes failure code, amount, and history. Simulated optimal action is hidden in the evaluation harness.
2. **Empirical Bootstrap Confidence Intervals**: 1,000 iterations per metric to calculate true 95% CI bounds.
3. **Deterministic Seed Control**: Fully reproducible across repeated benchmark runs.
