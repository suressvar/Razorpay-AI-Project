import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Row,
  Col,
  Button,
  Space,
  Tag,
  Typography,
  message,
  Timeline,
  Alert,
  Tooltip as AntTooltip,
  Dropdown,
  MenuProps,
} from 'antd';
import {
  SyncOutlined,
  ThunderboltOutlined,
  CheckCircleOutlined,
  DollarOutlined,
  UserSwitchOutlined,
  ArrowRightOutlined,
  RobotOutlined,
  SafetyCertificateOutlined,
  FieldTimeOutlined,
  DownloadOutlined,
  FileExcelOutlined,
  FileTextOutlined,
  PlayCircleOutlined,
  ShoppingCartOutlined,
  CreditCardOutlined,
  DownOutlined,
  CustomerServiceOutlined,
  ApiOutlined,
} from '@ant-design/icons';
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts';
import { fetchMetricsSummary, seedDemoData, simulateWebhook, fetchCases } from '../api';
import { SummaryMetrics } from '../types';
import { Card, KpiCard, PageHeader, Spinner, ErrorState } from '../components/Card';
import { InteractiveDemoTour } from '../components/InteractiveDemoTour';

const { Text } = Typography;

const CHART_DATA = [
  { time: 'Day 1', autopilot: 28, baseline: 12 },
  { time: 'Day 2', autopilot: 45, baseline: 18 },
  { time: 'Day 3', autopilot: 62, baseline: 24 },
  { time: 'Day 4', autopilot: 55, baseline: 20 },
  { time: 'Day 5', autopilot: 78, baseline: 28 },
  { time: 'Day 6', autopilot: 89, baseline: 31 },
  { time: 'Day 7', autopilot: 110, baseline: 36 },
];

function fmtInr(n: number) {
  return `₹${new Intl.NumberFormat('en-IN', { maximumFractionDigits: 0 }).format(n)}`;
}

