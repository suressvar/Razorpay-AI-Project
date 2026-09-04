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
