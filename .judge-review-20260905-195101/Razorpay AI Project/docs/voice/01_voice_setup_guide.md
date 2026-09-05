# Multilingual Voice Recovery Autopilot — Voice Setup Guide

## 1. System Architecture Overview

The Razorpay Recovery Autopilot voice system provides real-time, low-latency, and respectful recovery dialogue across **7 Indian Languages** (`en-IN`, `hi-IN`, `kn-IN`, `ta-IN`, `te-IN`, `mr-IN`, `bn-IN`) and **6 Code-Switched Dialects** (Hinglish, Kanglish, Tanglish, Tenglish, Marathi-English, Bengali-English).

```text
Microphone (WebAudio 16kHz PCM)
  ↓
Audio Validation & Signal RMS / VAD Trimming
  ↓
Speech-to-Text (Local Indic Tokenizers & Acoustic Models)
  ↓
Language & Code-Switch Detection (Auto Detect + Uncertainty Gating)
  ↓
Locale Speech-Text Normalizer (₹ Lakh/Crore, Dates, Times, Masked IDs)
  ↓
Intent & Entity Extraction (Structured Contracts)
  ↓
Deterministic Safety Policy Engine (Anti-OTP, Anti-PIN, DND Locks)
  ↓
Clarification or Confirmation Gating (State Machine Idempotency)
  ↓
Localized Response Generator & SSML Prosody Wrapper
  ↓
Text-to-Speech Engine (High-Quality WAV 24kHz Synthesis + Browser Fallback)
  ↓
Interruptible Audio Playback (Instant Microphone Cancellation)
  ↓
Redacted Audit Event Log
```

---

## 2. Quick Start Commands

### Backend Startup
```bash
# Navigate to project root
cd "Razorpay AI Project"

# Activate environment and launch FastAPI backend
python -m uvicorn recovery_autopilot.main:app --host 127.0.0.1 --port 8000 --app-dir backend/src
```

### Frontend Startup
```bash
cd frontend
npm install
npm run dev
```
Open `http://localhost:5173` in Google Chrome, Microsoft Edge, or Firefox.

---

## 3. Configuration Parameters (`.env`)

| Variable | Default Value | Description |
| :--- | :--- | :--- |
| `VOICE_ENABLED` | `true` | Master toggle for voice recovery agents |
| `VOICE_STT_PROVIDER` | `local_multilingual` | STT provider (`local_multilingual`, `whisper`, `mock`) |
| `VOICE_TTS_PROVIDER` | `local_multilingual` | TTS engine (`local_multilingual`, `browser_only`) |
| `VOICE_MIN_CONFIDENCE` | `0.75` | Minimum transcription confidence before conversation repair |
| `VOICE_SESSION_TIMEOUT_SEC` | `300` | Inactivity timeout in seconds |
| `VOICE_AUDIO_RETENTION` | `false` | Zero-trust default: never retains raw audio PCM files |

---

## 4. Key Components

- **Voice Session Manager**: `backend/src/recovery_autopilot/voice/voice_session.py`
- **Deterministic State Machine**: `backend/src/recovery_autopilot/voice/state_machine.py`
- **Locale Normalizer**: `backend/src/recovery_autopilot/voice/tts/tts_normalization.py`
- **Pronunciation Lexicon**: `backend/src/recovery_autopilot/voice/tts/lexicon.py`
- **TTS Engine**: `backend/src/recovery_autopilot/voice/tts/local_tts_provider.py`
- **Demo Reliability Mode**: `backend/src/recovery_autopilot/voice/readiness.py`
