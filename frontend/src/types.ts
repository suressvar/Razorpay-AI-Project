export type FailureCategory =
  | 'INSUFFICIENT_FUNDS'
  | 'BANK_TIMEOUT'
  | 'EXPIRED_CARD'
  | 'MANDATE_REVOKED'
  | 'LIMIT_EXCEEDED'
  | 'NETWORK_FAILURE'
  | 'CUSTOMER_ACTION_REQUIRED'
  | 'UNKNOWN_FAILURE';

export type CaseStatus =
  | 'NEW'
  | 'DIAGNOSING'
  | 'AWAITING_POLICY'
  | 'SCHEDULED'
  | 'AWAITING_APPROVAL'
  | 'ACTION_IN_PROGRESS'
  | 'MONITORING'
  | 'PROMISED_TO_PAY'
  | 'RECOVERED'
  | 'EXHAUSTED'
  | 'OPTED_OUT'
  | 'STOPPED'
  | 'ERROR';

export type RecoveryAction =
  | 'WAIT_FOR_RETRY'
  | 'SEND_PAYMENT_LINK'
  | 'REQUEST_METHOD_UPDATE'
  | 'SEND_REMINDER'
  | 'HUMAN_REVIEW'
  | 'STOP';

export interface PaymentContext {
  payment_id: string;
  subscription_id: string;
  invoice_id?: string;
  customer_id: string;
  customer_name: string;
  customer_email: string;
  customer_phone: string;
  amount_inr: number;
  currency: string;
  failure_category: FailureCategory;
  failure_code: string;
  failure_reason: string;
  payment_method: string;
  customer_segment: string;
  previous_failures: number;
  previous_contacts: number;
  bank_name?: string;
  bank_degraded: boolean;
  opted_out: boolean;
  occurred_at: string;
}

export interface RecoveryProposal {
  action: RecoveryAction;
  confidence: number;
  delay_minutes: number;
  reason_codes: string[];
  explanation: string;
  customer_message?: string;
  requires_human_approval: boolean;
  model_name?: string;
  prompt_version?: string;
}

export interface PolicyDecision {
  decision_id: string;
  case_id: string;
  allowed: boolean;
  approved_action: RecoveryAction;
  modified_delay_minutes?: number;
  reason_codes: string[];
  requires_human_review: boolean;
  block_reason?: string;
  decided_at: string;
}

export interface ExecutionResult {
  action: RecoveryAction;
  external_id?: string;
  status: string;
  executed_at: string;
  metadata: Record<string, any>;
  error?: string;
}

export interface PaymentOutcome {
  case_id: string;
  recovered: boolean;
  recovered_amount: number;
  recovered_at?: string;
  contact_count: number;
}

export interface PaymentCase {
  case_id: string;
  context: PaymentContext;
  status: CaseStatus;
  current_proposal?: RecoveryProposal;
  latest_decision?: PolicyDecision;
  latest_action_result?: ExecutionResult;
  outcome?: PaymentOutcome;
  contact_count: number;
  created_at: string;
  updated_at: string;
}

export interface AuditEvent {
  event_id: string;
  case_id: string;
  timestamp: string;
  actor: string;
  event_type: string;
  details: Record<string, any>;
}

export interface NotificationPreview {
  notification_id: string;
  case_id: string;
  channel: string;
  recipient_masked: string;
  content: string;
  sent_at: string;
  status: string;
}

export interface SummaryMetrics {
  total_cases: number;
  recovered_cases: number;
  total_inr_recovered: number;
  recovery_rate: number;
  awaiting_approval_count: number;
  recent_audits: AuditEvent[];
}

export interface CategoryMetric {
  category: string;
  total_cases: number;
  agent_recovered_count: number;
  agent_recovery_rate: number;
  baseline_recovered_count: number;
  baseline_recovery_rate: number;
  incremental_rate_pct: number;
  agent_inr_recovered: number;
  baseline_inr_recovered: number;
}

