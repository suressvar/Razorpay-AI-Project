import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Table,
  Input,
  Select,
  Button,
  Space,
  Tag,
  Typography,
  Tooltip,
} from 'antd';
import type { ColumnsType } from 'antd/es/table';
import {
  SearchOutlined,
  SyncOutlined,
  EyeOutlined,
  FilterOutlined,
} from '@ant-design/icons';
import { fetchCases } from '../api';
import { PaymentCase } from '../types';
import { Card, PageHeader, ErrorState, EmptyState } from '../components/Card';
import { statusTag, categoryTag, actionTag } from '../components/Badge';

const { Text } = Typography;

const STATUS_OPTIONS = [
  { value: 'ALL', label: 'All Statuses' },
  { value: 'NEW', label: 'New' },
  { value: 'DIAGNOSING', label: 'Diagnosing' },
  { value: 'AWAITING_POLICY', label: 'Awaiting Policy' },
  { value: 'SCHEDULED', label: 'Scheduled' },
  { value: 'AWAITING_APPROVAL', label: 'Awaiting Approval' },
  { value: 'ACTION_IN_PROGRESS', label: 'Action In Progress' },
  { value: 'MONITORING', label: 'Monitoring' },
  { value: 'PROMISED_TO_PAY', label: 'Promised To Pay' },
  { value: 'RECOVERED', label: 'Recovered' },
  { value: 'EXHAUSTED', label: 'Exhausted' },
  { value: 'OPTED_OUT', label: 'Opted Out' },
  { value: 'STOPPED', label: 'Stopped' },
  { value: 'ERROR', label: 'Error' },
];

const CATEGORY_OPTIONS = [
  { value: 'ALL', label: 'All Categories' },
  { value: 'INSUFFICIENT_FUNDS', label: 'Insufficient Funds' },
  { value: 'BANK_TIMEOUT', label: 'Bank Timeout' },
  { value: 'EXPIRED_CARD', label: 'Expired Card' },
  { value: 'MANDATE_REVOKED', label: 'Mandate Revoked' },
  { value: 'LIMIT_EXCEEDED', label: 'Limit Exceeded' },
  { value: 'NETWORK_FAILURE', label: 'Network Failure' },
  { value: 'CUSTOMER_ACTION_REQUIRED', label: 'Action Required' },
  { value: 'UNKNOWN_FAILURE', label: 'Unknown Failure' },
];

function fmtInr(n: number) {
  return `₹${new Intl.NumberFormat('en-IN', { maximumFractionDigits: 0 }).format(n)}`;
}

export default function Cases() {
  const navigate = useNavigate();
  const [cases, setCases] = useState<PaymentCase[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [status, setStatus] = useState('ALL');
  const [category, setCategory] = useState('ALL');
  const [search, setSearch] = useState('');

  const load = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await fetchCases(status, category, 200);
      setCases(data);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, [status, category]);

  const filtered = cases.filter((c) => {
    if (!search.trim()) return true;
    const q = search.toLowerCase();
    return (
      c.case_id.toLowerCase().includes(q) ||
      c.context.customer_id.toLowerCase().includes(q) ||
      c.context.customer_email.toLowerCase().includes(q) ||
      c.context.customer_name?.toLowerCase().includes(q)
    );
  });

  const columns: ColumnsType<PaymentCase> = [
    {
      title: 'Case ID',
      dataIndex: 'case_id',
      key: 'case_id',
      render: (id: string) => (
        <span className="font-mono text-xs font-semibold text-blue-600">
          {id.length > 18 ? `${id.substring(0, 18)}...` : id}
        </span>
      ),
    },
    {
      title: 'Customer Details',
      key: 'customer',
      render: (_, record) => (
        <div>
          <div className="font-semibold text-slate-800 text-xs">
            {record.context.customer_name || record.context.customer_id}
          </div>
          <div className="text-[11px] text-slate-500">{record.context.customer_email}</div>
        </div>
      ),
    },
    {
      title: 'Amount (INR)',
      dataIndex: ['context', 'amount_inr'],
      key: 'amount',
      sorter: (a, b) => a.context.amount_inr - b.context.amount_inr,
      render: (amt: number) => (
        <span className="font-bold text-slate-900 text-xs">
          {fmtInr(amt)}
        </span>
      ),
    },
    {
      title: 'Failure Category',
      dataIndex: ['context', 'failure_category'],
      key: 'failure_category',
      render: (cat: string) => categoryTag(cat),
    },
    {
      title: 'Status',
      dataIndex: 'status',
      key: 'status',
      render: (st: string) => statusTag(st),
    },
    {
      title: 'Action Strategy',
      key: 'action',
      render: (_, record) => {
        const act = record.latest_decision?.approved_action || record.current_proposal?.action;
        return act ? actionTag(act) : <Text type="secondary" className="text-xs">—</Text>;
      },
    },
    {
      title: 'Contacts',
      dataIndex: 'contact_count',
      key: 'contact_count',
      align: 'center',
      render: (cnt: number) => (
        <Tag color={cnt > 2 ? 'red' : cnt > 0 ? 'orange' : 'default'} style={{ margin: 0 }}>
          {cnt} / 3 max
        </Tag>
      ),
    },
    {
      title: 'Action',
      key: 'actions',
      align: 'right',
      render: (_, record) => (
        <Button
          type="primary"
          size="small"
          icon={<EyeOutlined />}
          onClick={() => navigate(`/cases/${record.case_id}`)}
          className="bg-blue-600 text-xs"
        >
          Inspect
        </Button>
      ),
    },
  ];

  return (
    <div>
      <PageHeader
        title="Subscription Recovery Cases"
        actions={
          <Button icon={<SyncOutlined />} onClick={load} loading={loading}>
            Refresh
          </Button>
        }
      />

      <Card className="mb-4">
        {/* Filters and Search Bar */}
        <div className="flex flex-wrap items-center gap-3">
          <Input
            placeholder="Search by Case ID, Customer name or Email..."
            prefix={<SearchOutlined className="text-slate-400" />}
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            style={{ width: 320 }}
            allowClear
          />

          <Select
            value={status}
            onChange={setStatus}
            options={STATUS_OPTIONS}
            style={{ width: 180 }}
            suffixIcon={<FilterOutlined />}
          />

          <Select
            value={category}
            onChange={setCategory}
            options={CATEGORY_OPTIONS}
            style={{ width: 200 }}
          />

          {(status !== 'ALL' || category !== 'ALL' || search) && (
            <Button
              type="text"
              onClick={() => {
                setStatus('ALL');
                setCategory('ALL');
                setSearch('');
              }}
            >
              Clear Filters
            </Button>
          )}
        </div>
      </Card>

      {error ? (
        <ErrorState message={error} onRetry={load} />
      ) : (
        <Card bordered={false} className="p-0">
          <Table
            columns={columns}
            dataSource={filtered}
            rowKey="case_id"
            loading={loading}
            pagination={{
              pageSize: 10,
              showSizeChanger: true,
              pageSizeOptions: ['10', '20', '50'],
              showTotal: (total) => `Total ${total} cases`,
            }}
            size="middle"
          />
        </Card>
      )}
    </div>
  );
}
