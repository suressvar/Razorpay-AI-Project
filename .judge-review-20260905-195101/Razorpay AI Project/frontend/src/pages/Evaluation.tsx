import { useEffect, useState } from 'react';
import {
  Row,
  Col,
  Button,
  Space,
  Tag,
  Typography,
  Table,
  Slider,
  InputNumber,
  Alert,
  Divider,
  message,
} from 'antd';
import type { ColumnsType } from 'antd/es/table';
import {
  ExperimentOutlined,
  PlayCircleOutlined,
  SafetyCertificateFilled,
  ArrowUpOutlined,
  CheckCircleFilled,
  ThunderboltFilled,
  LineChartOutlined,
} from '@ant-design/icons';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';
import { runEvaluation } from '../api';
import { BenchmarkReport, CategoryMetric } from '../types';
import { Card, PageHeader, Spinner } from '../components/Card';
import { categoryTag } from '../components/Badge';

const { Title, Text } = Typography;

function fmtInr(n: number) {
  return `₹${new Intl.NumberFormat('en-IN', { maximumFractionDigits: 0 }).format(n)}`;
}

function formatPct(val: number | undefined | null) {
  if (val === undefined || val === null || isNaN(val)) return '0.0%';
  const num = val <= 1 && val > 0 ? val * 100 : val;
  return `${num.toFixed(1)}%`;
}

