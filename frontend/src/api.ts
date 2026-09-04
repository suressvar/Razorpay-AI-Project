import {
  AuditEvent,
  BenchmarkReport,
  CopilotChatResponse,
  CreatePaymentLinkPayload,
  CreatePaymentLinkResponse,
  NotificationPreview,
  PaymentCase,
  SummaryMetrics,
} from './types';

const API_BASE = '';

async function handleResponseError(res: Response, fallbackMessage: string): Promise<never> {
  let errMsg = fallbackMessage;
  try {
    const err = await res.json();
    if (typeof err.detail === 'string') {
      errMsg = err.detail;
    } else if (Array.isArray(err.detail)) {
      errMsg = err.detail.map((d: any) => d.msg || JSON.stringify(d)).join(', ');
    } else if (err.message) {
      errMsg = err.message;
    }
  } catch {
    const txt = await res.text().catch(() => '');
    if (txt && !txt.includes('<!DOCTYPE') && !txt.includes('<html')) {
      errMsg = txt;
    } else {
      errMsg = `${fallbackMessage} (Status ${res.status})`;
    }
  }
  throw new Error(errMsg);
}

export async function fetchMetricsSummary(): Promise<SummaryMetrics> {
  const res = await fetch(`${API_BASE}/metrics/summary`);
  if (!res.ok) await handleResponseError(res, 'Failed to fetch metrics summary');
  return res.json();
}

export async function fetchEvaluationMetrics(): Promise<BenchmarkReport> {
  const res = await fetch(`${API_BASE}/metrics/evaluation`);
  if (!res.ok) await handleResponseError(res, 'Failed to fetch evaluation metrics');
  return res.json();
}

export async function fetchCases(
  status?: string,
  category?: string,
  limit: number = 100
): Promise<PaymentCase[]> {
  const params = new URLSearchParams();
  if (status && status !== 'ALL') params.append('status', status);
  if (category && category !== 'ALL') params.append('category', category);
  params.append('limit', limit.toString());

  const res = await fetch(`${API_BASE}/cases?${params.toString()}`);
  if (!res.ok) await handleResponseError(res, 'Failed to fetch cases');
  return res.json();
}

export async function fetchCaseDetail(caseId: string): Promise<PaymentCase> {
  const res = await fetch(`${API_BASE}/cases/${caseId}`);
  if (!res.ok) await handleResponseError(res, 'Failed to fetch case details');
  return res.json();
}

export async function fetchCaseAudit(caseId: string): Promise<AuditEvent[]> {
  const res = await fetch(`${API_BASE}/cases/${caseId}/audit`);
  if (!res.ok) await handleResponseError(res, 'Failed to fetch case audit trail');
  return res.json();
}

export async function fetchCaseNotifications(caseId: string): Promise<NotificationPreview[]> {
  const res = await fetch(`${API_BASE}/cases/${caseId}/notifications`);
  if (!res.ok) await handleResponseError(res, 'Failed to fetch case notifications');
  return res.json();
}

export async function approveCase(caseId: string, operatorId: string = 'ops_admin'): Promise<any> {
  const res = await fetch(`${API_BASE}/cases/${caseId}/approve`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-Operator-Role': 'admin',
      'X-Operator-Id': operatorId,
    },
    body: JSON.stringify({ operator_id: operatorId }),
  });
  if (!res.ok) {
    await handleResponseError(res, 'Approval failed');
  }
  return res.json();
}

export async function rejectCase(
  caseId: string,
  reason: string,
  operatorId: string = 'ops_admin'
): Promise<any> {
  const res = await fetch(`${API_BASE}/cases/${caseId}/reject`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-Operator-Role': 'admin',
      'X-Operator-Id': operatorId,
    },
    body: JSON.stringify({ operator_id: operatorId, reason }),
  });
  if (!res.ok) {
    await handleResponseError(res, 'Rejection failed');
  }
  return res.json();
}

export async function retryCaseNow(caseId: string): Promise<any> {
  const res = await fetch(`${API_BASE}/cases/${caseId}/retry`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-Operator-Role': 'admin',
      'X-Operator-Id': 'ops_admin',
    },
  });
  if (!res.ok) {
    await handleResponseError(res, 'Retry failed');
  }
  return res.json();
}


export async function seedDemoData(count: number = 50, seed: number = 42): Promise<any> {
  const res = await fetch(`${API_BASE}/demo/seed`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ count, seed }),
  });
  if (!res.ok) {
    await handleResponseError(res, 'Failed to seed demo data');
  }
  return res.json();
}

export async function clearAllDemoData(): Promise<any> {
  const res = await fetch(`${API_BASE}/demo/clear`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
  });
  if (!res.ok) {
    await handleResponseError(res, 'Failed to clear application demo data');
  }
  return res.json();
}


