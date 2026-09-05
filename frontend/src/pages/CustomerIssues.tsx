import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Table,
  Tag,
  Button,
  Space,
  Input,
  Select,
  Card,
  Row,
  Col,
  Typography,
  Badge,
  Modal,
  Form,
  message,
  Tooltip,
} from 'antd';
import {
  ExclamationCircleOutlined,
  SearchOutlined,
  PlusOutlined,
  RobotOutlined,
  EyeOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
  SyncOutlined,
  WarningOutlined,
  SafetyCertificateOutlined,
} from '@ant-design/icons';
import { fetchCustomerIssues, createCustomerIssue } from '../api';
import { CustomerIssue, IssueStatus, IssueSeverity } from '../types';

const { Title, Text, Paragraph } = Typography;

export default function CustomerIssues() {
  const navigate = useNavigate();
  const [issues, setIssues] = useState<CustomerIssue[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [statusFilter, setStatusFilter] = useState<string>('ALL');
  const [severityFilter, setSeverityFilter] = useState<string>('ALL');
  const [searchEmail, setSearchEmail] = useState<string>('');
  const [isCreateModalOpen, setIsCreateModalOpen] = useState<boolean>(false);
  const [createForm] = Form.useForm();
  const [creating, setCreating] = useState<boolean>(false);

  useEffect(() => {
    loadIssues();
  }, [statusFilter, severityFilter]);

  const loadIssues = async () => {
    setLoading(true);
    try {
      const filters: any = {};
      if (statusFilter !== 'ALL') filters.status = statusFilter;
      if (severityFilter !== 'ALL') filters.severity = severityFilter;
      if (searchEmail.trim()) filters.customer_email = searchEmail.trim();

      const res = await fetchCustomerIssues(filters);
      setIssues(Array.isArray(res) ? res : ((res as any).issues || []));
    } catch (err: any) {
      message.error(err.message || 'Failed to load issues');
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = () => {
    loadIssues();
  };

  const handleCreateIssue = async (values: any) => {
    setCreating(true);
    try {
      const newIssue = await createCustomerIssue(values);
      message.success(`Issue created: ${newIssue.issue_id}`);
      setIsCreateModalOpen(false);
      createForm.resetFields();
      loadIssues();
      navigate(`/issues/${newIssue.issue_id}`);
    } catch (err: any) {
      message.error(err.message || 'Failed to create issue');
    } finally {
      setCreating(false);
    }
  };

  // Stat calculations
  const totalCount = issues.length;
  const activeCount = issues.filter((i) => !['RESOLVED', 'CLOSED'].includes(i.status)).length;
  const investigatingCount = issues.filter((i) => i.status === 'INVESTIGATING').length;
  const resolvedCount = issues.filter((i) => i.status === 'RESOLVED').length;

  const getStatusTag = (status: IssueStatus) => {
    switch (status) {
      case 'NEW':
        return <Tag color="blue">NEW</Tag>;
      case 'INVESTIGATING':
        return <Tag color="processing" icon={<SyncOutlined spin />}>INVESTIGATING</Tag>;
      case 'AWAITING_INFO':
        return <Tag color="orange" icon={<ClockCircleOutlined />}>AWAITING INFO</Tag>;
      case 'ACTION_IN_PROGRESS':
        return <Tag color="cyan">ACTION IN PROGRESS</Tag>;
      case 'MONITORING':
        return <Tag color="purple">MONITORING</Tag>;
      case 'RESOLVED':
        return <Tag color="green" icon={<CheckCircleOutlined />}>RESOLVED</Tag>;
      case 'CLOSED':
        return <Tag color="default">CLOSED</Tag>;
      default:
        return <Tag>{status}</Tag>;
    }
  };

  const getSeverityTag = (severity: IssueSeverity) => {
    switch (severity) {
      case 'CRITICAL':
        return <Tag color="error">CRITICAL</Tag>;
      case 'HIGH':
        return <Tag color="volcano">HIGH</Tag>;
      case 'MEDIUM':
        return <Tag color="gold">MEDIUM</Tag>;
      case 'LOW':
        return <Tag color="blue">LOW</Tag>;
      default:
        return <Tag>{severity}</Tag>;
    }
  };

  const columns = [
    {
      title: 'Issue ID & Title',
      key: 'title',
      render: (_: any, record: CustomerIssue) => (
        <div>
          <div className="font-semibold text-slate-800 hover:text-blue-600 cursor-pointer" onClick={() => navigate(`/issues/${record.issue_id}`)}>
            {record.title}
          </div>
          <div className="text-xs text-slate-400 font-mono flex items-center gap-2 mt-0.5">
            <span>{record.issue_id}</span>
            <span>•</span>
            <span>{record.category}</span>
          </div>
        </div>
      ),
    },
    {
      title: 'Customer',
      key: 'customer',
      render: (_: any, record: CustomerIssue) => (
        <div>
          <div className="text-sm font-medium text-slate-700">{record.customer_name || 'N/A'}</div>
          <div className="text-xs text-slate-400">{record.customer_email || '—'}</div>
        </div>
      ),
    },
    {
      title: 'Status',
      dataIndex: 'status',
      key: 'status',
      render: (status: IssueStatus) => getStatusTag(status),
    },
    {
      title: 'Severity',
      dataIndex: 'severity',
      key: 'severity',
      render: (sev: IssueSeverity) => getSeverityTag(sev),
    },
    {
      title: 'Evidence / Causes',
      key: 'evidence_count',
      render: (_: any, record: CustomerIssue) => (
        <Space orientation="vertical" size={2}>
          <Text className="text-xs text-slate-600">
            <strong>{record.evidence?.length || 0}</strong> evidence item(s)
          </Text>
          <Text className="text-xs text-slate-500">
            <strong>{record.possible_causes?.length || 0}</strong> cause hypothesis
          </Text>
        </Space>
      ),
    },
    {
      title: 'Resolution',
      key: 'resolution',
      render: (_: any, record: CustomerIssue) => (
        record.resolution_verified ? (
          <Tag color="success" icon={<CheckCircleOutlined />}>Verified</Tag>
        ) : record.status === 'RESOLVED' ? (
          <Tag color="warning">Unverified</Tag>
        ) : (
          <Text type="secondary" className="text-xs">In Progress</Text>
        )
      ),
    },
    {
      title: 'Actions',
      key: 'actions',
      render: (_: any, record: CustomerIssue) => (
        <Space orientation="horizontal" size="small">
          <Button
            size="small"
            icon={<EyeOutlined />}
            onClick={() => navigate(`/issues/${record.issue_id}`)}
          >
            Details
          </Button>
          <Button
            size="small"
            type="primary"
            ghost
            icon={<RobotOutlined />}
            onClick={() => navigate(`/copilot?query=Investigate issue ${record.issue_id} for ${record.customer_email || ''}&case_id=${record.case_id || ''}`)}
          >
            Ray AI
          </Button>
        </Space>
      ),
    },
  ];

  return (
    <div style={{ maxWidth: 1300, margin: '0 auto', paddingBottom: 60 }}>
      {/* Page Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <Title level={3} style={{ margin: 0 }}>
            Customer Issues Tracker
          </Title>
          <Paragraph type="secondary" style={{ margin: '4px 0 0 0' }}>
            Track customer payment issues from report to verified resolution with evidence collection, root-cause analysis, and action execution.
          </Paragraph>
        </div>

        <Space>
          <Button
            icon={<RobotOutlined />}
            onClick={() => navigate('/copilot')}
          >
            Open Ray AI Copilot
          </Button>
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => setIsCreateModalOpen(true)}
            style={{ background: '#0052cc' }}
          >
            Create Issue
          </Button>
        </Space>
      </div>

      {/* Stats Summary Cards */}
      <Row gutter={[16, 16]} className="mb-6">
        <Col xs={12} sm={6}>
          <Card size="small" className="border-slate-200 shadow-sm">
            <div className="text-xs text-slate-500 font-semibold uppercase">Total Issues</div>
            <div className="text-2xl font-bold text-slate-900 mt-1">{totalCount}</div>
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card size="small" className="border-slate-200 shadow-sm">
            <div className="text-xs text-amber-600 font-semibold uppercase">Active / Open</div>
            <div className="text-2xl font-bold text-amber-700 mt-1">{activeCount}</div>
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card size="small" className="border-slate-200 shadow-sm">
            <div className="text-xs text-blue-600 font-semibold uppercase">Investigating</div>
            <div className="text-2xl font-bold text-blue-700 mt-1">{investigatingCount}</div>
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card size="small" className="border-slate-200 shadow-sm">
            <div className="text-xs text-emerald-600 font-semibold uppercase">Verified Resolved</div>
            <div className="text-2xl font-bold text-emerald-700 mt-1">{resolvedCount}</div>
          </Card>
        </Col>
      </Row>

      {/* Filter Bar */}
      <Card size="small" className="mb-4 border-slate-200 shadow-sm">
        <Row gutter={[16, 16]} align="middle">
          <Col xs={24} md={6}>
            <Input
              placeholder="Search by customer email..."
              prefix={<SearchOutlined className="text-slate-400" />}
              value={searchEmail}
              onChange={(e) => setSearchEmail(e.target.value)}
              onPressEnter={handleSearch}
              allowClear
            />
          </Col>
          <Col xs={12} md={5}>
            <div className="flex items-center gap-2">
              <span className="text-xs text-slate-500 font-semibold">Status:</span>
              <Select
                value={statusFilter}
                onChange={setStatusFilter}
                style={{ width: '100%' }}
                options={[
                  { value: 'ALL', label: 'All Statuses' },
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
          </Col>
          <Col xs={12} md={5}>
            <div className="flex items-center gap-2">
              <span className="text-xs text-slate-500 font-semibold">Severity:</span>
              <Select
                value={severityFilter}
                onChange={setSeverityFilter}
                style={{ width: '100%' }}
                options={[
                  { value: 'ALL', label: 'All Severities' },
                  { value: 'CRITICAL', label: 'Critical' },
                  { value: 'HIGH', label: 'High' },
                  { value: 'MEDIUM', label: 'Medium' },
                  { value: 'LOW', label: 'Low' },
                ]}
              />
            </div>
          </Col>
          <Col xs={24} md={8} style={{ textAlign: 'right' }}>
            <Button onClick={loadIssues} loading={loading}>
              Refresh List
            </Button>
          </Col>
        </Row>
      </Card>

      {/* Issues Table */}
      <Card className="border-slate-200 shadow-sm p-0">
        <Table
          columns={columns}
          dataSource={issues}
          rowKey="issue_id"
          loading={loading}
          pagination={{ pageSize: 15 }}
          locale={{ emptyText: 'No customer issues found. Use the AI Copilot to investigate or create a new issue.' }}
        />
      </Card>

      {/* Create Issue Modal */}
      <Modal
        title="Create Customer Issue"
        open={isCreateModalOpen}
        onCancel={() => setIsCreateModalOpen(false)}
        footer={null}
        width={600}
      >
        <Form
          form={createForm}
          layout="vertical"
          onFinish={handleCreateIssue}
          initialValues={{ severity: 'MEDIUM', category: 'PAYMENT_FAILURE' }}
        >
          <Form.Item
            name="title"
            label="Issue Title"
            rules={[{ required: true, message: 'Please provide an issue title' }]}
          >
            <Input placeholder="e.g. Payment debited twice for Priya Sharma" />
          </Form.Item>

          <Row gutter={12}>
            <Col span={12}>
              <Form.Item
                name="category"
                label="Category"
                rules={[{ required: true }]}
              >
                <Select
                  options={[
                    { value: 'PAYMENT_FAILURE', label: 'Payment Failure' },
                    { value: 'PAYMENT_PENDING', label: 'Payment Pending' },
                    { value: 'DEBIT_WITHOUT_CONFIRMATION', label: 'Debit Without Confirmation' },
                    { value: 'DUPLICATE_PAYMENT', label: 'Duplicate Payment' },
                    { value: 'ORDER_PAYMENT_MISMATCH', label: 'Order/Payment Mismatch' },
                    { value: 'REFUND_DELAY', label: 'Refund Delay' },
                    { value: 'WEBHOOK_ISSUE', label: 'Webhook Issue' },
                    { value: 'GENERAL_INQUIRY', label: 'General Inquiry' },
                  ]}
                />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="severity" label="Severity" rules={[{ required: true }]}>
                <Select
                  options={[
                    { value: 'CRITICAL', label: 'Critical' },
                    { value: 'HIGH', label: 'High' },
                    { value: 'MEDIUM', label: 'Medium' },
                    { value: 'LOW', label: 'Low' },
                  ]}
                />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={12}>
            <Col span={12}>
              <Form.Item name="customer_name" label="Customer Name">
                <Input placeholder="Customer name" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="customer_email" label="Customer Email">
                <Input placeholder="customer@example.com" />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={12}>
            <Col span={12}>
              <Form.Item name="payment_id" label="Payment ID (Optional)">
                <Input placeholder="pay_..." />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="order_id" label="Order ID (Optional)">
                <Input placeholder="order_..." />
              </Form.Item>
            </Col>
          </Row>

          <Form.Item name="reported_symptoms" label="Reported Symptoms / Customer Description">
            <Input.TextArea rows={3} placeholder="Describe the customer's issue or paste inquiry..." />
          </Form.Item>

          <div className="flex justify-end gap-2 pt-2">
            <Button onClick={() => setIsCreateModalOpen(false)}>Cancel</Button>
            <Button type="primary" htmlType="submit" loading={creating} style={{ background: '#0052cc' }}>
              Create & Open Issue
            </Button>
          </div>
        </Form>
      </Modal>
    </div>
  );
}
