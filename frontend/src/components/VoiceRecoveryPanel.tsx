import React, { useState, useEffect, useRef } from 'react';
import {
  PhoneOutlined,
  AudioOutlined,
  AudioMutedOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  SafetyCertificateOutlined,
  UserSwitchOutlined,
  SendOutlined,
  DeleteOutlined,
  ExperimentOutlined,
  SoundOutlined,
  ThunderboltOutlined,
  StopOutlined,
  ClockCircleOutlined,
  CheckOutlined,
} from '@ant-design/icons';
import {
  startVoiceSession,
  getVoiceSession,
  setVoiceSessionConsent,
  sendVoiceUtterance,
  confirmVoiceAction,
  escalateVoiceSession,
  deleteVoiceTranscript,
  fetchVoiceScenarios,
  fetchVoiceEvaluation,
} from '../api';
import {
  VoiceSession,
  VoiceScenarioPreset,
  VoiceEvaluationReport,
  VoiceTurn,
} from '../types';

interface VoiceRecoveryPanelProps {
  caseId: string;
  amountInr: number;
  customerName: string;
  customerPhone?: string;
  onRefreshCase?: () => void;
}

export const VoiceRecoveryPanel: React.FC<VoiceRecoveryPanelProps> = ({
  caseId,
  amountInr,
  customerName,
  customerPhone,
  onRefreshCase,
}) => {
  const [session, setSession] = useState<VoiceSession | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [isListening, setIsListening] = useState<boolean>(false);
  const [isSpeaking, setIsSpeaking] = useState<boolean>(false);
  const [inputText, setInputText] = useState<string>('');
  const [scenarios, setScenarios] = useState<VoiceScenarioPreset[]>([]);
  const [evalReport, setEvalReport] = useState<VoiceEvaluationReport | null>(null);
  const [showEvalModal, setShowEvalModal] = useState<boolean>(false);
  const [actionSuccessMsg, setActionSuccessMsg] = useState<string | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const transcriptEndRef = useRef<HTMLDivElement>(null);
  const recognitionRef = useRef<any>(null);

  // Auto-scroll transcript
  useEffect(() => {
    transcriptEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [session?.turns]);

  // Load scenarios on mount
  useEffect(() => {
    fetchVoiceScenarios()
      .then(setScenarios)
      .catch((e) => console.warn('Could not load voice scenarios', e));
  }, []);

  // Initialize Speech Recognition if supported
  useEffect(() => {
    const SpeechRecognition =
      (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (SpeechRecognition) {
      const recog = new SpeechRecognition();
      recog.continuous = false;
      recog.interimResults = false;
      recog.lang = 'hi-IN'; // Hinglish / Indian English / Hindi

      recog.onresult = (event: any) => {
        const transcript = event.results[0][0].transcript;
        if (transcript) {
          setInputText(transcript);
          handleSendUtterance(transcript);
        }
        setIsListening(false);
      };

      recog.onerror = (event: any) => {
        console.warn('Speech recognition error:', event.error);
        setIsListening(false);
      };

      recog.onend = () => {
        setIsListening(false);
      };

      recognitionRef.current = recog;
    }
  }, [session]);

  const speakText = (text: string) => {
    if ('speechSynthesis' in window) {
      window.speechSynthesis.cancel();
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.rate = 0.95;
      utterance.pitch = 1.0;
      utterance.onstart = () => setIsSpeaking(true);
      utterance.onend = () => setIsSpeaking(false);
      utterance.onerror = () => setIsSpeaking(false);

      // Try selecting an Indian English voice if available
      const voices = window.speechSynthesis.getVoices();
      const indianVoice = voices.find(
        (v) => v.lang.includes('IN') || v.name.includes('India') || v.name.includes('Hindi')
      );
      if (indianVoice) {
        utterance.voice = indianVoice;
      }
      window.speechSynthesis.speak(utterance);
    }
  };

  const handleStartSession = async () => {
    setLoading(true);
    setErrorMsg(null);
    try {
      const newSession = await startVoiceSession(caseId);
      setSession(newSession);
      if (newSession.turns && newSession.turns.length > 0) {
        speakText(newSession.turns[0].text);
      }
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to start voice session');
    } finally {
      setLoading(false);
    }
  };

  const handleGrantConsent = async (granted: boolean) => {
    if (!session) return;
    setLoading(true);
    try {
      const updated = await setVoiceSessionConsent(session.session_id, granted);
      setSession(updated);
      const lastTurn = updated.turns[updated.turns.length - 1];
      if (lastTurn && lastTurn.role === 'agent') {
        speakText(lastTurn.text);
      }
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to record consent');
    } finally {
      setLoading(false);
    }
  };

  const handleSendUtterance = async (textToSend?: string) => {
    const text = (textToSend || inputText).trim();
    if (!text || !session) return;

    setInputText('');
    setLoading(true);
    setErrorMsg(null);
    try {
      const res = await sendVoiceUtterance(session.session_id, text);
      setSession(res.session);
      const lastTurn = res.session.turns[res.session.turns.length - 1];
      if (lastTurn && lastTurn.role === 'agent') {
        speakText(lastTurn.text);
      }
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to process speech utterance');
    } finally {
      setLoading(false);
    }
  };

  const handleToggleMic = () => {
    if (!recognitionRef.current) {
      alert('Speech recognition is not supported in this browser. You can type in the text box below.');
      return;
    }

    if (isListening) {
      recognitionRef.current.stop();
      setIsListening(false);
    } else {
      try {
        recognitionRef.current.start();
        setIsListening(true);
      } catch (err) {
        console.warn('Speech recognition start failed:', err);
      }
    }
  };

  const handleConfirmAction = async () => {
    if (!session) return;
    setLoading(true);
    try {
      const res = await confirmVoiceAction(session.session_id);
      setSession(res.session);
      setActionSuccessMsg(
        res.result.status === 'PROMISED_TO_PAY'
          ? 'Promise to Pay successfully scheduled! Case updated to PROMISED_TO_PAY.'
          : 'Razorpay Payment Link generated and dispatched via WhatsApp!'
      );
      if (onRefreshCase) onRefreshCase();
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to confirm action');
    } finally {
      setLoading(false);
    }
  };

  const handleEscalateToHuman = async () => {
    if (!session) return;
    setLoading(true);
    try {
      const res = await escalateVoiceSession(session.session_id, 'Customer requested human agent');
      setSession(res);
      setActionSuccessMsg('Transferred session to human operator queue.');
      if (onRefreshCase) onRefreshCase();
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to escalate');
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteTranscript = async () => {
    if (!session) return;
    if (!confirm('Are you sure you want to permanently purge this customer voice transcript?')) return;
    setLoading(true);
    try {
      await deleteVoiceTranscript(session.session_id);
      setSession({
        ...session,
        turns: [],
      });
      setActionSuccessMsg('Voice transcript permanently purged for privacy compliance.');
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to delete transcript');
    } finally {
      setLoading(false);
    }
  };

  const handleLoadEvaluation = async () => {
    setLoading(true);
    try {
      const report = await fetchVoiceEvaluation();
      setEvalReport(report);
      setShowEvalModal(true);
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to load evaluation');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden mb-6">
      {/* Header Banner */}
      <div className="bg-gradient-to-r from-blue-900 via-indigo-900 to-slate-900 px-6 py-4 text-white flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 rounded-full bg-blue-500/20 border border-blue-400/40 flex items-center justify-center text-blue-400">
            <PhoneOutlined className="text-xl animate-pulse" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <h3 className="text-lg font-bold text-white tracking-wide">Hinglish Voice Recovery Agent</h3>
              <span className="px-2 py-0.5 rounded text-xs font-semibold bg-emerald-500/20 text-emerald-300 border border-emerald-400/30">
                Aarav AI • Safe Hinglish
              </span>
            </div>
            <p className="text-xs text-blue-200/80">
              Interactive voice dialogue with consent gating, anti-OTP guardrails & Promise-to-Pay scheduling
            </p>
          </div>
        </div>

        <div className="flex items-center space-x-2">
          <button
            onClick={handleLoadEvaluation}
            className="px-3 py-1.5 text-xs font-semibold bg-white/10 hover:bg-white/20 text-white rounded-lg border border-white/20 transition flex items-center space-x-1.5"
          >
            <ExperimentOutlined />
            <span>Benchmark & Safety Stats</span>
          </button>

          {!session ? (
            <button
              onClick={handleStartSession}
              disabled={loading}
              className="px-4 py-2 text-xs font-bold bg-blue-600 hover:bg-blue-500 text-white rounded-lg shadow transition flex items-center space-x-1.5"
            >
              <PhoneOutlined />
              <span>Start Voice Call Demo</span>
            </button>
          ) : (
            <button
              onClick={handleDeleteTranscript}
              disabled={loading}
              className="px-3 py-1.5 text-xs font-semibold bg-red-500/20 hover:bg-red-500/30 text-red-300 rounded-lg border border-red-500/30 transition flex items-center space-x-1"
              title="Purge transcript for privacy"
            >
              <DeleteOutlined />
              <span>Purge Transcript</span>
            </button>
          )}
        </div>
      </div>

      {/* Safety & Compliance Sub-Header */}
      <div className="bg-slate-50 border-b border-gray-200 px-6 py-2.5 flex flex-wrap items-center justify-between text-xs text-gray-600 gap-2">
        <div className="flex items-center space-x-4">
          <span className="flex items-center space-x-1 text-emerald-700 font-medium">
            <SafetyCertificateOutlined className="text-emerald-600" />
            <span>Anti-OTP / Anti-PIN Zero Credential Lock: Active</span>
          </span>
          <span className="flex items-center space-x-1 text-blue-700 font-medium">
            <ClockCircleOutlined className="text-blue-600" />
            <span>Promise-to-Pay SLA: 24h pause</span>
          </span>
        </div>
        <div className="flex items-center space-x-2">
          <span className="text-gray-500">Target Amount:</span>
          <span className="font-bold text-gray-900">₹{amountInr.toLocaleString('en-IN', { minimumFractionDigits: 2 })}</span>
        </div>
      </div>

      {/* Main Body */}
      <div className="p-6">
        {actionSuccessMsg && (
          <div className="mb-4 p-3 bg-emerald-50 border border-emerald-200 rounded-lg text-emerald-800 text-xs flex items-center justify-between">
            <span className="flex items-center space-x-2">
              <CheckCircleOutlined className="text-emerald-600" />
              <span>{actionSuccessMsg}</span>
            </span>
            <button onClick={() => setActionSuccessMsg(null)} className="text-emerald-600 hover:text-emerald-900 font-bold">
              ×
            </button>
          </div>
        )}

        {errorMsg && (
          <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-red-800 text-xs flex items-center justify-between">
            <span className="flex items-center space-x-2">
              <CloseCircleOutlined className="text-red-600" />
              <span>{errorMsg}</span>
            </span>
            <button onClick={() => setErrorMsg(null)} className="text-red-600 hover:text-red-900 font-bold">
              ×
            </button>
          </div>
        )}

        {/* 8 Scenario Presets for 1-Click Judge Evaluation */}
        <div className="mb-6">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-bold text-gray-700 uppercase tracking-wider flex items-center space-x-1.5">
              <ThunderboltOutlined className="text-amber-500" />
              <span>Judge Quick Scenarios (1-Click Test)</span>
            </span>
            <span className="text-[11px] text-gray-500">Simulate common Indian customer voice responses</span>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
            {scenarios.map((sc) => (
              <button
                key={sc.scenario_id}
                onClick={async () => {
                  if (!session) {
                    const newSess = await startVoiceSession(caseId);
                    setSession(newSess);
                    await setVoiceSessionConsent(newSess.session_id, true);
                    const res = await sendVoiceUtterance(newSess.session_id, sc.sample_utterances[0]);
                    setSession(res.session);
                    speakText(res.session.turns[res.session.turns.length - 1].text);
                  } else {
                    if (!session.has_consent) {
                      await setVoiceSessionConsent(session.session_id, true);
                    }
                    const res = await sendVoiceUtterance(session.session_id, sc.sample_utterances[0]);
                    setSession(res.session);
                    speakText(res.session.turns[res.session.turns.length - 1].text);
                  }
                }}
                className="text-left p-2.5 rounded-lg border border-gray-200 hover:border-blue-500 hover:bg-blue-50/50 transition group flex flex-col justify-between"
              >
                <div>
                  <div className="text-xs font-bold text-gray-800 group-hover:text-blue-600 mb-1">
                    {sc.title}
                  </div>
                  <div className="text-[11px] text-gray-500 line-clamp-2 italic">
                    "{sc.sample_utterances[0]}"
                  </div>
                </div>
                <div className="mt-2 text-[10px] font-semibold text-indigo-600 flex items-center justify-between">
                  <span>Intent: {sc.expected_intent}</span>
                  <span className="text-gray-400">▶</span>
                </div>
              </button>
            ))}
          </div>
        </div>

        {/* Voice Session Container */}
        {!session ? (
          <div className="text-center py-10 bg-slate-50 rounded-xl border border-dashed border-gray-300">
            <div className="w-16 h-16 rounded-full bg-blue-100 text-blue-600 flex items-center justify-center mx-auto mb-3 text-2xl">
              <PhoneOutlined />
            </div>
            <h4 className="text-base font-bold text-gray-800 mb-1">Consent-Based Hinglish Voice Assistant</h4>
            <p className="text-xs text-gray-500 max-w-md mx-auto mb-4">
              Demonstrates a real-time recovery dialogue with Aarav. Aarav asks for customer consent, explains why the subscription renewal failed, and safely arranges payment links or Promise-to-Pay.
            </p>
            <button
              onClick={handleStartSession}
              disabled={loading}
              className="px-5 py-2.5 bg-blue-600 hover:bg-blue-500 text-white text-xs font-bold rounded-lg shadow transition"
            >
              Start Voice Call Demo
            </button>
          </div>
        ) : (
          <div className="border border-gray-200 rounded-xl overflow-hidden bg-slate-900 text-white">
            {/* Status Bar */}
            <div className="bg-slate-800/80 px-4 py-2.5 border-b border-slate-700 flex flex-wrap items-center justify-between text-xs gap-2">
              <div className="flex items-center space-x-3">
                <span className="flex items-center space-x-1.5 font-semibold text-emerald-400">
                  <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-pulse"></span>
                  <span>Session Active: {session.session_id}</span>
                </span>
                <span className="text-slate-400">|</span>
                <span className="px-2 py-0.5 rounded text-[11px] font-mono bg-slate-700 text-blue-300 border border-slate-600">
                  State: {session.state}
                </span>
              </div>

              <div className="flex items-center space-x-3">
                {isSpeaking && (
                  <span className="text-blue-400 flex items-center space-x-1 font-medium animate-pulse">
                    <SoundOutlined />
                    <span>Agent Speaking...</span>
                  </span>
                )}
                {isListening && (
                  <span className="text-emerald-400 flex items-center space-x-1 font-medium animate-pulse">
                    <AudioOutlined />
                    <span>Listening to customer...</span>
                  </span>
                )}
              </div>
            </div>

            {/* Consent Banner (If in AWAITING_CONSENT state) */}
            {!session.has_consent && session.state === 'AWAITING_CONSENT' && (
              <div className="p-4 bg-amber-500/10 border-b border-amber-500/30 flex flex-wrap items-center justify-between gap-3">
                <div className="flex items-center space-x-3">
                  <div className="text-amber-400 text-xl font-bold">🔒</div>
                  <div>
                    <div className="text-xs font-bold text-amber-300">Customer Consent Required</div>
                    <div className="text-[11px] text-amber-200/80">
                      The voice assistant must receive explicit consent before discussing subscription payment details.
                    </div>
                  </div>
                </div>

                <div className="flex items-center space-x-2">
                  <button
                    onClick={() => handleGrantConsent(true)}
                    disabled={loading}
                    className="px-3 py-1.5 bg-emerald-600 hover:bg-emerald-500 text-white rounded text-xs font-bold flex items-center space-x-1 shadow"
                  >
                    <CheckOutlined />
                    <span>Grant Consent ("Haan, boliye")</span>
                  </button>
                  <button
                    onClick={() => handleGrantConsent(false)}
                    disabled={loading}
                    className="px-3 py-1.5 bg-slate-700 hover:bg-slate-600 text-gray-300 rounded text-xs font-semibold"
                  >
                    <span>Decline ("Nahi, baad me")</span>
                  </button>
                </div>
              </div>
            )}

            {/* Live Chat Transcript */}
            <div className="p-4 max-h-80 overflow-y-auto space-y-3 bg-slate-950/60 font-sans">
              {session.turns.length === 0 ? (
                <div className="text-center py-6 text-slate-500 text-xs">
                  No transcript messages yet.
                </div>
              ) : (
                session.turns.map((turn, idx) => (
                  <div
                    key={turn.turn_id || idx}
                    className={`flex ${turn.role === 'customer' ? 'justify-end' : 'justify-start'}`}
                  >
                    <div
                      className={`max-w-[80%] rounded-xl p-3.5 ${
                        turn.role === 'customer'
                          ? 'bg-blue-600 text-white rounded-br-none'
                          : 'bg-slate-800 text-slate-100 border border-slate-700 rounded-bl-none shadow'
                      }`}
                    >
                      <div className="flex items-center justify-between text-[10px] text-slate-300 mb-1 gap-2">
                        <span className="font-bold uppercase tracking-wider">
                          {turn.role === 'customer' ? 'Customer' : 'Aarav (AI Agent)'}
                        </span>
                        {turn.detected_intent && (
                          <span className="px-1.5 py-0.5 rounded bg-blue-900/80 text-blue-200 font-mono text-[9px] border border-blue-700">
                            Intent: {turn.detected_intent} ({(turn.confidence_score * 100).toFixed(0)}%)
                          </span>
                        )}
                      </div>

                      {/* Primary Hinglish Speech */}
                      <p className="text-xs leading-relaxed font-medium">{turn.text}</p>

                      {/* Subtitle / English Translation */}
                      {turn.translated_text && turn.role === 'agent' && (
                        <div className="mt-1.5 pt-1.5 border-t border-slate-700/60 text-[11px] text-slate-400 italic">
                          <span className="text-slate-500 not-italic mr-1">🇬🇧 Translation:</span>
                          {turn.translated_text}
                        </div>
                      )}
                    </div>
                  </div>
                ))
              )}
              <div ref={transcriptEndRef} />
            </div>

            {/* Promise to Pay or Action Confirmation Card */}
            {session.promise_draft && session.state === 'AWAITING_CONFIRMATION' && (
              <div className="p-4 bg-indigo-950/80 border-t border-indigo-800 flex flex-wrap items-center justify-between gap-3">
                <div>
                  <div className="text-xs font-bold text-indigo-300 flex items-center space-x-1.5">
                    <ClockCircleOutlined className="text-indigo-400" />
                    <span>Promise to Pay Arrangement Drafted</span>
                  </div>
                  <div className="text-[11px] text-indigo-200/80 mt-0.5">
                    Customer agreed to pay <strong className="text-white">₹{session.promise_draft.promised_amount}</strong> on{' '}
                    <strong className="text-white">{session.promise_draft.promised_date}</strong>. Retries will pause.
                  </div>
                </div>

                <div className="flex items-center space-x-2">
                  <button
                    onClick={handleConfirmAction}
                    disabled={loading}
                    className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-xs font-bold shadow flex items-center space-x-1.5"
                  >
                    <CheckCircleOutlined />
                    <span>Confirm & Schedule Promise</span>
                  </button>
                  <button
                    onClick={handleEscalateToHuman}
                    disabled={loading}
                    className="px-3 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg text-xs font-semibold"
                  >
                    Escalate to Human
                  </button>
                </div>
              </div>
            )}

            {/* Link Confirmation Card */}
            {!session.promise_draft && session.state === 'AWAITING_CONFIRMATION' && (
              <div className="p-4 bg-emerald-950/80 border-t border-emerald-800 flex flex-wrap items-center justify-between gap-3">
                <div>
                  <div className="text-xs font-bold text-emerald-300 flex items-center space-x-1.5">
                    <CheckCircleOutlined className="text-emerald-400" />
                    <span>Razorpay Payment Link Ready to Dispatch</span>
                  </div>
                  <div className="text-[11px] text-emerald-200/80 mt-0.5">
                    Send secure link for <strong className="text-white">₹{session.amount}</strong> to customer WhatsApp/SMS.
                  </div>
                </div>

                <button
                  onClick={handleConfirmAction}
                  disabled={loading}
                  className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg text-xs font-bold shadow flex items-center space-x-1.5"
                >
                  <SendOutlined />
                  <span>Send WhatsApp Payment Link</span>
                </button>
              </div>
            )}

            {/* Escalated / Terminated State Notice */}
            {session.state === 'ESCALATED_TO_HUMAN' && (
              <div className="p-3 bg-amber-950/80 border-t border-amber-800 text-xs text-amber-300 flex items-center space-x-2">
                <UserSwitchOutlined className="text-amber-400 text-base" />
                <span>This case has been escalated to a Human Support Specialist for manual resolution.</span>
              </div>
            )}

            {session.state === 'TERMINATED' && (
              <div className="p-3 bg-red-950/80 border-t border-red-800 text-xs text-red-300 flex items-center space-x-2">
                <StopOutlined className="text-red-400 text-base" />
                <span>Call ended / Customer registered for Do Not Disturb (DND).</span>
              </div>
            )}

            {/* Spoken Utterance Input Bar */}
            <div className="p-3 bg-slate-900 border-t border-slate-800 flex items-center space-x-2">
              <button
                onClick={handleToggleMic}
                disabled={session.state === 'TERMINATED' || !session.has_consent}
                className={`w-10 h-10 rounded-full flex items-center justify-center text-lg transition ${
                  isListening
                    ? 'bg-red-500 text-white animate-bounce shadow-lg'
                    : 'bg-blue-600 hover:bg-blue-500 text-white'
                } disabled:opacity-40 disabled:cursor-not-allowed`}
                title={isListening ? 'Stop listening' : 'Start speaking (Mic)'}
              >
                {isListening ? <AudioMutedOutlined /> : <AudioOutlined />}
              </button>

              <input
                type="text"
                value={inputText}
                onChange={(e) => setInputText(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') handleSendUtterance();
                }}
                disabled={session.state === 'TERMINATED' || !session.has_consent || loading}
                placeholder={
                  !session.has_consent
                    ? 'Please grant consent above to start speaking...'
                    : 'Type customer speech or click mic (e.g. "Kal shaam ko pay kar dunga", "WhatsApp pe link bhej do")...'
                }
                className="flex-1 bg-slate-800 text-white text-xs px-3.5 py-2.5 rounded-lg border border-slate-700 focus:outline-none focus:border-blue-500 disabled:opacity-50"
              />

              <button
                onClick={() => handleSendUtterance()}
                disabled={!inputText.trim() || !session.has_consent || loading}
                className="px-4 py-2.5 bg-blue-600 hover:bg-blue-500 disabled:opacity-40 disabled:cursor-not-allowed text-white text-xs font-bold rounded-lg transition flex items-center space-x-1"
              >
                <SendOutlined />
                <span>Send</span>
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Benchmark & Evaluation Modal */}
      {showEvalModal && evalReport && (
        <div className="fixed inset-0 z-50 bg-black/60 flex items-center justify-center p-4 backdrop-blur-sm">
          <div className="bg-white rounded-2xl max-w-2xl w-full p-6 shadow-2xl border border-gray-200 max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between border-b pb-3 mb-4">
              <div className="flex items-center space-x-2">
                <ExperimentOutlined className="text-blue-600 text-xl" />
                <h3 className="text-base font-bold text-gray-900">Multilingual Voice Agent Benchmark Report</h3>
              </div>
              <button
                onClick={() => setShowEvalModal(false)}
                className="text-gray-400 hover:text-gray-600 text-xl font-bold"
              >
                ✕
              </button>
            </div>

            {/* Scorecards */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-6">
              <div className="p-3 bg-blue-50 rounded-xl border border-blue-100 text-center">
                <div className="text-2xl font-black text-blue-700">
                  {(evalReport.intent_accuracy * 100).toFixed(1)}%
                </div>
                <div className="text-[11px] text-blue-900 font-semibold mt-0.5">Intent Accuracy</div>
              </div>

              <div className="p-3 bg-indigo-50 rounded-xl border border-indigo-100 text-center">
                <div className="text-2xl font-black text-indigo-700">
                  {(evalReport.macro_f1 * 100).toFixed(1)}%
                </div>
                <div className="text-[11px] text-indigo-900 font-semibold mt-0.5">Macro F1 Score</div>
              </div>

              <div className="p-3 bg-emerald-50 rounded-xl border border-emerald-100 text-center">
                <div className="text-2xl font-black text-emerald-700">
                  {evalReport.safety_violation_rate === 0 ? '0.00%' : `${(evalReport.safety_violation_rate * 100).toFixed(2)}%`}
                </div>
                <div className="text-[11px] text-emerald-900 font-semibold mt-0.5">Safety Violations</div>
              </div>

              <div className="p-3 bg-purple-50 rounded-xl border border-purple-100 text-center">
                <div className="text-2xl font-black text-purple-700">
                  {(evalReport.human_escalation_fidelity * 100).toFixed(1)}%
                </div>
                <div className="text-[11px] text-purple-900 font-semibold mt-0.5">Escalation Fidelity</div>
              </div>
            </div>

            {/* Per-class Metrics Table */}
            <h4 className="text-xs font-bold text-gray-800 uppercase tracking-wider mb-2">
              Performance by Intent Category ({evalReport.dataset_size} Multilingual Test Utterances)
            </h4>
            <div className="border border-gray-200 rounded-lg overflow-hidden mb-4">
              <table className="min-w-full divide-y divide-gray-200 text-xs">
                <thead className="bg-gray-50 text-gray-700 font-bold">
                  <tr>
                    <th className="px-3 py-2 text-left">Intent Category</th>
                    <th className="px-3 py-2 text-right">Precision</th>
                    <th className="px-3 py-2 text-right">Recall</th>
                    <th className="px-3 py-2 text-right">F1-Score</th>
                    <th className="px-3 py-2 text-right">Support</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200 font-mono text-[11px]">
                  {Object.entries(evalReport.per_class_metrics).map(([intentName, stats]) => (
                    <tr key={intentName} className="hover:bg-gray-50">
                      <td className="px-3 py-1.5 font-semibold text-gray-800 font-sans">{intentName}</td>
                      <td className="px-3 py-1.5 text-right">{(stats.precision * 100).toFixed(0)}%</td>
                      <td className="px-3 py-1.5 text-right">{(stats.recall * 100).toFixed(0)}%</td>
                      <td className="px-3 py-1.5 text-right font-bold text-blue-600">{(stats.f1 * 100).toFixed(0)}%</td>
                      <td className="px-3 py-1.5 text-right text-gray-500">{stats.support}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div className="text-right">
              <button
                onClick={() => setShowEvalModal(false)}
                className="px-4 py-2 bg-gray-900 hover:bg-gray-800 text-white rounded-lg text-xs font-bold"
              >
                Close Report
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
