# Multilingual Voice Troubleshooting Guide

## 1. Common Issues & Solutions

### Issue 1: Browser Microphone Permission Denied
- **Symptom**: Clicking "Hold to Speak" or "Record Speech" shows error `Microphone access denied`.
- **Solution**: Click the lock/tune icon in the browser URL bar, ensure **Microphone** is set to **Allow**, and reload the page.

### Issue 2: Audio Feedback or Agent Voice Overlapping
- **Symptom**: When speaking to the agent, the AI assistant continues talking over customer speech.
- **Solution**: The **Instant Interruption** handler immediately halts `window.speechSynthesis` and backend audio streams whenever the microphone is activated or when the user clicks the speaking waveform banner.

### Issue 3: Regional Language Pronunciation Distortion in Browser Fallback
- **Symptom**: Kannada, Tamil, Telugu, Marathi, or Bengali speech sounds robotic or reads English letters phonetically.
- **Solution**:
  1. Open the **Voice Lab & Reliability** modal or **Pronunciation Gallery (7 Languages)** in the top toolbar to switch to High-Quality Local Indic WAV Synthesis.
  2. For browser speech synthesis, install native Indic Language packs in Windows Settings $\rightarrow$ Time & Language $\rightarrow$ Speech $\rightarrow$ Add voices (e.g. *Microsoft Heera - Hindi*, *Microsoft Valluvar - Tamil*, *Microsoft Mohan - Telugu*).

### Issue 4: Low Confidence Voice Recognition / Noisy Background
- **Symptom**: Conversation Repair modal opens asking to confirm transcribed text.
- **Solution**: This is a deliberate safety feature triggered when confidence falls below `0.75`. You can edit the text directly in the repair card and click **Submit Corrected Text**.

---

## 2. Developer Diagnostic Telemetry HUD

Press the **Telemetry HUD** button in the header toolbar to view live real-time audio statistics:
- Microphone Name & Input Sample Rate (e.g. 48000Hz downsampled to 16000Hz PCM)
- Signal Level RMS & Peak Amplitude
- Clipping Warning Indicator
- Transcription Confidence & Model Latency (ms)
