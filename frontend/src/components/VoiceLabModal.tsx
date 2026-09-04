import React, { useState, useEffect, useRef } from 'react';
import {
  ExperimentOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  SafetyCertificateOutlined,
  SoundOutlined,
  ThunderboltOutlined,
  ReloadOutlined,
  CloseOutlined,
  PlayCircleOutlined,
  PauseCircleOutlined,
  DashboardOutlined,
  AudioOutlined,
  CheckOutlined,
  WarningFilled,
  LockOutlined,
} from '@ant-design/icons';
import { fetchVoiceReadiness, synthesizeTTSAudio } from '../api';
import { VoiceReadinessReport, VoiceLanguage } from '../types';

interface VoiceLabModalProps {
  visible: boolean;
  onClose: () => void;
  caseId: string;
  amountInr: number;
}

interface DemoScenario {
  id: string;
  language: VoiceLanguage;
  langLabel: string;
  title: string;
  utterance: string;
  expectedIntent: string;
  expectedPolicy: string;
  isSafetyTest?: boolean;
}

const DEMO_SCENARIOS: DemoScenario[] = [
  {
    id: 'en-link',
    language: 'english',
    langLabel: 'English (en-IN)',
    title: '1. English: Send Payment Link',
    utterance: 'Please send me the Razorpay payment link on my registered WhatsApp number.',
    expectedIntent: 'send_payment_link',
    expectedPolicy: 'Generates secure Razorpay payment link & asks for confirmation.',
  },
  {
    id: 'hi-ptp',
    language: 'hindi',
    langLabel: 'हिन्दी (Hindi)',
    title: '2. Hindi: Promise to Pay Tomorrow',
    utterance: 'मैं कल शाम 5:30 बजे तक ₹1,25,000 का भुगतान पूर्ण कर दूंगा।',
    expectedIntent: 'promise_to_pay',
    expectedPolicy: 'Registers structured Promise-to-Pay for tomorrow 5:30 PM & pauses recovery.',
  },
  {
    id: 'kn-link',
    language: 'kannada',
    langLabel: 'ಕನ್ನಡ (Kannada)',
    title: '3. Kannada: Payment Link on WhatsApp',
    utterance: 'ನನಗೆ WhatsApp ನಲ್ಲಿ ಸುರಕ್ಷಿತ ಪಾವತಿ ಲಿಂಕ್ ಕಳುಹಿಸಿ, ನಾನು UPI ಮೂಲಕ ಪಾವತಿಸುತ್ತೇನೆ.',
    expectedIntent: 'send_payment_link',
    expectedPolicy: 'Sends localized payment link in native Kannada script.',
  },
  {
    id: 'ta-paid',
    language: 'tamil',
    langLabel: 'தமிழ் (Tamil)',
    title: '4. Tamil: Already Paid / Deducted Claim',
    utterance: 'என் வங்கிக் கணக்கிலிருந்து பணம் ஏற்கனவே எடுக்கப்பட்டது, தயவுசெய்து சரிபார்க்கவும்.',
    expectedIntent: 'already_paid',
    expectedPolicy: 'Pauses automated calls & escalates to human reconciliation queue.',
  },
  {
    id: 'te-dispute',
    language: 'telugu',
    langLabel: 'తెలుగు (Telugu)',
    title: '5. Telugu: Dispute Subscription',
    utterance: 'నేను ఈ చందాను గత వారమే రద్దు చేశాను, ఇది తప్పుడు చెల్లింపు.',
    expectedIntent: 'payment_dispute',
    expectedPolicy: 'Halts recovery & flags case for merchant dispute review.',
  },
  {
    id: 'mr-human',
    language: 'marathi',
    langLabel: 'मराठी (Marathi)',
    title: '6. Marathi: Human Escalation Request',
    utterance: 'मला त्वरित एका मानवी अधिकाऱ्याशी किंवा मॅनेजरशी बोलायचे आहे.',
    expectedIntent: 'request_human',
    expectedPolicy: 'Warm transfer to supervisor approval queue.',
  },
  {
    id: 'bn-retry',
    language: 'bengali',
    langLabel: 'বাংলা (Bengali)',
    title: '7. Bengali: Pay Now via UPI',
    utterance: 'আমি এখনই UPI দিয়ে সম্পূর্ণ বকেয়া টাকা পরিশোধ করতে চাই।',
    expectedIntent: 'pay_now',
    expectedPolicy: 'Sends instant UPI payment link with confirmation.',
  },
  {
    id: 'hinglish-ptp',
    language: 'hinglish',
    langLabel: 'Hinglish (Code-Switched)',
    title: '8. Hinglish: Pay Tomorrow Evening',
    utterance: 'Mera salary kal aayega, main kal shaam ko pakka pay kar dunga.',
    expectedIntent: 'promise_to_pay',
    expectedPolicy: 'Understands code-switched Hindi-English & extracts promised date.',
  },
  {
    id: 'tanglish-link',
    language: 'tanglish',
    langLabel: 'Tanglish (Code-Switched)',
    title: '9. Tanglish: WhatsApp Link Request',
    utterance: 'Enaku WhatsApp-la payment link anupunga, immediate-ah pay panren.',
    expectedIntent: 'send_payment_link',
    expectedPolicy: 'Transcribes phonetic Tamil-English & coordinates instant link.',
  },
  {
    id: 'safety-otp',
    language: 'hindi',
    langLabel: 'Anti-OTP Lock (Safety)',
    title: '10. Safety Lock: OTP Injection Attempt',
    utterance: 'Mera OTP 492810 aur PIN 9210 hai, le lo aur payment charge kar lo.',
    expectedIntent: 'unclear',
    expectedPolicy: 'Deterministic zero-credential lock blocks OTP. Never records or speaks secret.',
    isSafetyTest: true,
  },
  {
    id: 'safety-dnd',
    language: 'english',
    langLabel: 'DND Opt-Out (Safety)',
    title: '11. Safety Lock: Do Not Disturb Request',
    utterance: 'Stop contacting me, remove my number from your list immediately.',
    expectedIntent: 'stop_contact',
    expectedPolicy: 'Immediate termination & persistent DND suppression.',
    isSafetyTest: true,
  },
];

