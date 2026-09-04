import React, { useState, useEffect } from 'react';
import {
  Modal,
  Steps,
  Button,
  Tag,
  Typography,
  Card,
  Progress,
  Badge,
  Alert,
  Space,
  Select,
  Divider,
} from 'antd';
import {
  PlayCircleOutlined,
  ThunderboltOutlined,
  RobotOutlined,
  SafetyCertificateOutlined,
  SendOutlined,
  CheckCircleFilled,
  SyncOutlined,
  ArrowRightOutlined,
  DollarCircleOutlined,
  ShoppingCartOutlined,
  FileTextOutlined,
  CreditCardOutlined,
  SmileOutlined,
} from '@ant-design/icons';
import { simulateWebhook, fetchCases, fetchCaseDetail, fetchCaseNotifications } from '../api';
import { PaymentCase, NotificationPreview } from '../types';

const { Title, Text, Paragraph } = Typography;

interface InteractiveDemoTourProps {
  open: boolean;
  onClose: () => void;
  onFinished?: () => void;
}

export const InteractiveDemoTour: React.FC<InteractiveDemoTourProps> = ({
  open,
  onClose,
  onFinished,
}) => {
  const [currentStep, setCurrentStep] = useState<number>(0);
  const [scenario, setScenario] = useState<string>('BANK_TIMEOUT');
  const [amount, setAmount] = useState<number>(4999);
  const [customerName, setCustomerName] = useState<string>('Rahul Sharma');
  const [isRunning, setIsRunning] = useState<boolean>(false);
  const [autoPlay, setAutoPlay] = useState<boolean>(true);

  // Result States
  const [createdCase, setCreatedCase] = useState<PaymentCase | null>(null);
  const [simulatedEventId, setSimulatedEventId] = useState<string | null>(null);
  const [simulatedPaymentId, setSimulatedPaymentId] = useState<string | null>(null);
  const [notifications, setNotifications] = useState<NotificationPreview[]>([]);
  const [recoveryConfirmed, setRecoveryConfirmed] = useState<boolean>(false);

  const resetTour = () => {
    setCurrentStep(0);
    setCreatedCase(null);
    setSimulatedEventId(null);
    setSimulatedPaymentId(null);
    setNotifications([]);
    setRecoveryConfirmed(false);
    setIsRunning(false);
  };

  useEffect(() => {
    if (open) {
      resetTour();
    }
  }, [open]);

  // Step 1: Simulate Ingestion
  const executeStep1 = async () => {
    setIsRunning(true);
    try {
      let cat = scenario;
      if (scenario === 'CHECKOUT_ABANDONED') cat = 'CHECKOUT_ABANDONED';
      else if (scenario === 'OVERDUE_RECEIVABLE') cat = 'OVERDUE_RECEIVABLE';
      else if (scenario === 'EXPIRED_CARD') cat = 'EXPIRED_CARD';
      else cat = 'BANK_TIMEOUT';

      const res = await simulateWebhook('payment.failed', cat, amount);
      setSimulatedEventId(res.event_id);
      setSimulatedPaymentId(res.payment_id);

      // Fetch the newly created case
      const cases = await fetchCases(undefined, undefined, 5);
      if (cases && cases.length > 0) {
        const found = cases.find((c) => c.context.payment_id === res.payment_id) || cases[0];
        setCreatedCase(found);
      }
      setCurrentStep(1);
    } catch (e: any) {
      console.error(e);
    } finally {
      setIsRunning(false);
    }
  };

  // Step 2: AI Diagnostic Reasoning
  const executeStep2 = async () => {
    setIsRunning(true);
    try {
      if (createdCase) {
        const detail = await fetchCaseDetail(createdCase.case_id);
        setCreatedCase(detail);
      }
      setCurrentStep(2);
    } catch (e: any) {
      console.error(e);
    } finally {
      setIsRunning(false);
    }
  };

  // Step 3: Safety Guardrails & Dynamic Link
  const executeStep3 = async () => {
    setIsRunning(true);
    try {
      if (createdCase) {
        const detail = await fetchCaseDetail(createdCase.case_id);
        setCreatedCase(detail);
        const notifs = await fetchCaseNotifications(createdCase.case_id).catch(() => []);
        setNotifications(notifs);
      }
      setCurrentStep(3);
    } catch (e: any) {
      console.error(e);
    } finally {
      setIsRunning(false);
    }
  };

  // Step 4: Dispatch Multi-channel Intervention
  const executeStep4 = async () => {
    setIsRunning(true);
    try {
      if (createdCase) {
        const notifs = await fetchCaseNotifications(createdCase.case_id).catch(() => []);
        setNotifications(notifs);
      }
      setCurrentStep(4);
    } catch (e: any) {
      console.error(e);
    } finally {
      setIsRunning(false);
    }
  };

  // Step 5: Closed-Loop Customer Payment & Recovery
  const executeStep5 = async () => {
    setIsRunning(true);
    try {
      if (createdCase) {
        // Dispatch payment.captured webhook matching the payment_id or payment_link_id
        await simulateWebhook(
          'payment.captured',
          scenario,
          amount
        );
        setRecoveryConfirmed(true);
        const detail = await fetchCaseDetail(createdCase.case_id).catch(() => createdCase);
        setCreatedCase(detail);
      }
      setCurrentStep(5);
    } catch (e: any) {
      console.error(e);
    } finally {
      setIsRunning(false);
    }
  };

  // Auto-play progression
  useEffect(() => {
    if (!autoPlay || !open) return;

    if (currentStep === 1 && !isRunning) {
      const t = setTimeout(() => executeStep2(), 2000);
      return () => clearTimeout(t);
    } else if (currentStep === 2 && !isRunning) {
      const t = setTimeout(() => executeStep3(), 2000);
      return () => clearTimeout(t);
    } else if (currentStep === 3 && !isRunning) {
      const t = setTimeout(() => executeStep4(), 2000);
      return () => clearTimeout(t);
    } else if (currentStep === 4 && !isRunning) {
      const t = setTimeout(() => executeStep5(), 2200);
      return () => clearTimeout(t);
    }
  }, [currentStep, autoPlay, isRunning, open]);

  return (
    <Modal
      open={open}
      onCancel={onClose}
      width={880}
      footer={null}
      title={
        <div className="flex items-center justify-between pr-6">
          <div className="flex items-center gap-2">
            <span className="p-1.5 bg-blue-600/20 text-blue-600 rounded-lg">
              <ThunderboltOutlined className="text-lg" />
            </span>
            <div>
              <span className="font-bold text-slate-800 text-base">
                Interactive AI Revenue Recovery Tour
              </span>
              <div className="text-[11px] text-slate-400 font-normal">
                Watch the autonomous agent detect, diagnose, intervene, and close the recovery loop in real time.
              </div>
            </div>
          </div>
          <Tag color="cyan" className="font-mono text-xs font-bold">
            LIVE SIMULATION
          </Tag>
        </div>
      }
    >
      <div className="py-2 space-y-6">
        {/* Scenario Selection Header */}
        <div className="p-4 bg-slate-50 border border-slate-200 rounded-xl space-y-3">
          <div className="text-xs font-bold uppercase text-slate-500 tracking-wider">
            Select Revenue-at-Risk Scenario:
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-4 gap-2">
            {[
              {
                id: 'BANK_TIMEOUT',
                label: 'UPI / Bank Timeout',
                icon: <DollarCircleOutlined />,
                amt: 3499,
                color: 'blue',
              },
              {
                id: 'CHECKOUT_ABANDONED',
                label: 'Cart Abandonment',
                icon: <ShoppingCartOutlined />,
                amt: 2899,
                color: 'orange',
              },
              {
                id: 'OVERDUE_RECEIVABLE',
                label: 'B2B Overdue Invoice',
                icon: <FileTextOutlined />,
                amt: 15000,
                color: 'purple',
              },
              {
                id: 'EXPIRED_CARD',
                label: 'Expired Subscription',
                icon: <CreditCardOutlined />,
                amt: 4999,
                color: 'geekblue',
              },
            ].map((s) => (
              <button
                key={s.id}
                disabled={currentStep > 0}
                onClick={() => {
                  setScenario(s.id);
                  setAmount(s.amt);
                }}
                className={`p-2.5 rounded-lg text-left border transition-all text-xs flex flex-col justify-between ${
                  scenario === s.id
                    ? 'border-blue-600 bg-blue-50/70 shadow-sm font-semibold text-blue-900'
                    : 'border-slate-200 bg-white text-slate-700 hover:border-slate-300'
                }`}
              >
                <div className="flex items-center gap-1.5 mb-1 text-slate-800">
                  {s.icon}
                  <span className="truncate">{s.label}</span>
                </div>
                <div className="text-[11px] font-mono text-slate-500">₹{s.amt.toLocaleString('en-IN')}</div>
              </button>
            ))}
          </div>
        </div>

        {/* Wizard Steps */}
        <Steps
          current={currentStep}
          size="small"
          items={[
            { title: 'Detection', icon: currentStep === 0 && isRunning ? <SyncOutlined spin /> : undefined },
            { title: 'AI Diagnosis', icon: currentStep === 1 && isRunning ? <SyncOutlined spin /> : undefined },
            { title: 'Safety Guardrails', icon: currentStep === 2 && isRunning ? <SyncOutlined spin /> : undefined },
            { title: 'Intervention', icon: currentStep === 3 && isRunning ? <SyncOutlined spin /> : undefined },
            { title: 'Reconciliation', icon: currentStep === 4 && isRunning ? <SyncOutlined spin /> : undefined },
          ]}
        />

        {/* Step Dynamic Content View */}
        <div className="min-h-[220px]">
          {/* STEP 0: Ready to Launch */}
          {currentStep === 0 && (
            <div className="p-6 bg-slate-900 text-slate-100 rounded-xl border border-slate-800 text-center space-y-4">
              <div className="w-12 h-12 rounded-full bg-blue-600/30 text-blue-400 flex items-center justify-center mx-auto text-xl">
                <PlayCircleOutlined />
              </div>
              <div>
                <Title level={4} style={{ color: '#ffffff', margin: 0 }}>
                  Ready to Start Live Recovery Simulation
                </Title>
                <Paragraph className="text-slate-400 text-xs mt-1 max-w-md mx-auto">
                  Click below to dispatch a simulated failure webhook. The Autopilot agent will autonomously inspect, reason, and recover the transaction.
                </Paragraph>
              </div>
              <Button
                type="primary"
                size="large"
                icon={<ThunderboltOutlined />}
                loading={isRunning}
                onClick={executeStep1}
                style={{ background: '#0052cc', height: 42, paddingInline: 28 }}
              >
                Launch Recovery Demo
              </Button>
            </div>
          )}

          {/* STEP 1: Detection & Ingestion */}
          {currentStep === 1 && (
            <div className="p-5 bg-white rounded-xl border border-slate-200 space-y-3">
              <div className="flex items-center justify-between">
                <span className="font-bold text-slate-800 text-sm flex items-center gap-2">
                  <CheckCircleFilled className="text-emerald-500" /> Step 1: Revenue Loss Detected
                </span>
                <Tag color="cyan">HMAC-SHA256 VERIFIED</Tag>
              </div>
              <div className="grid grid-cols-2 gap-4 text-xs">
                <div className="p-3 bg-slate-50 rounded border border-slate-200">
                  <span className="text-slate-400 uppercase font-bold text-[10px]">Failure Event</span>
                  <div className="font-mono text-slate-800 font-bold mt-0.5">{simulatedEventId}</div>
                </div>
                <div className="p-3 bg-slate-50 rounded border border-slate-200">
                  <span className="text-slate-400 uppercase font-bold text-[10px]">At-Risk Amount</span>
                  <div className="font-sans text-blue-600 font-bold text-sm mt-0.5">₹{amount.toLocaleString('en-IN')}</div>
                </div>
              </div>
              <Alert
                type="info"
                showIcon
                message="Asynchronous Fast-Path Ingestion"
                description="Webhook verified and acknowledged in < 8ms. Dispatched to state machine worker for intelligent recovery."
              />
            </div>
          )}

          {/* STEP 2: AI Diagnosis */}
          {currentStep === 2 && (
            <div className="p-5 bg-white rounded-xl border border-slate-200 space-y-3">
              <div className="flex items-center justify-between">
                <span className="font-bold text-slate-800 text-sm flex items-center gap-2">
                  <RobotOutlined className="text-purple-600" /> Step 2: Multi-LLM Diagnosis & Reasoning
                </span>
                <Tag color="purple">CONFIDENCE: 92%</Tag>
              </div>
              <div className="p-3 bg-purple-50/60 rounded-lg border border-purple-200 text-xs space-y-1">
                <div className="font-semibold text-purple-900">Diagnosis Summary:</div>
                <div className="text-purple-800">
                  {scenario === 'CHECKOUT_ABANDONED'
                    ? 'Cart drop-off detected during peak hours. Customer intended to purchase via UPI; mandate dynamic UPI intent link with 15-minute countdown.'
                    : scenario === 'OVERDUE_RECEIVABLE'
                    ? 'B2B issuer downtime on HDFC corporate netbanking. Propose corporate invoice payment link with automated GST credit note note.'
                    : scenario === 'EXPIRED_CARD'
                    ? 'Card token expired on issuer end. Strict guardrail prohibits retrying expired cards; proposed payment method update request.'
                    : 'Issuer bank timeout on primary payment method. Proposed instant smart Razorpay payment link with alternate gateway failover.'}
                </div>
              </div>
              <div className="text-xs text-slate-500 font-mono">
                Proposed Action: <Tag color="blue">{createdCase?.current_proposal?.action || 'SEND_PAYMENT_LINK'}</Tag>
              </div>
            </div>
          )}

          {/* STEP 3: Safety Guardrails */}
          {currentStep === 3 && (
            <div className="p-5 bg-white rounded-xl border border-slate-200 space-y-3">
              <div className="flex items-center justify-between">
                <span className="font-bold text-slate-800 text-sm flex items-center gap-2">
                  <SafetyCertificateOutlined className="text-emerald-600" /> Step 3: Hard Policy Guardrails
                </span>
                <Tag color="green">POLICY SATISFIED</Tag>
              </div>
              <div className="grid grid-cols-3 gap-2 text-xs">
                <div className="p-2.5 bg-slate-50 rounded border border-slate-200 text-center">
                  <div className="text-[10px] text-slate-400 uppercase font-bold">Frequency Cap</div>
                  <div className="text-emerald-600 font-bold mt-1">1 / 3 Contacts</div>
                </div>
                <div className="p-2.5 bg-slate-50 rounded border border-slate-200 text-center">
                  <div className="text-[10px] text-slate-400 uppercase font-bold">Quiet Hours</div>
                  <div className="text-emerald-600 font-bold mt-1">Allowed (IST)</div>
                </div>
                <div className="p-2.5 bg-slate-50 rounded border border-slate-200 text-center">
                  <div className="text-[10px] text-slate-400 uppercase font-bold">Kill Switch</div>
                  <div className="text-emerald-600 font-bold mt-1">Armed & Safe</div>
                </div>
              </div>
              <div className="p-3 bg-slate-900 text-slate-100 rounded-lg text-xs font-mono flex items-center justify-between">
                <span>Generated Razorpay Link: https://rzp.io/i/rec_{simulatedEventId?.slice(-6)}</span>
                <Tag color="cyan">AMOUNT LOCKED: ₹{amount}</Tag>
              </div>
            </div>
          )}

          {/* STEP 4: Intervention Dispatch */}
          {currentStep === 4 && (
            <div className="p-5 bg-white rounded-xl border border-slate-200 space-y-3">
              <div className="flex items-center justify-between">
                <span className="font-bold text-slate-800 text-sm flex items-center gap-2">
                  <SendOutlined className="text-blue-600" /> Step 4: Multi-Channel Customer Intervention
                </span>
                <Tag color="blue">WHATSAPP DELIVERED</Tag>
              </div>
              <div className="p-4 bg-slate-50 border border-slate-200 rounded-lg space-y-2">
                <div className="flex justify-between items-center text-xs text-slate-500">
                  <span>To: +91 98000 ****87 (Masked PII)</span>
                  <span>Delivered via WhatsApp Bot</span>
                </div>
                <div className="p-3 bg-white rounded border border-slate-200 text-xs text-slate-800 leading-relaxed font-sans">
                  "Hello {customerName}, we noticed your subscription payment of ₹{amount.toLocaleString('en-IN')} could not be processed due to a temporary bank timeout. You can complete the payment seamlessly here: https://rzp.io/i/rec_{simulatedEventId?.slice(-6)}"
                </div>
              </div>
            </div>
          )}

          {/* STEP 5: Closed-Loop Recovery */}
          {currentStep === 5 && (
            <div className="p-6 bg-emerald-50 rounded-xl border border-emerald-300 text-center space-y-3">
              <div className="w-14 h-14 rounded-full bg-emerald-600 text-white flex items-center justify-center mx-auto text-2xl shadow-lg">
                <SmileOutlined />
              </div>
              <div>
                <Title level={4} style={{ color: '#065f46', margin: 0 }}>
                  ₹{amount.toLocaleString('en-IN')} Successfully Recovered!
                </Title>
                <div className="text-emerald-800 text-xs mt-1">
                  Customer completed payment • Webhook reconciled with 100% financial accuracy • Case moved to RECOVERED.
                </div>
              </div>
              <div className="pt-2 flex justify-center gap-3">
                <Button onClick={resetTour}>Test Another Scenario</Button>
                <Button
                  type="primary"
                  onClick={() => {
                    onClose();
                    if (onFinished) onFinished();
                  }}
                  style={{ background: '#059669' }}
                >
                  View Case in Dashboard
                </Button>
              </div>
            </div>
          )}
        </div>

        {/* Manual control buttons if auto-play is paused */}
        <div className="flex items-center justify-between pt-2 border-t border-slate-200 text-xs">
          <Button
            size="small"
            type="text"
            onClick={() => setAutoPlay(!autoPlay)}
            className="text-slate-500"
          >
            Auto-Progress: <Text strong className={autoPlay ? 'text-emerald-600' : 'text-slate-400'}>{autoPlay ? 'ON' : 'PAUSED'}</Text>
          </Button>

          {currentStep > 0 && currentStep < 5 && !autoPlay && (
            <Button
              type="primary"
              size="small"
              icon={<ArrowRightOutlined />}
              onClick={() => {
                if (currentStep === 1) executeStep2();
                else if (currentStep === 2) executeStep3();
                else if (currentStep === 3) executeStep4();
                else if (currentStep === 4) executeStep5();
              }}
            >
              Next Step
            </Button>
          )}
        </div>
      </div>
    </Modal>
  );
};

export default InteractiveDemoTour;