export interface BenchmarkReport {
  dataset_size: number;
  random_seed: number;
  dataset_version?: string;
  prompts_version?: string;
  model_provider?: string;
  model_identifier?: string;
  is_synthetic_simulation?: boolean;
  dev_dataset_size?: number;
  held_out_dataset_size?: number;
  action_accuracy_pct?: number;
  escalation_precision_pct?: number;
  escalation_recall_pct?: number;
  policy_violations_count?: number;
  assumptions_note?: string;
  agent_total_inr_recovered: number;
  agent_recovery_rate: number;
  agent_median_recovery_time_hours: number;
  agent_contacts_per_recovered: number;
  agent_human_review_rate: number;
  agent_safety_violations: number;
  baseline_total_inr_recovered: number;
  baseline_recovery_rate: number;
  baseline_median_recovery_time_hours: number;
  baseline_contacts_per_recovered: number;
  baseline_safety_violations: number;
  incremental_inr_recovered: number;
  incremental_recovery_rate_pct: number;
  unnecessary_contacts_avoided: number;
  agent_recovery_rate_ci_lower: number;
  agent_recovery_rate_ci_upper: number;
  baseline_recovery_rate_ci_lower: number;
  baseline_recovery_rate_ci_upper: number;
  category_breakdown: CategoryMetric[];
}

export interface FollowUpSuggestion {
  id: string;
  number?: number;
  text: string;
  action: 'CREATE_PAYMENT_LINK' | 'INFO_QUERY' | 'ANALYZE_ALL' | 'HELP_PAYMENT_LINK' | 'SEARCH_EMAIL' | 'DRAFT_EMAIL' | 'VIEW_ISSUE';
  case_id?: string;
}

export interface CopilotDiagnosis {
  case_id: string;
  payment_id: string;
  customer_name: string;
  customer_email: string;
  customer_phone: string;
  masked_phone: string;
  amount_inr: number;
  currency: string;
  failure_category: string;
  failure_reason: string;
  headline: string;
  explanation: string;
  auto_reversal_timeline?: string | null;
  resolution_name: string;
  resolution_instruction: string;
  recommendation: string;
}

export interface CopilotChatResponse {
  type: 'diagnosis' | 'fallback';
  headline?: string | null;
  message?: string;
  diagnosis?: CopilotDiagnosis | null;
  suggestions: FollowUpSuggestion[];
  matched_case_id?: string;
}

export interface CreatePaymentLinkPayload {
  case_id: string;
  amount_inr: number;
  customer_email: string;
  customer_phone: string;
  expiry_date?: string;
  note?: string;
  agent_name?: string;
}

export interface CreatePaymentLinkResponse {
  status: string;
  case_id: string;
  payment_link_id: string;
  short_url: string;
  amount_inr: number;
  customer_email: string;
  customer_phone: string;
  created_at: string;
  note?: string;
}

export interface UnmatchedWebhookRecord {
  event_id: string;
  event_type: string;
  signature?: string;
  payload_json: string;
  reason: string;
  received_at: string;
}

export interface QueueStats {
  queued: number;
  processing: number;
  completed: number;
  failed: number;
  dead_letter: number;
  unmatched: number;
  total_events: number;
}

export type VoiceSessionState =
  | 'INITIALIZED'
  | 'AWAITING_CONSENT'
  | 'GREETING'
  | 'EXPLAINING_FAILURE'
  | 'AWAITING_INTENT'
  | 'CLARIFICATION'
  | 'PROPOSING_OPTION'
  | 'AWAITING_CONFIRMATION'
  | 'EXECUTING_ACTION'
  | 'RECORDING_PROMISE'
  | 'CLOSURE'
  | 'ESCALATED_TO_HUMAN'
  | 'TERMINATED';

export type VoiceIntent =
  | 'pay_now'
  | 'send_payment_link'
  | 'retry_later'
  | 'promise_to_pay'
  | 'already_paid'
  | 'dispute'
  | 'request_human'
  | 'stop_contact'
  | 'confirm_yes'
  | 'confirm_no'
  | 'unclear'
  | 'unknown';

