import {
  AuditEvent,
  BenchmarkReport,
  NotificationPreview,
  PaymentCase,
  SummaryMetrics,
} from './types';

const API_BASE = '';

export async function fetchMetricsSummary(): Promise<SummaryMetrics> {
  const res = await fetch(`${API_BASE}/metrics/summary`);
  if (!res.ok) throw new Error('Failed to fetch metrics summary');
  return res.json();
}

export async function fetchEvaluationMetrics(): Promise<BenchmarkReport> {
  const res = await fetch(`${API_BASE}/metrics/evaluation`);
  if (!res.ok) throw new Error('Failed to fetch evaluation metrics');
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
  if (!res.ok) throw new Error('Failed to fetch cases');
  return res.json();
}

export async function fetchCaseDetail(caseId: string): Promise<PaymentCase> {
  const res = await fetch(`${API_BASE}/cases/${caseId}`);
  if (!res.ok) throw new Error('Failed to fetch case details');
  return res.json();
}

export async function fetchCaseAudit(caseId: string): Promise<AuditEvent[]> {
  const res = await fetch(`${API_BASE}/cases/${caseId}/audit`);
  if (!res.ok) throw new Error('Failed to fetch case audit trail');
  return res.json();
}

export async function fetchCaseNotifications(caseId: string): Promise<NotificationPreview[]> {
  const res = await fetch(`${API_BASE}/cases/${caseId}/notifications`);
  if (!res.ok) throw new Error('Failed to fetch case notifications');
  return res.json();
}

export async function approveCase(caseId: string, operatorId: string = 'ops_admin'): Promise<any> {
  const res = await fetch(`${API_BASE}/cases/${caseId}/approve`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ operator_id: operatorId }),
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || 'Approval failed');
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
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ operator_id: operatorId, reason }),
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || 'Rejection failed');
  }
  return res.json();
}

export async function retryCaseNow(caseId: string): Promise<any> {
  const res = await fetch(`${API_BASE}/cases/${caseId}/retry`, {
    method: 'POST',
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || 'Retry failed');
  }
  return res.json();
}

export async function seedDemoData(count: number = 50, seed: number = 42): Promise<any> {
  const res = await fetch(`${API_BASE}/demo/seed`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ count, seed }),
  });
  if (!res.ok) throw new Error('Failed to seed demo data');
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
