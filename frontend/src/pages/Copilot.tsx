import React, { useState, useRef, useEffect } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import {
  Card,
  Input,
  Button,
  Tag,
  Avatar,
  Modal,
  Form,
  InputNumber,
  DatePicker,
  message,
  Tooltip,
  Spin,
  Badge,
  Divider,
  Space,
  Steps,
} from 'antd';
import {
  RobotFilled,
  UserOutlined,
  SendOutlined,
  PaperClipOutlined,
  LikeOutlined,
  DislikeOutlined,
  CopyOutlined,
  ShareAltOutlined,
  CheckCircleFilled,
  LinkOutlined,
  CloseCircleFilled,
  InfoCircleOutlined,
  ThunderboltFilled,
  FileImageOutlined,
  SafetyCertificateOutlined,
  MailOutlined,
  AuditOutlined,
  DollarCircleOutlined,
} from '@ant-design/icons';
import { sendCopilotMessage, createCopilotPaymentLink, investigateCopilotV2, investigateRefund } from '../api';
import {
  CopilotDiagnosis,
  FollowUpSuggestion,
  CreatePaymentLinkResponse,
  CopilotV2Investigation,
} from '../types';

const { TextArea } = Input;

interface MessageItem {
  id: string;
  sender: 'user' | 'assistant';
  timestamp: string;
  text?: string;
  imagePreview?: string;
  imageName?: string;
  diagnosis?: CopilotDiagnosis;
  investigation?: CopilotV2Investigation;
  fallbackMessage?: string;
  createdPaymentLink?: CreatePaymentLinkResponse;
  suggestions?: FollowUpSuggestion[];
  userFeedback?: 'like' | 'dislike' | null;
}

const CATEGORY_CHIPS = [
  { key: 'payments', label: 'Failed Payments', prompt: 'Customer is facing a payment failure issue' },
  { key: 'settlements', label: 'Settlements & Refunds', prompt: 'Check refund status for a failed payment' },
  { key: 'mandates', label: 'Subscription Mandates', prompt: 'Why was the recurring subscription mandate revoked?' },
  { key: 'support', label: 'Customer Inquiries', prompt: 'Customer complaint regarding auto-debit failure' },
];