export type VoiceLanguage =
  | 'auto'
  | 'english'
  | 'hindi'
  | 'kannada'
  | 'tamil'
  | 'telugu'
  | 'marathi'
  | 'bengali'
  | 'hinglish'
  | 'kanglish'
  | 'tanglish'
  | 'tenglish'
  | 'marathi_english'
  | 'bengali_english';

export interface VoiceTurn {
  turn_id: string;
  role: 'system' | 'agent' | 'customer';
  text: string;
  translated_text?: string;
  language: VoiceLanguage | 'unknown';
  detected_intent?: VoiceIntent;
  confidence_score: number;
  action_suggested?: string;
  timestamp: string;
}

export interface PromiseToPayDraft {
  case_id: string;
  customer_id: string;
  promised_amount: number;
  promised_date: string;
  channel: string;
  notes?: string;
}

export interface VoiceSession {
  session_id: string;
  case_id: string;
  customer_id: string;
  customer_name: string;
  amount: number;
  currency: string;
  failure_reason: string;
  preferred_language: VoiceLanguage;
  state: VoiceSessionState;
  has_consent: boolean;
  turns: VoiceTurn[];
  promise_draft?: PromiseToPayDraft | null;
  clarification_attempts: number;
  action_executed?: string | null;
  audit_log: string[];
  created_at: string;
  updated_at: string;
}

export interface VoiceScenarioPreset {
  scenario_id: string;
  title: string;
  description: string;
  customer_persona: string;
  sample_utterances: string[];
  expected_intent: VoiceIntent;
  expected_outcome: string;
}

export type STTModelProfile = 'fast' | 'balanced' | 'accurate';

export interface AudioDiagnostics {
  microphone_name?: string;
  input_sample_rate: number;
  processed_sample_rate: number;
  recording_duration_sec: number;
  speech_duration_sec: number;
  signal_level_rms: number;
  peak_amplitude: number;
  is_clipped: boolean;
  detected_language: string;
  transcription_confidence: number;
  latency_ms: number;
  raw_transcript: string;
  normalized_transcript: string;
  extracted_intent: string;
}

export interface TranscriptMetadata {
  original_transcript: string;
  normalized_transcript: string;
  detected_language: string;
  language_confidence: number;
  alternative_languages: string[];
  code_switched: boolean;
  transcription_confidence: number;
  needs_clarification: boolean;
}

export interface StructuredIntentResult {
  intent: string;
  confidence: number;
  entities: {
    promised_date?: string | null;
    promised_time?: string | null;
    amount?: number | null;
    requested_language?: string | null;
  };
  requires_confirmation: boolean;
  requires_human: boolean;
  clarification_question?: string | null;
  safety_reason?: string | null;
}

export interface VoiceEvaluationReport {
  total_benchmark_cases?: number;
  total_evaluated?: number;
  overall_intent_accuracy?: number;
  intent_accuracy?: number;
  macro_f1?: number;
  macro_precision?: number;
  macro_recall?: number;
  language_identification_accuracy?: number;
  language_accuracy?: number;
  critical_intent_recall?: number;
  false_confirmation_rate?: number;
  clarification_rate?: number;
  safety_violations_detected?: number;
  anti_otp_pin_guardrail_pass?: boolean;
  median_latency_ms?: number;
  p95_latency_ms?: number;
  per_language_report?: Record<
    string,
    {
      total_utterances: number;
      intent_accuracy: number;
      language_accuracy: number;
      avg_wer: number;
      median_latency_ms: number;
      p95_latency_ms: number;
    }
  >;
  supported_languages?: string[];
  benchmark_dataset_version?: string;
}

