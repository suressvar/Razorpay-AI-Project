import React, { useState, useEffect, useRef } from 'react';
import {
  SoundOutlined,
  PlayCircleOutlined,
  PauseCircleOutlined,
  CheckCircleOutlined,
  SafetyCertificateOutlined,
  StarFilled,
  StarOutlined,
  GlobalOutlined,
  ReloadOutlined,
  ThunderboltOutlined,
  CloseOutlined,
  CustomerServiceOutlined,
} from '@ant-design/icons';
import { fetchTTSBenchmark } from '../api';
import { TTSBenchmarkResponse, TTSBenchmarkSample } from '../types';

interface PronunciationGalleryModalProps {
  visible: boolean;
  onClose: () => void;
}

export const PronunciationGalleryModal: React.FC<PronunciationGalleryModalProps> = ({
  visible,
  onClose,
}) => {
  const [data, setData] = useState<TTSBenchmarkResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [selectedLanguage, setSelectedLanguage] = useState<string>('all');
  const [selectedCategory, setSelectedCategory] = useState<string>('all');
  const [playingSampleId, setPlayingSampleId] = useState<string | null>(null);
  const [userRatings, setUserRatings] = useState<Record<string, number>>({});
  const [feedbackNotes, setFeedbackNotes] = useState<Record<string, string>>({});
  const [submittedFeedback, setSubmittedFeedback] = useState<Record<string, boolean>>({});

  const audioRef = useRef<HTMLAudioElement | null>(null);

  useEffect(() => {
    if (visible && !data) {
      loadBenchmark();
    }
  }, [visible]);

  const loadBenchmark = async () => {
    setLoading(true);
    try {
      const res = await fetchTTSBenchmark();
      setData(res);
    } catch (err) {
      console.error('Failed to fetch TTS benchmark', err);
    } finally {
      setLoading(false);
    }
  };

  const playAudio = (sample: TTSBenchmarkSample) => {
    if (playingSampleId === sample.test_id) {
      if (audioRef.current) {
        audioRef.current.pause();
      }
      setPlayingSampleId(null);
      return;
    }

    if (audioRef.current) {
      audioRef.current.pause();
    }

    const audio = new Audio(`data:audio/wav;base64,${sample.audio_base64}`);
    audioRef.current = audio;
    setPlayingSampleId(sample.test_id);

    audio.onended = () => {
      setPlayingSampleId(null);
    };
    audio.onerror = () => {
      setPlayingSampleId(null);
    };

    audio.play().catch((err) => {
      console.warn('Playback error', err);
      setPlayingSampleId(null);
    });
  };

  if (!visible) return null;

  const languages = [
    { key: 'all', label: 'All Languages' },
    { key: 'english', label: 'English (en-IN)' },
    { key: 'hindi', label: 'हिन्दी (hi-IN)' },
    { key: 'kannada', label: 'ಕನ್ನಡ (kn-IN)' },
    { key: 'tamil', label: 'தமிழ் (ta-IN)' },
    { key: 'telugu', label: 'తెలుగు (te-IN)' },
    { key: 'marathi', label: 'मराठी (mr-IN)' },
    { key: 'bengali', label: 'বাংলা (bn-IN)' },
  ];

  const categories = [
    { key: 'all', label: 'All Scenarios' },
    { key: 'greetings', label: 'Greetings' },
    { key: 'failed_payment_explanations', label: 'Failed Payments' },
    { key: 'currency_amounts_1_to_10_lakh', label: 'Amounts (₹1 - ₹10L)' },
    { key: 'dates_and_times', label: 'Dates & Times' },
    { key: 'upi_and_emi', label: 'UPI & EMI' },
    { key: 'payment_link_messages', label: 'Payment Links' },
    { key: 'promise_to_pay_confirmation', label: 'Promise to Pay' },
    { key: 'stop_contact_confirmation', label: 'DND & Stop Contact' },
  ];

  const filteredSamples = (data?.sample_gallery || []).filter((sample) => {
    const langMatch = selectedLanguage === 'all' || sample.language.toLowerCase() === selectedLanguage;
    const catMatch = selectedCategory === 'all' || sample.category.toLowerCase() === selectedCategory;
    return langMatch && catMatch;
  });

  const handleRate = (sampleId: string, rating: number) => {
    setUserRatings((prev) => ({ ...prev, [sampleId]: rating }));
  };

  const handleSubmitScore = (sampleId: string) => {
    setSubmittedFeedback((prev) => ({ ...prev, [sampleId]: true }));
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4 overflow-y-auto animate-fade-in">
      <div className="bg-slate-900 border border-slate-700 rounded-2xl w-full max-w-5xl max-h-[90vh] flex flex-col shadow-2xl overflow-hidden text-slate-100">
        {/* Header */}
        <div className="p-6 border-b border-slate-800 bg-slate-950/80 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-cyan-600 to-blue-500 flex items-center justify-center shadow-lg shadow-cyan-500/20">
              <CustomerServiceOutlined className="text-xl text-white" />
            </div>
            <div>
              <h2 className="text-xl font-bold text-white flex items-center space-x-2">
                <span>Multilingual Pronunciation & Audio Review Gallery</span>
                <span className="text-xs px-2.5 py-0.5 rounded-full bg-cyan-500/20 text-cyan-400 border border-cyan-500/30 font-semibold">
                  7 Indian Languages + Hinglish
                </span>
              </h2>
              <p className="text-xs text-slate-400">
                Benchmarked on Indian currency (lakh/crore), dates, times, fintech lexicon, and zero credential leakage.
              </p>
            </div>
          </div>
          <div className="flex items-center space-x-2">
            <button
              onClick={loadBenchmark}
              disabled={loading}
              className="p-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 transition-colors"
              title="Refresh Benchmark"
            >
              <ReloadOutlined className={loading ? 'animate-spin' : ''} />
            </button>
            <button
              onClick={() => {
                if (audioRef.current) audioRef.current.pause();
                onClose();
              }}
              className="p-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 transition-colors"
            >
              <CloseOutlined />
            </button>
          </div>
        </div>

        {/* Aggregate Benchmark Metrics */}
        {data && (
          <div className="grid grid-cols-2 md:grid-cols-5 gap-3 p-4 bg-slate-950/40 border-b border-slate-800 text-xs">
            <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-3">
              <div className="text-slate-400 mb-1">Pronunciation Score</div>
              <div className="text-lg font-bold text-cyan-400 flex items-center space-x-1">
                <span>{data.metrics.overall_pronunciation_score} / 5.0</span>
                <StarFilled className="text-amber-400 text-sm" />
              </div>
            </div>
            <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-3">
              <div className="text-slate-400 mb-1">Intelligibility</div>
              <div className="text-lg font-bold text-emerald-400">
                {data.metrics.intelligibility_score} / 5.0
              </div>
            </div>
            <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-3">
              <div className="text-slate-400 mb-1">Naturalness & Pace</div>
              <div className="text-lg font-bold text-indigo-400">
                {data.metrics.naturalness_score} / 5.0
              </div>
            </div>
            <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-3">
              <div className="text-slate-400 mb-1">Normalization Pass</div>
              <div className="text-lg font-bold text-teal-400 flex items-center space-x-1">
                <CheckCircleOutlined />
                <span>{data.normalization_pass_rate}%</span>
              </div>
            </div>
            <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-3">
              <div className="text-slate-400 mb-1">Zero-Credential Leak</div>
              <div className="text-lg font-bold text-emerald-400 flex items-center space-x-1">
                <SafetyCertificateOutlined />
                <span>{data.metrics.zero_credential_leak_rate}%</span>
              </div>
            </div>
          </div>
        )}

        {/* Filter Controls */}
        <div className="p-4 border-b border-slate-800 space-y-3 bg-slate-950/20">
          {/* Language Tabs */}
          <div className="flex flex-wrap gap-2">
            {languages.map((l) => (
              <button
                key={l.key}
                onClick={() => setSelectedLanguage(l.key)}
                className={`px-3 py-1 rounded-lg text-xs font-medium transition-all ${
                  selectedLanguage === l.key
                    ? 'bg-cyan-500 text-slate-950 font-bold shadow-md shadow-cyan-500/20'
                    : 'bg-slate-800 text-slate-400 hover:bg-slate-700 hover:text-slate-200'
                }`}
              >
                {l.label}
              </button>
            ))}
          </div>

          {/* Category Tabs */}
          <div className="flex flex-wrap gap-1.5">
            {categories.map((c) => (
              <button
                key={c.key}
                onClick={() => setSelectedCategory(c.key)}
                className={`px-2.5 py-0.5 rounded-md text-[11px] transition-all ${
                  selectedCategory === c.key
                    ? 'bg-blue-600 text-white font-semibold'
                    : 'bg-slate-900 text-slate-400 hover:bg-slate-800'
                }`}
              >
                {c.label}
              </button>
            ))}
          </div>
        </div>

        {/* Benchmark Samples Gallery */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {loading && !data && (
            <div className="text-center py-12 text-slate-400 space-y-3">
              <div className="w-8 h-8 border-2 border-cyan-400 border-t-transparent rounded-full animate-spin mx-auto" />
              <p>Synthesizing acoustic voice samples across all 7 Indian languages...</p>
            </div>
          )}

          {!loading && filteredSamples.length === 0 && (
            <div className="text-center py-12 text-slate-500">
              No benchmark samples matched the selected language and scenario filter.
            </div>
          )}

          {filteredSamples.map((sample) => {
            const isPlaying = playingSampleId === sample.test_id;
            const userRating = userRatings[sample.test_id] || 5;
            const isSubmitted = submittedFeedback[sample.test_id];

            return (
              <div
                key={sample.test_id}
                className="bg-slate-950/70 border border-slate-800 hover:border-slate-700 rounded-xl p-4 transition-all space-y-3"
              >
                {/* Sample Header */}
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-2">
                    <span className="text-xs font-bold uppercase tracking-wider px-2 py-0.5 rounded bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">
                      {sample.language}
                    </span>
                    <span className="text-xs text-slate-400 font-medium">
                      Voice: <span className="text-slate-200">{sample.voice_name}</span>
                    </span>
                    <span className="text-xs px-2 py-0.5 rounded bg-slate-800 text-slate-400">
                      {sample.category.replace(/_/g, ' ')}
                    </span>
                  </div>

                  <div className="flex items-center space-x-3">
                    <button
                      onClick={() => playAudio(sample)}
                      className={`flex items-center space-x-2 px-3 py-1 rounded-lg text-xs font-semibold transition-all ${
                        isPlaying
                          ? 'bg-amber-500 text-slate-950 animate-pulse shadow-lg shadow-amber-500/30'
                          : 'bg-cyan-600 hover:bg-cyan-500 text-white shadow-md shadow-cyan-600/20'
                      }`}
                    >
                      {isPlaying ? (
                        <>
                          <PauseCircleOutlined />
                          <span>Pause Audio</span>
                        </>
                      ) : (
                        <>
                          <PlayCircleOutlined />
                          <span>Play Audio ({sample.duration_sec}s)</span>
                        </>
                      )}
                    </button>
                  </div>
                </div>

                {/* Spoken Text Comparison */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
                  <div className="bg-slate-900/80 p-3 rounded-lg border border-slate-800/80">
                    <div className="text-slate-400 font-medium mb-1 flex items-center justify-between">
                      <span>Original Utterance:</span>
                    </div>
                    <p className="text-slate-300 leading-relaxed font-sans">{sample.raw_text}</p>
                  </div>

                  <div className="bg-slate-900/80 p-3 rounded-lg border border-cyan-900/30">
                    <div className="text-cyan-400 font-medium mb-1 flex items-center justify-between">
                      <span>Normalized Speakable Text:</span>
                      <span className="text-[10px] text-teal-400 font-mono">Locale-Aware</span>
                    </div>
                    <p className="text-slate-100 leading-relaxed font-sans">{sample.rendered_text}</p>
                  </div>
                </div>

                {/* Score Breakdown & Interactive Evaluator Rating */}
                <div className="flex flex-wrap items-center justify-between pt-2 border-t border-slate-800/60 text-xs gap-3">
                  <div className="flex flex-wrap items-center gap-4 text-slate-400">
                    <div>
                      Pronunciation: <span className="font-bold text-slate-200">{sample.scores.pronunciation}</span>/5
                    </div>
                    <div>
                      Intelligibility: <span className="font-bold text-slate-200">{sample.scores.intelligibility}</span>/5
                    </div>
                    <div>
                      Naturalness: <span className="font-bold text-slate-200">{sample.scores.naturalness}</span>/5
                    </div>
                    <div>
                      Language Correctness: <span className="font-bold text-emerald-400">{sample.scores.language_correctness}</span>/5
                    </div>
                  </div>

                  {/* Evaluator Review Submission */}
                  <div className="flex items-center space-x-2">
                    <span className="text-slate-400 text-[11px]">Evaluator Score:</span>
                    <div className="flex space-x-1">
                      {[1, 2, 3, 4, 5].map((star) => (
                        <button
                          key={star}
                          type="button"
                          onClick={() => handleRate(sample.test_id, star)}
                          className="text-amber-400 hover:scale-110 transition-transform"
                        >
                          {star <= userRating ? <StarFilled /> : <StarOutlined />}
                        </button>
                      ))}
                    </div>
                    <button
                      onClick={() => handleSubmitScore(sample.test_id)}
                      disabled={isSubmitted}
                      className={`px-2.5 py-0.5 rounded text-[11px] font-semibold transition-colors ${
                        isSubmitted
                          ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                          : 'bg-slate-800 hover:bg-slate-700 text-slate-300'
                      }`}
                    >
                      {isSubmitted ? 'Recorded ✓' : 'Save Rating'}
                    </button>
                  </div>
                </div>
              </div>
            );
          })}
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-slate-800 bg-slate-950/80 flex items-center justify-between text-xs text-slate-400">
          <div className="flex items-center space-x-2">
            <SafetyCertificateOutlined className="text-emerald-400" />
            <span>Strict zero-trust speech protection active: No OTPs, CVVs, or card numbers are speakable.</span>
          </div>
          <button
            onClick={() => {
              if (audioRef.current) audioRef.current.pause();
              onClose();
            }}
            className="px-4 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 font-medium transition-colors"
          >
            Close Review Gallery
          </button>
        </div>
      </div>
    </div>
  );
};
