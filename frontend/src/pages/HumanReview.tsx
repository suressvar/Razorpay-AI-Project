import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Table,
  Button,
  Space,
  Tag,
  Typography,
  Modal,
  Input,
  message,
  Descriptions,
  Progress,
  Row,
  Col,
  Alert,
} from 'antd';
import type { ColumnsType } from 'antd/es/table';
import {
  UserSwitchOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  SyncOutlined,
  EyeOutlined,
  SafetyCertificateOutlined,
  ExclamationCircleOutlined,
  RobotOutlined,
} from '@ant-design/icons';
import { fetchCases, approveCase, rejectCase } from '../api';
import { PaymentCase } from '../types';
import { Card, PageHeader, ErrorState, EmptyState } from '../components/Card';
import { categoryTag, actionTag } from '../components/Badge';

const { Text, Paragraph } = Typography;
const { TextArea } = Input;

function fmtInr(n: number) {
  return `₹${new Intl.NumberFormat('en-IN').format(n)}`;
}

export default function HumanReview() {
  const navigate = useNavigate();
  const [cases, setCases] = useState<PaymentCase[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedCase, setSelectedCase] = useState<PaymentCase | null>(null);
  const [modalType, setModalType] = useState<'approve' | 'reject' | null>(null);
  const [rejectReason, setRejectReason] = useState('');
  const [processing, setProcessing] = useState(false);

  const load = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await fetchCases('AWAITING_APPROVAL', undefined, 100);
      setCases(data);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const handleApproveConfirm = async () => {
    if (!selectedCase) return;
    try {
      setProcessing(true);
      await approveCase(selectedCase.case_id);
      message.success(`Approved intervention for Case ${selectedCase.case_id.substring(0, 12)}...`);
      setModalType(null);
      setSelectedCase(null);
      await load();
    } catch (e: any) {
      message.error(`Approval failed: ${e.message}`);
    } finally {
      setProcessing(false);
    }
  };

  const handleRejectConfirm = async () => {
    if (!selectedCase) return;
    if (!rejectReason.trim()) {
      message.warning('Please provide a reason for rejection');
      return;
    }
    try {
      setProcessing(true);
      await rejectCase(selectedCase.case_id, rejectReason);
      message.info(`Rejected and stopped Case ${selectedCase.case_id.substring(0, 12)}...`);
      setModalType(null);
      setSelectedCase(null);
      setRejectReason('');
      await load();
    } catch (e: any) {
      message.error(`Rejection failed: ${e.message}`);
    } finally {
      setProcessing(false);
    }
  };

  const columns: ColumnsType<PaymentCase> = [
    {
      title: 'Case ID',
      dataIndex: 'case_id',
      key: 'case_id',
      render: (id: string) => (
        <span className="font-mono text-xs font-semibold text-blue-600">
          {id.substring(0, 16)}...
        </span>
      ),
    },
    {
      title: 'Customer Details',
      key: 'customer',
      render: (_, r) => (
        <div>
          <div className="font-semibold text-slate-800 text-xs">
            {r.context.customer_name || r.context.customer_id}
          </div>
          <div className="text-[11px] text-slate-500">{r.context.customer_email}</div>
        </div>
      ),
    },
    {
      title: 'Amount',
      dataIndex: ['context', 'amount_inr'],
      key: 'amount',
      render: (amt: number) => (
        <span className="font-bold text-slate-900 text-xs">
          {fmtInr(amt)}
        </span>
      ),
    },
    {
      title: 'Failure Category',
      dataIndex: ['context', 'failure_category'],
      key: 'category',
      render: (cat: string) => categoryTag(cat),
    },
    {
      title: 'Proposed AI Action',
      key: 'proposal',
      render: (_, r) => {
        const act = r.current_proposal?.action;
        return act ? actionTag(act) : <Tag color="default">NONE</Tag>;
      },
    },
    {
      title: 'Confidence',
      key: 'confidence',
      render: (_, r) => {
        const conf = r.current_proposal?.confidence ?? 0;
        return (
          <div style={{ width: 100 }}>
            <Progress
              percent={Math.round(conf * 100)}
              size="small"
              strokeColor={conf >= 0.75 ? '#10b981' : '#f59e0b'}
            />
          </div>
        );
      },
    },
    {
      title: 'Operator Actions',
      key: 'actions',
      align: 'right',
      render: (_, record) => (
        <Space>
          <Button
            type="primary"
            size="small"
            icon={<CheckCircleOutlined />}
            className="bg-emerald-600 hover:bg-emerald-700 text-xs"
            onClick={() => {
              setSelectedCase(record);
              setModalType('approve');
            }}
          >
            Approve
          </Button>
          <Button
            danger
            size="small"
            icon={<CloseCircleOutlined />}
            className="text-xs"
            onClick={() => {
              setSelectedCase(record);
              setModalType('reject');
            }}
          >
            Reject
          </Button>
          <Button
            size="small"
            icon={<EyeOutlined />}
            onClick={() => navigate(`/cases/${record.case_id}`)}
            className="text-xs"
          />
        </Space>
      ),
    },
  ];

  return (
    <div>
      <PageHeader
        title="Human Review Queue"
        actions={
          <Button icon={<SyncOutlined />} onClick={load} loading={loading}>
            Refresh Queue
          </Button>
        }
      />

      {error ? (
        <ErrorState message={error} onRetry={load} />
      ) : cases.length === 0 && !loading ? (
        <EmptyState
          message="No cases currently awaiting human approval."
          action={
            <Button type="primary" onClick={() => navigate('/')}>
              Back to Overview
            </Button>
          }
        />
      ) : (
        <Card bordered={false} className="p-0">
          <Table
            columns={columns}
            dataSource={cases}
            rowKey="case_id"
            loading={loading}
            pagination={{ pageSize: 10 }}
            size="middle"
          />
        </Card>
      )}

      {/* Approval Modal */}
      <Modal
        title={
          <Space>
            <CheckCircleOutlined className="text-emerald-500" />
            <span>Confirm Intervention Approval</span>
          </Space>
        }
        open={modalType === 'approve' && !!selectedCase}
        onOk={handleApproveConfirm}
        onCancel={() => {
          setModalType(null);
          setSelectedCase(null);
        }}
        confirmLoading={processing}
        okText="Approve & Dispatch"
        okButtonProps={{ className: 'bg-emerald-600 hover:bg-emerald-700' }}
      >
        {selectedCase && (
          <div className="space-y-4 py-2">
            <Descriptions bordered size="small" column={1}>
              <Descriptions.Item label="Case ID">
                <span className="font-mono text-xs">{selectedCase.case_id}</span>
              </Descriptions.Item>
              <Descriptions.Item label="Customer">
                {selectedCase.context.customer_name} ({selectedCase.context.customer_email})
              </Descriptions.Item>
              <Descriptions.Item label="Amount">
                <span className="font-bold text-slate-900">{fmtInr(selectedCase.context.amount_inr)}</span>
              </Descriptions.Item>
              <Descriptions.Item label="Proposed Action">
                {actionTag(selectedCase.current_proposal?.action || 'NONE')}
              </Descriptions.Item>
            </Descriptions>

            {selectedCase.current_proposal?.explanation && (
              <div className="p-3 bg-slate-50 border border-slate-200 rounded text-xs text-slate-700">
                <span className="font-semibold block mb-1">AI Diagnostic Rationale:</span>
                {selectedCase.current_proposal.explanation}
              </div>
            )}
          </div>
        )}
      </Modal>

      {/* Rejection Modal */}
      <Modal
        title={
          <Space>
            <CloseCircleOutlined className="text-rose-500" />
            <span>Reject Recovery Intervention</span>
          </Space>
        }
        open={modalType === 'reject' && !!selectedCase}
        onOk={handleRejectConfirm}
        onCancel={() => {
          setModalType(null);
          setSelectedCase(null);
          setRejectReason('');
        }}
        confirmLoading={processing}
        okText="Reject & Stop"
        okButtonProps={{ danger: true }}
      >
        {selectedCase && (
          <div className="space-y-4 py-2">
            <p className="text-xs text-slate-600 m-0">
              Rejecting this case will stop autonomous recovery and mark the case as STOPPED.
            </p>
            <div>
              <Text className="text-xs font-semibold text-slate-700 block mb-1">
                Reason for Rejection (Required):
              </Text>
              <TextArea
                rows={3}
                placeholder="e.g., Customer requested opt-out over phone / suspicious account / duplicate retry"
                value={rejectReason}
                onChange={(e) => setRejectReason(e.target.value)}
              />
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
}
