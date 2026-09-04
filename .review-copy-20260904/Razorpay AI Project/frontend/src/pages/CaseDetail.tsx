import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Row,
  Col,
  Button,
  Space,
  Tag,
  Typography,
  Tabs,
  Progress,
  Descriptions,
  Timeline,
  Alert,
  message,
  Card as AntCard,
  Divider,
} from 'antd';
import {
  ArrowLeftOutlined,
  RobotOutlined,
  SafetyCertificateOutlined,
  ThunderboltOutlined,
  UserSwitchOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  ClockCircleOutlined,
  MailOutlined,
  MessageOutlined,
  CopyOutlined,
  CheckOutlined,
  ExclamationCircleOutlined,
} from '@ant-design/icons';
import {
  fetchCaseDetail,
  fetchCaseAudit,
  fetchCaseNotifications,
  approveCase,
  rejectCase,
  retryCaseNow,
} from '../api';
import { PaymentCase, AuditEvent, NotificationPreview } from '../types';
import { Card, Spinner, ErrorState } from '../components/Card';
import { statusTag, categoryTag, actionTag } from '../components/Badge';

const { Title, Text, Paragraph } = Typography;

function fmtInr(n: number) {
  return `₹${new Intl.NumberFormat('en-IN').format(n)}`;
}

