import React, { useState, useEffect } from 'react';
import {
  Card,
  Tabs,
  Form,
  Input,
  Button,
  Switch,
  Select,
  Slider,
  InputNumber,
  Tag,
  Typography,
  Row,
  Col,
  Divider,
  Modal,
  message,
  Radio,
} from 'antd';
import {
  KeyOutlined,
  RobotOutlined,
  SafetyCertificateOutlined,
  CodeOutlined,
  ThunderboltOutlined,
  CopyOutlined,
  SaveOutlined,
  ReloadOutlined,
  ExclamationCircleOutlined,
  CheckCircleFilled,
  LockOutlined,
  UnlockOutlined,
  GlobalOutlined,
  BugOutlined,
  ApiOutlined,
  SendOutlined,
  ExperimentOutlined,
  FileTextOutlined,
} from '@ant-design/icons';
import {
  fetchAccountSettings,
  updateAccountSettings,
  toggleKillSwitch,
  testAIModelInference,
  simulateTestWebhook,
  fetchSystemDiagnostics,
} from '../api';
import { AccountSettingsData } from '../types';

const { Title, Text } = Typography;
const { Option } = Select;

export default function AccountSettings() {
  const [loading, setLoading] = useState<boolean>(true);
  const [saving, setSaving] = useState<boolean>(false);
  const [settings, setSettings] = useState<AccountSettingsData | null>(null);
  const [diagnostics, setDiagnostics] = useState<any>(null);
  const [activeTab, setActiveTab] = useState<string>('apikeys');
  const [showKeySecret, setShowKeySecret] = useState<boolean>(false);
  const [selectedSdk, setSelectedSdk] = useState<string>('python');

  // Test Inference state
  const [testingModel, setTestingModel] = useState<boolean>(false);
  const [modelTestResult, setModelTestResult] = useState<any>(null);
  const [testErrorCode, setTestErrorCode] = useState<string>('BAD_REQUEST_PAYMENT_TIMED_OUT');
  const [testAmount, setTestAmount] = useState<number>(4999);

  // Test Webhook state
  const [testingWebhook, setTestingWebhook] = useState<boolean>(false);
  const [webhookTestResult, setWebhookTestResult] = useState<any>(null);

  // Forms & Modals
  const [form] = Form.useForm();
  const [isKillSwitchModalOpen, setIsKillSwitchModalOpen] = useState<boolean>(false);
  const [killSwitchReason, setKillSwitchReason] = useState<string>('');

  const loadAll = async () => {
    setLoading(true);
    try {
      const [data, diag] = await Promise.all([
        fetchAccountSettings(),
        fetchSystemDiagnostics().catch(() => null),
      ]);
      setSettings(data);
      setDiagnostics(diag);

      form.setFieldsValue({
        // AI Model Form
        active_provider: data.ai_model.active_provider,
        gemini_model: data.ai_model.gemini_model,
        openai_model: data.ai_model.openai_model,
        openai_base_url: data.ai_model.openai_base_url,
        ollama_model: data.ai_model.ollama_model,
        ollama_base_url: data.ai_model.ollama_base_url,

        // Policies Form
        payment_execution_mode: data.gateway.execution_mode,
        human_review_threshold_inr: data.policies.human_review_threshold_inr,
        min_confidence_threshold: data.policies.min_confidence_threshold * 100,
        max_contact_attempts: data.policies.max_contact_attempts,
        min_hours_between_contacts: data.policies.min_hours_between_contacts,
        voice_enabled: data.voice.voice_enabled,
      });
    } catch (err: any) {
      message.error(err.message || 'Failed to load developer settings');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAll();
  }, []);

  const copyToClipboard = (text: string, label: string) => {
    navigator.clipboard.writeText(text);
    message.success(`${label} copied to clipboard`);
  };

  const getBasicAuthHeader = () => {
    const keyId = settings?.gateway.key_id || 'rzp_test_demo12345678';
    const secret = 'sample_secret';
    const encoded = btoa(`${keyId}:${secret}`);
    return `Basic ${encoded}`;
  };

  const handleSaveAISettings = async (values: any) => {
    setSaving(true);
    try {
      await updateAccountSettings({
        model_provider: values.active_provider,
        gemini_api_key: values.gemini_api_key,
        gemini_model: values.gemini_model,
        openai_api_key: values.openai_api_key,
        openai_model: values.openai_model,
        ollama_model: values.ollama_model,
        ollama_base_url: values.ollama_base_url,
      });
      message.success('AI settings saved');
      await loadAll();
    } catch (err: any) {
      message.error(err.message || 'Failed to save AI settings');
    } finally {
      setSaving(false);
    }
  };

  const handleSavePolicySettings = async (values: any) => {
    setSaving(true);
    try {
      await updateAccountSettings({
        payment_execution_mode: values.payment_execution_mode,
        human_review_threshold_inr: values.human_review_threshold_inr,
        min_confidence_threshold: (values.min_confidence_threshold || 70) / 100,
        max_contact_attempts: values.max_contact_attempts,
        min_hours_between_contacts: values.min_hours_between_contacts,
        voice_enabled: values.voice_enabled,
      });
      message.success('Policies updated');
      await loadAll();
    } catch (err: any) {
      message.error(err.message || 'Failed to update policies');
    } finally {
      setSaving(false);
    }
  };

  const handleToggleKillSwitch = async (targetActive: boolean) => {
    try {
      await toggleKillSwitch(targetActive, killSwitchReason || 'Developer override via Settings');
      message.warning(`Kill-Switch ${targetActive ? 'ACTIVATED' : 'DEACTIVATED'}`);
      setIsKillSwitchModalOpen(false);
      setKillSwitchReason('');
      await loadAll();
    } catch (err: any) {
      message.error(err.message || 'Failed to toggle kill switch');
    }
  };

  const handleRunModelTest = async () => {
    setTestingModel(true);
    setModelTestResult(null);
    try {
      const res = await testAIModelInference({
        error_code: testErrorCode,
        amount_inr: testAmount,
        customer_tier: 'vip',
      });
      setModelTestResult(res);
      message.success(`Inference: ${res.latency_ms} ms`);
    } catch (err: any) {
      message.error(err.message || 'Inference test failed');
    } finally {
      setTestingModel(false);
    }
  };

  const handleRunWebhookSimulation = async () => {
    setTestingWebhook(true);
    setWebhookTestResult(null);
    try {
      const res = await simulateTestWebhook();
      setWebhookTestResult(res);
      message.success(`Webhook: ${res.latency_ms} ms`);
    } catch (err: any) {
      message.error(err.message || 'Webhook simulation failed');
    } finally {
      setTestingWebhook(false);
    }
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-12">
      {/* Developer Header */}
      <div className="bg-slate-900 text-white p-5 rounded-xl border border-slate-800 shadow-md flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <span className="p-2 bg-blue-600/30 border border-blue-500/40 rounded-lg text-blue-400">
            <CodeOutlined className="text-xl" />
          </span>
          <div className="flex items-center gap-2">
            <Title level={3} style={{ margin: 0, color: '#ffffff' }}>
              Developer Settings & API Controls
            </Title>
            <Tag color="cyan" className="font-mono text-xs font-bold">
              DEV POV
            </Tag>
            <Tag color="blue" className="font-mono text-xs">
              {settings?.gateway.execution_mode === 'razorpay_test' ? 'SANDBOX API' : 'SYNTHETIC MODE'}
            </Tag>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <Button
            ghost
            icon={<ReloadOutlined />}
            onClick={loadAll}
            loading={loading}
            className="text-slate-200 border-slate-700 hover:text-white"
          >
            Sync Config
          </Button>
          <Button
            type="primary"
            href="https://dashboard.razorpay.com/app/keys"
            target="_blank"
            rel="noopener noreferrer"
            icon={<GlobalOutlined />}
            style={{ background: '#0052cc' }}
          >
            Razorpay API Keys Console
          </Button>
        </div>
      </div>

      {/* Developer Navigation Tabs */}
      <Card bodyStyle={{ padding: '0 24px 24px 24px' }}>
        <Tabs
          activeKey={activeTab}
          onChange={setActiveTab}
          size="large"
          items={[
            // --- TAB 1: API Keys & Auth ---
            {
              key: 'apikeys',
              label: (
                <span className="flex items-center gap-2 font-medium">
                  <KeyOutlined /> API Keys & Credentials
                </span>
              ),
              children: (
                <div className="pt-4 space-y-6">
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <div className="p-4 bg-slate-50 border border-slate-200 rounded-lg">
                      <div className="text-xs text-slate-400 font-bold uppercase">Active Key ID</div>
                      <div className="text-sm font-mono font-bold text-slate-800 mt-1">
                        {settings?.gateway.key_id || 'rzp_test_...'}
                      </div>
                      <div className="text-[11px] text-emerald-600 mt-1 flex items-center gap-1">
                        <CheckCircleFilled /> Test Key Authorized
                      </div>
                    </div>

                    <div className="p-4 bg-slate-50 border border-slate-200 rounded-lg">
                      <div className="text-xs text-slate-400 font-bold uppercase">Key Secret Status</div>
                      <div className="text-sm font-semibold text-slate-800 mt-1">
                        {settings?.gateway.key_secret_configured ? 'Configured & Encrypted' : 'Not Set'}
                      </div>
                    </div>

                    <div className="p-4 bg-slate-50 border border-slate-200 rounded-lg">
                      <div className="text-xs text-slate-400 font-bold uppercase">Autopilot Ingestion URL</div>
                      <div className="text-sm font-mono text-slate-800 mt-1 truncate">
                        http://127.0.0.1:8000
                      </div>
                      <div className="text-[11px] text-blue-600 mt-1">FastAPI ASGI Server (Online)</div>
                    </div>
                  </div>

                  {/* Credentials Section */}
                  <div className="p-6 bg-slate-900 text-slate-100 rounded-xl border border-slate-800 space-y-5 font-mono text-xs">
                    <div className="flex items-center justify-between pb-3 border-b border-slate-800">
                      <div className="font-bold text-sm text-slate-200 flex items-center gap-2">
                        <KeyOutlined className="text-blue-400" /> Gateway Authentication Credentials
                      </div>
                      <Tag color="cyan">Sandbox Environment</Tag>
                    </div>

                    <div className="space-y-4">
                      <div>
                        <div className="text-slate-400 mb-1 flex items-center justify-between">
                          <span>RAZORPAY_KEY_ID</span>
                          <Button
                            type="text"
                            size="small"
                            className="text-slate-300 hover:text-white"
                            icon={<CopyOutlined />}
                            onClick={() => copyToClipboard(settings?.gateway.key_id || '', 'Key ID')}
                          >
                            Copy Key ID
                          </Button>
                        </div>
                        <Input
                          value={settings?.gateway.key_id || 'rzp_test_...'}
                          readOnly
                          className="bg-slate-950 border-slate-800 text-emerald-400 font-mono text-xs"
                        />
                      </div>

                      <div>
                        <div className="text-slate-400 mb-1 flex items-center justify-between">
                          <span>RAZORPAY_KEY_SECRET</span>
                          <Button
                            type="text"
                            size="small"
                            className="text-slate-300 hover:text-white"
                            icon={<CopyOutlined />}
                            onClick={() => copyToClipboard('sample_test_secret', 'Key Secret')}
                          >
                            Copy Secret
                          </Button>
                        </div>
                        <div className="flex gap-2">
                          <Input.Password
                            value={showKeySecret ? (settings?.gateway.key_secret_configured ? 'sample_test_key_secret_configured' : '') : '••••••••••••••••••••••••'}
                            readOnly
                            visibilityToggle={{
                              visible: showKeySecret,
                              onVisibleChange: setShowKeySecret,
                            }}
                            className="bg-slate-950 border-slate-800 text-slate-200 font-mono text-xs flex-1"
                          />
                        </div>
                      </div>

                      <div>
                        <div className="text-slate-400 mb-1 flex items-center justify-between">
                          <span>HTTP BASIC AUTH HEADER</span>
                          <Button
                            type="text"
                            size="small"
                            className="text-slate-300 hover:text-white"
                            icon={<CopyOutlined />}
                            onClick={() => copyToClipboard(`Authorization: ${getBasicAuthHeader()}`, 'Basic Auth Header')}
                          >
                            Copy Header
                          </Button>
                        </div>
                        <Input
                          value={`Authorization: ${getBasicAuthHeader()}`}
                          readOnly
                          className="bg-slate-950 border-slate-800 text-blue-300 font-mono text-xs"
                        />
                      </div>
                    </div>
                  </div>
                </div>
              ),
            },

            // --- TAB 2: Webhooks & Ingestion ---
            {
              key: 'webhooks',
              label: (
                <span className="flex items-center gap-2 font-medium">
                  <ApiOutlined /> Webhooks & Signature Verification
                </span>
              ),
              children: (
                <div className="pt-4 space-y-6">
                  {/* Webhook Endpoint Config */}
                  <div className="p-5 bg-slate-50 border border-slate-200 rounded-xl space-y-4">
                    <div className="flex items-center justify-between">
                      <div className="font-bold text-slate-800 text-sm">Webhook Ingestion Endpoint</div>
                      <Tag color="green">HMAC-SHA256 ENFORCED</Tag>
                    </div>

                    <div className="flex items-center gap-2">
                      <Input
                        value={settings?.merchant.webhook_url || 'http://127.0.0.1:8000/webhooks/razorpay'}
                        readOnly
                        className="font-mono text-xs bg-white"
                      />
                      <Button
                        icon={<CopyOutlined />}
                        onClick={() =>
                          copyToClipboard(
                            settings?.merchant.webhook_url || 'http://127.0.0.1:8000/webhooks/razorpay',
                            'Webhook URL'
                          )
                        }
                      >
                        Copy URL
                      </Button>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-2">
                      <div className="p-3 bg-white rounded border border-slate-200">
                        <div className="text-xs text-slate-400">Webhook Secret (X-Razorpay-Signature)</div>
                        <div className="font-mono text-xs font-bold text-slate-800 mt-1">
                          {settings?.gateway.webhook_secret_masked || '••••••••'}
                        </div>
                      </div>
                      <div className="p-3 bg-white rounded border border-slate-200">
                        <div className="text-xs text-slate-400">Signature Algorithm</div>
                        <div className="font-mono text-xs font-bold text-slate-800 mt-1">
                          HMAC-SHA256 (Hex Digest)
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Subscribed Events */}
                  <div className="p-5 bg-slate-50 border border-slate-200 rounded-xl space-y-3">
                    <div className="font-bold text-slate-800 text-sm">Subscribed Events</div>
                    <div className="flex flex-wrap gap-2">
                      {[
                        'payment.failed',
                        'payment.captured',
                        'payment_link.paid',
                        'subscription.charged',
                        'subscription.cancelled',
                        'invoice.expired',
                      ].map((evt) => (
                        <Tag key={evt} color="geekblue" className="px-3 py-1 font-mono text-xs rounded-md">
                          <CheckCircleFilled className="mr-1 text-emerald-500" /> {evt}
                        </Tag>
                      ))}
                    </div>
                  </div>

                  {/* Developer Webhook Simulator */}
                  <div className="p-6 bg-slate-900 text-slate-100 rounded-xl border border-slate-800 space-y-4">
                    <div className="flex items-center justify-between">
                      <div className="font-bold text-sm text-slate-200 flex items-center gap-2">
                        <ThunderboltOutlined className="text-amber-400" /> Webhook Simulator & Latency Benchmark
                      </div>
                      <Button
                        type="primary"
                        icon={<SendOutlined />}
                        onClick={handleRunWebhookSimulation}
                        loading={testingWebhook}
                        style={{ background: '#0052cc' }}
                      >
                        Dispatch Test Event
                      </Button>
                    </div>

                    {webhookTestResult && (
                      <div className="p-4 bg-slate-950 rounded-lg border border-slate-800 space-y-2 text-xs font-mono">
                        <div className="flex items-center justify-between text-emerald-400">
                          <span>Status: {webhookTestResult.status.toUpperCase()}</span>
                          <span className="text-cyan-400">Latency: {webhookTestResult.latency_ms} ms</span>
                        </div>
                        <div className="text-slate-400">
                          Event ID: <span className="text-slate-200">{webhookTestResult.event_id}</span>
                        </div>
                        <div className="text-slate-400">
                          Payment ID: <span className="text-slate-200">{webhookTestResult.payment_id}</span>
                        </div>
                        <div className="text-slate-400">
                          HMAC Signature: <span className="text-amber-300">{webhookTestResult.signature_computed}</span>
                        </div>
                        <div className="text-slate-400">
                          Verification: <Tag color="success">{webhookTestResult.verification_status}</Tag>
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              ),
            },

            // --- TAB 3: AI Inference Ops ---
            {
              key: 'aimodels',
              label: (
                <span className="flex items-center gap-2 font-medium">
                  <RobotOutlined /> AI Inference & LLM Ops
                </span>
              ),
              children: (
                <div className="pt-4 space-y-6">
                  <Form form={form} layout="vertical" onFinish={handleSaveAISettings} className="space-y-6">
                    <div className="p-6 bg-slate-50 rounded-xl border border-slate-200 space-y-6">
                      <Row gutter={[24, 24]}>
                        <Col span={24} md={12}>
                          <Form.Item
                            name="active_provider"
                            label={<span className="font-semibold text-slate-700">Active AI Inference Provider</span>}
                          >
                            <Select size="large">
                              <Option value="openai">OpenAI (GPT-4o / GPT-4o-mini)</Option>
                              <Option value="gemini">Google Gemini (gemini-3.7-flash / Pro)</Option>
                              <Option value="ollama">Ollama Local (qwen3:8b / Llama 3)</Option>
                              <Option value="fake">Deterministic Heuristic Mock (Offline Testing)</Option>
                            </Select>
                          </Form.Item>
                        </Col>

                        <Col span={24} md={12}>
                          <div className="p-4 bg-blue-50 border border-blue-200 rounded-lg text-xs space-y-1">
                            <div className="font-bold text-blue-900 flex items-center gap-1.5">
                              <ThunderboltOutlined /> Active Provider Status
                            </div>
                            <div className="text-blue-800">
                              Currently routing to: <Text strong className="uppercase">{settings?.ai_model.active_provider}</Text>
                            </div>
                          </div>
                        </Col>
                      </Row>

                      <Divider className="text-xs font-bold uppercase text-slate-400">
                        Provider Credentials & Endpoints
                      </Divider>

                      <Row gutter={[24, 24]}>
                        {/* OpenAI Config */}
                        <Col span={24} md={12}>
                          <Card title="OpenAI Configuration" size="small" className="border-slate-200">
                            <Form.Item name="openai_model" label="Model Identifier">
                              <Input placeholder="gpt-4o-mini" />
                            </Form.Item>
                            <Form.Item
                              name="openai_api_key"
                              label="OpenAI API Key"
                            >
                              <Input.Password placeholder="sk-proj-..." />
                            </Form.Item>
                          </Card>
                        </Col>

                        {/* Gemini Config */}
                        <Col span={24} md={12}>
                          <Card title="Google Gemini Configuration" size="small" className="border-slate-200">
                            <Form.Item name="gemini_model" label="Model Identifier">
                              <Input placeholder="gemini-3.7-flash" />
                            </Form.Item>
                            <Form.Item
                              name="gemini_api_key"
                              label="Gemini API Key"
                            >
                              <Input.Password placeholder="AIzaSy..." />
                            </Form.Item>
                          </Card>
                        </Col>

                        {/* Ollama Config */}
                        <Col span={24} md={12}>
                          <Card title="Ollama Local LLM Configuration" size="small" className="border-slate-200">
                            <Form.Item name="ollama_base_url" label="Base URL">
                              <Input placeholder="http://localhost:11434" />
                            </Form.Item>
                            <Form.Item name="ollama_model" label="Model Name">
                              <Input placeholder="qwen3:8b" />
                            </Form.Item>
                          </Card>
                        </Col>
                      </Row>
                    </div>

                    <div className="flex justify-end">
                      <Button
                        type="primary"
                        htmlType="submit"
                        icon={<SaveOutlined />}
                        loading={saving}
                        size="large"
                        style={{ background: '#0052cc' }}
                      >
                        Save Model Configuration
                      </Button>
                    </div>
                  </Form>

                  {/* Developer LLM Playground */}
                  <div className="p-6 bg-slate-900 text-slate-100 rounded-xl border border-slate-800 space-y-4">
                    <div className="flex items-center justify-between">
                      <div className="font-bold text-sm text-slate-200 flex items-center gap-2">
                        <ExperimentOutlined className="text-purple-400" /> AI Reasoning Playground & Benchmark
                      </div>
                      <Button
                        type="primary"
                        icon={<ThunderboltOutlined />}
                        onClick={handleRunModelTest}
                        loading={testingModel}
                        style={{ background: '#7c3aed' }}
                      >
                        Test Model Inference
                      </Button>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div>
                        <div className="text-xs text-slate-400 mb-1">Simulated Error Code</div>
                        <Select
                          value={testErrorCode}
                          onChange={setTestErrorCode}
                          className="w-full"
                          options={[
                            { value: 'BAD_REQUEST_PAYMENT_TIMED_OUT', label: 'BAD_REQUEST_PAYMENT_TIMED_OUT (UPI / Bank)' },
                            { value: 'GATEWAY_ERROR_ISSUER_DOWN', label: 'GATEWAY_ERROR_ISSUER_DOWN (HDFC Bank)' },
                            { value: 'BAD_REQUEST_INSUFFICIENT_FUNDS', label: 'BAD_REQUEST_INSUFFICIENT_FUNDS' },
                            { value: 'BAD_REQUEST_PAYMENT_DECLINED_BY_BANK', label: 'BAD_REQUEST_PAYMENT_DECLINED_BY_BANK' },
                          ]}
                        />
                      </div>
                      <div>
                        <div className="text-xs text-slate-400 mb-1">Transaction Amount (INR)</div>
                        <InputNumber
                          value={testAmount}
                          onChange={(val) => setTestAmount(val || 4999)}
                          prefix="₹"
                          className="w-full"
                        />
                      </div>
                    </div>

                    {modelTestResult && (
                      <div className="p-4 bg-slate-950 rounded-lg border border-slate-800 space-y-2 text-xs font-mono">
                        <div className="flex items-center justify-between">
                          <span className="text-emerald-400">Provider: {modelTestResult.provider} ({modelTestResult.model})</span>
                          <span className="text-cyan-400 font-bold">Inference Latency: {modelTestResult.latency_ms} ms</span>
                        </div>
                        <pre className="text-slate-200 bg-slate-900 p-3 rounded border border-slate-800 overflow-x-auto text-[11px] whitespace-pre-wrap">
                          {typeof modelTestResult.raw_output === 'object'
                            ? JSON.stringify(modelTestResult.raw_output, null, 2)
                            : modelTestResult.raw_output}
                        </pre>
                      </div>
                    )}
                  </div>
                </div>
              ),
            },

            // --- TAB 4: SDKs & Code Snippets ---
            {
              key: 'sdk',
              label: (
                <span className="flex items-center gap-2 font-medium">
                  <CodeOutlined /> SDKs & Code Quickstart
                </span>
              ),
              children: (
                <div className="pt-4 space-y-6">
                  <div className="flex items-center justify-between">
                    <div className="font-bold text-slate-800 text-sm">Integration Quickstart</div>
                    <Radio.Group
                      value={selectedSdk}
                      onChange={(e) => setSelectedSdk(e.target.value)}
                      optionType="button"
                      buttonStyle="solid"
                    >
                      <Radio.Button value="python">Python</Radio.Button>
                      <Radio.Button value="nodejs">Node.js</Radio.Button>
                      <Radio.Button value="curl">cURL / HTTP</Radio.Button>
                    </Radio.Group>
                  </div>

                  {selectedSdk === 'python' && (
                    <div className="p-5 bg-slate-950 text-slate-200 rounded-xl font-mono text-xs space-y-3 border border-slate-800">
                      <div className="flex items-center justify-between text-slate-400 pb-2 border-b border-slate-800">
                        <span>python_recovery_agent.py</span>
                        <Button
                          type="text"
                          size="small"
                          className="text-slate-300 hover:text-white"
                          icon={<CopyOutlined />}
                          onClick={() =>
                            copyToClipboard(
                              `import razorpay
import requests

# 1. Initialize Razorpay Gateway Client
client = razorpay.Client(auth=("${settings?.gateway.key_id || 'rzp_test_...'}", "YOUR_KEY_SECRET"))

# 2. Ingest failed payment into Autonomous Recovery Engine
payload = {
    "payment_id": "pay_test_983214",
    "amount": 4999.0,
    "error_code": "BAD_REQUEST_PAYMENT_TIMED_OUT",
    "customer_email": "customer@example.com",
    "customer_phone": "+919876543210"
}
res = requests.post("http://127.0.0.1:8000/cases/initiate", json=payload)
print("Recovery Plan:", res.json())`,
                              'Python Code'
                            )
                          }
                        >
                          Copy
                        </Button>
                      </div>
                      <pre className="text-emerald-400 overflow-x-auto">{`import razorpay
import requests

# 1. Initialize Razorpay Gateway Client
client = razorpay.Client(auth=("${settings?.gateway.key_id || 'rzp_test_...'}", "YOUR_KEY_SECRET"))

# 2. Ingest failed payment into Autonomous Recovery Engine
payload = {
    "payment_id": "pay_test_983214",
    "amount": 4999.0,
    "error_code": "BAD_REQUEST_PAYMENT_TIMED_OUT",
    "customer_email": "customer@example.com",
    "customer_phone": "+919876543210"
}
res = requests.post("http://127.0.0.1:8000/cases/initiate", json=payload)
print("Recovery Plan:", res.json())`}</pre>
                    </div>
                  )}

                  {selectedSdk === 'nodejs' && (
                    <div className="p-5 bg-slate-950 text-slate-200 rounded-xl font-mono text-xs space-y-3 border border-slate-800">
                      <div className="flex items-center justify-between text-slate-400 pb-2 border-b border-slate-800">
                        <span>webhook_handler.js</span>
                        <Button
                          type="text"
                          size="small"
                          className="text-slate-300 hover:text-white"
                          icon={<CopyOutlined />}
                          onClick={() =>
                            copyToClipboard(
                              `const crypto = require('crypto');
const express = require('express');
const app = express();

app.post('/webhooks/razorpay', express.raw({ type: 'application/json' }), (req, res) => {
  const secret = process.env.RAZORPAY_WEBHOOK_SECRET;
  const signature = req.headers['x-razorpay-signature'];

  const expectedSignature = crypto
    .createHmac('sha256', secret)
    .update(req.body)
    .digest('hex');

  if (signature === expectedSignature) {
    console.log('Valid Webhook Event:', JSON.parse(req.body));
    return res.status(200).json({ status: 'ok' });
  }
  return res.status(400).send('Invalid signature');
});`,
                              'Node.js Webhook Code'
                            )
                          }
                        >
                          Copy
                        </Button>
                      </div>
                      <pre className="text-cyan-400 overflow-x-auto">{`const crypto = require('crypto');
const express = require('express');
const app = express();

app.post('/webhooks/razorpay', express.raw({ type: 'application/json' }), (req, res) => {
  const secret = process.env.RAZORPAY_WEBHOOK_SECRET;
  const signature = req.headers['x-razorpay-signature'];

  const expectedSignature = crypto
    .createHmac('sha256', secret)
    .update(req.body)
    .digest('hex');

  if (signature === expectedSignature) {
    console.log('Valid Webhook Event:', JSON.parse(req.body));
    return res.status(200).json({ status: 'ok' });
  }
  return res.status(400).send('Invalid signature');
});`}</pre>
                    </div>
                  )}

                  {selectedSdk === 'curl' && (
                    <div className="p-5 bg-slate-950 text-slate-200 rounded-xl font-mono text-xs space-y-3 border border-slate-800">
                      <div className="flex items-center justify-between text-slate-400 pb-2 border-b border-slate-800">
                        <span>curl_examples.sh</span>
                        <Button
                          type="text"
                          size="small"
                          className="text-slate-300 hover:text-white"
                          icon={<CopyOutlined />}
                          onClick={() =>
                            copyToClipboard(
                              `# 1. Fetch Real-Time Recovery Metrics
curl -X GET http://127.0.0.1:8000/metrics/summary

# 2. Query AI Copilot
curl -X POST http://127.0.0.1:8000/copilot/chat \\
  -H "Content-Type: application/json" \\
  -d '{"message": "What is our current recovery rate for UPI failures?"}'`,
                              'cURL Commands'
                            )
                          }
                        >
                          Copy
                        </Button>
                      </div>
                      <pre className="text-amber-400 overflow-x-auto">{`# 1. Fetch Real-Time Recovery Metrics
curl -X GET http://127.0.0.1:8000/metrics/summary

# 2. Query AI Copilot
curl -X POST http://127.0.0.1:8000/copilot/chat \\
  -H "Content-Type: application/json" \\
  -d '{"message": "What is our current recovery rate for UPI failures?"}'`}</pre>
                    </div>
                  )}
                </div>
              ),
            },

            // --- TAB 5: Safety Guardrails & Policies ---
            {
              key: 'policies',
              label: (
                <span className="flex items-center gap-2 font-medium">
                  <SafetyCertificateOutlined /> Guardrails & Safety Policies
                </span>
              ),
              children: (
                <div className="pt-4 space-y-6">
                  {/* Emergency Kill Switch Control */}
                  <div className={`p-6 rounded-xl border ${settings?.gateway.kill_switch_active ? 'bg-red-50 border-red-300' : 'bg-slate-50 border-slate-200'}`}>
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2 font-bold text-base text-slate-800">
                        {settings?.gateway.kill_switch_active ? (
                          <LockOutlined className="text-red-500 text-lg" />
                        ) : (
                          <UnlockOutlined className="text-emerald-500 text-lg" />
                        )}
                        Autonomous Execution Kill-Switch
                      </div>

                      <Switch
                        checked={settings?.gateway.kill_switch_active}
                        onChange={(checked) => {
                          if (checked) {
                            setIsKillSwitchModalOpen(true);
                          } else {
                            handleToggleKillSwitch(false);
                          }
                        }}
                        checkedChildren="ACTIVE"
                        unCheckedChildren="OFF"
                        className={settings?.gateway.kill_switch_active ? 'bg-red-600' : ''}
                      />
                    </div>
                  </div>

                  {/* Policy Parameters Form */}
                  <Form form={form} layout="vertical" onFinish={handleSavePolicySettings} className="space-y-6">
                    <div className="p-6 bg-slate-50 rounded-xl border border-slate-200">
                      <Row gutter={[24, 24]}>
                        <Col span={24} md={12}>
                          <Form.Item
                            name="payment_execution_mode"
                            label={<span className="font-semibold text-slate-700">Execution Mode</span>}
                          >
                            <Select size="large">
                              <Option value="synthetic">Synthetic Mode (Offline Simulation)</Option>
                              <Option value="razorpay_test">Razorpay Test Mode (rzp_test_ API)</Option>
                              <Option value="production" disabled>Production Mode (Dual Locks Required)</Option>
                            </Select>
                          </Form.Item>
                        </Col>

                        <Col span={24} md={12}>
                          <Form.Item
                            name="human_review_threshold_inr"
                            label={<span className="font-semibold text-slate-700">High-Value Human Review Threshold (INR)</span>}
                          >
                            <InputNumber size="large" className="w-full" prefix="₹" min={100} max={1000000} />
                          </Form.Item>
                        </Col>

                        <Col span={24} md={12}>
                          <Form.Item
                            name="min_confidence_threshold"
                            label={<span className="font-semibold text-slate-700">Minimum AI Confidence Threshold (%)</span>}
                          >
                            <Slider min={50} max={99} marks={{ 50: '50%', 70: '70%', 90: '90%' }} />
                          </Form.Item>
                        </Col>

                        <Col span={24} md={12}>
                          <Form.Item
                            name="max_contact_attempts"
                            label={<span className="font-semibold text-slate-700">Max Contact Attempts</span>}
                          >
                            <InputNumber size="large" className="w-full" min={1} max={5} />
                          </Form.Item>
                        </Col>

                        <Col span={24} md={12}>
                          <Form.Item
                            name="min_hours_between_contacts"
                            label={<span className="font-semibold text-slate-700">Minimum Cooldown (Hours)</span>}
                          >
                            <InputNumber size="large" className="w-full" min={6} max={72} />
                          </Form.Item>
                        </Col>

                        <Col span={24} md={12}>
                          <Form.Item
                            name="voice_enabled"
                            label={<span className="font-semibold text-slate-700">Voice Recovery Agent</span>}
                            valuePropName="checked"
                          >
                            <Switch checkedChildren="ON" unCheckedChildren="OFF" />
                          </Form.Item>
                        </Col>
                      </Row>
                    </div>

                    <div className="flex justify-end">
                      <Button
                        type="primary"
                        htmlType="submit"
                        icon={<SaveOutlined />}
                        loading={saving}
                        size="large"
                        style={{ background: '#0052cc' }}
                      >
                        Save Safety Policies
                      </Button>
                    </div>
                  </Form>
                </div>
              ),
            },

            // --- TAB 6: System Diagnostics & Runtime ---
            {
              key: 'diagnostics',
              label: (
                <span className="flex items-center gap-2 font-medium">
                  <BugOutlined /> System Diagnostics & Logs
                </span>
              ),
              children: (
                <div className="pt-4 space-y-6">
                  {diagnostics && (
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                      <div className="p-5 bg-slate-50 border border-slate-200 rounded-xl space-y-3">
                        <div className="font-bold text-slate-800 text-sm">Runtime Environment</div>
                        <div className="space-y-2 text-xs">
                          <div className="flex justify-between py-1 border-b border-slate-200">
                            <span className="text-slate-500">Python Version</span>
                            <span className="font-mono font-bold text-slate-800">{diagnostics.runtime.python_version}</span>
                          </div>
                          <div className="flex justify-between py-1 border-b border-slate-200">
                            <span className="text-slate-500">Framework</span>
                            <span className="font-mono text-slate-800">{diagnostics.runtime.framework}</span>
                          </div>
                          <div className="flex justify-between py-1 border-b border-slate-200">
                            <span className="text-slate-500">Database Engine</span>
                            <span className="font-mono text-slate-800">{diagnostics.runtime.database_engine}</span>
                          </div>
                          <div className="flex justify-between py-1">
                            <span className="text-slate-500">Worker Queue</span>
                            <span className="font-mono text-slate-800">{diagnostics.runtime.worker_queue}</span>
                          </div>
                        </div>
                      </div>

                      <div className="p-5 bg-slate-50 border border-slate-200 rounded-xl space-y-3">
                        <div className="font-bold text-slate-800 text-sm">API Endpoints</div>
                        <div className="space-y-2 text-xs font-mono">
                          {Object.entries(diagnostics.endpoints).map(([key, url]: any) => (
                            <div key={key} className="flex justify-between items-center py-1 border-b border-slate-200">
                              <span className="text-slate-500 uppercase">{key}</span>
                              <a href={url} target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline truncate max-w-[200px]">
                                {url}
                              </a>
                            </div>
                          ))}
                        </div>
                      </div>
                    </div>
                  )}

                  <div className="p-5 bg-slate-900 text-slate-200 rounded-xl border border-slate-800 space-y-3">
                    <div className="flex items-center justify-between">
                      <div className="font-bold text-sm text-slate-200 flex items-center gap-2">
                        <FileTextOutlined className="text-blue-400" /> Interactive OpenAPI / Swagger Docs
                      </div>
                      <Button
                        type="primary"
                        href="http://127.0.0.1:8000/docs"
                        target="_blank"
                        rel="noopener noreferrer"
                        icon={<GlobalOutlined />}
                        style={{ background: '#0052cc' }}
                      >
                        Open Swagger UI (/docs)
                      </Button>
                    </div>
                  </div>
                </div>
              ),
            },
          ]}
        />
      </Card>

      {/* Kill Switch Confirmation Modal */}
      <Modal
        title={
          <div className="flex items-center gap-2 text-red-600">
            <ExclamationCircleOutlined /> Activate Emergency Kill-Switch?
          </div>
        }
        open={isKillSwitchModalOpen}
        onOk={() => handleToggleKillSwitch(true)}
        onCancel={() => setIsKillSwitchModalOpen(false)}
        okText="Activate Kill-Switch"
        okButtonProps={{ danger: true }}
      >
        <div className="space-y-3 py-2 text-xs text-slate-600">
          <div>
            <div className="font-semibold text-slate-700 mb-1">Reason:</div>
            <Input
              placeholder="e.g., Upstream bank outage, security inspection"
              value={killSwitchReason}
              onChange={(e) => setKillSwitchReason(e.target.value)}
            />
          </div>
        </div>
      </Modal>
    </div>
  );
}