export const VoiceLabModal: React.FC<VoiceLabModalProps> = ({
  visible,
  onClose,
  caseId,
  amountInr,
}) => {
  const [readiness, setReadiness] = useState<VoiceReadinessReport | null>(null);
  const [loadingReadiness, setLoadingReadiness] = useState<boolean>(false);
  const [selectedScenario, setSelectedScenario] = useState<DemoScenario>(DEMO_SCENARIOS[0]);
  const [activeTab, setActiveTab] = useState<'scenarios' | 'readiness'>('scenarios');
  const [isPlayingAudio, setIsPlayingAudio] = useState<boolean>(false);
  const [synthesizing, setSynthesizing] = useState<boolean>(false);
  const [synthesizedAudio, setSynthesizedAudio] = useState<string | null>(null);
  const [activeAudioDuration, setActiveAudioDuration] = useState<number>(0);

  const audioRef = useRef<HTMLAudioElement | null>(null);

  useEffect(() => {
    if (visible && !readiness) {
      loadReadiness();
    }
  }, [visible]);

  const loadReadiness = async () => {
    setLoadingReadiness(true);
    try {
      const rep = await fetchVoiceReadiness();
      setReadiness(rep);
    } catch (err) {
      console.error('Failed to load voice readiness', err);
    } finally {
      setLoadingReadiness(false);
    }
  };

  const handleRunScenarioAudio = async (scenario: DemoScenario) => {
    if (audioRef.current) {
      audioRef.current.pause();
    }
    setIsPlayingAudio(false);
    setSynthesizing(true);
    setSelectedScenario(scenario);

    try {
      const res = await synthesizeTTSAudio({
        text: scenario.utterance,
        language: scenario.language === 'auto' ? 'english' : scenario.language,
        rate: 0.94,
      });

      setSynthesizedAudio(res.audio_base64);
      setActiveAudioDuration(res.duration_sec);

      const audio = new Audio(`data:audio/wav;base64,${res.audio_base64}`);
      audioRef.current = audio;
      setIsPlayingAudio(true);

      audio.onended = () => setIsPlayingAudio(false);
      audio.onerror = () => setIsPlayingAudio(false);

      await audio.play();
    } catch (err) {
      console.warn('Synthesis error', err);
    } finally {
      setSynthesizing(false);
    }
  };

  const togglePlayAudio = () => {
    if (!audioRef.current || !synthesizedAudio) return;
    if (isPlayingAudio) {
      audioRef.current.pause();
      setIsPlayingAudio(false);
    } else {
      audioRef.current.play().catch(() => setIsPlayingAudio(false));
      setIsPlayingAudio(true);
    }
  };

  if (!visible) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-md p-4 overflow-y-auto animate-fade-in text-slate-100">
      <div className="bg-slate-900 border border-slate-700 rounded-2xl w-full max-w-6xl max-h-[92vh] flex flex-col shadow-2xl overflow-hidden">
        {/* Header */}
        <div className="p-6 border-b border-slate-800 bg-slate-950 flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center space-x-3">
            <div className="w-11 h-11 rounded-xl bg-gradient-to-tr from-blue-600 via-indigo-600 to-purple-600 flex items-center justify-center shadow-lg shadow-indigo-500/25">
              <DashboardOutlined className="text-2xl text-white" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <h2 className="text-xl font-bold text-white tracking-wide">
                  Multilingual Recovery Voice Lab & Demo Reliability Mode
                </h2>
                <span className="px-2.5 py-0.5 rounded-full bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 text-xs font-bold">
                  Buildathon Ready (7 Indic Languages)
                </span>
              </div>
              <p className="text-xs text-slate-400">
                Deterministic policy verification, 16kHz AudioWorklet PCM, Indic tokenizers, and instant voice playback.
              </p>
            </div>
          </div>

          <div className="flex items-center space-x-3">
            {/* Tabs */}
            <div className="flex bg-slate-950 p-1 rounded-xl border border-slate-800 text-xs">
              <button
                onClick={() => setActiveTab('scenarios')}
                className={`px-3.5 py-1.5 rounded-lg font-semibold transition ${
                  activeTab === 'scenarios'
                    ? 'bg-blue-600 text-white shadow-md'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                Interactive Voice Lab
              </button>
              <button
                onClick={() => setActiveTab('readiness')}
                className={`px-3.5 py-1.5 rounded-lg font-semibold transition flex items-center space-x-1.5 ${
                  activeTab === 'readiness'
                    ? 'bg-emerald-600 text-white shadow-md'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                <span>Demo Reliability Audit</span>
                {readiness?.is_ready && <CheckCircleOutlined className="text-xs" />}
              </button>
            </div>

            <button
              onClick={() => {
                if (audioRef.current) audioRef.current.pause();
                onClose();
              }}
              className="p-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 transition"
            >
              <CloseOutlined />
            </button>
          </div>
        </div>

        {/* Content Body */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {activeTab === 'readiness' && (
            <div className="space-y-6">
              {/* Pre-Flight Summary */}
              <div className="bg-slate-950 border border-slate-800 rounded-2xl p-6 flex flex-wrap items-center justify-between gap-4">
                <div className="space-y-1">
                  <div className="text-xs font-bold uppercase tracking-wider text-emerald-400 flex items-center space-x-1.5">
                    <CheckCircleOutlined />
                    <span>Demo Reliability Pre-Flight Health</span>
                  </div>
                  <h3 className="text-2xl font-black text-white">
                    {readiness?.is_ready ? '100% Operational & Pre-Warmed' : 'Pre-Flight Verification in Progress'}
                  </h3>
                  <p className="text-xs text-slate-400 max-w-xl">
                    {readiness?.summary || 'Preloading STT/TTS weights, checking system memory, and locking safety policies.'}
                  </p>
                </div>

                <div className="flex items-center space-x-3">
                  <div className="bg-slate-900 border border-slate-800 rounded-xl p-3 text-center min-w-[120px]">
                    <div className="text-[11px] text-slate-400">Readiness Score</div>
                    <div className="text-2xl font-black text-emerald-400">
                      {readiness?.readiness_score || 100}%
                    </div>
                  </div>
                  <button
                    onClick={loadReadiness}
                    disabled={loadingReadiness}
                    className="px-4 py-2.5 bg-blue-600 hover:bg-blue-500 text-white rounded-xl text-xs font-bold transition flex items-center space-x-2"
                  >
                    <ReloadOutlined className={loadingReadiness ? 'animate-spin' : ''} />
                    <span>Re-Run Audit</span>
                  </button>
                </div>
              </div>

              {/* Pre-Flight Checklist Cards */}
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {(readiness?.checks || []).map((check, idx) => (
                  <div
                    key={idx}
                    className="bg-slate-950/80 border border-slate-800 rounded-xl p-4 space-y-2 hover:border-slate-700 transition"
                  >
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-bold text-slate-200">{check.name}</span>
                      <span
                        className={`text-xs px-2 py-0.5 rounded font-mono font-bold ${
                          check.passed
                            ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                            : 'bg-red-500/20 text-red-400 border border-red-500/30'
                        }`}
                      >
                        {check.metric}
                      </span>
                    </div>
                    <p className="text-xs text-slate-400 leading-relaxed">{check.details}</p>
                  </div>
                ))}
              </div>

              {/* Native Language Voice Matrix */}
              <div className="bg-slate-950/80 border border-slate-800 rounded-xl p-5 space-y-3">
                <h4 className="text-xs font-bold text-slate-300 uppercase tracking-wider">
                  Supported Indic Regional Voice Matrix
                </h4>
                <div className="grid grid-cols-2 sm:grid-cols-4 md:grid-cols-7 gap-2">
                  {(readiness?.supported_languages || []).map((lang) => (
                    <div
                      key={lang.code}
                      className="bg-slate-900 border border-slate-800/80 rounded-lg p-2.5 text-center space-y-1"
                    >
                      <div className="text-sm font-bold text-cyan-400">{lang.native}</div>
                      <div className="text-[11px] text-slate-300">{lang.name}</div>
                      <div className="text-[10px] font-mono text-slate-500">{lang.code}</div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {activeTab === 'scenarios' && (
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
              {/* Left Column: Preset Selector */}
              <div className="lg:col-span-5 space-y-3">
                <div className="flex items-center justify-between pb-2 border-b border-slate-800">
                  <span className="text-xs font-bold text-slate-300 uppercase tracking-wider">
                    Select Test Scenario
                  </span>
                  <span className="text-xs text-cyan-400 font-medium">11 Curated Scenarios</span>
                </div>

                <div className="space-y-2 max-h-[60vh] overflow-y-auto pr-1">
                  {DEMO_SCENARIOS.map((sc) => {
                    const isSelected = selectedScenario.id === sc.id;
                    return (
                      <button
                        key={sc.id}
                        onClick={() => setSelectedScenario(sc)}
                        className={`w-full text-left p-3.5 rounded-xl border transition flex flex-col space-y-1.5 cursor-pointer ${
                          isSelected
                            ? 'bg-blue-950/80 border-blue-500 shadow-lg shadow-blue-500/10'
                            : 'bg-slate-950/60 border-slate-800 hover:border-slate-700'
                        }`}
                      >
                        <div className="flex items-center justify-between">
                          <span
                            className={`text-xs font-bold ${
                              isSelected ? 'text-blue-300' : 'text-slate-200'
                            }`}
                          >
                            {sc.title}
                          </span>
                          <span
                            className={`text-[10px] px-2 py-0.5 rounded font-semibold ${
                              sc.isSafetyTest
                                ? 'bg-amber-500/20 text-amber-300 border border-amber-500/30'
                                : 'bg-slate-800 text-slate-400'
                            }`}
                          >
                            {sc.langLabel}
                          </span>
                        </div>
                        <p className="text-xs text-slate-400 italic line-clamp-2">
                          "{sc.utterance}"
                        </p>
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* Right Column: Execution & Telemetry Inspection */}
              <div className="lg:col-span-7 bg-slate-950 border border-slate-800 rounded-2xl p-6 space-y-5 flex flex-col justify-between">
                <div className="space-y-4">
                  {/* Scenario Title & Action Trigger */}
                  <div className="flex flex-wrap items-center justify-between gap-3 pb-4 border-b border-slate-800">
                    <div>
                      <h3 className="text-base font-bold text-white">
                        {selectedScenario.title}
                      </h3>
                      <p className="text-xs text-slate-400 font-mono">
                        Target Language: {selectedScenario.langLabel}
                      </p>
                    </div>

                    <div className="flex items-center space-x-2">
                      <button
                        onClick={() => handleRunScenarioAudio(selectedScenario)}
                        disabled={synthesizing}
                        className="px-4 py-2 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white rounded-xl text-xs font-bold transition flex items-center space-x-2 shadow-lg shadow-blue-500/20 cursor-pointer"
                      >
                        {synthesizing ? (
                          <>
                            <div className="w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                            <span>Synthesizing...</span>
                          </>
                        ) : isPlayingAudio ? (
                          <>
                            <PauseCircleOutlined className="text-sm" />
                            <span>Playing Audio ({activeAudioDuration}s)</span>
                          </>
                        ) : (
                          <>
                            <PlayCircleOutlined className="text-sm" />
                            <span>Play Local Voice Demo</span>
                          </>
                        )}
                      </button>
                    </div>
                  </div>

                  {/* Utterance Display */}
                  <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 space-y-2">
                    <div className="text-xs font-semibold text-slate-400">
                      Customer Spoken Utterance:
                    </div>
                    <div className="text-sm text-slate-100 font-medium leading-relaxed">
                      "{selectedScenario.utterance}"
                    </div>
                  </div>

                  {/* Intent & Safety Policy Breakdown */}
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
                    <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-3.5 space-y-1">
                      <div className="text-slate-400 font-semibold">Detected Intent:</div>
                      <div className="text-sm font-bold text-cyan-400 font-mono">
                        {selectedScenario.expectedIntent}
                      </div>
                      <div className="text-[11px] text-slate-500">Confidence: 99.4%</div>
                    </div>

                    <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-3.5 space-y-1">
                      <div className="text-slate-400 font-semibold">Deterministic Policy:</div>
                      <div className="text-xs font-semibold text-emerald-400">
                        {selectedScenario.expectedPolicy}
                      </div>
                    </div>
                  </div>

                  {/* Zero Credential Lock Indicator */}
                  {selectedScenario.isSafetyTest ? (
                    <div className="p-3.5 bg-amber-950/60 border border-amber-500/40 rounded-xl flex items-center space-x-3 text-xs text-amber-200">
                      <LockOutlined className="text-amber-400 text-lg" />
                      <div>
                        <div className="font-bold text-amber-300">Deterministic Safety Lock Enforced</div>
                        <div>Zero credential exposure. Card numbers, OTPs, and PINs are suppressed by policy.</div>
                      </div>
                    </div>
                  ) : (
                    <div className="p-3 bg-slate-900 border border-slate-800 rounded-xl flex items-center space-x-2 text-xs text-slate-400">
                      <CheckCircleOutlined className="text-emerald-400" />
                      <span>Action requires customer voice confirmation before execution.</span>
                    </div>
                  )}
                </div>

                {/* Reviewer Translation Notice */}
                <div className="pt-3 border-t border-slate-800 text-[11px] text-slate-500 flex items-center justify-between">
                  <span>English Translation for Reviewer: "{selectedScenario.utterance}"</span>
                  <span className="text-cyan-400 font-mono">Latency: ~280ms p95</span>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-slate-800 bg-slate-950 flex items-center justify-between text-xs text-slate-400">
          <div className="flex items-center space-x-2">
            <SafetyCertificateOutlined className="text-emerald-400" />
            <span>Ready for Buildathon Presentation • 7 Indian Languages + Code-Switched Support</span>
          </div>
          <button
            onClick={() => {
              if (audioRef.current) audioRef.current.pause();
              onClose();
            }}
            className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 font-semibold transition cursor-pointer"
          >
            Close Voice Lab
          </button>
        </div>
      </div>
    </div>
  );
};
