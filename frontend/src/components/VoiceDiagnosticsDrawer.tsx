import React from 'react';
import { Drawer, Tag, Descriptions, Progress, Typography, Space, Divider, Alert } from 'antd';
import {
  AudioOutlined,
  ThunderboltOutlined,
  CheckCircleFilled,
  WarningFilled,
  DashboardOutlined,
  FieldTimeOutlined,
  SafetyCertificateOutlined,
} from '@ant-design/icons';
import { AudioDiagnostics } from '../types';

const { Text, Paragraph } = Typography;

interface VoiceDiagnosticsDrawerProps {
  open: boolean;
  onClose: () => void;
  diagnostics: AudioDiagnostics | null;
}

export const VoiceDiagnosticsDrawer: React.FC<VoiceDiagnosticsDrawerProps> = ({
  open,
  onClose,
  diagnostics,
}) => {
  if (!diagnostics) return null;

  const isSafe = !diagnostics.is_clipped && diagnostics.transcription_confidence >= 0.70;

  return (
    <Drawer
      title={
        <div className="flex items-center justify-between">
          <span className="flex items-center gap-2 text-slate-800 font-bold">
            <DashboardOutlined className="text-blue-600" />
            <span>Developer Voice & Audio Telemetry HUD</span>
          </span>
          <Tag color={isSafe ? 'green' : 'gold'}>
            {isSafe ? 'SIGNAL OPTIMAL' : 'QUALITY WARNING'}
          </Tag>
        </div>
      }
      placement="right"
      width={480}
      onClose={onClose}
      open={open}
      styles={{ body: { background: '#f8fafc', padding: 20 } }}
    >
      <div className="space-y-4">
        {/* Signal Level & Clipping Health */}
        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
          <div className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-2 flex items-center justify-between">
            <span>Audio Signal & VAD Health</span>
            {diagnostics.is_clipped ? (
              <span className="text-red-600 font-bold flex items-center gap-1 text-xs">
                <WarningFilled /> CLIPPING DETECTED
              </span>
            ) : (
              <span className="text-emerald-600 font-bold flex items-center gap-1 text-xs">
                <CheckCircleFilled /> PEAK HEADROOM OK
              </span>
            )}
          </div>

          <div className="space-y-2">
            <div>
              <div className="flex justify-between text-xs mb-1">
                <span className="text-slate-600">Signal Level (RMS)</span>
                <span className="font-mono font-bold text-slate-800">
                  {(diagnostics.signal_level_rms * 100).toFixed(1)}%
                </span>
              </div>
              <Progress
                percent={Math.min(100, Math.round(diagnostics.signal_level_rms * 100))}
                status={diagnostics.is_clipped ? 'exception' : 'active'}
                strokeColor={diagnostics.is_clipped ? '#ef4444' : '#10b981'}
                showInfo={false}
              />
            </div>

            <div className="grid grid-cols-2 gap-2 pt-2 text-xs">
              <div className="p-2 bg-slate-50 rounded border border-slate-100">
                <span className="text-slate-400 block text-[10px]">Peak Amplitude</span>
                <span className="font-mono font-bold text-slate-800">{diagnostics.peak_amplitude}</span>
              </div>
              <div className="p-2 bg-slate-50 rounded border border-slate-100">
                <span className="text-slate-400 block text-[10px]">Speech / Total Duration</span>
                <span className="font-mono font-bold text-slate-800">
                  {diagnostics.speech_duration_sec}s / {diagnostics.recording_duration_sec}s
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Hardware & DSP Pipeline */}
        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
          <div className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-3">
            Hardware & DSP Configuration
          </div>
          <Descriptions column={1} size="small" bordered className="text-xs">
            <Descriptions.Item label="Microphone Device">
              <span className="font-medium text-slate-800">{diagnostics.microphone_name || 'Default Input'}</span>
            </Descriptions.Item>
            <Descriptions.Item label="Capture Sample Rate">
              <span className="font-mono text-slate-700">{diagnostics.input_sample_rate} Hz</span>
            </Descriptions.Item>
            <Descriptions.Item label="Processed PCM Mono">
              <span className="font-mono text-slate-700">{diagnostics.processed_sample_rate} Hz (16-bit)</span>
            </Descriptions.Item>
            <Descriptions.Item label="Total Processing Latency">
              <span className="font-mono font-bold text-blue-600">
                <FieldTimeOutlined className="mr-1" />
                {diagnostics.latency_ms} ms
              </span>
            </Descriptions.Item>
          </Descriptions>
        </div>

        {/* Language & Transcription Comparison */}
        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
          <div className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-3">
            Transcription & Normalization
          </div>

          <div className="space-y-3 text-xs">
            <div>
              <span className="text-slate-500 block mb-1">Raw STT Transcript:</span>
              <div className="p-2.5 bg-slate-900 text-slate-100 rounded-lg font-mono text-[11px] select-all">
                {diagnostics.raw_transcript || '(empty / unintelligible)'}
              </div>
            </div>

            <div>
              <span className="text-slate-500 block mb-1">Normalized Multi-Lingual Transcript:</span>
              <div className="p-2.5 bg-blue-50 text-blue-900 border border-blue-200 rounded-lg font-mono text-[11px] select-all">
                {diagnostics.normalized_transcript || '(empty)'}
              </div>
            </div>

            <div className="grid grid-cols-2 gap-2 pt-1">
              <div className="p-2 bg-slate-50 rounded border border-slate-100">
                <span className="text-slate-400 block text-[10px]">Detected Language</span>
                <Tag color="geekblue" className="mt-0.5 font-bold">
                  {diagnostics.detected_language}
                </Tag>
              </div>
              <div className="p-2 bg-slate-50 rounded border border-slate-100">
                <span className="text-slate-400 block text-[10px]">Confidence Score</span>
                <span className="font-mono font-bold text-slate-800">
                  {(diagnostics.transcription_confidence * 100).toFixed(0)}%
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Extracted Intent Contract */}
        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
          <div className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-2">
            Structured Intent Classification
          </div>
          <div className="flex items-center justify-between p-2.5 bg-slate-100 rounded-lg">
            <span className="text-xs text-slate-600">Extracted Intent:</span>
            <Tag color="purple" className="font-mono font-bold">
              {diagnostics.extracted_intent}
            </Tag>
          </div>
        </div>
      </div>
    </Drawer>
  );
};