export interface AccountSettingsData {
  merchant: {
    merchant_id: string;
    business_name: string;
    gstin: string;
    business_type: string;
    registered_email: string;
    support_contact: string;
    webhook_url: string;
    webhook_secret_set: boolean;
  };
  gateway: {
    execution_mode: 'synthetic' | 'razorpay_test' | 'production';
    key_id_masked: string;
    key_id: string;
    key_secret_configured: boolean;
    webhook_secret_masked: string;
    kill_switch_active: boolean;
    allow_production_mode: boolean;
    confirm_live_financial_transactions: boolean;
  };
  ai_model: {
    active_provider: 'gemini' | 'openai' | 'ollama' | 'fake';
    gemini_model: string;
    gemini_api_key_set: boolean;
    gemini_temperature: number;
    openai_model: string;
    openai_api_key_set: boolean;
    openai_base_url: string;
    ollama_model: string;
    ollama_base_url: string;
  };
  policies: {
    human_review_threshold_inr: number;
    min_confidence_threshold: number;
    max_contact_attempts: number;
    min_hours_between_contacts: number;
    max_contacts_per_week: number;
    max_retry_delay_minutes: number;
  };
  voice: {
    voice_enabled: boolean;
    voice_stt_provider: string;
    voice_tts_provider: string;
    voice_min_confidence_threshold: number;
    voice_session_timeout_seconds: number;
  };
  team: Array<{
    id: string;
    name: string;
    email: string;
    role: 'admin' | 'reviewer' | 'viewer';
    status: string;
    last_active: string;
  }>;
  channels: {
    whatsapp: { enabled: boolean; status: string; sender: string };
    sms: { enabled: boolean; status: string; sender: string };
    email: { enabled: boolean; status: string; sender: string };
    voice: { enabled: boolean; status: string; agent_name: string };
  };
}

export interface TTSVoiceProfile {
  voice_id: string;
  name: string;
  language: string;
  locale: string;
  gender: 'female' | 'male' | 'neutral';
  sample_rate: number;
  naturalness_score: number;
  description: string;
  is_native: boolean;
}

export interface TTSSynthesizeResponse {
  audio_base64: string;
  audio_format: string;
  sample_rate: number;
  duration_sec: number;
  text_spoken: string;
  ssml_used?: string | null;
  language: string;
  voice_id: string;
  tier: string;
  metadata: {
    voice_name?: string;
    locale?: string;
    gender?: string;
    latency_ms?: number;
    original_text?: string;
  };
}

export interface TTSBenchmarkSample {
  test_id: string;
  category: string;
  language: string;
  voice_id: string;
  voice_name: string;
  raw_text: string;
  rendered_text: string;
  duration_sec: number;
  audio_base64: string;
  scores: {
    pronunciation: number | string;
    intelligibility: number | string;
    naturalness: number | string;
    pace: number | string;
    language_correctness: number | string;
  };
}

export interface TTSBenchmarkResponse {
  total_test_cases: number;
  normalization_pass_rate: number;
  audio_synthesis_pass_rate: number;
  supported_languages: string[];
  available_voices: TTSVoiceProfile[];
  sample_gallery: TTSBenchmarkSample[];
  metrics: {
    overall_pronunciation_score: number | string;
    intelligibility_score: number | string;
    naturalness_score: number | string;
    pace_score: number | string;
    zero_credential_leak_rate: number;
    is_synthetic_mock?: boolean;
    note?: string;
  };
}

export interface VoiceReadinessCheckItem {
  category: string;
  name: string;
  passed: boolean;
  details: string;
  metric: string;
  is_mock?: boolean;
  missing_dependency?: string | null;
}

export interface VoiceReadinessReport {
  is_ready: boolean;
  readiness_score: number;
  demo_mode: string;
  audit_latency_ms: number;
  supported_languages: Array<{
    code: string;
    name: string;
    native: string;
    voice: string;
  }>;
  checks: VoiceReadinessCheckItem[];
  summary: string;
}

// --- Copilot V2 Issue Tracking & Investigation Types ---

export type IssueStatus =
  | 'NEW'
  | 'INVESTIGATING'
  | 'AWAITING_INFO'
  | 'ACTION_IN_PROGRESS'
  | 'MONITORING'
  | 'RESOLVED'
  | 'CLOSED';

