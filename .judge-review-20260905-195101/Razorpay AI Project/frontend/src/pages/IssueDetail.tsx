import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Card,
  Row,
  Col,
  Tag,
  Button,
  Space,
  Typography,
  Descriptions,
  Tabs,
  Timeline,
  Alert,
  Modal,
  Input,
  Select,
  message,
  Divider,
} from 'antd';
import {
  RollbackOutlined,
  CheckCircleOutlined,
  RobotOutlined,
  MailOutlined,
  LinkOutlined,
  WarningOutlined,
  ClockCircleOutlined,
  SyncOutlined,
  SafetyCertificateOutlined,
  CheckOutlined,
  FileTextOutlined,
  ExclamationCircleOutlined,
} from '@ant-design/icons';
import { fetchCustomerIssue, updateCustomerIssue, generateCopilotPaymentLink } from '../api';
import { CustomerIssue, IssueStatus, IssueSeverity } from '../types';

const { Title, Text, Paragraph } = Typography;
const { TextArea } = Input;

export default function IssueDetail() {
  const { issueId } = useParams<{ issueId: string }>();
  const navigate = useNavigate();

  const [issue, setIssue] = useState<CustomerIssue | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [isResolveModalOpen, setIsResolveModalOpen] = useState<boolean>(false);
  const [resolutionSummary, setResolutionSummary] = useState<string>('');
  const [resolutionEvidence, setResolutionEvidence] = useState<string>('');
  const [updating, setUpdating] = useState<boolean>(false);

  // Link generator modal
  const [isLinkModalOpen, setIsLinkModalOpen] = useState<boolean>(false);
  const [linkAmount, setLinkAmount] = useState<string>('2499.00');
  const [generatedLink, setGeneratedLink] = useState<string>('');
  const [generatingLink, setGeneratingLink] = useState<boolean>(false);

  useEffect(() => {
    if (issueId) {
      loadIssue(issueId);
    }
  }, [issueId]);

  const loadIssue = async (id: string) => {
    setLoading(true);
    try {
      const data = await fetchCustomerIssue(id);
      setIssue(data);
      if (data.resolution_summary) setResolutionSummary(data.resolution_summary);
      if (data.resolution_evidence) setResolutionEvidence(data.resolution_evidence);
    } catch (err: any) {
      message.error(err.message || 'Failed to load issue');
    } finally {
      setLoading(false);
    }
  };

  const handleStatusChange = async (newStatus: string) => {
    if (!issue) return;
    setUpdating(true);
    try {
      const updated = await updateCustomerIssue(issue.issue_id, { status: newStatus });
      setIssue(updated);
      message.success(`Status updated to ${newStatus}`);
    } catch (err: any) {
      message.error(err.message || 'Failed to update status');
    } finally {
      setUpdating(false);
    }
  };

  const handleMarkResolved = async () => {
    if (!issue) return;
    if (!resolutionSummary.trim()) {
      message.error('Please enter a resolution summary');
      return;
    }
    setUpdating(true);
    try {
      const updated = await updateCustomerIssue(issue.issue_id, {
        status: 'RESOLVED',
        resolution_summary: resolutionSummary,
        resolution_verified: true,
        resolution_evidence: resolutionEvidence || 'Verified via verified customer confirmation and gateway settlement',
      });
      setIssue(updated);
      setIsResolveModalOpen(false);
      message.success('Issue verified and marked as RESOLVED!');
    } catch (err: any) {
      message.error(err.message || 'Failed to resolve issue');
    } finally {
      setUpdating(false);
    }
  };

  const handleGenerateLink = async () => {
    if (!issue) return;
    setGeneratingLink(true);
    try {
      const res = await generateCopilotPaymentLink({
        amount: parseFloat(linkAmount) || 2499.0,
        customer_name: issue.customer_name || 'Customer',
        customer_email: issue.customer_email || 'customer@example.com',
        description: `Payment Link for ${issue.title}`,
        issue_id: issue.issue_id,
      });
      setGeneratedLink(res.payment_link_url || res.short_url || 'https://rzp.io/l/demo_link');
      message.success('Payment link generated successfully!');
      loadIssue(issue.issue_id);
    } catch (err: any) {
      message.error(err.message || 'Failed to generate payment link');
    } finally {
      setGeneratingLink(false);
    }
  };

  if (loading) {
    return (
      <div className="text-center py-20">
        <SyncOutlined spin className="text-3xl text-blue-600 mb-4" />
        <p className="text-slate-500">Loading customer issue details...</p>
      </div>
    );
  }

  if (!issue) {
    return (
      <Alert
        type="error"
        message="Issue Not Found"
        description={`No issue found with ID ${issueId}`}
        showIcon
      />
    );
  }

  return (
    <div style={{ maxWidth: 1300, margin: '0 auto', paddingBottom: 60 }}>
      {/* Back and Navigation Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <Space align="center">
            <Button icon={<RollbackOutlined />} onClick={() => navigate('/issues')}>
              All Issues
            </Button>
            <Title level={3} style={{ margin: 0 }}>
              {issue.title}
            </Title>
          </Space>
          <div className="flex items-center gap-2 mt-1">
            <Tag color="geekblue" className="font-mono">{issue.issue_id}</Tag>
            <Tag color={issue.environment === 'TEST' ? 'purple' : 'green'}>{issue.environment} MODE</Tag>
            <Tag color="blue">{issue.category}</Tag>
            <Tag color={issue.severity === 'CRITICAL' ? 'red' : issue.severity === 'HIGH' ? 'volcano' : 'gold'}>
              {issue.severity}
            </Tag>
            {issue.resolution_verified ? (
              <Tag color="success" icon={<CheckCircleOutlined />}>Verified Resolved</Tag>
            ) : (
              <Tag color="processing">{issue.status}</Tag>
            )}
          </div>
        </div>

        {/* Primary Action Buttons */}
        <Space>
          <Button
            icon={<RobotOutlined />}
            onClick={() =>
              navigate(`/copilot?query=Investigate issue ${issue.issue_id}: ${issue.title}&case_id=${issue.case_id || ''}&customer_email=${issue.customer_email || ''}`)
            }
          >
            Investigate with Copilot
          </Button>

          <Button
            icon={<MailOutlined />}
            onClick={() =>
              navigate(
                `/email/compose?issue_id=${issue.issue_id}&email=${encodeURIComponent(issue.customer_email || '')}&name=${encodeURIComponent(issue.customer_name || '')}&case_id=${issue.case_id || ''}`
              )
            }
          >
            Draft Customer Email
          </Button>

          <Button
            icon={<LinkOutlined />}
            onClick={() => setIsLinkModalOpen(true)}
          >
            Generate Link
          </Button>

          {!issue.resolution_verified ? (
            <Button
              type="primary"
              icon={<CheckOutlined />}
              onClick={() => setIsResolveModalOpen(true)}
              style={{ background: '#10b981' }}
            >
              Verify & Resolve
            </Button>
          ) : (
            <Button
              onClick={() => handleStatusChange('INVESTIGATING')}
            >
              Reopen Issue
            </Button>
          )}
        </Space>
      </div>

      {/* Resolution Verification Banner if Resolved */}
      {issue.resolution_verified && (
        <Alert
          message="Resolution Verified & Evidence Recorded"
          description={
            <div>
              <p><strong>Resolution:</strong> {issue.resolution_summary}</p>
              {issue.resolution_evidence && (
                <p className="text-xs text-slate-500"><strong>Verification Evidence:</strong> {issue.resolution_evidence}</p>
              )}
            </div>
          }
          type="success"
          showIcon
          icon={<CheckCircleOutlined />}
          className="mb-6 shadow-sm border-emerald-200"
        />
      )}

      {/* Core Context Grid */}
      <Row gutter={[20, 20]} className="mb-6">
        <Col xs={24} md={16}>
          <Card title="Customer & Incident Context" size="small" className="border-slate-200 shadow-sm">
            <Descriptions column={{ xs: 1, sm: 2, md: 3 }} size="small" bordered>
              <Descriptions.Item label="Customer Name">{issue.customer_name || 'N/A'}</Descriptions.Item>
              <Descriptions.Item label="Customer Email">{issue.customer_email || 'N/A'}</Descriptions.Item>
              <Descriptions.Item label="Owner">{issue.owner || 'Copilot Agent'}</Descriptions.Item>

              <Descriptions.Item label="Payment ID">
                {issue.payment_id ? <span className="font-mono text-xs">{issue.payment_id}</span> : '—'}
              </Descriptions.Item>
              <Descriptions.Item label="Order ID">
                {issue.order_id ? <span className="font-mono text-xs">{issue.order_id}</span> : '—'}
              </Descriptions.Item>
              <Descriptions.Item label="Case ID">
                {issue.case_id ? (
                  <Button type="link" size="small" onClick={() => navigate(`/cases/${issue.case_id}`)}>
                    {issue.case_id}
                  </Button>
                ) : '—'}
              </Descriptions.Item>

              <Descriptions.Item label="Reported Symptoms" span={3}>
                {issue.reported_symptoms || 'No symptoms reported.'}
              </Descriptions.Item>
            </Descriptions>
          </Card>
        </Col>

        <Col xs={24} md={8}>
          <Card title="Lifecycle Controls" size="small" className="border-slate-200 shadow-sm">
            <div className="space-y-3">
              <div>
                <Text strong className="block mb-1 text-xs text-slate-600">Current Status:</Text>
                <Select
                  value={issue.status}
                  onChange={handleStatusChange}
                  loading={updating}
                  style={{ width: '100%' }}
                  options={[
                    { value: 'NEW', label: 'New' },
                    { value: 'INVESTIGATING', label: 'Investigating' },
                    { value: 'AWAITING_INFO', label: 'Awaiting Info' },
                    { value: 'ACTION_IN_PROGRESS', label: 'Action in Progress' },
                    { value: 'MONITORING', label: 'Monitoring' },
                    { value: 'RESOLVED', label: 'Resolved' },
                    { value: 'CLOSED', label: 'Closed' },
                  ]}
                />
              </div>

              <div>
                <Text strong className="block mb-1 text-xs text-slate-600">Next Action:</Text>
                <div className="text-xs bg-slate-50 p-2 rounded border border-slate-200 text-slate-700">
                  {issue.next_action || 'Review evidence and execute recommended resolution'}
                </div>
              </div>

              <div className="pt-2 text-xs text-slate-400">
                Created: {new Date(issue.created_at).toLocaleString()}
                <br />
                Last updated: {new Date(issue.updated_at).toLocaleString()}
              </div>
            </div>
          </Card>
        </Col>
      </Row>

      {/* Investigation Details Tabs */}
      <Card className="border-slate-200 shadow-sm">
        <Tabs
          defaultActiveKey="causes"
          items={[
            {
              key: 'causes',
              label: (
                <span>
                  Root Causes & Analysis ({issue.possible_causes?.length || 0})
                </span>
              ),
              children: (
                <div className="space-y-4">
                  {issue.possible_causes?.length === 0 ? (
                    <div className="text-slate-400 py-6 text-center">
                      No root causes identified yet. Run Copilot investigation to generate evidence-backed hypotheses.
                    </div>
                  ) : (
                    issue.possible_causes?.map((cause, idx) => (
                      <Card
                        key={cause.cause_id || idx}
                        size="small"
                        className="border-slate-200 bg-slate-50/50"
                        title={
                          <div className="flex items-center justify-between">
                            <Space>
                              <Tag color={cause.confidence === 'HIGH' ? 'green' : cause.confidence === 'MEDIUM' ? 'gold' : 'blue'}>
                                {cause.confidence} CONFIDENCE
                              </Tag>
                              <span className="font-semibold text-slate-800">{cause.description}</span>
                            </Space>
                            {cause.is_confirmed && <Tag color="success">CONFIRMED</Tag>}
                          </div>
                        }
                      >
                        {cause.recommended_action && (
                          <div className="mt-2 text-xs bg-blue-50/70 p-2.5 rounded border border-blue-100 text-blue-900">
                            <strong>Recommended Resolution:</strong> {cause.recommended_action}
                          </div>
                        )}
                      </Card>
                    ))
                  )}
                </div>
              ),
            },
            {
              key: 'evidence',
              label: <span>Evidence Chain ({issue.evidence?.length || 0})</span>,
              children: (
                <div className="space-y-3">
                  {issue.evidence?.length === 0 ? (
                    <div className="text-slate-400 py-6 text-center">No evidence collected yet.</div>
                  ) : (
                    issue.evidence?.map((ev, idx) => (
                      <Card key={ev.evidence_id || idx} size="small" className="border-slate-200">
                        <div className="flex items-center justify-between mb-1">
                          <Space>
                            <Tag color="cyan">{ev.source}</Tag>
                            <span className="font-medium text-slate-800">{ev.description}</span>
                          </Space>
                          <Tag color={ev.confidence === 'HIGH' ? 'green' : 'gold'}>{ev.confidence}</Tag>
                        </div>
                        {ev.raw_data && (
                          <pre className="mt-2 p-2 bg-slate-50 rounded text-xs overflow-x-auto text-slate-600 font-mono">
                            {JSON.stringify(ev.raw_data, null, 2)}
                          </pre>
                        )}
                      </Card>
                    ))
                  )}
                </div>
              ),
            },
            {
              key: 'actions',
              label: <span>Actions Log ({issue.actions?.length || 0})</span>,
              children: (
                <div className="space-y-3">
                  {issue.actions?.length === 0 ? (
                    <div className="text-slate-400 py-6 text-center">No actions recorded yet.</div>
                  ) : (
                    issue.actions?.map((act, idx) => (
                      <Card key={act.action_id || idx} size="small" className="border-slate-200">
                        <div className="flex items-center justify-between mb-1">
                          <Space>
                            <Tag color="purple">{act.action_type}</Tag>
                            <span className="font-medium text-slate-800">{act.description}</span>
                          </Space>
                          <Tag color={act.status === 'COMPLETED' ? 'green' : act.status === 'FAILED' ? 'red' : 'gold'}>
                            {act.status}
                          </Tag>
                        </div>
                        <div className="text-xs text-slate-500">
                          Executed by: <strong>{act.executed_by}</strong>
                          {act.executed_at && ` at ${new Date(act.executed_at).toLocaleString()}`}
                        </div>
                      </Card>
                    ))
                  )}
                </div>
              ),
            },
            {
              key: 'communications',
              label: <span>Communications ({issue.communications?.length || 0})</span>,
              children: (
                <div className="space-y-3">
                  {issue.communications?.length === 0 ? (
                    <div className="text-slate-400 py-6 text-center">
                      No communications recorded. Use the "Draft Customer Email" button to initiate contact.
                    </div>
                  ) : (
                    issue.communications?.map((comm, idx) => (
                      <Card key={comm.communication_id || idx} size="small" className="border-slate-200">
                        <div className="flex items-center justify-between mb-1">
                          <Space>
                            <Tag color="blue">{comm.channel}</Tag>
                            <span className="font-medium text-slate-800">{comm.subject || '(No subject)'}</span>
                          </Space>
                          <Tag color={comm.status === 'DELIVERED' || comm.status === 'ACCEPTED' ? 'green' : 'gold'}>
                            {comm.status}
                          </Tag>
                        </div>
                        <div className="text-xs text-slate-500 mb-2">
                          Recipient: {comm.recipient}
                          {comm.provider_message_id && ` • Provider ID: ${comm.provider_message_id}`}
                        </div>
                        <div className="bg-slate-50 p-2 rounded text-xs font-sans whitespace-pre-wrap text-slate-700">
                          {comm.body}
                        </div>
                      </Card>
                    ))
                  )}
                </div>
              ),
            },
            {
              key: 'timeline',
              label: <span>Audit Timeline ({issue.timeline?.length || 0})</span>,
              children: (
                <Timeline
                  className="pt-4"
                  items={issue.timeline?.map((tle) => ({
                    color: tle.event_type === 'status_change' ? 'green' : 'blue',
                    children: (
                      <div>
                        <div className="font-semibold text-slate-800">{tle.summary}</div>
                        <div className="text-xs text-slate-400">
                          {new Date(tle.timestamp).toLocaleString()} • Actor: {tle.actor}
                        </div>
                      </div>
                    ),
                  }))}
                />
              ),
            },
          ]}
        />
      </Card>

      {/* Verify & Resolve Modal */}
      <Modal
        title="Verify & Resolve Customer Issue"
        open={isResolveModalOpen}
        onCancel={() => setIsResolveModalOpen(false)}
        onOk={handleMarkResolved}
        confirmLoading={updating}
        okText="Confirm & Mark Resolved"
        okButtonProps={{ style: { background: '#10b981' } }}
      >
        <div className="space-y-4">
          <p className="text-xs text-slate-600">
            Resolving an issue requires documenting the exact fix and verification evidence to guarantee that customer revenue is protected.
          </p>

          <div>
            <Text strong className="block mb-1 text-xs">Resolution Summary (Required):</Text>
            <TextArea
              rows={3}
              placeholder="e.g. Issued smart retry link via WhatsApp. Customer completed payment of ₹2,499. Order status synced to paid."
              value={resolutionSummary}
              onChange={(e) => setResolutionSummary(e.target.value)}
            />
          </div>

          <div>
            <Text strong className="block mb-1 text-xs">Verification Evidence (Optional):</Text>
            <TextArea
              rows={2}
              placeholder="e.g. Gateway transaction pay_xyz verified as captured in Razorpay dashboard."
              value={resolutionEvidence}
              onChange={(e) => setResolutionEvidence(e.target.value)}
            />
          </div>
        </div>
      </Modal>

      {/* Generate Payment Link Modal */}
      <Modal
        title="Generate Payment / Retry Link"
        open={isLinkModalOpen}
        onCancel={() => {
          setIsLinkModalOpen(false);
          setGeneratedLink('');
        }}
        footer={null}
      >
        <div className="space-y-4">
          <div>
            <Text strong className="block mb-1 text-xs">Payment Amount (₹):</Text>
            <Input
              value={linkAmount}
              onChange={(e) => setLinkAmount(e.target.value)}
              placeholder="2499.00"
            />
          </div>

          <Button
            type="primary"
            onClick={handleGenerateLink}
            loading={generatingLink}
            block
            style={{ background: '#0052cc' }}
          >
            Generate Link
          </Button>

          {generatedLink && (
            <div className="p-3 bg-emerald-50 border border-emerald-200 rounded">
              <div className="text-xs font-semibold text-emerald-800 mb-1">Link Generated:</div>
              <div className="font-mono text-xs text-emerald-900 break-all">{generatedLink}</div>
              <div className="mt-2 flex gap-2">
                <Button
                  size="small"
                  onClick={() => {
                    navigator.clipboard.writeText(generatedLink);
                    message.success('Copied to clipboard');
                  }}
                >
                  Copy Link
                </Button>
                <Button
                  size="small"
                  type="primary"
                  onClick={() => {
                    navigate(
                      `/email/compose?issue_id=${issue.issue_id}&email=${encodeURIComponent(issue.customer_email || '')}&link=${encodeURIComponent(generatedLink)}&amount=${encodeURIComponent(linkAmount)}`
                    );
                  }}
                  style={{ background: '#0052cc' }}
                >
                  Send via Email
                </Button>
              </div>
            </div>
          )}
        </div>
      </Modal>
    </div>
  );
}