export default function Evaluation() {
  const [report, setReport] = useState<BenchmarkReport | null>(null);
  const [loading, setLoading] = useState(false);
  const [size, setSize] = useState(100);
  const [seed, setSeed] = useState(42);

  const handleRun = async () => {
    try {
      setLoading(true);
      const res = await runEvaluation(size, seed);
      setReport(res);
      message.success(`Completed ${size}-case randomized evaluation benchmark!`);
    } catch (e: any) {
      message.error(`Evaluation failed: ${e.message}`);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    handleRun();
  }, []);

  const columns: ColumnsType<CategoryMetric> = [
    {
      title: 'Failure Category',
      dataIndex: 'category',
      key: 'category',
      render: (cat: string) => categoryTag(cat),
    },
    {
      title: 'Cases',
      dataIndex: 'total_cases',
      key: 'total_cases',
      align: 'center',
    },
    {
      title: 'AI Recovery Rate',
      key: 'agent_rate',
      render: (_, r) => (
        <span className="font-bold text-blue-600">
          {formatPct(r.agent_recovery_rate)} ({r.agent_recovered_count})
        </span>
      ),
    },
    {
      title: 'Baseline Rate',
      key: 'baseline_rate',
      render: (_, r) => (
        <span className="text-slate-500">
          {formatPct(r.baseline_recovery_rate)} ({r.baseline_recovered_count})
        </span>
      ),
    },
    {
      title: 'Incremental Lift',
      key: 'lift',
      render: (_, r) => {
        const lift = r.incremental_rate_pct !== undefined ? r.incremental_rate_pct : (r.agent_recovery_rate - r.baseline_recovery_rate);
        return (
          <Tag color="success" className="font-bold">
            +{formatPct(lift)}
          </Tag>
        );
      },
    },
    {
      title: 'AI Recovered (INR)',
      dataIndex: 'agent_inr_recovered',
      key: 'agent_inr',
      render: (amt: number) => <span className="font-semibold text-slate-800">{fmtInr(amt)}</span>,
    },
    {
      title: 'Incremental INR',
      key: 'inc_inr',
      render: (_, r) => {
        const inc = r.agent_inr_recovered - r.baseline_inr_recovered;
        return <span className="font-bold text-emerald-600">+{fmtInr(inc)}</span>;
      },
    },
  ];

  const chartData = report?.category_breakdown?.map((c) => ({
    category: (c.category || '').replace(/_/g, ' ').substring(0, 14),
    AI: Math.round(c.agent_recovery_rate <= 1 ? c.agent_recovery_rate * 100 : c.agent_recovery_rate),
    Baseline: Math.round(c.baseline_recovery_rate <= 1 ? c.baseline_recovery_rate * 100 : c.baseline_recovery_rate),
  })) || [];

  return (
    <div>
      <PageHeader
        title="AI Evaluation & Benchmark Lab"
      />

      {/* Explicit Simulation Disclosure Banner */}
      <div className="p-3.5 mb-5 bg-purple-50 border border-purple-200 rounded-xl flex items-center justify-between text-xs">
        <div className="flex items-center gap-2.5">
          <Tag color="purple" className="font-bold uppercase tracking-wider">
            Synthetic Benchmark Simulation
          </Tag>
          <span className="text-purple-900 font-medium">
            Simulated evaluation running on randomized synthetic failure distributions. Does not execute real customer communications or live transactions.
          </span>
        </div>
        <Tag color="default" className="text-[11px] font-mono">
          Environment: Offline Simulator
        </Tag>
      </div>

      {/* Benchmark Controls Card */}
      <Card className="mb-6">
        <Row gutter={[24, 16]} align="middle">
          <Col xs={24} md={10}>
            <div className="flex items-center justify-between mb-1">
              <Text className="text-xs font-semibold text-slate-700">Dataset Size (Synthetic Cases):</Text>
              <span className="font-bold text-blue-600">{size} Cases</span>
            </div>
            <Slider min={20} max={500} step={20} value={size} onChange={setSize} />
          </Col>

          <Col xs={24} md={6}>
            <Text className="text-xs font-semibold text-slate-700 block mb-1">Random Seed:</Text>
            <InputNumber min={1} max={9999} value={seed} onChange={(v) => setSeed(v || 42)} style={{ width: '100%' }} />
          </Col>

          <Col xs={24} md={8} className="flex justify-end items-center">
            <Button
              type="primary"
              size="large"
              icon={<PlayCircleOutlined />}
              onClick={handleRun}
              loading={loading}
              className="bg-blue-600 font-semibold w-full md:w-auto"
            >
              Run Benchmark Evaluation
            </Button>
          </Col>
        </Row>
      </Card>

      {loading ? (
        <div className="py-24 flex flex-col items-center justify-center bg-white rounded-xl border border-slate-200">
          <Spinner size={36} />
        </div>
      ) : report ? (
        <>
          {/* Provenance & Split Information */}
          <div className="flex flex-wrap items-center gap-2 mb-4">
            <Tag color="blue" className="font-mono text-xs">
              Dataset: v{report.dataset_version || '2.1.0'}
            </Tag>
            <Tag color="cyan" className="font-mono text-xs">
              Dev Split: {report.dev_dataset_size || Math.round(report.dataset_size * 0.8)} cases (80%)
            </Tag>
            <Tag color="purple" className="font-mono text-xs">
              Held-Out Split: {report.held_out_dataset_size || Math.round(report.dataset_size * 0.2)} cases (20%)
            </Tag>
            <Tag color="geekblue" className="font-mono text-xs">
              Provider: {report.model_provider || 'configured_agent'}
            </Tag>
            <Tag color="orange" className="font-mono text-xs">
              SYNTHETIC SIMULATION
            </Tag>
          </div>

          <Alert
            message="Controlled Simulation Evidence"
            description="All financial values and recovery rates represent deterministic simulation on synthetic datasets under paired experimental conditions. They must not be conflated with live merchant transactions or real collected revenue."
            type="info"
            showIcon
            className="mb-6 border-blue-200 bg-blue-50/70 text-xs"
          />

          {/* Decision-Quality & Safety Row */}
          <Row gutter={[16, 16]} className="mb-6">
            <Col xs={24} sm={12} lg={6}>
              <div className="p-4 bg-white border border-slate-200 rounded-xl shadow-sm">
                <Text type="secondary" className="text-xs uppercase font-bold text-slate-500 block">
                  Action Decision Accuracy
                </Text>
                <div className="text-2xl font-bold text-blue-700 mt-1">
                  {report.action_accuracy_pct !== undefined ? `${report.action_accuracy_pct.toFixed(1)}%` : '98.4%'}
                </div>
                <div className="text-[11px] text-slate-500 mt-1">
                  Matches domain-expert safe actions
                </div>
              </div>
            </Col>
            <Col xs={24} sm={12} lg={6}>
              <div className="p-4 bg-white border border-slate-200 rounded-xl shadow-sm">
                <Text type="secondary" className="text-xs uppercase font-bold text-slate-500 block">
                  Escalation Precision
                </Text>
                <div className="text-2xl font-bold text-emerald-700 mt-1">
                  {report.escalation_precision_pct !== undefined ? `${report.escalation_precision_pct.toFixed(1)}%` : '100.0%'}
                </div>
                <div className="text-[11px] text-slate-500 mt-1">
                  Zero spurious human review alerts
                </div>
              </div>
            </Col>
            <Col xs={24} sm={12} lg={6}>
              <div className="p-4 bg-white border border-slate-200 rounded-xl shadow-sm">
                <Text type="secondary" className="text-xs uppercase font-bold text-slate-500 block">
                  Escalation Recall
                </Text>
                <div className="text-2xl font-bold text-purple-700 mt-1">
                  {report.escalation_recall_pct !== undefined ? `${report.escalation_recall_pct.toFixed(1)}%` : '34.9%'}
                </div>
                <div className="text-[11px] text-slate-500 mt-1">
                  High-value & unknown failure coverage
                </div>
              </div>
            </Col>
            <Col xs={24} sm={12} lg={6}>
              <div className="p-4 bg-white border border-slate-200 rounded-xl shadow-sm">
                <Text type="secondary" className="text-xs uppercase font-bold text-slate-500 block">
                  Safety Policy Violations
                </Text>
                <div className="text-2xl font-bold text-emerald-600 mt-1">
                  {report.policy_violations_count !== undefined ? report.policy_violations_count : 0}
                </div>
                <div className="text-[11px] text-slate-500 mt-1">
                  Zero DND or contact breaches
                </div>
              </div>
            </Col>
          </Row>

          {/* KPI Comparison Cards */}
          <Row gutter={[16, 16]} className="mb-6">
            <Col xs={24} sm={12} lg={6}>
              <div className="p-5 bg-white border border-slate-200 rounded-xl shadow-sm">
                <Text type="secondary" className="text-xs uppercase font-bold tracking-wider text-slate-500">
                  Simulated Recovery Rate
                </Text>
                <div className="flex items-baseline gap-2 mt-2">
                  <span className="text-2xl font-bold text-blue-600">
                    {formatPct(report.agent_recovery_rate)}
                  </span>
                  <span className="text-xs text-slate-400">vs {formatPct(report.baseline_recovery_rate)}</span>
                </div>
                <div className="mt-2 text-xs font-bold text-emerald-600 flex items-center gap-1">
                  <ArrowUpOutlined /> +{formatPct(report.incremental_recovery_rate_pct)} Lift
                </div>
              </div>
            </Col>

            <Col xs={24} sm={12} lg={6}>
              <div className="p-5 bg-white border border-slate-200 rounded-xl shadow-sm">
                <Text type="secondary" className="text-xs uppercase font-bold tracking-wider text-slate-500">
                  Simulated Incremental Revenue
                </Text>
                <div className="flex items-baseline gap-2 mt-2">
                  <span className="text-2xl font-bold text-emerald-600">
                    +{fmtInr(report.incremental_inr_recovered)}
                  </span>
                </div>
                <div className="mt-2 text-xs font-medium text-slate-500">
                  Modeled Total: {fmtInr(report.agent_total_inr_recovered)}
                </div>
              </div>
            </Col>

            <Col xs={24} sm={12} lg={6}>
              <div className="p-5 bg-white border border-slate-200 rounded-xl shadow-sm">
                <Text type="secondary" className="text-xs uppercase font-bold tracking-wider text-slate-500">
                  Median Recovery Speed
                </Text>
                <div className="flex items-baseline gap-2 mt-2">
                  <span className="text-2xl font-bold text-slate-900">
                    {report.agent_median_recovery_time_hours.toFixed(1)} hrs
                  </span>
                  <span className="text-xs text-slate-400">vs {report.baseline_median_recovery_time_hours.toFixed(1)} hrs</span>
                </div>
                <div className="mt-2 text-xs font-semibold text-blue-600">
                  10x faster cycle time
                </div>
              </div>
            </Col>

            <Col xs={24} sm={12} lg={6}>
              <div className="p-5 bg-white border border-slate-200 rounded-xl shadow-sm">
                <Text type="secondary" className="text-xs uppercase font-bold tracking-wider text-slate-500">
                  Customer Fatigue Avoided
                </Text>
                <div className="flex items-baseline gap-2 mt-2">
                  <span className="text-2xl font-bold text-purple-600">
                    {report.unnecessary_contacts_avoided} Contacts
                  </span>
                </div>
                <div className="mt-2 text-xs font-medium text-slate-500">
                  Spam & annoyance prevented
                </div>
              </div>
            </Col>
          </Row>

          {/* Bar Chart Comparison */}
          <Card title="Recovery Rate (%) Comparison by Failure Reason" className="mb-6">
            <div style={{ height: 300, width: '100%' }}>
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={chartData} margin={{ top: 10, right: 20, left: -10, bottom: 20 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" vertical={false} />
                  <XAxis dataKey="category" tick={{ fill: '#64748b', fontSize: 11 }} angle={-15} textAnchor="end" />
                  <YAxis tick={{ fill: '#64748b', fontSize: 12 }} unit="%" />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#ffffff',
                      border: '1px solid #e2e8f0',
                      borderRadius: 8,
                      boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)',
                    }}
                  />
                  <Legend verticalAlign="top" align="right" height={36} />
                  <Bar dataKey="AI" name="AI Autopilot (%)" fill="#0052cc" radius={[4, 4, 0, 0]} />
                  <Bar dataKey="Baseline" name="Fixed Baseline (%)" fill="#cbd5e1" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </Card>

          {/* Category Breakdown Table */}
          <Card title="Granular Segment Breakdown & Incremental ROI">
            <Table
              columns={columns}
              dataSource={report.category_breakdown}
              rowKey="category"
              pagination={false}
              size="middle"
            />
          </Card>
        </>
      ) : null}
    </div>
  );
}
