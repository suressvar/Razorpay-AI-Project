# Privacy, Security & Zero-Trust Audio Retention Policy

## 1. Zero-Trust Audio Storage

The Razorpay Recovery Autopilot voice subsystem strictly adheres to financial privacy and NPCI/RBI security regulations:

1. **No Raw Audio Retention by Default (`VOICE_AUDIO_RETENTION=false`)**:
   - Customer audio frames streamed via AudioWorklet 16kHz PCM are processed strictly in ephemeral system memory buffers.
   - Raw audio bytes are immediately discarded following transcription and feature extraction.
2. **Deterministic Anti-OTP & Anti-PIN Lock**:
   - Any customer or fraudster attempt to speak an OTP, UPI PIN, ATM PIN, CVV, or 16-digit card number is immediately intercepted before reaching any database or LLM.
   - Credentials are redacted from the conversation transcript as `[confidential details omitted]` or `[confidential card]`.
3. **Customer Consent Gating**:
   - The AI agent strictly identifies itself as *"Razorpay AI Recovery Assistant"* and requests explicit conversational consent before discussing subscription details or payment amounts.
4. **Permanent Transcript Purging**:
   - The customer or compliance officer can trigger permanent transcript deletion at any time via `DELETE /voice/sessions/{session_id}/transcript`.

---

## 2. Redacted Audit Event Structure

Every customer voice turn generates an immutable, redacted audit trail:

```json
{
  "event_id": "audit_v99281a",
  "session_id": "vses_77192840",
  "timestamp": "2026-09-05T00:22:17Z",
  "customer_id_masked": "cust_***821",
  "actor": "voice_ai_assistant",
  "language": "hi-IN",
  "detected_intent": "send_payment_link",
  "confidence": 0.994,
  "redacted_transcript": "कृपया मुझे WhatsApp पर पेमेंट लिंक भेजें",
  "proposed_action": "generate_payment_link",
  "requires_confirmation": true,
  "credentials_intercepted": 0,
  "dnd_opt_out_honored": true
}
```
