/**
 * Production-Shaped Browser PCM 16kHz Audio Pipeline.
 * Features:
 * - 16kHz Mono PCM Encoding without double resampling
 * - Echo cancellation, noise suppression, and AGC
 * - Real-time RMS signal level & clipping detection
 * - Voice Activity Detection (VAD) and silence trimming
 * - Base64 WAV conversion for backend STT engine
 */

export interface AudioRecordingStats {
  microphoneName: string;
  inputSampleRate: number;
  processedSampleRate: number;
  recordingDurationSec: number;
  speechDurationSec: number;
  signalLevelRms: number;
  peakAmplitude: number;
  isClipped: boolean;
  base64Audio: string;
}

export class PcmAudioRecorder {
  private audioContext: AudioContext | null = null;
  private mediaStream: MediaStream | null = null;
  private sourceNode: MediaStreamAudioSourceNode | null = null;
  private processorNode: ScriptProcessorNode | null = null;
  private pcmChunks: Float32Array[] = [];
  private isRecording: boolean = false;
  private startTime: number = 0;
  private onLevelUpdate?: (rms: number, peak: number) => void;
  private micName: string = 'Default Microphone';
  private peakSeen: number = 0;
  private totalSpeechSamples: number = 0;

  constructor(onLevelUpdate?: (rms: number, peak: number) => void) {
    this.onLevelUpdate = onLevelUpdate;
  }

  public async start(): Promise<void> {
    this.pcmChunks = [];
    this.peakSeen = 0;
    this.totalSpeechSamples = 0;

    // Check mediaDevices support
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      throw new Error('Microphone audio capture is not supported in this browser.');
    }

    this.mediaStream = await navigator.mediaDevices.getUserMedia({
      audio: {
        echoCancellation: true,
        noiseSuppression: true,
        autoGainControl: true,
        channelCount: 1,
      },
    });

    // Detect microphone label
    const audioTrack = this.mediaStream.getAudioTracks()[0];
    if (audioTrack && audioTrack.label) {
      this.micName = audioTrack.label;
    }

    const AudioCtx = window.AudioContext || (window as any).webkitAudioContext;
    this.audioContext = new AudioCtx();

    this.sourceNode = this.audioContext.createMediaStreamSource(this.mediaStream);
    // Buffer size 4096 gives smooth 16kHz processing
    this.processorNode = this.audioContext.createScriptProcessor(4096, 1, 1);

    this.processorNode.onaudioprocess = (e: AudioProcessingEvent) => {
      if (!this.isRecording) return;
      const inputBuffer = e.inputBuffer.getChannelData(0);
      const copy = new Float32Array(inputBuffer.length);
      copy.set(inputBuffer);
      this.pcmChunks.push(copy);

      // RMS & Peak calculation for VAD
      let sumSq = 0;
      let framePeak = 0;
      for (let i = 0; i < inputBuffer.length; i++) {
        const abs = Math.abs(inputBuffer[i]);
        if (abs > framePeak) framePeak = abs;
        sumSq += inputBuffer[i] * inputBuffer[i];
      }
      if (framePeak > this.peakSeen) this.peakSeen = framePeak;

      const rms = Math.sqrt(sumSq / inputBuffer.length);
      if (rms > 0.012) {
        this.totalSpeechSamples += inputBuffer.length;
      }

      if (this.onLevelUpdate) {
        this.onLevelUpdate(rms, framePeak);
      }
    };

    this.sourceNode.connect(this.processorNode);
    this.processorNode.connect(this.audioContext.destination);

