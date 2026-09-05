import React, { useState, useEffect } from 'react';
import {
  Table,
  Card,
  Tag,
  Typography,
  Space,
  Button,
  Modal,
  Input,
  Tooltip,
  Badge,
  Alert,
  message,
} from 'antd';
import {
  DisconnectOutlined,
  CopyOutlined,
  EyeOutlined,
  ReloadOutlined,
  CheckCircleOutlined,
  WarningOutlined,
} from '@ant-design/icons';
import { fetchUnmatchedWebhooks, fetchQueueStats } from '../api';
import { UnmatchedWebhookRecord, QueueStats } from '../types';

const { Title, Text, Paragraph } = Typography;

export default function UnmatchedEvents() {
  const [loading, setLoading] = useState(false);
  const [records, setRecords] = useState<UnmatchedWebhookRecord[]>([]);
  const [queueStats, setQueueStats] = useState<QueueStats | null>(null);
  const [selectedRecord, setSelectedRecord] = useState<UnmatchedWebhookRecord | null>(null);
  const [searchTerm, setSearchTerm] = useState('');

  const loadData = async () => {
    setLoading(true);
    try {
      const [unmatched, stats] = await Promise.all([
        fetchUnmatchedWebhooks(100),
        fetchQueueStats(),
      ]);
      setRecords(unmatched);
      setQueueStats(stats);
    } catch (err: any) {
      message.error(err.message || 'Failed to load unmatched events');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 15000);
    return () => clearInterval(interval);
  }, []);

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    message.success('Copied to clipboard');
  };

  const filtered = records.filter(
    (r) =>
      r.event_id.toLowerCase().includes(searchTerm.toLowerCase()) ||
      r.event_type.toLowerCase().includes(searchTerm.toLowerCase()) ||
      r.reason.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const columns = [
    {
      title: 'Event ID',
      dataIndex: 'event_id',
      key: 'event_id',
      render: (id: string) => (
        <Space>
          <Text code copyable>
            {id}
          </Text>
        </Space>
      ),
    },
    {
      title: 'Event Type',
      dataIndex: 'event_type',
      key: 'event_type',
      render: (type: string) => {
        let color = 'default';
        if (type.includes('captured') || type.includes('paid')) color = 'gold';
        else if (type.includes('failed')) color = 'volcano';
        return <Tag color={color}>{type}</Tag>;
      },
    },
    {
      title: 'Reason / Discrepancy',
      dataIndex: 'reason',
      key: 'reason',
      render: (reason: string) => (
        <div className="flex items-center gap-1.5 text-amber-700 bg-amber-50 px-2.5 py-1 rounded border border-amber-200 text-xs">
          <WarningOutlined />
          <span>{reason}</span>
        </div>
      ),
    },
    {
      title: 'Received At',
      dataIndex: 'received_at',
      key: 'received_at',
      render: (ts: string) => <Text type="secondary">{ts ? new Date(ts).toLocaleString() : '-'}</Text>,
    },
    {
      title: 'Action',
      key: 'action',
      render: (_: any, record: UnmatchedWebhookRecord) => (
        <Button
          size="small"
          icon={<EyeOutlined />}
          onClick={() => setSelectedRecord(record)}
        >
          View Payload
        </Button>
      ),
    },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
        <div className="flex items-center gap-2">
          <DisconnectOutlined className="text-xl text-amber-600" />
          <Title level={3} style={{ margin: 0, color: '#0f172a' }}>
            Unmatched Webhook Events
          </Title>
        </div>

        <Space>
          <Button icon={<ReloadOutlined />} onClick={loadData} loading={loading}>
            Refresh
          </Button>
        </Space>
      </div>

      {/* Queue Health Strip */}
      {queueStats && (
        <div className="grid grid-cols-2 md:grid-cols-6 gap-3">
          <Card size="small" className="border-slate-200 text-center">
            <div className="text-xs text-slate-500 font-medium">Queued</div>
            <div className="text-lg font-bold text-blue-600">{queueStats.queued}</div>
          </Card>
          <Card size="small" className="border-slate-200 text-center">
            <div className="text-xs text-slate-500 font-medium">Processing</div>
            <div className="text-lg font-bold text-amber-600">{queueStats.processing}</div>
          </Card>
          <Card size="small" className="border-slate-200 text-center">
            <div className="text-xs text-slate-500 font-medium">Completed</div>
            <div className="text-lg font-bold text-emerald-600">{queueStats.completed}</div>
          </Card>
          <Card size="small" className="border-slate-200 text-center">
            <div className="text-xs text-slate-500 font-medium">Unmatched Quarantined</div>
            <div className="text-lg font-bold text-orange-600">{records.length}</div>
          </Card>
          <Card size="small" className="border-slate-200 text-center">
            <div className="text-xs text-slate-500 font-medium">Dead Letter Queue</div>
            <div className="text-lg font-bold text-red-600">{queueStats.dead_letter}</div>
          </Card>
          <Card size="small" className="border-slate-200 text-center">
            <div className="text-xs text-slate-500 font-medium">Total Received</div>
            <div className="text-lg font-bold text-slate-800">{queueStats.total_events}</div>
          </Card>
        </div>
      )}

      {/* Main Table Card */}
      <Card className="shadow-sm border-slate-200">
        <div className="mb-4 flex justify-between items-center">
          <Input.Search
            placeholder="Search by Event ID, Type, or Reason..."
            style={{ width: 350 }}
            allowClear
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
          <Text type="secondary" className="text-xs">
            Showing {filtered.length} unmatched records
          </Text>
        </div>

        <Table
          columns={columns}
          dataSource={filtered}
          rowKey="event_id"
          loading={loading}
          pagination={{ pageSize: 15, showTotal: (total) => `Total ${total} unmatched events` }}
          locale={{
            emptyText: (
              <div className="py-12 text-center">
                <CheckCircleOutlined className="text-4xl text-emerald-500 mb-2" />
                <div className="text-sm font-semibold text-slate-700">Zero Unmatched Events</div>
                <div className="text-xs text-slate-400 max-w-sm mx-auto mt-1">
                  All incoming financial webhooks have been correlated and matched to active recovery cases with exact identifier matching.
                </div>
              </div>
            ),
          }}
        />
      </Card>

      {/* Payload Modal */}
      <Modal
        title="Unmatched Webhook Payload Details"
        open={!!selectedRecord}
        onCancel={() => setSelectedRecord(null)}
        footer={[
          <Button key="close" type="primary" onClick={() => setSelectedRecord(null)}>
            Close
          </Button>,
        ]}
        width={700}
      >
        {selectedRecord && (
          <div className="space-y-4">
            <Alert
              message="Isolation Reason"
              description={selectedRecord.reason}
              type="warning"
              showIcon
            />
            <div>
              <Text strong className="text-xs text-slate-500 uppercase tracking-wide">
                Raw JSON Payload
              </Text>
              <pre className="p-3 bg-slate-900 text-slate-200 rounded-lg text-xs font-mono overflow-auto max-h-96 mt-1">
                {(() => {
                  try {
                    return JSON.stringify(JSON.parse(selectedRecord.payload_json), null, 2);
                  } catch {
                    return selectedRecord.payload_json;
                  }
                })()}
              </pre>
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
}
