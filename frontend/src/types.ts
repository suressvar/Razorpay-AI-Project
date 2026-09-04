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
  action: 'CREATE_PAYMENT_LINK' | 'INFO_QUERY' | 'ANALYZE_ALL' | 'HELP_PAYMENT_LINK' | 'SEARCH_EMAIL';
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

export interface VoiceTurn {
  turn_id: string;
  role: 'system' | 'agent' | 'customer';
  text: string;
  translated_text?: string;
  language: 'hinglish' | 'hindi' | 'english' | 'unknown';
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

export interface VoiceEvaluationReport {
  total_evaluated: number;
  intent_accuracy: number;
  macro_f1: number;
  language_accuracy: number;
  safety_violation_rate: number;
  human_escalation_fidelity: number;
  per_class_metrics: Record<string, { precision: number; recall: number; f1: number; support: number }>;
  dataset_size: number;
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


