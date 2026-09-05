import React, { useState, useEffect } from 'react';
import { useSearchParams, useNavigate, useParams } from 'react-router-dom';
import {
  Card,
  Input,
  Select,
  Button,
  Typography,
  Space,
  Tag,
  Alert,
  Divider,
  Row,
  Col,
  Descriptions,
  message,
  Tabs,
  Modal,
} from 'antd';
import {
  MailOutlined,
  SendOutlined,
  RollbackOutlined,
  CheckCircleOutlined,
  ExclamationCircleOutlined,
  SafetyCertificateOutlined,
  EyeOutlined,
  EditOutlined,
  LinkOutlined,
} from '@ant-design/icons';
import { createEmailDraft, fetchEmailDraft, sendEmailDraft } from '../api';
import { EmailDraft } from '../types';

const { Title, Text, Paragraph } = Typography;
const { TextArea } = Input;

export default function EmailCompose() {
  const [searchParams] = useSearchParams();
  const { draftId } = useParams<{ draftId?: string }>();
  const navigate = useNavigate();

  // State
  const [loading, setLoading] = useState<boolean>(false);
  const [sending, setSending] = useState<boolean>(false);
  const [currentDraft, setCurrentDraft] = useState<EmailDraft | null>(null);

  // Form state
  const [recipientEmail, setRecipientEmail] = useState<string>(searchParams.get('email') || '');
  const [recipientName, setRecipientName] = useState<string>(searchParams.get('name') || '');
  const [templateId, setTemplateId] = useState<string>(searchParams.get('template') || 'payment_failure');
  const [subject, setSubject] = useState<string>('');
  const [bodyText, setBodyText] = useState<string>('');
  const [bodyHtml, setBodyHtml] = useState<string>('');
  const [amount, setAmount] = useState<string>(searchParams.get('amount') || '2,499.00');
  const [paymentLink, setPaymentLink] = useState<string>(searchParams.get('link') || '');
  const [issueId, setIssueId] = useState<string>(searchParams.get('issue_id') || '');
  const [caseId, setCaseId] = useState<string>(searchParams.get('case_id') || '');

  // Result state
  const [sendResult, setSendResult] = useState<any>(null);

  // Load existing draft if draftId is in URL
  useEffect(() => {
    if (draftId) {
      loadDraft(draftId);
    } else {
      generateInitialDraft();
    }
  }, [draftId]);

  const loadDraft = async (id: string) => {
    setLoading(true);
    try {
      const draft = await fetchEmailDraft(id);
      setCurrentDraft(draft);
      setRecipientEmail(draft.recipient_email);
      setRecipientName(draft.recipient_name || '');
      setSubject(draft.subject);
      setBodyText(draft.body_text);
      setBodyHtml(draft.body_html);
      if (draft.issue_id) setIssueId(draft.issue_id);
      if (draft.case_id) setCaseId(draft.case_id);
      if (draft.template_id) setTemplateId(draft.template_id);
    } catch (err: any) {
      message.error(err.message || 'Failed to load email draft');
    } finally {
      setLoading(false);
    }
  };

  const generateInitialDraft = async () => {
    if (!recipientEmail) return;
    setLoading(true);
    try {
      const draft = await createEmailDraft({
        template_id: templateId,
        recipient_email: recipientEmail,
        recipient_name: recipientName || 'Valued Customer',
        variables: {
          amount,
          failure_reason: 'Bank decline / processing failure',
          resolution_instruction: 'Please retry using an alternative payment method.',
          payment_link_section: paymentLink ? `Secure Payment Link: ${paymentLink}\n\n` : '',
          payment_link_section_html: paymentLink
            ? `<p><a href="${paymentLink}" style="background:#0052cc;color:#fff;padding:8px 16px;text-decoration:none;border-radius:4px;display:inline-block;">Pay Now</a></p>`
            : '',
          payment_link_url: paymentLink,
          business_name: 'Merchant Services',
          expiry_info: '24 hours',
          issue_id: issueId || 'ISS-AUTO',
          resolution_summary: 'Payment settings refreshed and verified.',
        },
        issue_id: issueId || undefined,
        case_id: caseId || undefined,
      });
      setCurrentDraft(draft);
      setSubject(draft.subject);
      setBodyText(draft.body_text);
      setBodyHtml(draft.body_html);
    } catch (err: any) {
      message.error(err.message || 'Failed to generate initial draft');
    } finally {
      setLoading(false);
    }
  };

  const handleTemplateChange = (val: string) => {
    setTemplateId(val);
    // Regenerate with the new template
    setTimeout(() => {
      generateInitialDraft();
    }, 50);
  };

  const handleSend = () => {
    if (!recipientEmail || !recipientEmail.includes('@')) {
      message.error('Please enter a valid recipient email address.');
      return;
    }
    if (!subject.trim()) {
      message.error('Subject line cannot be empty.');
      return;
    }

    Modal.confirm({
      title: 'Authorize Customer Email Dispatch',
      icon: <SafetyCertificateOutlined style={{ color: '#0052cc' }} />,
      content: (
        <div>
          <p>You are about to dispatch this email to <strong>{recipientEmail}</strong>.</p>
          <div className="bg-slate-50 p-2 rounded border border-slate-200 text-xs my-2">
            <div><strong>Template:</strong> {templateId}</div>
            <div><strong>Environment:</strong> Simulated Test Sandbox (Idempotency Key Guaranteed)</div>
            {issueId && <div><strong>Linked Issue:</strong> {issueId}</div>}
          </div>
          <p className="text-xs text-slate-500">Duplicate prevention prevents multiple deliveries of this message.</p>
        </div>
      ),
      okText: 'Confirm & Send Email',
      cancelText: 'Cancel',
      okButtonProps: { style: { background: '#0052cc' } },
      onOk: async () => {
        setSending(true);
        try {
          // If no draft ID yet, save first
          let draftToUse = currentDraft;
          if (!draftToUse) {
            draftToUse = await createEmailDraft({
              template_id: templateId,
              recipient_email: recipientEmail,
              recipient_name: recipientName,
              variables: { amount, payment_link_url: paymentLink, business_name: 'Merchant Services' },
              issue_id: issueId || undefined,
              case_id: caseId || undefined,
            });
            setCurrentDraft(draftToUse);
          }

          const res = await sendEmailDraft(draftToUse.draft_id);
          setSendResult(res);
          if (res.is_duplicate) {
            message.warning('Email already sent. Duplicate send prevented.');
          } else {
            message.success('Email successfully dispatched to recipient.');
          }
        } catch (err: any) {
          message.error(err.message || 'Failed to dispatch email');
        } finally {
          setSending(false);
        }
      },
    });
  };

  return (
    <div style={{ maxWidth: 1200, margin: '0 auto', paddingBottom: 60 }}>
      {/* Header Bar */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <Space align="center">
            <Button
              icon={<RollbackOutlined />}
              onClick={() => navigate(-1)}
              style={{ marginRight: 8 }}
            >
              Back
            </Button>
            <Title level={3} style={{ margin: 0 }}>
              <MailOutlined className="mr-2 text-blue-600" /> Customer Email Dispatcher
            </Title>
          </Space>
          <Paragraph type="secondary" style={{ margin: '4px 0 0 0' }}>
            Authorized customer communication with template provenance, duplicate prevention, and linked issue auditing.
          </Paragraph>
        </div>

        <Space>
          {issueId && (
            <Button
              icon={<LinkOutlined />}
              onClick={() => navigate(`/issues/${issueId}`)}
            >
              View Linked Issue ({issueId})
            </Button>
          )}
          {caseId && (
            <Button
              onClick={() => navigate(`/cases/${caseId}`)}
            >
              View Case ({caseId})
            </Button>
          )}
        </Space>
      </div>

      {sendResult && (
        <Alert
          message={sendResult.is_duplicate ? 'Duplicate Delivery Prevented' : 'Email Sent Successfully'}
          description={
            <div>
              <p>{sendResult.message || `Status: ${sendResult.status}`}</p>
              {sendResult.provider_message_id && (
                <p className="text-xs font-mono">
                  Provider Message ID: <strong>{sendResult.provider_message_id}</strong>
                </p>
              )}
            </div>
          }
          type={sendResult.is_duplicate ? 'warning' : 'success'}
          showIcon
          icon={<CheckCircleOutlined />}
          style={{ marginBottom: 24 }}
          closable
        />
      )}

      <Row gutter={[24, 24]}>
        {/* Left Column: Form & Configuration */}
        <Col xs={24} lg={11}>
          <Card
            title={
              <div className="flex items-center justify-between">
                <span>Message Parameters</span>
                <Tag color="blue">SIMULATED DISPATCH</Tag>
              </div>
            }
            className="shadow-sm border-slate-200"
          >
            <div className="space-y-4">
              <div>
                <Text strong className="block mb-1 text-xs text-slate-600">
                  Select Template:
                </Text>
                <Select
                  value={templateId}
                  onChange={handleTemplateChange}
                  style={{ width: '100%' }}
                  options={[
                    { value: 'payment_failure', label: 'Payment Failure Notification' },
                    { value: 'payment_link', label: 'Payment Retry Link' },
                    { value: 'refund_update', label: 'Refund Processing Notice' },
                    { value: 'issue_resolved', label: 'Customer Issue Resolved' },
                    { value: 'escalation', label: 'Senior Specialist Escalation' },
                  ]}
                />
              </div>

              <Row gutter={12}>
                <Col span={12}>
                  <Text strong className="block mb-1 text-xs text-slate-600">
                    Recipient Name:
                  </Text>
                  <Input
                    placeholder="Customer Name"
                    value={recipientName}
                    onChange={(e) => setRecipientName(e.target.value)}
                  />
                </Col>
                <Col span={12}>
                  <Text strong className="block mb-1 text-xs text-slate-600">
                    Recipient Email:
                  </Text>
                  <Input
                    placeholder="customer@example.com"
                    value={recipientEmail}
                    onChange={(e) => setRecipientEmail(e.target.value)}
                  />
                </Col>
              </Row>

              <Row gutter={12}>
                <Col span={12}>
                  <Text strong className="block mb-1 text-xs text-slate-600">
                    Payment Amount (₹):
                  </Text>
                  <Input
                    placeholder="2,499.00"
                    value={amount}
                    onChange={(e) => setAmount(e.target.value)}
                  />
                </Col>
                <Col span={12}>
                  <Text strong className="block mb-1 text-xs text-slate-600">
                    Payment / Retry Link:
                  </Text>
                  <Input
                    placeholder="https://rzp.io/l/..."
                    value={paymentLink}
                    onChange={(e) => setPaymentLink(e.target.value)}
                  />
                </Col>
              </Row>

              <Divider style={{ margin: '12px 0' }} />

              <div>
                <Text strong className="block mb-1 text-xs text-slate-600">
                  Email Subject:
                </Text>
                <Input
                  placeholder="Subject line"
                  value={subject}
                  onChange={(e) => setSubject(e.target.value)}
                />
              </div>

              <div>
                <div className="flex justify-between items-center mb-1">
                  <Text strong className="text-xs text-slate-600">
                    Email Body (Plain Text):
                  </Text>
                  <Button
                    size="small"
                    type="link"
                    onClick={generateInitialDraft}
                    loading={loading}
                  >
                    Reset to Template
                  </Button>
                </div>
                <TextArea
                  rows={8}
                  value={bodyText}
                  onChange={(e) => setBodyText(e.target.value)}
                  style={{ fontFamily: 'monospace', fontSize: 12 }}
                />
              </div>

              <div className="pt-2">
                <Button
                  type="primary"
                  icon={<SendOutlined />}
                  onClick={handleSend}
                  loading={sending}
                  block
                  size="large"
                  style={{ background: '#0052cc', height: 44 }}
                >
                  Send Customer Email
                </Button>
              </div>
            </div>
          </Card>
        </Col>

        {/* Right Column: Live Message Preview */}
        <Col xs={24} lg={13}>
          <Card
            title={
              <div className="flex items-center justify-between">
                <span>Customer Inbox Preview</span>
                <span className="text-xs text-slate-400 font-normal">
                  Recipient View
                </span>
              </div>
            }
            className="shadow-sm border-slate-200"
          >
            {/* Email Header Mockup */}
            <div className="bg-slate-50 p-3 rounded-t border border-slate-200 mb-0">
              <div className="text-xs text-slate-500 mb-1">
                <span className="font-semibold text-slate-700">From:</span> Razorpay Merchant Services &lt;support@notifications.razorpay.com&gt;
              </div>
              <div className="text-xs text-slate-500 mb-1">
                <span className="font-semibold text-slate-700">To:</span> {recipientName || 'Customer'} &lt;{recipientEmail || 'customer@example.com'}&gt;
              </div>
              <div className="text-xs text-slate-500">
                <span className="font-semibold text-slate-700">Subject:</span> <strong className="text-slate-900">{subject || '(No subject)'}</strong>
              </div>
            </div>

            {/* Email Content Tabs */}
            <div className="border border-t-0 border-slate-200 rounded-b p-4 bg-white min-h-[360px]">
              <Tabs
                defaultActiveKey="preview"
                items={[
                  {
                    key: 'preview',
                    label: (
                      <span>
                        <EyeOutlined /> Rendered HTML
                      </span>
                    ),
                    children: (
                      <div className="p-4 bg-slate-50/50 rounded border border-slate-100 min-h-[280px]">
                        <div
                          dangerouslySetInnerHTML={{
                            __html:
                              bodyHtml ||
                              bodyText
                                .split('\n\n')
                                .map((p) => `<p style="margin-bottom:12px;">${p}</p>`)
                                .join(''),
                          }}
                        />
                      </div>
                    ),
                  },
                  {
                    key: 'text',
                    label: (
                      <span>
                        <EditOutlined /> Plain Text Version
                      </span>
                    ),
                    children: (
                      <pre className="p-3 bg-slate-50 rounded text-xs whitespace-pre-wrap font-sans text-slate-700 min-h-[280px]">
                        {bodyText || 'No plain text content available.'}
                      </pre>
                    ),
                  },
                ]}
              />
            </div>

            {/* Provenance and Governance Footer */}
            <div className="mt-4 p-3 bg-blue-50/60 border border-blue-100 rounded text-xs text-blue-900">
              <div className="font-semibold mb-1 flex items-center gap-1.5">
                <SafetyCertificateOutlined /> Security & Governance Controls
              </div>
              <ul className="list-disc pl-4 space-y-0.5 text-slate-600">
                <li>All outgoing emails are logged in the immutable audit trail.</li>
                <li>Idempotency keys prevent double sending if clicked repeatedly.</li>
                <li>Zero sensitive payment credentials (card numbers, PINs, OTPs) are ever drafted or transmitted.</li>
              </ul>
            </div>
          </Card>
        </Col>
      </Row>
    </div>
  );
}
