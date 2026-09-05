# Razorpay Recovery Autopilot — Comprehensive Defect Log & Remediation Record

> **Document Version:** 2.0.0  
> **Date:** September 5, 2026  
> **Auditor / Principal Engineer:** Independent Acceptance Tester  
> **Scope:** Track 03 AI Revenue Recovery Buildathon Submission

---

## Executive Summary

This defect log tracks every critical defect identified across the frontend, backend, security boundary, evaluation runner, and packaging infrastructure. Each item documents the observed failure, root cause analysis, reproduction steps, code fix, and automated regression verification.

---

## Defect Inventory & Status

| ID | Category | Severity | Description | Status | Regression Test |
|---|---|---|---|---|---|
| **DEF-01** | Security / Auth | **Critical** | Frontend defaulted to hardcoded `auth_token_admin_recovery_v1`, granting instant admin privileges without login | **RESOLVED** | `test_missing_authentication_rejected`, `test_spoofed_role_header_cannot_grant_privileges` |
| **DEF-02** | API / RBAC | **High** | `GET /webhooks/unmatched` was guarded by `require_reviewer` instead of public/viewer access, causing frontend toast error "Failed to fetch unmatched webhooks" | **RESOLVED** | `test_get_unmatched_webhooks_endpoint` in `test_async_webhooks.py` |
| **DEF-03** | Frontend / API | **Medium** | `fetchUnmatchedWebhooks` and `fetchQueueStats` in `frontend/src/api.ts` omitted `getAuthHeaders()` and lacked parsed error handler | **RESOLVED** | Verified in `frontend/src/api.ts` & clean Vite production build |
| **DEF-04** | Test Suite | **High** | Cross-suite interference: database state and background worker tasks leaked across test files when run together | **RESOLVED** | `test_api_flow.py`, `test_async_webhooks.py`, `test_payment_correlation.py` isolated with clean session factories (135/135 passing) |
| **DEF-05** | Evaluation | **Medium** | Benchmark runner reported development (80%) and held-out (20%) sizes, but evaluated aggregate metrics without distinct held-out reporting | **RESOLVED** | `backend/src/recovery_autopilot/evaluation/runner.py` & `metrics.py` now compute and report held-out metrics separately |
| **DEF-06** | Dependencies | **Low** | Setup instructions referenced nonexistent `backend/requirements.txt`; voice dependencies missing from pyproject optional deps | **RESOLVED** | Created `backend/requirements.txt`, root `requirements.txt`, updated `pyproject.toml` with `voice` optional group |
| **DEF-07** | Packaging | **High** | Repository root contained `.env` with API keys and local SQLite databases/journals (`recovery_autopilot.db`, `*.db-wal`) | **RESOLVED** | Packaged clean submission zip excluding `.env`, secrets, `.git`, `node_modules`, `*.db*`, `*.wal`, and caches |
| **DEF-08** | Multilingual Voice | **Medium** | Heuristic fallback speech generator lacked explicit labeling and native-speaker pronunciation disclaimer | **RESOLVED** | Lexicon verified across 7 Indic languages (Hindi, Kannada, Tamil, Telugu, Marathi, Bengali, English); disclaimers and review gallery verified |

---

## Detailed Root Cause & Remediation Logs

### DEF-01: Hard-Coded Administrator Bypass in Frontend
- **Observed Behavior:** In `frontend/src/api.ts`, `currentAuthToken` was initialized as `localStorage.getItem('recovery_auth_token') || 'auth_token_admin_recovery_v1'`. Opening the web app in an incognito window automatically endowed the client with administrator privileges.
- **Root Cause:** Seed token provided during early prototyping was never replaced with server-side identity verification.
- **Fix:** 
  1. Default token fallback removed from `frontend/src/api.ts` (`localStorage.getItem(...) || ''`).
  2. Integrated enterprise Operator Authentication modal in `App.tsx` backed by `POST /auth/login`.
  3. Dynamic expiring tokens (`tok_<hex>`) generated via server-side password hash validation (`hmac.compare_digest`).
  4. Explicit Demo Account quick-fill provided for review demonstration (`admin`, `reviewer`, `viewer`).
  5. Logout endpoint `POST /auth/logout` revokes session from server-side `TOKEN_REGISTRY`.
- **Verification:** Unit tests in `test_security_hardening.py` confirm unauthenticated mutations return HTTP 401; viewer tokens attempting approvals return HTTP 403.

### DEF-02: `GET /webhooks/unmatched` Endpoint 401 Rejection
- **Observed Behavior:** Navigating to `/unmatched` in the UI caused a red toast: *"Failed to fetch unmatched webhooks"*.
- **Root Cause:** `list_unmatched_webhooks` in `routes_webhooks.py` was decorated with `operator_id: str = Depends(require_reviewer)`. Unauthenticated browser sessions or viewer roles were blocked with 401 Unauthorized.
- **Fix:** Removed blocking reviewer dependency from `GET /webhooks/unmatched`, aligning it with `GET /cases` and `GET /webhooks/queue/stats` as an accessible read-only operational view.
- **Verification:** Added `test_get_unmatched_webhooks_endpoint` in `tests/integration/test_async_webhooks.py`. Passed 100%.

### DEF-03: Missing Auth Headers in Webhook API Client
- **Observed Behavior:** `fetchUnmatchedWebhooks` and `fetchQueueStats` called `fetch()` without headers or error parsing.
- **Fix:** Added `headers: getAuthHeaders()` and `await handleResponseError(...)` in `frontend/src/api.ts`.

### DEF-04: Full Backend Test Suite Flakiness
- **Observed Behavior:** Running individual test modules passed, but `pytest tests/unit tests/integration` failed due to shared database locks and background worker state.
- **Fix:** Isolated repository fixtures and in-process queue worker teardown across integration tests. Full test suite passes 135/135 tests in ~33 seconds.

### DEF-05: Held-Out Split Evaluation Missing
- **Observed Behavior:** `runner.py` defined `dev_size` and `held_out_size` but pooled all scenarios into a single aggregate metric calculation.
- **Fix:** Partitioned scenarios and simulation results into development (80%) and held-out test (20%) splits. Added distinct held-out decision accuracy, recovery rate, and escalation metrics to `BenchmarkReport`.

### DEF-06: Missing `requirements.txt` and Speech Dependency Declarations
- **Observed Behavior:** Documentation instructed `pip install -r requirements.txt`, which errored out with `file not found`.
- **Fix:** Created `backend/requirements.txt` and root `requirements.txt`. Added `voice` optional dependency group to `backend/pyproject.toml`.

### DEF-07: Secrets and SQLite Journals in Archive
- **Observed Behavior:** `.env` and `recovery_autopilot.db*` files resided in repository root.
- **Fix:** Automated packaging script `scripts/package_submission.py` creates a clean submission zip excluding `.env`, `*.db`, `*.wal`, `*.shm`, `node_modules`, `__pycache__`, and cache folders.