export async function triggerEvaluationRun(size: number = 500, seed: number = 42): Promise<BenchmarkReport> {
  const res = await fetch(`${API_BASE}/demo/run-evaluation`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ size, seed }),
  });
  if (!res.ok) throw new Error('Failed to run simulation benchmark');
  return res.json();
}

export const runEvaluation = triggerEvaluationRun;

export async function simulateWebhook(
  eventType: string = 'payment.failed',
  category: string = 'INSUFFICIENT_FUNDS',
  amountInr: number = 3499.0
): Promise<any> {
  const res = await fetch(`${API_BASE}/demo/simulate-webhook`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      event_type: eventType,
      category: category,
      amount_inr: amountInr,
    }),
  });
  if (!res.ok) throw new Error('Failed to simulate webhook');
  return res.json();
}

export async function sendCopilotMessage(
  query: string,
  imageBase64?: string,
  imageName?: string,
  agentName: string = 'Support Agent'
): Promise<CopilotChatResponse> {
  const res = await fetch(`${API_BASE}/copilot/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      query,
      image_base64: imageBase64,
      image_name: imageName,
      agent_name: agentName,
    }),
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || 'Copilot query failed');
  }
  return res.json();
}

export async function createCopilotPaymentLink(
  payload: CreatePaymentLinkPayload
): Promise<CreatePaymentLinkResponse> {
  const res = await fetch(`${API_BASE}/copilot/create-payment-link`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || 'Payment Link creation failed');
  }
  return res.json();
}

export async function fetchUnmatchedWebhooks(limit: number = 50, offset: number = 0): Promise<any[]> {
  const res = await fetch(`${API_BASE}/webhooks/unmatched?limit=${limit}&offset=${offset}`);
  if (!res.ok) throw new Error('Failed to fetch unmatched webhooks');
  return res.json();
}

export async function fetchQueueStats(): Promise<any> {
  const res = await fetch(`${API_BASE}/webhooks/queue/stats`);
  if (!res.ok) throw new Error('Failed to fetch queue statistics');
  return res.json();
}

// --- Voice Recovery Agent API ---

export async function fetchVoiceScenarios(): Promise<any[]> {
  const res = await fetch(`${API_BASE}/voice/scenarios`);
  if (!res.ok) throw new Error('Failed to fetch voice scenarios');
  return res.json();
}

export async function fetchVoiceEvaluation(): Promise<any> {
  const res = await fetch(`${API_BASE}/voice/evaluation`);
  if (!res.ok) throw new Error('Failed to fetch voice evaluation');
  return res.json();
}

export async function startVoiceSession(
  caseId: string,
  languageHint: import('./types').VoiceLanguage = 'english'
): Promise<any> {
  const res = await fetch(`${API_BASE}/voice/sessions/start`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ case_id: caseId, language_hint: languageHint }),
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || 'Failed to start voice session');
  }
  return res.json();
}

export async function getVoiceSession(sessionId: string): Promise<any> {
  const res = await fetch(`${API_BASE}/voice/sessions/${sessionId}`);
  if (!res.ok) throw new Error('Failed to retrieve voice session');
  return res.json();
}

export async function setVoiceSessionConsent(sessionId: string, consentGranted: boolean): Promise<any> {
  const res = await fetch(`${API_BASE}/voice/sessions/${sessionId}/consent`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ consent_granted: consentGranted }),
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || 'Failed to record consent');
  }
  return res.json();
}

export async function sendVoiceUtterance(
  sessionId: string,
  text: string,
  languageHint?: import('./types').VoiceLanguage,
  transcriptionConfidence?: number
): Promise<any> {
  const res = await fetch(`${API_BASE}/voice/sessions/${sessionId}/utterance`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      text,
      language_hint: languageHint,
      transcription_confidence: transcriptionConfidence,
    }),
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || 'Failed to process voice utterance');
  }
  return res.json();
}

export async function sendVoiceAudioUtterance(
  sessionId: string,
  audioBase64: string,
  languageHint?: string,
  profile: string = 'balanced',
  clientDiagnostics?: Record<string, any>
): Promise<any> {
  const res = await fetch(`${API_BASE}/voice/sessions/${sessionId}/audio`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      audio_base64: audioBase64,
      language_hint: languageHint || null,
      profile,
      client_diagnostics: clientDiagnostics || {},
    }),
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || 'Failed to process audio utterance');
  }
  return res.json();
}

export async function warmupSTT(profile: string = 'balanced'): Promise<any> {
  const res = await fetch(`${API_BASE}/voice/stt/warmup?profile=${profile}`, {
    method: 'POST',
  });
  if (!res.ok) throw new Error('Failed to warmup STT');
  return res.json();
}

export async function getSTTInfo(): Promise<any> {
  const res = await fetch(`${API_BASE}/voice/stt/info`);
  if (!res.ok) throw new Error('Failed to fetch STT info');
  return res.json();
}

export async function confirmVoiceAction(sessionId: string): Promise<any> {
  const res = await fetch(`${API_BASE}/voice/sessions/${sessionId}/confirm`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || 'Failed to confirm voice action');
  }
  return res.json();
}

export async function escalateVoiceSession(sessionId: string, reason?: string): Promise<any> {
  const res = await fetch(`${API_BASE}/voice/sessions/${sessionId}/escalate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ reason: reason || 'Customer request' }),
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || 'Failed to escalate voice session');
  }
  return res.json();
}