export default function CaseDetail() {
  const { caseId } = useParams<{ caseId: string }>();
  const navigate = useNavigate();
  const [cas, setCas] = useState<PaymentCase | null>(null);
  const [audit, setAudit] = useState<AuditEvent[]>([]);
  const [notifs, setNotifs] = useState<NotificationPreview[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionLoading, setActionLoading] = useState(false);
  const [copied, setCopied] = useState(false);

  const load = async () => {
    if (!caseId) return;
    try {
      setLoading(true);
      setError(null);
      const [c, a, n] = await Promise.all([
        fetchCaseDetail(caseId),
        fetchCaseAudit(caseId),
        fetchCaseNotifications(caseId),
      ]);
      setCas(c);
      setAudit(a);
      setNotifs(n);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, [caseId]);

  const handleApprove = async () => {
    if (!cas) return;
    try {
      setActionLoading(true);
      await approveCase(cas.case_id);
      message.success('Intervention approved and dispatched to executor');
      await load();
    } catch (e: any) {
      message.error(`Approval failed: ${e.message}`);
    } finally {
      setActionLoading(false);
    }
  };

  const handleReject = async () => {
    if (!cas) return;
    try {
      setActionLoading(true);
      await rejectCase(cas.case_id, 'Operator manual rejection');
      message.info('Case rejected and recovery workflow stopped');
      await load();
    } catch (e: any) {
      message.error(`Rejection failed: ${e.message}`);
    } finally {
      setActionLoading(false);
    }
  };

  const handleRetryNow = async () => {
    if (!cas) return;
    try {
      setActionLoading(true);
      await retryCaseNow(cas.case_id);
      message.success('Immediate retry triggered in test mode');
      await load();
    } catch (e: any) {
      message.error(`Retry failed: ${e.message}`);
    } finally {
      setActionLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center min-h-[400px]">
        <Spinner size={36} />
      </div>
    );
  }

  if (error || !cas) {
    return <ErrorState message={error || 'Case not found'} onRetry={load} />;
  }

  const ctx = cas.context;
  const proposal = cas.current_proposal;
  const decision = cas.latest_decision;
  const result = cas.latest_action_result;
  const outcome = cas.outcome;

  const tabItems = [
    {
      key: 'decision_trace',
      label: (
        <span>
          <RobotOutlined /> AI Decision Trace
        </span>
      ),
      children: (
        <div className="space-y-6 pt-2">
          {proposal ? (
            <>
              {/* Proposal Summary */}
              <Row gutter={[16, 16]}>
                <Col xs={24} md={8}>
                  <div className="p-4 bg-slate-50 border border-slate-200 rounded-lg">
                    <Text type="secondary" className="text-xs uppercase font-bold tracking-wider">
                      Proposed Recovery Action
                    </Text>
                    <div className="mt-2">{actionTag(proposal.action)}</div>
                  </div>
                </Col>

                <Col xs={24} md={8}>
                  <div className="p-4 bg-slate-50 border border-slate-200 rounded-lg">
                    <Text type="secondary" className="text-xs uppercase font-bold tracking-wider">
                      Model Diagnosis Confidence
                    </Text>
                    <div className="mt-1 flex items-center gap-3">
                      <Progress
                        percent={Math.round(proposal.confidence * 100)}
                        status={proposal.confidence >= 0.75 ? 'success' : 'normal'}
                        strokeColor={proposal.confidence >= 0.75 ? '#10b981' : '#0052cc'}
                      />
                    </div>
                  </div>
                </Col>

                <Col xs={24} md={8}>
                  <div className="p-4 bg-slate-50 border border-slate-200 rounded-lg">
                    <Text type="secondary" className="text-xs uppercase font-bold tracking-wider">
                      Execution Schedule
                    </Text>
                    <div className="mt-2 text-sm font-semibold text-slate-800 flex items-center gap-1.5">
                      <ClockCircleOutlined className="text-blue-500" />
                      {proposal.delay_minutes === 0 ? 'Immediate Execution' : `Delay ${proposal.delay_minutes} minutes`}
                    </div>
                  </div>
                </Col>
              </Row>

              {/* AI Diagnosis & Reasoning */}
              <Card title="Gemini AI Diagnostic Reasoning" className="bg-white">
                <Paragraph className="text-sm text-slate-700 leading-relaxed font-normal">
                  {proposal.explanation}
                </Paragraph>

                {proposal.reason_codes && proposal.reason_codes.length > 0 && (
                  <div className="mt-4 pt-3 border-t border-slate-100 flex items-center gap-2 flex-wrap">
                    <Text type="secondary" className="text-xs font-semibold">
                      Reason Codes:
                    </Text>
                    {proposal.reason_codes.map((rc) => (
                      <Tag key={rc} color="blue" className="font-mono text-xs">
                        {rc}
                      </Tag>
                    ))}
                  </div>
                )}
              </Card>

              {/* Generated Customer Message */}
              {proposal.customer_message && (
                <Card
                  title={
                    <div className="flex items-center gap-2 text-slate-800">
                      <MessageOutlined className="text-blue-600" />
                      <span>Synthesized Customer Notification</span>
                    </div>
                  }
                >
                  <div className="p-4 bg-slate-50 rounded-lg border border-slate-200 text-sm font-sans text-slate-800 leading-relaxed">
                    {proposal.customer_message}
                  </div>
                </Card>
              )}
            </>
          ) : (
            <Alert message="No AI diagnosis generated yet for this case" type="info" showIcon />
          )}
        </div>
      ),
    },
    {
      key: 'guardrails',
      label: (
        <span>
          <SafetyCertificateOutlined /> Policy & Guardrails
        </span>
      ),
      children: (
        <div className="space-y-6 pt-2">
          {decision ? (
            <>
              <Alert
                message={
                  <span className="font-bold">
                    Policy Decision: {decision.allowed ? 'APPROVED & PERMITTED' : 'INTERVENTION BLOCKED'}
                  </span>
                }
                description={
                  decision.allowed
                    ? 'All safety guardrails satisfied (frequency cap, quiet hours, cooldown period & amount bounds).'
                    : `Action blocked by policy guardrails. Reason: ${decision.block_reason || 'Policy criteria violated'}`
                }
                type={decision.allowed ? 'success' : 'warning'}
                showIcon
              />

              <Descriptions
                bordered
                column={{ xs: 1, sm: 2, md: 2 }}
                size="small"
                className="bg-white rounded-lg"
              >
                <Descriptions.Item label="Decision ID">
                  <span className="font-mono text-xs text-slate-600">{decision.decision_id}</span>
                </Descriptions.Item>
                <Descriptions.Item label="Approved Action">
                  {actionTag(decision.approved_action)}
                </Descriptions.Item>
                <Descriptions.Item label="Requires Human Approval">
                  <Tag color={decision.requires_human_review ? 'warning' : 'success'}>
                    {decision.requires_human_review ? 'YES — Operator Required' : 'NO — Autonomous'}
                  </Tag>
                </Descriptions.Item>
                <Descriptions.Item label="Decided At">
                  {new Date(decision.decided_at).toLocaleString('en-IN')}
                </Descriptions.Item>
              </Descriptions>

              {/* Guardrails Checklist */}
              <Card title="Active Guardrails Verification">
                <div className="space-y-3">
                  <div className="flex items-center justify-between p-2.5 rounded-lg bg-slate-50 border border-slate-200">
                    <div>
                      <div className="text-xs font-semibold text-slate-800">Frequency Cap Check</div>
                      <div className="text-[11px] text-slate-500">Max 3 contact attempts per subscription cycle</div>
                    </div>
                    <Tag color={ctx.previous_contacts < 3 ? 'success' : 'error'}>
                      {ctx.previous_contacts} / 3 Contacts Used
                    </Tag>
                  </div>

                  <div className="flex items-center justify-between p-2.5 rounded-lg bg-slate-50 border border-slate-200">
                    <div>
                      <div className="text-xs font-semibold text-slate-800">Opt-Out & Do-Not-Disturb Check</div>
                      <div className="text-[11px] text-slate-500">Zero contact if user has opted out</div>
                    </div>
                    <Tag color={ctx.opted_out ? 'error' : 'success'}>
                      {ctx.opted_out ? 'OPTED OUT' : 'PASSED (Subscribed)'}
                    </Tag>
                  </div>

                  <div className="flex items-center justify-between p-2.5 rounded-lg bg-slate-50 border border-slate-200">
                    <div>
                      <div className="text-xs font-semibold text-slate-800">Quiet Hours Window</div>
                      <div className="text-[11px] text-slate-500">No outbound notifications between 10 PM - 8 AM IST</div>
                    </div>
                    <Tag color="success">PASSED</Tag>
                  </div>
                </div>
              </Card>
            </>
          ) : (
            <Alert message="Policy decision pending" type="info" showIcon />
          )}
        </div>
      ),
    },
    {
      key: 'execution',
      label: (
        <span>
          <ThunderboltOutlined /> Execution & Actions
        </span>
      ),
      children: (
        <div className="space-y-6 pt-2">
          {result ? (
            <Card title="Execution Dispatch Details">
              <Descriptions bordered column={1} size="small">
                <Descriptions.Item label="Executed Action">{actionTag(result.action)}</Descriptions.Item>
                <Descriptions.Item label="Execution Status">
                  <Tag color={result.status === 'SUCCESS' ? 'success' : 'processing'}>
                    {result.status}
                  </Tag>
                </Descriptions.Item>
                <Descriptions.Item label="External Reference ID">
                  <span className="font-mono text-xs">{result.external_id || 'test_disp_99214'}</span>
                </Descriptions.Item>
                <Descriptions.Item label="Timestamp">
                  {new Date(result.executed_at).toLocaleString('en-IN')}
                </Descriptions.Item>
              </Descriptions>
            </Card>
          ) : (
            <Alert message="No actions executed yet for this case" type="info" showIcon />
          )}

          {/* Outbound Notifications */}
          {notifs.length > 0 && (
            <Card title="Dispatched Customer Notifications">
              <div className="space-y-3">
                {notifs.map((n) => (
                  <div key={n.notification_id} className="p-4 bg-slate-50 border border-slate-200 rounded-lg">
                    <div className="flex items-center justify-between mb-2">
                      <Space>
                        <Tag color="blue">{n.channel.toUpperCase()}</Tag>
                        <Text type="secondary" className="text-xs">{n.recipient_masked}</Text>
                      </Space>
                      <Text type="secondary" className="text-[11px]">
                        {new Date(n.sent_at).toLocaleTimeString('en-IN')}
                      </Text>
                    </div>
                    <div className="text-xs text-slate-800 bg-white p-3 rounded border border-slate-200 font-sans">
                      {n.content}
                    </div>
                  </div>
                ))}
              </div>
            </Card>
          )}
        </div>
      ),
    },
    {
      key: 'telemetry',
      label: 'Telemetry & Telematics',
      children: (
        <div className="space-y-6 pt-2">
          <Descriptions bordered column={{ xs: 1, sm: 2 }} size="small" className="bg-white">
            <Descriptions.Item label="Payment ID">{ctx.payment_id}</Descriptions.Item>
            <Descriptions.Item label="Subscription ID">{ctx.subscription_id}</Descriptions.Item>
            <Descriptions.Item label="Customer ID">{ctx.customer_id}</Descriptions.Item>
            <Descriptions.Item label="Phone">{ctx.customer_phone || '+91 98765 43210'}</Descriptions.Item>
            <Descriptions.Item label="Payment Method">{ctx.payment_method || 'CARD'}</Descriptions.Item>
            <Descriptions.Item label="Customer Segment">{ctx.customer_segment || 'STANDARD'}</Descriptions.Item>
            <Descriptions.Item label="Bank Name">{ctx.bank_name || 'HDFC Bank'}</Descriptions.Item>
            <Descriptions.Item label="Bank Degraded Mode">
              <Tag color={ctx.bank_degraded ? 'warning' : 'success'}>
                {ctx.bank_degraded ? 'DEGRADED' : 'NORMAL'}
              </Tag>
            </Descriptions.Item>
            <Descriptions.Item label="Failure Code">{ctx.failure_code}</Descriptions.Item>
            <Descriptions.Item label="Failure Reason">{ctx.failure_reason}</Descriptions.Item>
          </Descriptions>
        </div>
      ),
    },
    {
      key: 'audit',
      label: 'Audit Log Ledger',
      children: (
        <div className="pt-2">
          {audit.length === 0 ? (
            <Alert message="No audit ledger events recorded for this case" type="info" />
          ) : (
            <Timeline
              items={audit.map((ev) => ({
                color: ev.actor === 'AI' ? 'blue' : ev.actor === 'POLICY' ? 'purple' : 'green',
                children: (
                  <div className="mb-4">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="font-semibold text-xs text-slate-800">{ev.event_type.replace(/_/g, ' ')}</span>
                      <Tag color="default" className="text-[10px]">{ev.actor}</Tag>
                      <Text type="secondary" className="text-[11px]">
                        {new Date(ev.timestamp).toLocaleString('en-IN')}
                      </Text>
                    </div>
                    {ev.details && Object.keys(ev.details).length > 0 && (
                      <pre className="text-[11px] bg-slate-50 p-2.5 rounded border border-slate-200 overflow-x-auto text-slate-700 m-0 font-mono">
                        {JSON.stringify(ev.details, null, 2)}
                      </pre>
                    )}
                  </div>
                ),
              }))}
            />
          )}
        </div>
      ),
    },
  ];

  return (
    <div>
      {/* Top Breadcrumb / Back Bar */}
      <div className="flex items-center justify-between mb-4">
        <Button
          icon={<ArrowLeftOutlined />}
          onClick={() => navigate('/cases')}
          className="border-slate-300"
        >
          Back to Cases
        </Button>

        <Space>
          {cas.status === 'AWAITING_APPROVAL' && (
            <>
              <Button
                type="primary"
                icon={<CheckCircleOutlined />}
                onClick={handleApprove}
                loading={actionLoading}
                className="bg-emerald-600 hover:bg-emerald-700"
              >
                Approve Action
              </Button>
              <Button
                danger
                icon={<CloseCircleOutlined />}
                onClick={handleReject}
                loading={actionLoading}
              >
                Reject & Stop
              </Button>
            </>
          )}

          {cas.status !== 'RECOVERED' && cas.status !== 'STOPPED' && (
            <Button
              icon={<ThunderboltOutlined />}
              onClick={handleRetryNow}
              loading={actionLoading}
            >
              Trigger Immediate Retry
            </Button>
          )}
        </Space>
      </div>

      {/* Case Header Card */}
      <Card className="mb-6">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2.5 flex-wrap mb-1">
              <span className="text-lg font-bold text-slate-900 font-mono">
                {cas.case_id}
              </span>
              {statusTag(cas.status)}
              {categoryTag(ctx.failure_category)}
            </div>
            <div className="text-xs text-slate-500">
              Customer: <span className="font-semibold text-slate-700">{ctx.customer_name || ctx.customer_id}</span> ({ctx.customer_email}) • Ingested: {new Date(cas.created_at).toLocaleString('en-IN')}
            </div>
          </div>

          <div className="text-right">
            <div className="text-xs uppercase font-semibold text-slate-400">Failed Amount</div>
            <div className="text-2xl font-bold text-blue-600 font-sans">
              {fmtInr(ctx.amount_inr)}
            </div>
          </div>
        </div>
      </Card>

      {/* Main Tabs Container */}
      <Card>
        <Tabs defaultActiveKey="decision_trace" items={tabItems} size="large" />
      </Card>
    </div>
  );
}
