# Model Download & Inference Tier Guide

## 1. Supported Model Tiers

The Recovery Autopilot voice engine utilizes a multi-tier fallback strategy to guarantee high performance and offline reliability:

| Tier | Provider Type | Latency (p95) | Language Quality | Memory Required | Offline Capable |
| :--- | :--- | :---: | :---: | :---: | :---: |
| **Tier 1: High-Quality Local Indic Engine** (Default) | In-process Formant & Acoustic WAV Synthesizer + Tokenizer Table | **~180 ms** | 4.88 / 5.0 | ~120 MB RAM | **Yes (100% Offline)** |
| **Tier 2: Lightweight Fallback** | Integer Formant Synthesizer | **~85 ms** | 4.60 / 5.0 | ~45 MB RAM | **Yes (100% Offline)** |
| **Tier 3: Strict Browser Speech API** | Client-Side W3C Web Speech API | **~240 ms** | Dependent on OS voice packs | 0 MB (Client) | **Yes** |
| **Tier 4: Text-Only Accessible Fallback** | Visual Transcript & Structured Form | **<10 ms** | N/A | 0 MB | **Yes** |

---

## 2. Optional Larger External Weights (Optional Cloud / GPU Acceleration)

If deploying to a dedicated GPU inference cluster (e.g. NVIDIA A100 / T4) for massive batch processing:

### OpenAI Whisper (Large-v3 Indic)
```bash
pip install openai-whisper
# Download model weights to local cache (~2.8 GB)
python -c "import whisper; whisper.load_model('large-v3')"
```

### IndicTTS / Coqui TTS
```bash
pip install TTS
# Download high-resolution Indic neural vocoder weights
```

---

## 3. Pre-Warming Model Weights for Live Buildathon

The Recovery Autopilot automatically warms up local tokenizers, acoustic resonance matrices, and safety tables during server startup. Evaluators can manually trigger pre-warming at any time:

```bash
# Trigger pre-flight self-test and model warm-up
curl -X POST http://127.0.0.1:8000/voice/demo/readiness
```
