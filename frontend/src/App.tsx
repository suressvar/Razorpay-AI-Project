import { useState } from 'react';
import { Routes, Route, useNavigate, useLocation } from 'react-router-dom';
import { Layout, Menu, ConfigProvider, Tag, Typography, Space, Select, Switch } from 'antd';
import {
  DashboardOutlined,
  UnorderedListOutlined,
  UserSwitchOutlined,
  ExperimentOutlined,
  RobotOutlined,
  DisconnectOutlined,
  DatabaseOutlined,
  SettingOutlined,
  CheckCircleFilled,
} from '@ant-design/icons';
import { RazorpayLogo } from './components/RazorpayLogo';
import Overview from './pages/Overview';
import Cases from './pages/Cases';
import CaseDetail from './pages/CaseDetail';
import HumanReview from './pages/HumanReview';
import Evaluation from './pages/Evaluation';
import Copilot from './pages/Copilot';
import UnmatchedEvents from './pages/UnmatchedEvents';
import AccountSettings from './pages/AccountSettings';

import { PlayCircleOutlined } from '@ant-design/icons';
import InteractiveDemoTour from './components/InteractiveDemoTour';

const { Header, Content, Sider } = Layout;
const { Text } = Typography;

export default function App() {
  const navigate = useNavigate();
  const location = useLocation();
  const [dataMode, setDataMode] = useState<string>('live');
  const [isTourOpen, setIsTourOpen] = useState<boolean>(false);

  // Determine active menu item
  const getSelectedKey = () => {
    const path = location.pathname;
    if (path === '/') return 'overview';
    if (path.startsWith('/copilot')) return 'copilot';
    if (path.startsWith('/cases')) return 'cases';
    if (path.startsWith('/review')) return 'review';
    if (path.startsWith('/unmatched')) return 'unmatched';
    if (path.startsWith('/evaluation')) return 'evaluation';
    if (path.startsWith('/settings')) return 'settings';
    return 'overview';
  };

  const menuItems = [
    {
      key: 'overview',
      icon: <DashboardOutlined style={{ fontSize: 16 }} />,
      label: 'Overview & Metrics',
      onClick: () => navigate('/'),
    },
    {
      key: 'copilot',
      icon: <RobotOutlined style={{ fontSize: 16 }} />,
      label: 'AI Copilot',
      onClick: () => navigate('/copilot'),
    },
    {
      key: 'cases',
      icon: <UnorderedListOutlined style={{ fontSize: 16 }} />,
      label: 'Recovery Cases',
      onClick: () => navigate('/cases'),
    },
    {
      key: 'review',
      icon: <UserSwitchOutlined style={{ fontSize: 16 }} />,
      label: 'Human Review Queue',
      onClick: () => navigate('/review'),
    },
    {
      key: 'unmatched',
      icon: <DisconnectOutlined style={{ fontSize: 16 }} />,
      label: 'Unmatched Webhooks',
      onClick: () => navigate('/unmatched'),
    },
    {
      key: 'evaluation',
      icon: <ExperimentOutlined style={{ fontSize: 16 }} />,
      label: 'Benchmark & Lab',
      onClick: () => navigate('/evaluation'),
    },
  ];


  return (
    <ConfigProvider
      theme={{
        token: {
          colorPrimary: '#0052cc', // Razorpay electric blue
          colorInfo: '#0052cc',
          colorSuccess: '#10b981',
          colorWarning: '#f59e0b',
          colorError: '#ef4444',
          borderRadius: 8,
          fontFamily: `-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif`,
        },
        components: {
          Menu: {
            itemBg: 'transparent',
            itemColor: '#94a3b8',
            itemHoverColor: '#ffffff',
            itemHoverBg: 'rgba(255, 255, 255, 0.08)',
            itemSelectedColor: '#ffffff',
            itemSelectedBg: '#0052cc',
            itemBorderRadius: 8,
            itemMarginInline: 8,
          },
          Table: {
            headerBg: '#f8fafc',
            headerColor: '#475569',
            borderColor: '#e2e8f0',
            rowHoverBg: '#f1f5f9',
          },
          Card: {
            headerBg: '#ffffff',
          },
        },
      }}
    >
      <Layout style={{ minHeight: '100vh', background: '#f4f6f8' }}>
        {/* Fixed Enterprise Sidebar */}
        <Sider
          width={260}
          style={{
            background: '#0a192f',
            borderRight: '1px solid #1e293b',
            display: 'flex',
            flexDirection: 'column',
            position: 'fixed',
            left: 0,
            top: 0,
            bottom: 0,
            height: '100vh',
            zIndex: 100,
            overflowY: 'auto',
          }}
          breakpoint="lg"
          collapsedWidth="0"
        >
          {/* Brand Logo with Razorpay Branding */}
          <div className="px-5 py-4 border-b border-slate-800">
            <RazorpayLogo height={26} showAutopilotBadge={true} />
            <div className="text-[10px] text-slate-400 font-medium tracking-wider uppercase mt-1">
              Autonomous Recovery Engine
            </div>
          </div>

          {/* Navigation Menu */}
          <div className="py-4 flex-1">
            <div className="px-4 pb-2 text-[10px] font-bold uppercase tracking-wider text-slate-500">
              Navigation
            </div>
            <Menu
              theme="dark"
              mode="inline"
              selectedKeys={[getSelectedKey()]}
              items={menuItems}
              style={{ background: 'transparent', border: 'none' }}
            />
          </div>

          {/* Bottom Left Corner: Account & Settings */}
          <div className="p-3 border-t border-slate-800/80 bg-slate-900/60 mt-auto">
            {/* Pinned Account & Settings Button */}
            <button
              onClick={() => navigate('/settings')}
              className={`w-full flex items-center justify-between px-3.5 py-2.5 rounded-lg text-xs font-semibold transition-all select-none ${
                location.pathname === '/settings'
                  ? 'bg-slate-100 text-slate-900 shadow font-bold'
                  : 'text-slate-300 hover:text-white hover:bg-slate-800/80'
              }`}
            >
              <span className="flex items-center gap-2.5">
                <SettingOutlined className={`text-sm ${location.pathname === '/settings' ? 'text-slate-900' : 'text-slate-400'}`} />
                <span>Account & Settings</span>
              </span>
              {location.pathname === '/settings' && (
                <CheckCircleFilled className="text-blue-600 text-xs" />
              )}
            </button>
          </div>
        </Sider>

        {/* Main Content Layout (Offset by fixed sidebar) */}
        <Layout style={{ background: '#f4f6f8', marginLeft: 260, minHeight: '100vh', transition: 'all 0.2s' }}>
          {/* Top Enterprise Header */}
          <Header
            style={{
              background: '#ffffff',
              padding: '0 28px',
              height: 60,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              borderBottom: '1px solid #e2e8f0',
              position: 'sticky',
              top: 0,
              zIndex: 50,
            }}
          >
            <div className="flex items-center gap-3">
              {/* Data Mode Selector */}
              <div className="flex items-center gap-2 bg-slate-100 p-1 rounded-lg border border-slate-200">
                <Text strong className="text-xs text-slate-500 pl-2">
                  <DatabaseOutlined className="mr-1" /> Source:
                </Text>
                <Select
                  size="small"
                  value={dataMode}
                  onChange={(val) => {
                    setDataMode(val);
                    if (val === 'benchmark') navigate('/evaluation');
                    else if (val === 'live') navigate('/cases');
                  }}
                  style={{ width: 175 }}
                  bordered={false}
                  options={[
                    { value: 'live', label: '⚡ Live Cases' },
                    { value: 'benchmark', label: '🧪 Synthetic Benchmark' },
                    { value: 'razorpay_test', label: '💳 Razorpay Test Mode' },
                  ]}
                />
              </div>

              {dataMode === 'benchmark' ? (
                <Tag color="purple" style={{ fontSize: 11, padding: '2px 8px', borderRadius: 4 }}>
                  SIMULATED DATA
                </Tag>
              ) : dataMode === 'razorpay_test' ? (
                <Tag color="cyan" style={{ fontSize: 11, padding: '2px 8px', borderRadius: 4 }}>
                  RAZORPAY TEST API
                </Tag>
              ) : (
                <Tag color="geekblue" style={{ fontSize: 11, padding: '2px 8px', borderRadius: 4 }}>
                  DATABASE CASES
                </Tag>
              )}
            </div>

            <Space size="middle">
              <button
                onClick={() => setIsTourOpen(true)}
                className="flex items-center gap-2 px-3.5 py-1.5 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white rounded-lg text-xs font-bold shadow-md shadow-blue-500/20 transition cursor-pointer select-none"
                id="header-live-tour-btn"
              >
                <PlayCircleOutlined className="text-sm animate-pulse" />
                <span>⚡ Live Demo Tour (5-Step)</span>
              </button>

              <div className="flex items-center gap-2 px-3 py-1 bg-emerald-50 border border-emerald-200 rounded-md">
                <span className="w-2 h-2 rounded-full bg-emerald-500 animate-ping" />
                <span className="text-xs font-semibold text-emerald-800">AI Agent Active</span>
              </div>
            </Space>
          </Header>

          {/* Page Content */}
          <Content style={{ padding: '24px 28px', minHeight: 'calc(100vh - 60px)' }}>
            <InteractiveDemoTour open={isTourOpen} onClose={() => setIsTourOpen(false)} />
            <Routes>
              <Route path="/" element={<Overview />} />
              <Route path="/copilot" element={<Copilot />} />
              <Route path="/cases" element={<Cases />} />
              <Route path="/cases/:caseId" element={<CaseDetail />} />
              <Route path="/review" element={<HumanReview />} />
              <Route path="/unmatched" element={<UnmatchedEvents />} />
              <Route path="/evaluation" element={<Evaluation />} />
              <Route path="/settings" element={<AccountSettings />} />
            </Routes>
          </Content>
        </Layout>
      </Layout>
    </ConfigProvider>
  );
}
