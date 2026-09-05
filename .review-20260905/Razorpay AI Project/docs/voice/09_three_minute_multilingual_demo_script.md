# Three-Minute Multilingual Buildathon Demo Script

## Timing: 3 Minutes Total

---

### Minute 0:00 – 0:45: The Problem & The Pre-Flight Demo Reliability Mode
1. **Presenter**: *"Failed payment recovery in India is uniquely challenging because customers converse in code-switched regional languages, banks experience temporary server timeouts, and generic bots either leak sensitive OTPs or mispronounce Indian numbers. Today we present Razorpay Recovery Autopilot with a native multilingual conversational voice engine."*
2. **Action**: Open the UI at `http://localhost:5173/cases` and click on any case with a failed payment.
3. **Action**: Click **`⚡ Voice Lab & Reliability`** in the top toolbar to show the **Pre-Flight Health Audit** (100% operational score, 7 Indic tokenizers pre-warmed, 16kHz AudioWorklet active).

---

### Minute 0:45 – 1:45: Code-Switched Recovery (Hinglish & Indic Regional Dialogue)
1. **Presenter**: *"Let's test code-switched Hinglish and native Tamil/Kannada dialogue with instant Indian numbering conversion (expanding ₹1,25,000 to one lakh twenty-five thousand rupees)."*
2. **Action**: Select **Hinglish** from the language selector and click **Start Voice Call Demo**.
3. **Dialogue**:
   - **Agent**: *"Namaste, main Razorpay se aapka AI recovery assistant hoon. Kya main aapke ₹1,25,000 ke subscription payment ke baare mein baat kar sakta hoon?"*
   - **User / Preset**: *"Haan mujhe WhatsApp pe payment link bhej do, main UPI se pay kar deta hoon."*
   - **Agent**: *"Maine aapke WhatsApp par surakshit payment link bhej diya hai. Kya aap iski pushti karte hain?"*
4. **Action**: Click **`🔊 Replay Turn`** or toggle **`🐢 0.8x Slower Voice`** to show accessibility controls.

---

### Minute 1:45 – 2:30: Deterministic Safety Locks (Anti-OTP Defense & DND Opt-Out)
1. **Presenter**: *"Security is non-negotiable. What happens if a customer or fraudster attempts to share an OTP or PIN?"*
2. **Action**: Speak or trigger the Anti-OTP scenario: *"Mera OTP 492810 aur PIN 9210 hai, le lo."*
3. **Outcome**:
   - The agent strictly warns: *"For your security, Razorpay will never ask for your OTP, PIN, or CVV. Please do not share confidential credentials."*
   - Redacted audit log shows zero credentials stored or spoken.
4. **Action**: Say *"Stop calling me, add to DND"*.
   - Agent immediately terminates session and registers persistent DND suppression.

---

### Minute 2:30 – 3:00: Pronunciation Review Gallery & Judge Q&A
1. **Presenter**: *"We also built a judge review gallery where you can listen to all 84 test cases across English, Hindi, Kannada, Tamil, Telugu, Marathi, and Bengali."*
2. **Action**: Click **`🎙️ Pronunciation Gallery (7 Languages)`** in the toolbar to show the 7-language audio player with raw vs. normalized text comparison and 5-star rating widgets.
3. **Closing**: *"100% offline local CPU synthesis, zero OTP leaks, and sub-200ms latency. Thank you!"*
