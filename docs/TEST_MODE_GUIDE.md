# Razorpay Test Mode & Safety Guide

Recovery Autopilot implements a strict **3-Mode Architecture** for all payment gateway interactions:

| Mode | Key Requirement | Description | Network Activity |
| :--- | :--- | :--- | :--- |
| **`synthetic`** *(default)* | None (default placeholder keys allowed) | Fully deterministic local simulation. Generates IDs prefixed with `plink_syn_` and returns mock responses without calling Razorpay servers. | Zero network activity |
| **`razorpay_test`** | `rzp_test_...` and valid test secret | Makes authentic HTTPS requests to the Razorpay Test API (`https://api.razorpay.com/v1/payment_links`). Generates authentic Razorpay payment links (`plink_...`). | Authenticated Razorpay Test API calls only |
| **`production`** | `rzp_live_...` | **LOCKED BY DEFAULT.** Hard-blocked in code unless two independent explicit security flags (`ALLOW_PRODUCTION_MODE=true` AND `CONFIRM_LIVE_FINANCIAL_TRANSACTIONS=true`) are configured. | Blocked |

---

## 1. Safety Locks & Live Key Protection

1. **Automatic Prefix Enforcement**:
   - The application checks every configured `RAZORPAY_KEY_ID`.
   - If any key starting with `rzp_live_` is detected while running in `razorpay_test` mode or without production unlock flags, startup and execution are **immediately terminated with a `ValueError`**.
2. **Deterministic Fallback**:
   - If `PAYMENT_EXECUTION_MODE=synthetic`, no outbound HTTP requests are made.
3. **Audit & Log Redaction**:
   - Customer phone numbers (`+919876543210` -> `+919****210`) and email addresses (`user@domain.com` -> `use***@domain.com`) are automatically sanitized before appearing in audit logs or API outputs.

---

## 2. Setting Up Razorpay Test Mode

To run Recovery Autopilot against your own Razorpay Test Account:

### Step 1: Obtain Test Credentials from Razorpay Dashboard
1. Log in to your [Razorpay Dashboard](https://dashboard.razorpay.com/).
2. Switch to **Test Mode** (toggle in the top nav bar).
3. Navigate to **Settings -> API Keys -> Generate Test Key**.
4. Copy your **Key ID** (`rzp_test_...`) and **Key Secret**.

### Step 2: Configure Environment Variables
Edit your `.env` file or set environment variables:
```bash
PAYMENT_EXECUTION_MODE=razorpay_test
RAZORPAY_KEY_ID=rzp_test_YOUR_KEY_ID
RAZORPAY_KEY_SECRET=YOUR_KEY_SECRET
RAZORPAY_WEBHOOK_SECRET=YOUR_WEBHOOK_SECRET
```

### Step 3: Verify Credentials with Smoke Test Script
Run the automated verification script:
```bash
python scripts/smoke_test_razorpay.py
```
Expected output:
```text
============================================================
  Razorpay Test Mode Smoke Verification
============================================================
[*] Initializing GenuineRazorpayTestClient with Key ID: rzp_test_123...
[*] Dispatching test payment link creation request (Amount: ₹10.00 / 1000 paise)...

[SUCCESS] Test Payment Link Created Successfully!
  - Payment Link ID: plink_PXXXXXXXXXXXXX
  - Short URL:       https://rzp.io/i/XXXXXXX
  - Amount (Paise):  1000 (₹10.00)
  - Status:          created
```

---

## 3. Webhook Testing in Test Mode
In the Razorpay Dashboard (Test Mode):
1. Navigate to **Settings -> Webhooks -> Add New Webhook**.
2. Set Webhook URL: `https://<your-ngrok-or-domain>/api/v1/webhooks/razorpay`.
3. Set Secret to match `RAZORPAY_WEBHOOK_SECRET`.
4. Select active events:
   - `subscription.charged`
   - `payment.failed`
   - `payment.captured`
   - `payment_link.paid`