export default function Copilot() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();

  const [messages, setMessages] = useState<MessageItem[]>([]);
  const [inputText, setInputText] = useState('');
  const [loading, setLoading] = useState(false);
  const [selectedImage, setSelectedImage] = useState<{ base64: string; name: string } | null>(null);

  // Create Payment Link Modal state
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [activeDiagnosis, setActiveDiagnosis] = useState<CopilotDiagnosis | null>(null);
  const [submittingLink, setSubmittingLink] = useState(false);
  const [form] = Form.useForm();

  // Refund Modal state
  const [refundModalData, setRefundModalData] = useState<any>(null);
  const [refundModalOpen, setRefundModalOpen] = useState(false);
  const [checkingRefund, setCheckingRefund] = useState(false);

  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const chatBottomRef = useRef<HTMLDivElement | null>(null);

  const scrollToBottom = () => {
    chatBottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, loading]);

  // Read URL params and auto-trigger investigation if provided
  useEffect(() => {
    const q = searchParams.get('query');
    if (q) {
      handleSendMessage(q);
    }
  }, []);

  const handleImageUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    if (!file.type.startsWith('image/')) {
      message.error('Please upload an image or screenshot file (.png, .jpg, .jpeg, .webp)');
      return;
    }

    const reader = new FileReader();
    reader.onload = (uploadEvent) => {
      const base64 = uploadEvent.target?.result as string;
      setSelectedImage({
        base64,
        name: file.name,
      });
      message.success(`Screenshot attached: ${file.name}`);
    };
    reader.readAsDataURL(file);
    // Reset file input so user can re-select if desired
    e.target.value = '';
  };

  const removeSelectedImage = () => {
    setSelectedImage(null);
  };

  const handleSendMessage = async (customQuery?: string) => {
    const queryToSend = customQuery || inputText.trim();
    if (!queryToSend && !selectedImage) {
      return;
    }

    const currentImage = selectedImage;
    const userMsgId = `user_${Date.now()}`;
    const newMsg: MessageItem = {
      id: userMsgId,
      sender: 'user',
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      text: queryToSend || (currentImage ? `[Attached screenshot: ${currentImage.name}]` : ''),
      imagePreview: currentImage?.base64,
      imageName: currentImage?.name,
    };

    setMessages((prev) => [...prev, newMsg]);
    setInputText('');
    setSelectedImage(null);
    setLoading(true);

    // Try V2 Copilot structured investigation first
    try {
      const context = {
        current_page: window.location.pathname,
        case_id: searchParams.get('case_id') || undefined,
        customer_email: searchParams.get('customer_email') || undefined,
        payment_id: searchParams.get('payment_id') || undefined,
      };

      const invRes = await investigateCopilotV2(
        queryToSend || 'Customer support investigation request',
        context,
        currentImage?.base64
      );

      const assistantMsgId = `asst_${Date.now()}`;
      setMessages((prev) => [
        ...prev,
        {
          id: assistantMsgId,
          sender: 'assistant',
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
          investigation: invRes,
          diagnosis: invRes.diagnosis,
          suggestions: [
            { id: 's_draft', text: 'Draft customer email with solution', action: 'DRAFT_EMAIL' },
            { id: 's_link', text: 'Generate retry payment link', action: 'CREATE_PAYMENT_LINK' },
            { id: 's_issue', text: `View tracked issue (${invRes.issue_id})`, action: 'VIEW_ISSUE' },
          ],
          userFeedback: null,
        },
      ]);
      setLoading(false);
      return;
    } catch (v2Err) {
      // Graceful fallback to v1 template matching
      console.warn('V2 investigation engine fallback:', v2Err);
    }

    try {
      const res = await sendCopilotMessage(
        queryToSend || 'Customer support complaint screenshot attached',
        currentImage?.base64,
        currentImage?.name,
        'Support Agent'
      );

      const assistantMsgId = `asst_${Date.now()}`;
      if (res.type === 'diagnosis' && res.diagnosis) {
        setMessages((prev) => [
          ...prev,
          {
            id: assistantMsgId,
            sender: 'assistant',
            timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
            diagnosis: res.diagnosis || undefined,
            suggestions: res.suggestions,
            userFeedback: null,
          },
        ]);
      } else {
        setMessages((prev) => [
          ...prev,
          {
            id: assistantMsgId,
            sender: 'assistant',
            timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
            fallbackMessage: res.message || 'No matching payment records found.',
            suggestions: res.suggestions,
            userFeedback: null,
          },
        ]);
      }
    } catch (err: any) {
      message.error(`Diagnosis request failed: ${err.message}`);
      setMessages((prev) => [
        ...prev,
        {
          id: `asst_err_${Date.now()}`,
          sender: 'assistant',
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
          fallbackMessage: `Error connecting to Razorpay Recovery Diagnosis engine: ${err.message}. Please try again or specify a Payment ID manually.`,
          suggestions: [
            { id: 's_retry', text: 'Retry with Payment ID', action: 'INFO_QUERY' },
            { id: 's_all', text: 'Analyse all my failed payments', action: 'ANALYZE_ALL' },
          ],
          userFeedback: null,
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleSuggestionClick = (suggestion: FollowUpSuggestion, diagnosisContext?: CopilotDiagnosis, investigationContext?: CopilotV2Investigation) => {
    if (suggestion.action === 'CREATE_PAYMENT_LINK') {
      const diag = diagnosisContext || activeDiagnosis;
      if (diag) {
        openPaymentLinkModal(diag);
      } else {
        handleSendMessage(suggestion.text);
      }
    } else if (suggestion.action === 'DRAFT_EMAIL') {
      const diag = diagnosisContext || activeDiagnosis;
      const issueId = investigationContext?.issue_id || '';
      navigate(
        `/email/compose?issue_id=${issueId}&email=${encodeURIComponent(diag?.customer_email || '')}&name=${encodeURIComponent(diag?.customer_name || '')}&amount=${encodeURIComponent(diag?.amount_inr || '')}&case_id=${diag?.case_id || ''}`
      );
    } else if (suggestion.action === 'VIEW_ISSUE') {
      const issueId = investigationContext?.issue_id;
      if (issueId) {
        navigate(`/issues/${issueId}`);
      } else {
        navigate('/issues');
      }
    } else {
      handleSendMessage(suggestion.text);
    }
  };

  const openPaymentLinkModal = (diag: CopilotDiagnosis) => {
    setActiveDiagnosis(diag);
    form.setFieldsValue({
      amount_inr: diag.amount_inr,
      customer_email: diag.customer_email,
      customer_phone: diag.masked_phone || diag.customer_phone,
      expiry_date: null,
      note: `Payment for subscription renewal (${diag.customer_name})`,
    });
    setIsModalOpen(true);
  };

  const handleCreatePaymentLinkSubmit = async () => {
    try {
      const values = await form.validateFields();
      if (!activeDiagnosis) return;

      setSubmittingLink(true);

      const res = await createCopilotPaymentLink({
        case_id: activeDiagnosis.case_id,
        amount_inr: Number(values.amount_inr),
        customer_email: values.customer_email,
        customer_phone: values.customer_phone,
        expiry_date: values.expiry_date ? values.expiry_date.format('YYYY-MM-DD') : undefined,
        note: values.note,
        agent_name: 'Support Agent',
      });

      setIsModalOpen(false);
      message.success('Payment Link created successfully on Razorpay!');

      // Post success card in chat
      const successMsgId = `link_success_${Date.now()}`;
      setMessages((prev) => [
        ...prev,
        {
          id: successMsgId,
          sender: 'assistant',
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
          createdPaymentLink: res,
          suggestions: [
            { id: 's_status', text: 'Track link status', action: 'INFO_QUERY' },
            { id: 's_next', text: 'What happens to the failed amount?', action: 'INFO_QUERY' },
            { id: 's_analyse', text: 'Analyse all my failed payments', action: 'ANALYZE_ALL' },
          ],
          userFeedback: null,
        },
      ]);
    } catch (err: any) {
      message.error(`Failed to create payment link: ${err.message}`);
    } finally {
      setSubmittingLink(false);
    }
  };

  const handleFeedback = (messageId: string, feedbackType: 'like' | 'dislike') => {
    setMessages((prev) =>
      prev.map((msg) =>
        msg.id === messageId
          ? { ...msg, userFeedback: msg.userFeedback === feedbackType ? null : feedbackType }
          : msg
      )
    );
    if (feedbackType === 'like') {
      message.success('Thank you for your feedback!');
    } else {
      message.info('Feedback recorded for agent improvement.');
    }
  };

  const copyToClipboard = (text: string, label: string = 'Content') => {
    navigator.clipboard.writeText(text);
    message.success(`${label} copied to clipboard!`);
  };

  const shareDiagnosis = (diag: CopilotDiagnosis) => {
    const summary = `Razorpay AI Recovery Diagnosis:\n${diag.headline}\nRoot Cause: ${diag.explanation}\nResolution: ${diag.recommendation}`;
    navigator.clipboard.writeText(summary);
    message.success('Summary copied for customer reply!');
  };

  return (
    <div className="max-w-5xl mx-auto flex flex-col h-[calc(100vh-108px)]">
      {/* Top Header Bar */}
      <div className="mb-4 bg-white px-6 py-3.5 rounded-xl border border-slate-200 shadow-sm flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-full bg-blue-50 border border-blue-200 flex items-center justify-center text-blue-600 text-base">
            <RobotFilled />
          </div>
          <div className="flex items-center gap-2">
            <h2 className="text-base font-bold text-slate-800 m-0">Ray AI Copilot</h2>
            <Badge status="processing" text={<span className="text-xs text-emerald-600 font-medium">Ready</span>} />
          </div>
        </div>
      </div>


      {/* Main Chat Container */}
      <Card
        className="flex-1 flex flex-col overflow-hidden shadow-sm border border-slate-200 rounded-xl"
        bodyStyle={{
          display: 'flex',
          flexDirection: 'column',
          height: '100%',
          padding: '16px 20px',
        }}
      >
        {/* Messages Scroll Area */}
        <div className="flex-1 overflow-y-auto pr-2 space-y-5">
          {/* Welcome Screen when thread is empty */}
          {messages.length === 0 && (
            <div className="py-8 flex flex-col items-center justify-center text-center">
              <div className="w-16 h-16 rounded-2xl bg-gradient-to-tr from-blue-600 to-indigo-600 text-white flex items-center justify-center text-2xl shadow-md mb-3">
                <ThunderboltFilled />
              </div>
              <h3 className="text-lg font-bold text-slate-800 m-0">Ray AI Copilot</h3>

              {/* Quick Action Chips */}
              <div className="mt-5 w-full max-w-2xl">
                <div className="flex flex-wrap gap-2 justify-center">
                  {CATEGORY_CHIPS.map((chip) => (
                    <button
                      key={chip.key}
                      onClick={() => handleSendMessage(chip.prompt)}
                      className="px-3 py-1.5 bg-slate-50 hover:bg-blue-50 border border-slate-200 hover:border-blue-300 rounded-lg text-xs font-medium text-slate-700 hover:text-blue-700 transition-all flex items-center gap-1.5 shadow-sm"
                    >
                      <span>{chip.label}</span>
                    </button>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* Conversation Bubbles */}
          {messages.map((msg) => (
            <div key={msg.id} className="flex flex-col">
              {/* User Bubble */}
              {msg.sender === 'user' && (
                <div className="flex justify-end items-start gap-2.5 mb-2">
                  <div className="max-w-xl bg-blue-600 text-white rounded-2xl rounded-tr-sm px-4 py-3 shadow-sm">
                    {msg.imagePreview && (
                      <div className="mb-2 bg-blue-700/60 p-1.5 rounded-lg border border-blue-400/30">
                        <div className="flex items-center gap-1.5 text-[11px] text-blue-100 mb-1">
                          <FileImageOutlined /> {msg.imageName || 'Attached Screenshot'}
                        </div>
                        <img
                          src={msg.imagePreview}
                          alt="Uploaded complaint screenshot"
                          className="max-h-48 rounded object-cover cursor-pointer hover:opacity-95"
                          onClick={() => {
                            Modal.info({
                              title: msg.imageName || 'Attached Screenshot',
                              width: 700,
                              content: <img src={msg.imagePreview} alt="Screenshot" className="w-full rounded mt-2" />,
                            });
                          }}
                        />
                      </div>
                    )}
                    <p className="text-sm m-0 leading-relaxed whitespace-pre-wrap">{msg.text}</p>
                    <div className="text-[10px] text-blue-200 text-right mt-1">{msg.timestamp}</div>
                  </div>
                  <Avatar size={32} icon={<UserOutlined />} className="bg-slate-700 mt-1" />
                </div>
              )}

              {/* Assistant Bubble */}
              {msg.sender === 'assistant' && (
                <div className="flex justify-start items-start gap-3 mb-4">
                  <Avatar size={34} icon={<RobotFilled />} className="bg-blue-600 text-white mt-1 shadow-sm" />

                  <div className="max-w-2xl bg-white border border-slate-200 rounded-2xl rounded-tl-sm p-4 shadow-sm">
                    {/* Rich Diagnosis & Investigation View */}
                    {(msg.investigation || msg.diagnosis) && (
                      <div>
                        {/* Investigation Reasoning Trace Chips */}
                        {msg.investigation?.steps && msg.investigation.steps.length > 0 && (
                          <div className="mb-3 bg-slate-50 p-2.5 rounded-lg border border-slate-200">
                            <div className="text-[10px] font-bold text-slate-500 uppercase tracking-wider mb-1.5 flex items-center justify-between">
                              <span className="flex items-center gap-1">
                                <SafetyCertificateOutlined className="text-blue-600" /> Multi-Step Investigation Trace
                              </span>
                              <span className="text-emerald-600 font-medium font-mono text-[10px]">VERIFIED</span>
                            </div>
                            <div className="flex flex-wrap gap-1">
                              {msg.investigation.steps.map((st, i) => (
                                <Tag key={i} color="success" icon={<CheckCircleFilled className="text-[10px]" />} style={{ fontSize: 11, padding: '1px 6px' }}>
                                  {((st.step || st.step_type || st.title || 'Step') as string).replace(/_/g, ' ')} {st.duration_ms ? `(${st.duration_ms}ms)` : ''}
                                </Tag>
                              ))}
                            </div>
                          </div>
                        )}

                        {/* Bold Diagnosis Headline */}
                        <div className="text-sm font-bold text-slate-900 leading-snug mb-2 flex items-start gap-1.5">
                          <span className="text-blue-600 font-extrabold text-base leading-none">•</span>
                          <span>{msg.investigation?.what_happened?.headline || msg.diagnosis?.headline}</span>
                        </div>

                        {/* Plain Language Explanation */}
                        <p className="text-xs text-slate-600 leading-relaxed mb-3">
                          {msg.investigation?.what_happened?.explanation || msg.diagnosis?.explanation}
                        </p>

                        {/* Auto-reversal Timeline (if relevant) */}
                        {(msg.investigation?.what_happened?.auto_reversal_timeline || msg.diagnosis?.auto_reversal_timeline) && (
                          <div className="mb-3.5 px-3 py-2 bg-sky-50 border border-sky-200 rounded-lg flex items-start gap-2 text-xs text-sky-800">
                            <InfoCircleOutlined className="text-sky-600 mt-0.5" />
                            <div>
                              <span className="font-semibold">Auto-Reversal: </span>
                              {msg.investigation?.what_happened?.auto_reversal_timeline || msg.diagnosis?.auto_reversal_timeline}
                            </div>
                          </div>
                        )}

                        {/* Verified Evidence Section */}
                        {msg.investigation?.verified_evidence && msg.investigation.verified_evidence.length > 0 && (
                          <div className="mb-3.5 bg-slate-50/70 p-2.5 rounded-lg border border-slate-200">
                            <div className="text-[10px] font-bold uppercase tracking-wider text-slate-500 mb-2 flex items-center justify-between">
                              <span>Verified Evidence Facts</span>
                              <span className="text-[10px] text-slate-400 font-normal">
                                {msg.investigation.verified_evidence.length} facts collected
                              </span>
                            </div>
                            <div className="space-y-1.5">
                              {msg.investigation.verified_evidence.map((ev, i) => (
                                <div key={i} className="p-2 bg-white border border-slate-200 rounded text-xs flex items-start justify-between">
                                  <div>
                                    <Tag color="geekblue" className="text-[10px] font-mono mr-1.5">{ev.source}</Tag>
                                    <span className="text-slate-700">{ev.description}</span>
                                  </div>
                                  <Tag color={ev.confidence === 'HIGH' ? 'green' : 'gold'} className="text-[10px]">
                                    {ev.confidence}
                                  </Tag>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}

                        {/* Ranked Potential Root Causes */}
                        {msg.investigation?.possible_causes && msg.investigation.possible_causes.length > 0 && (
                          <div className="mb-3.5">
                            <div className="text-[10px] font-bold uppercase tracking-wider text-slate-500 mb-1.5">
                              Identified Root Causes (Ranked by Confidence)
                            </div>
                            <div className="space-y-1.5">
                              {msg.investigation.possible_causes.map((cause, i) => (
                                <div key={i} className="p-2.5 bg-blue-50/50 border border-blue-100 rounded text-xs">
                                  <div className="flex items-center justify-between mb-1">
                                    <span className="font-semibold text-slate-900">{cause.description}</span>
                                    <Tag color={cause.confidence === 'HIGH' ? 'green' : cause.confidence === 'MEDIUM' ? 'gold' : 'blue'} className="text-[10px]">
                                      {cause.confidence} CONFIDENCE
                                    </Tag>
                                  </div>
                                  {cause.recommended_action && (
                                    <div className="text-[11px] text-slate-600 mt-1">
                                      <span className="font-medium text-slate-700">Action:</span> {cause.recommended_action}
                                    </div>
                                  )}
                                </div>
                              ))}
                            </div>
                          </div>
                        )}

                        {/* How to Resolve This Section */}
                        <div className="mt-3 pt-3 border-t border-slate-100 bg-slate-50/70 -mx-4 px-4 py-3">
                          <div className="text-[11px] font-bold uppercase tracking-wider text-slate-500 mb-1.5">
                            Recommended Resolution Plan
                          </div>
                          <div className="text-xs text-slate-700 mb-2">
                            <span className="font-semibold text-slate-900">
                              {msg.investigation?.recommended_solution?.resolution_name || msg.diagnosis?.resolution_name}
                            </span> —{' '}
                            {msg.investigation?.recommended_solution?.resolution_instruction || msg.diagnosis?.resolution_instruction}
                          </div>

                          <div className="px-3 py-2 bg-white rounded-lg border border-blue-200 text-xs text-slate-800 flex items-start gap-2 shadow-xs">
                            <span className="font-bold text-blue-600">Ray AI Advice:</span>
                            <span className="text-slate-700">
                              {msg.investigation?.recommended_solution?.recommendation || msg.diagnosis?.recommendation}
                            </span>
                          </div>

                          {/* Authorized Operations Bar */}
                          <div className="mt-3 pt-2.5 border-t border-slate-200 flex flex-wrap gap-2">
                            <Button
                              size="small"
                              type="primary"
                              icon={<MailOutlined />}
                              onClick={() => {
                                const diag = msg.investigation?.diagnosis || msg.diagnosis;
                                navigate(
                                  `/email/compose?issue_id=${msg.investigation?.issue_id || ''}&email=${encodeURIComponent(diag?.customer_email || '')}&name=${encodeURIComponent(diag?.customer_name || '')}&amount=${encodeURIComponent(diag?.amount_inr || '')}&case_id=${msg.investigation?.case_id || diag?.case_id || ''}`
                                );
                              }}
                              style={{ background: '#0052cc' }}
                            >
                              Draft Customer Email
                            </Button>

                            {msg.investigation?.issue_id && (
                              <Button
                                size="small"
                                icon={<AuditOutlined />}
                                onClick={() => navigate(`/issues/${msg.investigation!.issue_id}`)}
                              >
                                Track Issue ({msg.investigation.issue_id})
                              </Button>
                            )}

                            <Button
                              size="small"
                              icon={<LinkOutlined />}
                              onClick={() => openPaymentLinkModal(msg.investigation?.diagnosis || msg.diagnosis)}
                            >
                              Generate Link
                            </Button>

                            <Button
                              size="small"
                              icon={<DollarCircleOutlined />}
                              onClick={async () => {
                                const diag = msg.investigation?.diagnosis || msg.diagnosis;
                                setCheckingRefund(true);
                                try {
                                  const refRes = await investigateRefund({ payment_id: diag?.payment_id, case_id: diag?.case_id });
                                  setRefundModalData(refRes);
                                  setRefundModalOpen(true);
                                } catch (err: any) {
                                  message.error(err.message || 'Failed to check refund');
                                } finally {
                                  setCheckingRefund(false);
                                }
                              }}
                              loading={checkingRefund}
                            >
                              Check Refund
                            </Button>
                          </div>
                        </div>

                        {/* Message-level Feedback Icons */}
                        <div className="flex items-center justify-between mt-3 pt-2 border-t border-slate-100 text-slate-400 text-xs">
                          <div className="flex items-center gap-3">
                            <Tooltip title="Helpful diagnosis">
                              <button
                                onClick={() => handleFeedback(msg.id, 'like')}
                                className={`p-1 rounded hover:text-blue-600 hover:bg-slate-100 transition-colors ${msg.userFeedback === 'like' ? 'text-blue-600 font-bold' : ''
                                  }`}
                              >
                                <LikeOutlined />
                              </button>
                            </Tooltip>
                            <Tooltip title="Not helpful">
                              <button
                                onClick={() => handleFeedback(msg.id, 'dislike')}
                                className={`p-1 rounded hover:text-rose-600 hover:bg-slate-100 transition-colors ${msg.userFeedback === 'dislike' ? 'text-rose-600 font-bold' : ''
                                  }`}
                              >
                                <DislikeOutlined />
                              </button>
                            </Tooltip>
                            <Tooltip title="Copy diagnosis">
                              <button
                                onClick={() => copyToClipboard(msg.diagnosis!.headline, 'Diagnosis')}
                                className="p-1 rounded hover:text-slate-700 hover:bg-slate-100 transition-colors"
                              >
                                <CopyOutlined />
                              </button>
                            </Tooltip>
                            <Tooltip title="Share customer response summary">
                              <button
                                onClick={() => shareDiagnosis(msg.diagnosis!)}
                                className="p-1 rounded hover:text-slate-700 hover:bg-slate-100 transition-colors"
                              >
                                <ShareAltOutlined />
                              </button>
                            </Tooltip>
                          </div>
                          <span className="text-[10px] text-slate-400">{msg.timestamp}</span>
                        </div>
                      </div>
                    )}

                    {/* Payment Link Success Card */}
                    {msg.createdPaymentLink && (
                      <div>
                        <div className="flex items-center gap-2 mb-2">
                          <Tag color="success" className="font-semibold px-2 py-0.5 text-xs flex items-center gap-1">
                            <CheckCircleFilled /> Payment Link Created
                          </Tag>
                        </div>


                        <div className="bg-emerald-50/70 border border-emerald-200 rounded-xl p-3 mb-3">
                          <div className="flex items-center justify-between text-xs mb-1.5">
                            <span className="text-slate-600 font-medium">Amount:</span>
                            <span className="font-bold text-slate-900 text-sm">
                              ₹{msg.createdPaymentLink.amount_inr.toLocaleString('en-IN')}
                            </span>
                          </div>
                          <div className="flex items-center justify-between text-xs mb-2">
                            <span className="text-slate-600 font-medium">Recipient:</span>
                            <span className="text-slate-800 font-mono text-[11px]">
                              {msg.createdPaymentLink.customer_email}
                            </span>
                          </div>

                          <div className="mt-2">
                            <div className="text-[11px] font-semibold text-slate-600 mb-1">Generated Payment Link:</div>
                            <div className="flex items-center gap-2">
                              <Input
                                readOnly
                                value={msg.createdPaymentLink.short_url}
                                className="font-mono text-xs bg-white text-blue-700"
                                prefix={<LinkOutlined className="text-slate-400" />}
                              />
                              <Button
                                type="primary"
                                icon={<CopyOutlined />}
                                onClick={() => copyToClipboard(msg.createdPaymentLink!.short_url, 'Payment Link URL')}
                                className="bg-blue-600"
                              >
                                Copy
                              </Button>
                            </div>
                          </div>
                        </div>

                        {/* Feedback Icons */}
                        <div className="flex items-center justify-between text-slate-400 text-xs pt-1">
                          <div className="flex items-center gap-3">
                            <button
                              onClick={() => handleFeedback(msg.id, 'like')}
                              className={`p-1 hover:text-blue-600 ${msg.userFeedback === 'like' ? 'text-blue-600 font-bold' : ''}`}
                            >
                              <LikeOutlined />
                            </button>
                            <button
                              onClick={() => handleFeedback(msg.id, 'dislike')}
                              className={`p-1 hover:text-rose-600 ${msg.userFeedback === 'dislike' ? 'text-rose-600 font-bold' : ''}`}
                            >
                              <DislikeOutlined />
                            </button>
                            <button
                              onClick={() => copyToClipboard(msg.createdPaymentLink!.short_url, 'Payment Link')}
                              className="p-1 hover:text-slate-700"
                            >
                              <CopyOutlined />
                            </button>
                          </div>
                          <span className="text-[10px] text-slate-400">{msg.timestamp}</span>
                        </div>
                      </div>
                    )}

                    {/* Fallback Message View */}
                    {msg.fallbackMessage && (
                      <div>
                        <p className="text-xs text-slate-700 leading-relaxed m-0">{msg.fallbackMessage}</p>
                        <div className="text-[10px] text-slate-400 text-right mt-2">{msg.timestamp}</div>
                      </div>
                    )}

                    {/* Follow-up Suggestions Block */}
                    {msg.suggestions && msg.suggestions.length > 0 && (
                      <div className="mt-3 pt-3 border-t border-slate-100">
                        <div className="text-[11px] font-bold text-slate-500 uppercase tracking-wider mb-2">
                          How can I help you next?
                        </div>
                        <div className="flex flex-col gap-1.5">
                          {msg.suggestions.map((sug, idx) => (
                            <button
                              key={sug.id || idx}
                              onClick={() => handleSuggestionClick(sug, msg.diagnosis || undefined, msg.investigation || undefined)}
                              className="text-left px-3 py-2 rounded-lg bg-slate-50 hover:bg-blue-50 border border-slate-200 hover:border-blue-300 text-xs text-slate-700 hover:text-blue-700 font-medium transition-colors flex items-center justify-between group"
                            >
                              <span className="flex items-center gap-2">
                                <span className="w-4 h-4 rounded-full bg-slate-200 group-hover:bg-blue-200 text-slate-600 group-hover:text-blue-700 text-[10px] font-bold flex items-center justify-center">
                                  {idx + 1}
                                </span>
                                <span>{sug.text}</span>
                              </span>
                              <span className="text-slate-400 group-hover:text-blue-600 text-xs">→</span>
                            </button>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          ))}

          {/* Loading Indicator */}
          {loading && (
            <div className="flex justify-start items-center gap-3">
              <Avatar size={34} icon={<RobotFilled />} className="bg-blue-600 text-white" />
              <div className="bg-white border border-slate-200 rounded-2xl rounded-tl-sm px-4 py-3 shadow-sm flex items-center gap-2 text-xs text-slate-500">
                <Spin size="small" />
                <span>Cross-referencing Razorpay records and diagnosing failure cause...</span>
              </div>
            </div>
          )}

          <div ref={chatBottomRef} />
        </div>

        {/* Input & Action Bar */}
        <div className="pt-3 border-t border-slate-200">
          {/* Selected Attachment Chip */}
          {selectedImage && (
            <div className="mb-2 flex items-center gap-2 bg-blue-50 border border-blue-200 rounded-lg px-3 py-1.5 text-xs text-blue-800 w-fit">
              <FileImageOutlined className="text-blue-600" />
              <span className="font-medium max-w-xs truncate">{selectedImage.name}</span>
              <button
                onClick={removeSelectedImage}
                className="text-blue-500 hover:text-rose-600 ml-1 transition-colors"
              >
                <CloseCircleFilled />
              </button>
            </div>
          )}

          {/* Input Bar */}
          <div className="flex items-center gap-2">
            <input
              type="file"
              ref={fileInputRef}
              onChange={handleImageUpload}
              accept="image/*"
              className="hidden"
            />
            <Tooltip title="Attach screenshot or complaint email image">
              <Button
                icon={<PaperClipOutlined />}
                onClick={() => fileInputRef.current?.click()}
                className={`flex items-center justify-center ${selectedImage ? 'text-blue-600 border-blue-400 bg-blue-50' : 'text-slate-600'
                  }`}
              />
            </Tooltip>

            <Input
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              onPressEnter={(e) => {
                if (!e.shiftKey) {
                  e.preventDefault();
                  handleSendMessage();
                }
              }}
              placeholder="Type customer message / complaint or ask a question (e.g., 'Customer Rahul faced a payment failure')..."
              className="rounded-lg text-sm py-2"
              disabled={loading}
            />

            <Button
              type="primary"
              icon={<SendOutlined />}
              onClick={() => handleSendMessage()}
              loading={loading}
              disabled={!inputText.trim() && !selectedImage}
              className="bg-blue-600 flex items-center justify-center font-medium px-4"
            >
              Send
            </Button>
          </div>
        </div>
      </Card>

      {/* "Create Payment Link" Pre-filled Modal */}
      <Modal
        title={
          <div className="flex items-center gap-2 text-slate-900 font-bold">
            <LinkOutlined className="text-blue-600" />
            <span>Create Razorpay Payment Link</span>
          </div>
        }
        open={isModalOpen}
        onCancel={() => setIsModalOpen(false)}
        footer={null}
        width={520}
        destroyOnClose
      >
        <div className="text-xs text-slate-500 mb-4 pb-3 border-b border-slate-100">
          Create payment link for <strong className="text-slate-800">{activeDiagnosis?.customer_name}</strong>.
        </div>

        <Form form={form} layout="vertical" onFinish={handleCreatePaymentLinkSubmit}>
          <Form.Item
            name="amount_inr"
            label={<span className="text-xs font-semibold text-slate-700">Amount (INR)</span>}
            rules={[{ required: true, message: 'Please enter recovery amount' }]}
          >
            <InputNumber
              className="w-full"
              prefix="₹"
              min={1}
              precision={2}
              formatter={(val) => `${val}`.replace(/\B(?=(\d{3})+(?!\d))/g, ',')}
            />
          </Form.Item>

          <Form.Item
            name="customer_email"
            label={<span className="text-xs font-semibold text-slate-700">Customer Email</span>}
            rules={[
              { required: true, message: 'Please enter customer email' },
              { type: 'email', message: 'Enter a valid email address' },
            ]}
          >
            <Input placeholder="customer@example.com" />
          </Form.Item>

          <Form.Item
            name="customer_phone"
            label={<span className="text-xs font-semibold text-slate-700">Customer Phone</span>}
            rules={[{ required: true, message: 'Please enter customer phone' }]}
          >
            <Input placeholder="+91 9800000000" />
          </Form.Item>

          <Form.Item
            name="expiry_date"
            label={<span className="text-xs font-semibold text-slate-700">Expiry Date (Optional)</span>}
          >
            <DatePicker className="w-full" placeholder="Select link expiry date" />
          </Form.Item>

          <Form.Item
            name="note"
            label={<span className="text-xs font-semibold text-slate-700">Note to Customer (Optional)</span>}
          >
            <TextArea rows={2} placeholder="Add a recovery note..." />
          </Form.Item>


          <div className="flex justify-end gap-2 pt-3 border-t border-slate-100 mt-4">
            <Button onClick={() => setIsModalOpen(false)} disabled={submittingLink}>
              Cancel
            </Button>
            <Button
              type="primary"
              htmlType="submit"
              loading={submittingLink}
              className="bg-blue-600 font-medium"
            >
              Create Payment Link
            </Button>
          </div>
        </Form>
      </Modal>

      {/* Refund Investigation Modal */}
      <Modal
        title={
          <div className="flex items-center gap-2 text-slate-900 font-bold">
            <DollarCircleOutlined className="text-blue-600" />
            <span>Refund Status & Eligibility</span>
          </div>
        }
        open={refundModalOpen}
        onCancel={() => setRefundModalOpen(false)}
        footer={null}
        width={540}
        destroyOnClose
      >
        {refundModalData && (
          <div className="space-y-3">
            <div className="bg-slate-50 p-3 rounded border border-slate-200 text-xs space-y-2">
              <div className="flex justify-between">
                <span className="text-slate-500">Payment ID:</span>
                <span className="font-mono font-semibold text-slate-800">{refundModalData.payment_id || '—'}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">Customer:</span>
                <span className="font-semibold text-slate-800">{refundModalData.customer_name || '—'}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">Original Amount:</span>
                <span className="font-semibold text-slate-800">
                  ₹{refundModalData.original_amount_inr ? refundModalData.original_amount_inr.toLocaleString() : '0.00'}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">Remaining Refundable:</span>
                <span className="font-semibold text-emerald-700">
                  ₹{refundModalData.remaining_refundable_inr ? refundModalData.remaining_refundable_inr.toLocaleString() : '0.00'}
                </span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-slate-500">Refund Status:</span>
                <Tag color={refundModalData.refund_eligible ? 'green' : 'orange'}>
                  {refundModalData.refund_status || (refundModalData.refund_eligible ? 'Eligible' : 'Not Eligible')}
                </Tag>
              </div>
            </div>

            {refundModalData.note && (
              <div className="p-2.5 bg-amber-50 border border-amber-200 rounded text-xs text-amber-900">
                <InfoCircleOutlined className="mr-1" />
                {refundModalData.note}
              </div>
            )}

            <div className="flex justify-end pt-2">
              <Button type="primary" onClick={() => setRefundModalOpen(false)} style={{ background: '#0052cc' }}>
                Close
              </Button>
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
}