export default function Overview() {
  const navigate = useNavigate();
  const [metrics, setMetrics] = useState<SummaryMetrics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [seeding, setSeeding] = useState(false);
  const [simulating, setSimulating] = useState(false);
  const [isTourOpen, setIsTourOpen] = useState(false);

  const load = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await fetchMetricsSummary();
      setMetrics(data);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const handleSeed = async () => {
    setSeeding(true);
    try {
      const res = await seedDemoData(50, 42);
      message.success(`Successfully seeded ${res.seeded_count} payment recovery cases`);
      await load();
    } catch (e: any) {
      message.error(`Seeding failed: ${e.message}`);
    } finally {
      setSeeding(false);
    }
  };

  const handleSimulate = async (category: string = 'INSUFFICIENT_FUNDS', amount: number = 3499) => {
    setSimulating(true);
    try {
      await simulateWebhook('payment.failed', category, amount);
      message.success(`Simulated webhook: ${category} (₹${amount.toLocaleString('en-IN')}) processed by AI Autopilot`);
      await load();
    } catch (e: any) {
      message.error(`Simulation failed: ${e.message}`);
    } finally {
      setSimulating(false);
    }
  };

  const simulateMenuItems: MenuProps['items'] = [
    {
      key: 'upi',
      label: 'UPI / Bank Timeout (₹3,499)',
      icon: <DollarOutlined className="text-blue-600" />,
      onClick: () => handleSimulate('BANK_TIMEOUT', 3499),
    },
    {
      key: 'cart',
      label: 'Checkout Cart Abandonment (₹2,899)',
      icon: <ShoppingCartOutlined className="text-amber-600" />,
      onClick: () => handleSimulate('CHECKOUT_ABANDONED', 2899),
    },
    {
      key: 'invoice',
      label: 'B2B Overdue Invoice (₹15,000)',
      icon: <FileTextOutlined className="text-purple-600" />,
      onClick: () => handleSimulate('OVERDUE_RECEIVABLE', 15000),
    },
    {
      key: 'card',
      label: 'Expired Subscription Card (₹4,999)',
      icon: <CreditCardOutlined className="text-red-600" />,
      onClick: () => handleSimulate('EXPIRED_CARD', 4999),
    },
  ];

  const handleExportReport = async (format: 'csv' | 'json') => {
    try {
      const cases = await fetchCases(undefined, undefined, 200);
      if (format === 'csv') {
        const headers = ['Case ID', 'Customer Name', 'Email', 'Phone', 'Amount (INR)', 'Failure Category', 'Status', 'Created At'];
        const rows = cases.map((c) => [
          c.case_id,
          `"${c.context.customer_name || c.context.customer_id}"`,
          `"${c.context.customer_email}"`,
          `"${c.context.customer_phone || ''}"`,
          c.context.amount_inr,
          `"${c.context.failure_category}"`,
          c.status,
          `"${c.created_at}"`,
        ]);
        const csvContent = 'data:text/csv;charset=utf-8,' + [headers.join(','), ...rows.map((r) => r.join(','))].join('\n');
        const encodedUri = encodeURI(csvContent);
        const link = document.createElement('a');
        link.setAttribute('href', encodedUri);
        link.setAttribute('download', `razorpay_revenue_recovery_report_${Date.now()}.csv`);
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        message.success('Executive Recovery CSV Report downloaded');
      } else {
        const jsonString = `data:text/json;charset=utf-8,${encodeURIComponent(
          JSON.stringify({ summary: metrics, cases }, null, 2)
        )}`;
        const link = document.createElement('a');
        link.setAttribute('href', jsonString);
        link.setAttribute('download', `razorpay_recovery_dataset_${Date.now()}.json`);
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        message.success('Recovery JSON Package downloaded');
      }
    } catch (e: any) {
      message.error(`Export failed: ${e.message}`);
    }
  };

  const exportMenuItems: MenuProps['items'] = [
    {
      key: 'csv',
      label: 'Download CSV Summary',
      icon: <FileExcelOutlined className="text-emerald-600" />,
      onClick: () => handleExportReport('csv'),
    },
    {
      key: 'json',
      label: 'Export Complete JSON Dataset',
      icon: <FileTextOutlined className="text-blue-600" />,
      onClick: () => handleExportReport('json'),
    },
    {
      key: 'print',
      label: 'Print Executive Summary',
      icon: <DownloadOutlined className="text-purple-600" />,
      onClick: () => window.print(),
    },
  ];

  const getActorTag = (actor: string) => {
    switch (actor) {
      case 'AI':
        return <Tag color="blue" icon={<RobotOutlined />}>AI Agent</Tag>;
      case 'POLICY':
        return <Tag color="purple" icon={<SafetyCertificateOutlined />}>Policy</Tag>;
      case 'EXECUTOR':
        return <Tag color="green" icon={<ThunderboltOutlined />}>Executor</Tag>;
      case 'HUMAN':
        return <Tag color="orange" icon={<UserSwitchOutlined />}>Human</Tag>;
      default:
        return <Tag color="default">{actor}</Tag>;
    }
  };

  return (
    <div>
      <PageHeader
        title="Payment Recovery Dashboard"
        actions={
          <Space>
            {/* Live workflow Button */}
            <button
              onClick={() => setIsTourOpen(true)}
              className="flex items-center gap-2 px-3.5 py-1.5 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white rounded-lg text-xs font-bold shadow-md shadow-blue-500/20 transition-all cursor-pointer select-none border-none"
              id="overview-live-workflow-btn"
            >
              <PlayCircleOutlined className="text-sm" />
              <span>Live workflow</span>
            </button>

            {/* Simulate Scenario Dropdown */}
            <Dropdown menu={{ items: simulateMenuItems }} placement="bottomRight">
              <Button
                icon={<ThunderboltOutlined />}
                loading={simulating}
                className="border-slate-300 font-semibold text-xs flex items-center rounded-lg h-[32px]"
              >
                <span>Simulate Scenario</span> <DownOutlined className="text-[10px] ml-1 text-slate-500" />
              </Button>
            </Dropdown>

            {/* Export Report Dropdown */}
            <Dropdown menu={{ items: exportMenuItems }} placement="bottomRight">
              <Button
                icon={<DownloadOutlined />}
                className="border-slate-300 font-medium"
              >
                Export Report ▼
              </Button>
            </Dropdown>

            <Button
              icon={<SyncOutlined />}
              onClick={handleSeed}
              loading={seeding}
              className="border-slate-300 font-medium"
            >
              Seed Data
            </Button>
          </Space>
        }
      />


      {loading && (
        <div className="flex justify-center items-center py-24">
          <Spinner size={32} />
        </div>
      )}

      {error && !loading && <ErrorState message={`Failed to load dashboard metrics: ${error}`} onRetry={load} />}

      {metrics && !loading && (
        <>
          {/* Top KPI Metrics Row */}
          <Row gutter={[16, 16]} className="mb-6">
            <Col xs={24} sm={12} lg={6}>
              <KpiCard
                label="Total Cases Ingested"
                value={metrics.total_cases.toLocaleString('en-IN')}
                icon={<ThunderboltOutlined />}
                trend="neutral"
                trendValue="Active webhook ingestion"
                badgeColor="#0052cc"
              />
            </Col>
            <Col xs={24} sm={12} lg={6}>
              <KpiCard
                label="Recovered Cases"
                value={metrics.recovered_cases.toLocaleString('en-IN')}
                icon={<CheckCircleOutlined />}
                trend="up"
                trendValue="+55.0% vs baseline"
                badgeColor="#10b981"
              />
            </Col>
            <Col xs={24} sm={12} lg={6}>
              <KpiCard
                label="Total Recovered (INR)"
                value={fmtInr(metrics.total_inr_recovered)}
                icon={<DollarOutlined />}
                trend="up"
                trendValue="Test mode verified"
                badgeColor="#f59e0b"
              />
            </Col>
            <Col xs={24} sm={12} lg={6}>
              <KpiCard
                label="Awaiting Human Review"
                value={metrics.awaiting_approval_count.toLocaleString('en-IN')}
                icon={<UserSwitchOutlined />}
                trend={metrics.awaiting_approval_count > 0 ? 'down' : 'neutral'}
                trendValue={metrics.awaiting_approval_count > 0 ? 'Action required' : 'Queue clear'}
                badgeColor="#8b5cf6"
              />
            </Col>
          </Row>

          {/* Charts and Live Audit Section */}
          <Row gutter={[16, 16]} className="mb-6">
            <Col xs={24} lg={16}>
              <Card
                title={<span className="font-semibold text-slate-800">Recovery Trend Analysis</span>}
              >
                <div style={{ height: 260, width: '100%' }}>
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={CHART_DATA} margin={{ top: 10, right: 20, left: -10, bottom: 0 }}>
                      <defs>
                        <linearGradient id="colorAutopilot" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#0052cc" stopOpacity={0.25} />
                          <stop offset="95%" stopColor="#0052cc" stopOpacity={0.0} />
                        </linearGradient>
                        <linearGradient id="colorBaseline" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#94a3b8" stopOpacity={0.2} />
                          <stop offset="95%" stopColor="#94a3b8" stopOpacity={0.0} />
                        </linearGradient>
                      </defs>
                      <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" vertical={false} />
                      <XAxis dataKey="time" tick={{ fill: '#64748b', fontSize: 12 }} axisLine={{ stroke: '#e2e8f0' }} tickLine={false} />
                      <YAxis tick={{ fill: '#64748b', fontSize: 12 }} axisLine={false} tickLine={false} />
                      <Tooltip
                        contentStyle={{
                          backgroundColor: '#ffffff',
                          border: '1px solid #e2e8f0',
                          borderRadius: 8,
                          boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)',
                          fontSize: 12,
                        }}
                      />
                      <Legend verticalAlign="top" align="right" height={36} iconType="circle" />
                      <Area
                        type="monotone"
                        dataKey="autopilot"
                        name="AI Autopilot"
                        stroke="#0052cc"
                        strokeWidth={2.5}
                        fill="url(#colorAutopilot)"
                      />
                      <Area
                        type="monotone"
                        dataKey="baseline"
                        name="Fixed-Rule Baseline"
                        stroke="#94a3b8"
                        strokeWidth={2}
                        strokeDasharray="4 4"
                        fill="url(#colorBaseline)"
                      />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
              </Card>
            </Col>

            <Col xs={24} lg={8}>
              <Card
                title={
                  <div className="flex items-center justify-between">
                    <span className="font-semibold text-slate-800">Live Decision Audit Stream</span>
                    <Button type="text" size="small" icon={<SyncOutlined />} onClick={load} />
                  </div>
                }
              >
                {metrics.recent_audits.length === 0 ? (
                  <div className="py-12 text-center text-slate-400 text-xs">
                    No recent audit events.
                  </div>
                ) : (
                  <div className="max-h-[260px] overflow-y-auto pr-1">
                    <Timeline
                      items={metrics.recent_audits.slice(0, 5).map((ev) => ({
                        color: ev.actor === 'AI' ? 'blue' : ev.actor === 'POLICY' ? 'purple' : 'green',
                        children: (
                          <div className="text-xs mb-2">
                            <div className="flex items-center justify-between gap-1 mb-1">
                              <span className="font-semibold text-slate-800">
                                {ev.event_type.replace(/_/g, ' ')}
                              </span>
                              <Text type="secondary" className="text-[10px]">
                                {new Date(ev.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                              </Text>
                            </div>
                            <div className="flex items-center gap-1.5">
                              {getActorTag(ev.actor)}
                              <span className="text-[11px] text-slate-500 font-mono truncate max-w-[120px]">
                                {ev.case_id}
                              </span>
                            </div>
                          </div>
                        ),
                      }))}
                    />
                  </div>
                )}
              </Card>
            </Col>
          </Row>

          {/* Quick Access Action Navigation */}
          <Row gutter={[16, 16]} className="mb-4">
            <Col xs={24} md={8}>
              <div
                onClick={() => navigate('/cases')}
                className="p-5 bg-white border border-slate-200 rounded-xl shadow-sm hover:shadow-md hover:border-blue-300 transition-all cursor-pointer group flex items-center justify-between"
              >
                <div>
                  <h4 className="font-semibold text-slate-900 m-0 group-hover:text-blue-600 transition-colors">
                    Recovery Cases
                  </h4>
                </div>
                <div className="w-8 h-8 rounded-full bg-slate-100 flex items-center justify-center text-slate-400 group-hover:bg-blue-50 group-hover:text-blue-600 transition-colors">
                  <ArrowRightOutlined />
                </div>
              </div>
            </Col>

            <Col xs={24} md={8}>
              <div
                onClick={() => navigate('/review')}
                className="p-5 bg-white border border-slate-200 rounded-xl shadow-sm hover:shadow-md hover:border-amber-300 transition-all cursor-pointer group flex items-center justify-between"
              >
                <div>
                  <h4 className="font-semibold text-slate-900 m-0 group-hover:text-amber-600 transition-colors">
                    Human Review Queue
                  </h4>
                </div>
                <div className="w-8 h-8 rounded-full bg-slate-100 flex items-center justify-center text-slate-400 group-hover:bg-amber-50 group-hover:text-amber-600 transition-colors">
                  <ArrowRightOutlined />
                </div>
              </div>
            </Col>

            <Col xs={24} md={8}>
              <div
                onClick={() => navigate('/evaluation')}
                className="p-5 bg-white border border-slate-200 rounded-xl shadow-sm hover:shadow-md hover:border-purple-300 transition-all cursor-pointer group flex items-center justify-between"
              >
                <div>
                  <h4 className="font-semibold text-slate-900 m-0 group-hover:text-purple-600 transition-colors">
                    Benchmark & Lab
                  </h4>
                </div>
                <div className="w-8 h-8 rounded-full bg-slate-100 flex items-center justify-center text-slate-400 group-hover:bg-purple-50 group-hover:text-purple-600 transition-colors">
                  <ArrowRightOutlined />
                </div>
              </div>
            </Col>
          </Row>

          <Row gutter={[16, 16]}>
            <Col xs={24} md={8}>
              <div
                onClick={() => navigate('/copilot')}
                className="p-5 bg-white border border-slate-200 rounded-xl shadow-sm hover:shadow-md hover:border-cyan-300 transition-all cursor-pointer group flex items-center justify-between"
              >
                <div>
                  <h4 className="font-semibold text-slate-900 m-0 group-hover:text-cyan-600 transition-colors">
                    AI Copilot
                  </h4>
                </div>
                <div className="w-8 h-8 rounded-full bg-slate-100 flex items-center justify-center text-slate-400 group-hover:bg-cyan-50 group-hover:text-cyan-600 transition-colors">
                  <ArrowRightOutlined />
                </div>
              </div>
            </Col>

            <Col xs={24} md={8}>
              <div
                onClick={() => navigate('/issues')}
                className="p-5 bg-white border border-slate-200 rounded-xl shadow-sm hover:shadow-md hover:border-emerald-300 transition-all cursor-pointer group flex items-center justify-between"
              >
                <div>
                  <h4 className="font-semibold text-slate-900 m-0 group-hover:text-emerald-600 transition-colors">
                    Customer Issues
                  </h4>
                </div>
                <div className="w-8 h-8 rounded-full bg-slate-100 flex items-center justify-center text-slate-400 group-hover:bg-emerald-50 group-hover:text-emerald-600 transition-colors">
                  <ArrowRightOutlined />
                </div>
              </div>
            </Col>

            <Col xs={24} md={8}>
              <div
                onClick={() => navigate('/unmatched')}
                className="p-5 bg-white border border-slate-200 rounded-xl shadow-sm hover:shadow-md hover:border-rose-300 transition-all cursor-pointer group flex items-center justify-between"
              >
                <div>
                  <h4 className="font-semibold text-slate-900 m-0 group-hover:text-rose-600 transition-colors">
                    Webhooks & Unmatched
                  </h4>
                </div>
                <div className="w-8 h-8 rounded-full bg-slate-100 flex items-center justify-center text-slate-400 group-hover:bg-rose-50 group-hover:text-rose-600 transition-colors">
                  <ArrowRightOutlined />
                </div>
              </div>
            </Col>
          </Row>
        </>
      )}

      {/* Interactive Demo Tour Modal */}
      <InteractiveDemoTour
        open={isTourOpen}
        onClose={() => setIsTourOpen(false)}
        onFinished={load}
      />
    </div>
  );
}
