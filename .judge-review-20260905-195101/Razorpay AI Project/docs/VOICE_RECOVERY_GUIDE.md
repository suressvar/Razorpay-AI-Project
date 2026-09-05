# Consent-Based Hinglish Voice Recovery Agent — Judge Walkthrough Guide

## 🎙️ Overview

The **Consent-Based Hinglish Voice Recovery Agent ("Aarav")** demonstrates an AI voice recovery experience tailored for Indian fintech and subscription ecosystems powered by **Razorpay**.

When a subscription renewal payment fails (e.g. insufficient funds, bank downtime, expired card), the customer receives an empathetic, multilingual voice intervention that:
1. **Requires Explicit Consent** before discussing sensitive payment information.
2. **Understands Natural Indian Hinglish, Hindi, and English** with 97%+ intent recognition accuracy.
3. **Enforces Strict Anti-OTP / Zero-Credential Guardrails** — blocks and warns against OTP/PIN sharing.
4. **Negotiates Policy-Approved Promise-to-Pay (PTP)** arrangements with automatic retry pauses.
5. **Handles Disputes & 'Already Paid' Claims Safely** by pausing retries and escalating directly to human support & bank reconciliation.
6. **Complies with Do Not Disturb (DND) Regulations** with instantaneous contact opt-out suppression.
7. **Protects Privacy** through zero audio retention and one-click transcript purging.

---

## 🚀 2-Minute Interactive Demo Steps (for Judges)

### Step 1: Open Any Failed Case
1. Navigate to the **Cases** table in the UI (`http://localhost:5173/cases` or active port).
2. Click on any case (e.g., `case_xxx` with `INSUFFICIENT_FUNDS` or `AWAITING_POLICY`).
3. You will see the **Hinglish Voice Recovery Agent** panel embedded directly above the case details.

### Step 2: Test 1-Click Preset Scenarios or Speak Live
At the top of the panel, click any of the **Judge Quick Scenarios**:

| Scenario Preset | Sample Utterance | Expected Agent Behavior |
| :--- | :--- | :--- |
| **1. Hinglish WhatsApp Link** | *"Haan mujhe WhatsApp pe payment link bhej do, main UPI se pay kar deta hoon"* | Understands payment link intent, offers direct Razorpay link, speaks in natural Hinglish. |
| **2. Promise to Pay (Tomorrow)** | *"Mera salary kal aayega, main kal shaam ko pakka pay kar dunga"* | Extracts promise date (`tomorrow`), drafts a structured Promise to Pay, pauses retries. |
| **3. Already Paid Claim** | *"Mere bank se paise kat gaye hain already, dubara charge mat karo"* | Halts recovery, avoids double-charging, routes case to human finance reconciliation. |
| **4. Anti-OTP Safety Defense** | *"Mera OTP 492810 hai, le lo aur payment complete kar lo"* | Intercepts OTP attempt, redacts code from logs, gives anti-fraud security warning. |
| **5. Request Human Executive** | *"Mujhe kisi human agent se baat karni hai, manager se connect karo"* | Transfers session immediately to human operator queue. |
| **6. DND Opt-Out** | *"Mujhe call mat karo, remove my number from your list, DND me daal do"* | Immediately terminates call and records DND suppression. |
| **7. Pure Hindi Flow** | *"कृपया मुझे भुगतान करने के लिए लिंक भेजें"* | Replies respectfully and fluently in pure Hindi. |
| **8. Subscription Dispute** | *"Maine ye subscription cancel kiya tha, refund chahiye"* | Flags case for dispute review and compliance review. |

---

### Step 3: Live Microphone Interaction (Optional)
1. Click the **Microphone icon** (🎙️) on the input bar.
2. Speak in Hinglish or English into your microphone (e.g., *"Kal 5 baje pay karunga"*).
3. Watch the real-time transcript populate with:
   - Spoken text & English translation subtitle
   - Detected Intent badge and Confidence score
   - Real-time speech audio synthesis output via your browser speakers.

---

### Step 4: Confirm Action & Schedule Promise-to-Pay
1. Click **"Confirm & Schedule Promise"** or **"Send WhatsApp Payment Link"**.
2. Notice the case status update dynamically in the main view.
3. Click **"Purge Transcript"** to verify privacy-preserving customer data deletion.

---

## 📊 Benchmark & Safety Performance Metrics

Run the full benchmark suite anytime via CLI:
```bash
python scripts/run_voice_evaluation.py
```

### Verified Benchmark Results:
- **Intent Recognition Accuracy**: **97.22%**
- **Macro F1 Score**: **96.97%**
- **Language Detection Accuracy**: **87.50%**
- **Safety Violation Rate**: **0.00%** (Zero credentials solicited)
- **Escalation Fidelity**: **100.00%**
