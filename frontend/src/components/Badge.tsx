import React from 'react';
import { Tag } from 'antd';
import {
  CheckCircleOutlined,
  SyncOutlined,
  ClockCircleOutlined,
  ExclamationCircleOutlined,
  CloseCircleOutlined,
  StopOutlined,
  SafetyCertificateOutlined,
} from '@ant-design/icons';

export function statusTag(status: string) {
  switch (status) {
    case 'RECOVERED':
      return <Tag color="success" icon={<CheckCircleOutlined />}>Recovered</Tag>;
    case 'PROMISED_TO_PAY':
      return <Tag color="cyan" icon={<ClockCircleOutlined />}>Promised To Pay</Tag>;
    case 'AWAITING_APPROVAL':
      return <Tag color="warning" icon={<ExclamationCircleOutlined />}>Awaiting Approval</Tag>;
    case 'SCHEDULED':
      return <Tag color="gold" icon={<ClockCircleOutlined />}>Scheduled</Tag>;
    case 'DIAGNOSING':
    case 'AWAITING_POLICY':
    case 'ACTION_IN_PROGRESS':
    case 'MONITORING':
      return <Tag color="processing" icon={<SyncOutlined spin />}>{status.replace(/_/g, ' ')}</Tag>;
    case 'EXHAUSTED':
      return <Tag color="error" icon={<CloseCircleOutlined />}>Exhausted</Tag>;
    case 'OPTED_OUT':
    case 'STOPPED':
      return <Tag color="default" icon={<StopOutlined />}>{status.replace(/_/g, ' ')}</Tag>;
    case 'ERROR':
      return <Tag color="error">{status}</Tag>;
    default:
      return <Tag color="blue">{status?.replace(/_/g, ' ') || 'NEW'}</Tag>;
  }
}

export function categoryTag(cat: string) {
  switch (cat) {
    case 'INSUFFICIENT_FUNDS':
      return <Tag color="magenta">Insufficient Funds</Tag>;
    case 'BANK_TIMEOUT':
      return <Tag color="orange">Bank Timeout</Tag>;
    case 'EXPIRED_CARD':
      return <Tag color="volcano">Expired Card</Tag>;
    case 'MANDATE_REVOKED':
      return <Tag color="red">Mandate Revoked</Tag>;
    case 'LIMIT_EXCEEDED':
      return <Tag color="gold">Limit Exceeded</Tag>;
    case 'NETWORK_FAILURE':
      return <Tag color="blue">Network Failure</Tag>;
    case 'CUSTOMER_ACTION_REQUIRED':
      return <Tag color="purple">Action Required</Tag>;
    default:
      return <Tag color="default">{cat?.replace(/_/g, ' ') || 'Unknown'}</Tag>;
  }
}

export function actionTag(action: string) {
  switch (action) {
    case 'WAIT_FOR_RETRY':
      return <Tag color="blue">Wait For Retry</Tag>;
    case 'SEND_PAYMENT_LINK':
      return <Tag color="green">Send Payment Link</Tag>;
    case 'REQUEST_METHOD_UPDATE':
      return <Tag color="purple">Request Method Update</Tag>;
    case 'SEND_REMINDER':
      return <Tag color="cyan">Send Reminder</Tag>;
    case 'HUMAN_REVIEW':
      return <Tag color="orange" icon={<SafetyCertificateOutlined />}>Human Review</Tag>;
    case 'STOP':
      return <Tag color="default">Stop</Tag>;
    default:
      return <Tag>{action?.replace(/_/g, ' ')}</Tag>;
  }
}

// Retain legacy helpers for backwards compatibility
export const statusBadge = statusTag;
export const categoryBadge = categoryTag;