    this.isRecording = true;
    this.startTime = performance.now();
  }

  public async stop(): Promise<AudioRecordingStats> {
    if (!this.isRecording) {
      throw new Error('Recorder is not actively recording.');
    }

    const durationSec = (performance.now() - this.startTime) / 1000;
    this.isRecording = false;

    // Disconnect audio nodes
    if (this.sourceNode && this.processorNode) {
      this.sourceNode.disconnect();
      this.processorNode.disconnect();
    }
    if (this.mediaStream) {
      this.mediaStream.getTracks().forEach((track) => track.stop());
    }

    const nativeSampleRate = this.audioContext ? this.audioContext.sampleRate : 44100;
    if (this.audioContext) {
      await this.audioContext.close();
      this.audioContext = null;
    }

    // Flatten chunks
    const totalSamples = this.pcmChunks.reduce((acc, chunk) => acc + chunk.length, 0);
    const merged = new Float32Array(totalSamples);
    let offset = 0;
    for (const chunk of this.pcmChunks) {
      merged.set(chunk, offset);
      offset += chunk.length;
    }

    // Downsample to 16kHz mono without double resampling
    const targetSampleRate = 16000;
    const resampled = this.downsampleBuffer(merged, nativeSampleRate, targetSampleRate);

    // VAD & Silence Trimming (Strip leading and trailing silence)
    const trimmed = this.trimSilence(resampled, 0.01);

    if (trimmed.length < targetSampleRate * 0.35) {
      throw new Error('Recording was too short or contained only silence. Please speak clearly.');
    }

    // Encode as 16-bit WAV
    const wavBytes = this.encodeWav(trimmed, targetSampleRate);
    const base64Audio = this.arrayBufferToBase64(wavBytes);

    const isClipped = this.peakSeen >= 0.98;
    const speechDurationSec = (this.totalSpeechSamples / nativeSampleRate);

    return {
      microphoneName: this.micName,
      inputSampleRate: nativeSampleRate,
      processedSampleRate: targetSampleRate,
      recordingDurationSec: parseFloat(durationSec.toFixed(2)),
      speechDurationSec: parseFloat(speechDurationSec.toFixed(2)),
      signalLevelRms: parseFloat((this.peakSeen * 0.707).toFixed(3)),
      peakAmplitude: parseFloat(this.peakSeen.toFixed(3)),
      isClipped,
      base64Audio,
    };
  }

  private downsampleBuffer(buffer: Float32Array, inputRate: number, outputRate: number): Float32Array {
    if (inputRate === outputRate) return buffer;
    const ratio = inputRate / outputRate;
    const newLength = Math.round(buffer.length / ratio);
    const result = new Float32Array(newLength);
    let offsetResult = 0;
    let offsetBuffer = 0;

    while (offsetResult < result.length) {
      const nextOffsetBuffer = Math.round((offsetResult + 1) * ratio);
      let accum = 0;
      let count = 0;
      for (let i = offsetBuffer; i < nextOffsetBuffer && i < buffer.length; i++) {
        accum += buffer[i];
        count++;
      }
      result[offsetResult] = count > 0 ? accum / count : 0;
      offsetResult++;
      offsetBuffer = nextOffsetBuffer;
    }
    return result;
  }

  private trimSilence(buffer: Float32Array, threshold: number = 0.01): Float32Array {
    let start = 0;
    while (start < buffer.length && Math.abs(buffer[start]) < threshold) {
      start++;
    }
    let end = buffer.length - 1;
    while (end > start && Math.abs(buffer[end]) < threshold) {
      end--;
    }
    return buffer.subarray(Math.max(0, start - 800), Math.min(buffer.length, end + 800));
  }

  private encodeWav(samples: Float32Array, sampleRate: number): ArrayBuffer {
    const buffer = new ArrayBuffer(44 + samples.length * 2);
    const view = new DataView(buffer);

    // RIFF identifier
    this.writeString(view, 0, 'RIFF');
    // file length
    view.setUint32(4, 36 + samples.length * 2, true);
    // RIFF type
    this.writeString(view, 8, 'WAVE');
    // format chunk identifier
    this.writeString(view, 12, 'fmt ');
    // format chunk length
    view.setUint32(16, 16, true);
    // sample format (raw PCM)
    view.setUint16(20, 1, true);
    // channel count (mono)
    view.setUint16(22, 1, true);
    // sample rate
    view.setUint32(24, sampleRate, true);
    // byte rate (sample rate * block align)
    view.setUint32(28, sampleRate * 2, true);
    // block align (channel count * bytes per sample)
    view.setUint16(32, 2, true);
    // bits per sample
    view.setUint16(34, 16, true);
    // data chunk identifier
    this.writeString(view, 36, 'data');
    // data chunk length
    view.setUint32(40, samples.length * 2, true);

    // Write 16-bit PCM samples
    let offset = 44;
    for (let i = 0; i < samples.length; i++) {
      const s = Math.max(-1, Math.min(1, samples[i]));
      view.setInt16(offset, s < 0 ? s * 0x8000 : s * 0x7fff, true);
      offset += 2;
    }
    return buffer;
  }

  private writeString(view: DataView, offset: number, string: string): void {
    for (let i = 0; i < string.length; i++) {
      view.setUint8(offset + i, string.charCodeAt(i));
    }
  }

  private arrayBufferToBase64(buffer: ArrayBuffer): string {
    let binary = '';
    const bytes = new Uint8Array(buffer);
    const len = bytes.byteLength;
    for (let i = 0; i < len; i++) {
      binary += String.fromCharCode(bytes[i]);
    }
    return window.btoa(binary);
  }
}
