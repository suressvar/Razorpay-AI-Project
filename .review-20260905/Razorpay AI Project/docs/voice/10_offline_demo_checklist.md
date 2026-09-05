# Buildathon Offline Demo Checklist & Presentation Runbook

## 1. Pre-Presentation Setup Checklist (T-15 Minutes)

- [ ] **Backend Server Running**:
  ```bash
  python -m uvicorn recovery_autopilot.main:app --host 127.0.0.1 --port 8000 --app-dir backend/src
  ```
- [ ] **Frontend Dev Server Running**:
  ```bash
  cd frontend && npm run dev
  ```
- [ ] **Microphone Permission Granted**:
  - Open Chrome/Edge at `http://localhost:5173/cases`
  - Verify microphone permission is allowed in browser settings.
- [ ] **Run Pre-Flight Self-Test**:
  - Click **`⚡ Voice Lab & Reliability`** in the header toolbar.
  - Verify **Readiness Score is 100%** with all 5 checks passed.
- [ ] **Audio Volume Check**:
  - Verify laptop speaker/headphone volume is at ~70% level.

---

## 2. Fast Recovery If WiFi / Network Drops During Demo

1. **Local Synthesis**: All STT tokenizers, intent classifiers, and high-quality WAV audio synthesizers run 100% locally in-process on CPU without needing external cloud API connections.
2. **Text Fallback**: If browser microphone permissions fail, the text input box at the bottom of the voice panel allows typing in Hindi, Tamil, Kannada, or English with the exact same deterministic safety policies.

---

## 3. Demo Quick Reference Keys

| Action | UI Button | Keyboard / Shortcut |
| :--- | :--- | :--- |
| **Start Call** | Start Voice Call Demo | Click button |
| **Instant Interruption** | Hold to Speak / Speaking Waveform | Tap or click |
| **Replay Last Response** | 🔊 Replay Turn | Click button |
| **Slower Voice (0.8x)** | 🐢 0.8x Slower Voice | Toggle button |
| **Open Voice Lab** | ⚡ Voice Lab & Reliability | Header button |
| **Pronunciation Gallery** | 🎙️ Pronunciation Gallery | Header button |
| **Purge Transcript** | Purge | Delete button |
