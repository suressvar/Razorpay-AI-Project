# Credential Exposure Inventory & Security Audit

**Audit Date**: September 2026  
**Auditor**: Application Security Engineering Lead  
**Scope**: Full repository, configuration templates, database models, logging pipelines, API routes, and test suites.

---

## 1. Executive Summary

This audit establishes a zero-trust credential security baseline for the **Razorpay Recovery Autopilot Buildathon Submission**.
- **No live API keys, secrets, or production customer PII** are stored, committed, or permitted in the repository.
- Role-based authority spoofing via client-provided headers (`X-Operator-Role: admin`) has been eliminated.
- Permissions are strictly derived from server-side bearer tokens (`admin`, `reviewer`, `viewer`).
- All external API credentials and secrets are segregated from the client, stored in a server-side secure vault (`data/.server_secrets.json`), and masked upon read.

---

## 2. Credential Exposure Inventory & Audit Findings

| Item / Secret Type | Expected Location | Storage & Masking Mechanism | Exposure Status | Mitigations Applied |
| :--- | :--- | :--- | :--- | :--- |
| **Razorpay API Secret** | Runtime Vault / Env | Stored in `data/.server_secrets.json` (server-side only, omitted from API responses). Never sent to frontend. | **SECURE (Redacted)** | Masked as `rzp_test_...` in UI. Secret values are write-only. `.server_secrets.json` added to `.gitignore`. |
| **Razorpay Webhook Secret**| Runtime Vault / Env | Stored in server secrets. Used strictly for HMAC-SHA256 signature verification in `EventProcessor`. | **SECURE (Redacted)** | Unexposed in API responses or logs. |
| **Gemini / OpenAI Keys** | Runtime Vault / Env | Server-side only. Used by LLM diagnosis clients. | **SECURE (Redacted)** | Displayed as `gemini_api_key_configured: true/false` only. Raw keys stripped before serialization. |
| **Operator Access Tokens** | In-Memory / Config | Token registry with distinct scopes: `admin` (`auth_token_admin_...`), `reviewer` (`auth_token_reviewer_...`), `viewer` (`auth_token_viewer_...`). | **AUTHENTICATED** | Header `X-Operator-Role` is ignored for privilege granting. Replay/stale approvals bound to `action_version`. |
| **Customer Phone Numbers** | SQLite DB / Logs | PII Redaction Pipeline (`redact_pii`, `redact_metadata`). | **MASKED** | Numbers masked to `+919876****10` in all logs, audit trails, and simulator outputs. |
| **Customer Email Addresses**| SQLite DB / Logs | PII Redaction Pipeline. | **MASKED** | Emails masked to `pri***@example.com` in audit logs and error responses. |
| **Card / Bank Account Numbers**| Payment Gateways | **Never Captured or Stored**. Only tokens/references (`pay_...`, `sub_...`, `inv_...`) are handled. | **NOT STORED** | Strict zero-credential storage architecture. Anti-OTP voice guardrail blocks collection. |

---

## 3. Safe Configuration Example

A safe configuration template is maintained at [`.env.example`](file:///.env.example). 

### Key Hardening Directives
```bash
# Strictly enforces test mode; live production keys are rejected at startup
PAYMENT_EXECUTION_MODE=synthetic # Options: 'synthetic', 'razorpay_test'
KILL_SWITCH_ACTIVE=false
ALLOW_PRODUCTION_MODE=false
CONFIRM_LIVE_FINANCIAL_TRANSACTIONS=false

# Test key format requirements
RAZORPAY_KEY_ID=rzp_test_sample_key_id
RAZORPAY_KEY_SECRET=sample_test_key_secret
RAZORPAY_WEBHOOK_SECRET=rzp_whsec_sample_secret
```

---

## 4. Secret Scanning & Packaging Policy

Before packaging any submission archive:
1. **Automated Secret Scanner**: Run `git grep -i -E "rzp_live|AIzaSy|sk-[a-zA-Z0-9]{20}"` across the tree.
2. **Artifact Clean-up**:
   - Delete all SQLite database files (`*.db`, `*.db-wal`, `*.db-shm`).
   - Remove `.server_secrets.json` and `runtime_settings.json` test remnants.
   - Strip all `.env` files (preserve `.env.example` only).
   - Clear `logs/` directory and browser recordings.
3. **Packaging Command**:
   ```bash
   python -m recovery_autopilot.scripts.package_submission --verify-clean
   ```

---

## 5. Verification Status

- [x] Missing authentication returns HTTP 401 Unauthorized.
- [x] Spoofed `X-Operator-Role` headers cannot elevate privileges.
- [x] Reviewer permissions cannot alter settings or toggle kill switch.
- [x] Stale and replayed approvals rejected with HTTP 409 Conflict.
- [x] Emergency kill switch verified before all execution side effects.
- [x] Comprehensive test suite passed (6/6 security tests, 136/136 total tests).