export async function deleteVoiceTranscript(sessionId: string): Promise<any> {
  const res = await fetch(`${API_BASE}/voice/sessions/${sessionId}/transcript`, {
    method: 'DELETE',
  });
  if (!res.ok) throw new Error('Failed to purge voice transcript');
  return res.json();
}

// --- Account & Settings API ---

export async function fetchAccountSettings(): Promise<import('./types').AccountSettingsData> {
  const res = await fetch(`${API_BASE}/admin/settings`);
  if (!res.ok) throw new Error('Failed to fetch account settings');
  return res.json();
}

export async function updateAccountSettings(
  payload: Partial<{
    model_provider: string;
    gemini_api_key: string;
    gemini_model: string;
    openai_api_key: string;
    openai_model: string;
    ollama_model: string;
    ollama_base_url: string;
    payment_execution_mode: string;
    human_review_threshold_inr: number;
    min_confidence_threshold: number;
    max_contact_attempts: number;
    min_hours_between_contacts: number;
    voice_enabled: boolean;
  }>,
  operatorId: string = 'ops_admin'
): Promise<any> {
  const res = await fetch(`${API_BASE}/admin/settings`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-Operator-Id': operatorId,
    },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || 'Failed to update settings');
  }
  return res.json();
}

export async function toggleKillSwitch(
  active: boolean,
  reason: string = 'Manual operator toggle via Account & Settings',
  operatorId: string = 'ops_admin'
): Promise<any> {
  const res = await fetch(`${API_BASE}/admin/kill-switch`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-Operator-Id': operatorId,
    },
    body: JSON.stringify({ active, reason }),
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || 'Failed to toggle kill switch');
  }
  return res.json();
}

export async function testAIModelInference(params: {
  error_code?: string;
  error_description?: string;
  amount_inr?: number;
  customer_tier?: string;
}): Promise<any> {
  const res = await fetch(`${API_BASE}/admin/test-model`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params),
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || 'Failed to test model inference');
  }
  return res.json();
}

export async function simulateTestWebhook(): Promise<any> {
  const res = await fetch(`${API_BASE}/admin/test-webhook`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || 'Failed to simulate test webhook');
  }
  return res.json();
}

export async function fetchSystemDiagnostics(): Promise<any> {
  const res = await fetch(`${API_BASE}/admin/system-diagnostics`);
  if (!res.ok) {
    throw new Error('Failed to fetch system diagnostics');
  }
  return res.json();
}

// --- Multilingual Text-to-Speech (TTS) API ---

export async function fetchTTSVoices(language?: string): Promise<import('./types').TTSVoiceProfile[]> {
  const url = language ? `${API_BASE}/voice/tts/voices?language=${encodeURIComponent(language)}` : `${API_BASE}/voice/tts/voices`;
  const res = await fetch(url);
  if (!res.ok) throw new Error('Failed to fetch TTS voices');
  return res.json();
}

export async function synthesizeTTSAudio(params: {
  text: string;
  language?: string;
  voice_id?: string;
  rate?: number;
  pitch?: number;
  tier?: string;
  use_ssml?: boolean;
}): Promise<import('./types').TTSSynthesizeResponse> {
  const res = await fetch(`${API_BASE}/voice/tts/synthesize`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params),
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || 'TTS synthesis failed');
  }
  return res.json();
}

export async function fetchTTSBenchmark(): Promise<import('./types').TTSBenchmarkResponse> {
  const res = await fetch(`${API_BASE}/voice/tts/benchmark`);
  if (!res.ok) throw new Error('Failed to run TTS benchmark');
  return res.json();
}

export async function fetchVoiceReadiness(): Promise<import('./types').VoiceReadinessReport> {
  const res = await fetch(`${API_BASE}/voice/demo/readiness`);
  if (!res.ok) throw new Error('Failed to fetch voice readiness audit');
  return res.json();
}