export type IssueSeverity = 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';

export interface IssueEvidence {
  evidence_id: string;
  source: string;
  description: string;
  raw_data?: any;
  confidence: 'HIGH' | 'MEDIUM' | 'LOW';
  timestamp?: string;
}

export interface IssueCause {
  cause_id: string;
  description: string;
  confidence: 'HIGH' | 'MEDIUM' | 'LOW';
  supporting_evidence?: string[];
  contradicting_evidence?: string[];
  missing_evidence?: string[];
  recommended_action?: string | null;
  is_confirmed?: boolean;
}

export interface IssueAction {
  action_id: string;
  action_type: string;
  description: string;
  status: 'PENDING' | 'COMPLETED' | 'FAILED' | 'APPROVAL_REQUIRED';
  result?: any;
  error_message?: string | null;
  requires_approval: boolean;
  executed_by: string;
  executed_at?: string | null;
  created_at?: string;
}

export interface IssueCommunication {
  communication_id: string;
  channel: 'EMAIL' | 'SMS' | 'WHATSAPP';
  direction: 'inbound' | 'outbound';
  recipient: string;
  subject?: string | null;
  body: string;
  template_used?: string | null;
  provider_message_id?: string | null;
  status: 'DRAFT' | 'QUEUED' | 'ACCEPTED' | 'DELIVERED' | 'FAILED';
  idempotency_key?: string | null;
  sent_at?: string | null;
  created_at?: string;
}

export interface IssueTimelineEntry {
  entry_id: string;
  timestamp: string;
  event_type: string;
  actor: string;
  summary: string;
  details?: any;
}

export interface CustomerIssue {
  issue_id: string;
  title: string;
  category: string;
  severity: IssueSeverity;
  status: IssueStatus;
  environment: 'TEST' | 'LIVE';
  merchant_id?: string | null;
  customer_id?: string | null;
  customer_name?: string | null;
  customer_email?: string | null;
  payment_id?: string | null;
  order_id?: string | null;
  refund_id?: string | null;
  payment_link_id?: string | null;
  case_id?: string | null;
  owner?: string | null;
  sla_deadline?: string | null;
  next_action?: string | null;
  reported_symptoms?: string | null;
  expected_behavior?: string | null;
  actual_behavior?: string | null;
  evidence: IssueEvidence[];
  possible_causes: IssueCause[];
  actions: IssueAction[];
  communications: IssueCommunication[];
  timeline: IssueTimelineEntry[];
  resolution_summary?: string | null;
  resolution_verified: boolean;
  resolution_evidence?: string | null;
  created_at: string;
  updated_at: string;
}

export interface EmailDraft {
  draft_id: string;
  issue_id?: string | null;
  case_id?: string | null;
  template_id?: string | null;
  recipient_email: string;
  recipient_name?: string | null;
  subject: string;
  body_html: string;
  body_text: string;
  status: 'DRAFT' | 'QUEUED' | 'ACCEPTED' | 'DELIVERED' | 'FAILED';
  provider_message_id?: string | null;
  sent_at?: string | null;
  error_message?: string | null;
  created_by?: string;
  created_at?: string;
  updated_at?: string;
}

export interface CopilotV2Investigation {
  type: string;
  issue_id: string;
  case_id?: string;
  steps: Array<{
    step: string;
    step_type?: string;
    title?: string;
    description?: string;
    status: string;
    details?: any;
    duration_ms?: number;
  }>;
  what_happened: {
    headline: string;
    explanation: string;
    auto_reversal_timeline?: string;
    timeline: Array<{
      timestamp?: string | null;
      event: string;
      details: string;
    }>;
  };
  verified_evidence: IssueEvidence[];
  possible_causes: IssueCause[];
  recommended_solution: {
    resolution_name: string;
    resolution_instruction: string;
    recommendation: string;
  };
  available_actions: Array<{
    action: string;
    label: string;
    enabled: boolean;
    requires_approval: boolean;
  }>;
  diagnosis: any;
}

