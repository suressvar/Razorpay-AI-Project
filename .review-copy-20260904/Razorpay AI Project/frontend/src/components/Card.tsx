import React from 'react';
import { Card as AntCard, Typography, Spin, Empty, Result, Button, Space } from 'antd';
import { LoadingOutlined, ArrowUpOutlined, ArrowDownOutlined, MinusOutlined } from '@ant-design/icons';

const { Title, Text } = Typography;

interface CardProps {
  children: React.ReactNode;
  className?: string;
  title?: React.ReactNode;
  extra?: React.ReactNode;
  bordered?: boolean;
}

export function Card({ children, className, title, extra, bordered = true }: CardProps) {
  return (
    <AntCard
      title={title}
      extra={extra}
      bordered={bordered}
      className={`bg-white shadow-sm border border-slate-200 rounded-xl ${className || ''}`}
      headStyle={{ borderBottom: '1px solid #f1f5f9', fontWeight: 600, fontSize: 14 }}
      bodyStyle={{ padding: '20px' }}
    >
      {children}
    </AntCard>
  );
}

interface KpiCardProps {
  label: string;
  value: string | number;
  sub?: string;
  icon?: React.ReactNode;
  trend?: 'up' | 'down' | 'neutral';
  trendValue?: string;
  badgeColor?: string;
  accentBorder?: string;
}

export function KpiCard({
  label,
  value,
  sub,
  icon,
  trend,
  trendValue,
  badgeColor = '#0052cc',
}: KpiCardProps) {
  return (
    <AntCard
      className="bg-white shadow-sm border border-slate-200 rounded-xl transition-all hover:shadow-md hover:border-blue-300"
      bodyStyle={{ padding: '18px 20px' }}
    >
      <div className="flex items-start justify-between">
        <div>
          <Text type="secondary" className="text-xs uppercase font-semibold tracking-wider text-slate-500">
            {label}
          </Text>
          <div className="mt-1">
            <span className="text-2xl font-bold text-slate-900 tracking-tight">{value}</span>
          </div>
          {sub && <p className="text-xs text-slate-500 mt-1 font-medium">{sub}</p>}
          {trendValue && (
            <div className="mt-2 flex items-center gap-1.5 text-xs font-semibold">
              {trend === 'up' && <span className="text-emerald-600 flex items-center gap-0.5"><ArrowUpOutlined /> {trendValue}</span>}
              {trend === 'down' && <span className="text-rose-600 flex items-center gap-0.5"><ArrowDownOutlined /> {trendValue}</span>}
              {trend === 'neutral' && <span className="text-slate-500 flex items-center gap-0.5"><MinusOutlined /> {trendValue}</span>}
            </div>
          )}
        </div>
        {icon && (
          <div
            className="w-10 h-10 rounded-lg flex items-center justify-center text-lg"
            style={{ backgroundColor: `${badgeColor}15`, color: badgeColor }}
          >
            {icon}
          </div>
        )}
      </div>
    </AntCard>
  );
}

export function Spinner({ size = 24 }: { size?: number; className?: string }) {
  const antIcon = <LoadingOutlined style={{ fontSize: size, color: '#0052cc' }} spin />;
  return <Spin indicator={antIcon} />;
}

export function PageHeader({
  title,
  subtitle,
  actions,
}: {
  title: string;
  subtitle?: string;
  actions?: React.ReactNode;
}) {
  return (
    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6 pb-4 border-b border-slate-200">
      <div>
        <Title level={4} style={{ margin: 0, color: '#0f172a', fontWeight: 700 }}>
          {title}
        </Title>
        {subtitle && (
          <Text type="secondary" className="text-xs sm:text-sm text-slate-500 mt-0.5 block">
            {subtitle}
          </Text>
        )}
      </div>
      {actions && <div className="flex items-center gap-2.5 flex-wrap">{actions}</div>}
    </div>
  );
}

export function EmptyState({ message, action }: { message: string; action?: React.ReactNode }) {
  return (
    <div className="py-16 bg-white rounded-xl border border-slate-200 flex flex-col items-center justify-center">
      <Empty description={<span className="text-slate-500 text-sm">{message}</span>}>
        {action}
      </Empty>
    </div>
  );
}

export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <Result
      status="error"
      title="Something went wrong"
      subTitle={message}
      extra={
        onRetry && (
          <Button type="primary" onClick={onRetry}>
            Try Again
          </Button>
        )
      }
    />
  );
}
