# Hardware & Memory Requirements

## 1. System Specifications

### Minimum Requirements (Local Demo / Judge Machine)
- **CPU**: Dual-core x86_64 or ARM64 (Intel Core i3 / AMD Ryzen 3 / Apple M1 or higher)
- **RAM**: 4 GB System Memory (Voice engine uses ~120 MB RAM)
- **Disk**: 500 MB Free Disk Space
- **Operating System**: Windows 10/11, macOS 12+, or Ubuntu 20.04+
- **Microphone**: Standard built-in laptop microphone or USB headset (16kHz+ capture support)
- **Audio Output**: Internal speakers or headphones

### Recommended Enterprise Cluster Requirements
- **CPU**: 8-Core Intel Xeon / AMD EPYC
- **RAM**: 16 GB DDR4/DDR5
- **GPU**: Optional NVIDIA T4 / A10G for concurrency > 500 simultaneous voice calls
- **Network**: Low latency (<100ms) for real-time WebSocket / AudioWorklet streaming

---

## 2. Process Memory Footprint & Resource Metrics

| Component | RAM Footprint | CPU Usage (Idle) | CPU Usage (Active Synthesis) |
| :--- | :---: | :---: | :---: |
| **FastAPI Backend Core** | ~65 MB | 0.1% | 1.2% |
| **STT Engine (7 Indic Tokenizers)** | ~45 MB | 0.0% | 3.5% |
| **TTS Engine (WAV 24kHz Synthesizer)** | ~55 MB | 0.0% | 4.8% |
| **Deterministic State Machine & Policies** | ~8 MB | 0.0% | 0.2% |
| **Total Voice Engine Subsystem** | **~173 MB** | **< 0.5%** | **< 10% on 4-core CPU** |
