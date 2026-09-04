import { Routes, Route, useNavigate, useLocation } from 'react-router-dom';
import { Layout, Menu, ConfigProvider, Tag, Typography, Badge as AntBadge, Avatar, Space } from 'antd';
import {
  DashboardOutlined,
  UnorderedListOutlined,
  UserSwitchOutlined,
  ExperimentOutlined,
  SafetyCertificateFilled,
} from '@ant-design/icons';
import { RazorpayLogo } from './components/RazorpayLogo';
import Overview from './pages/Overview';
import Cases from './pages/Cases';
import CaseDetail from './pages/CaseDetail';
import HumanReview from './pages/HumanReview';
import Evaluation from './pages/Evaluation';

const { Header, Content, Sider } = Layout;
const { Text } = Typography;

export default function App() {
  const navigate = useNavigate();
  const location = useLocation();

  // Determine active menu item
  const getSelectedKey = () => {
    const path = location.pathname;
    if (path === '/') return 'overview';
    if (path.startsWith('/cases')) return 'cases';
    if (path.startsWith('/review')) return 'review';
    if (path.startsWith('/evaluation')) return 'evaluation';
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
        {/* Modern Enterprise Sidebar */}
        <Sider
          width={260}
          style={{
            background: '#0a192f',
            borderRight: '1px solid #1e293b',
            display: 'flex',
            flexDirection: 'column',
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

          {/* Guardrails Safety Status Footer */}
          <div className="p-4 mx-3 mb-4 rounded-lg bg-slate-900/90 border border-slate-800 text-xs">
            <div className="flex items-center justify-between text-slate-300 font-semibold mb-1">
              <span className="flex items-center gap-1.5 text-blue-400">
                <SafetyCertificateFilled /> Guardrails Active
              </span>
              <span className="inline-block w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
            </div>
            <p className="text-[11px] text-slate-400 m-0 leading-tight">
              Safety-bounded execution with human-in-the-loop overrides.
            </p>
          </div>
        </Sider>

        {/* Main Content Layout */}
        <Layout style={{ background: '#f4f6f8' }}>
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
              zIndex: 10,
            }}
          >
            <div className="flex items-center gap-3">
              <Tag color="geekblue" style={{ fontSize: 12, padding: '2px 8px', borderRadius: 4 }}>
                TEST MODE
              </Tag>
              <Text className="text-xs text-slate-500 hidden sm:inline">
                Razorpay Subscription Recovery Engine v1.0
              </Text>
            </div>

            <Space size="middle">
              <div className="flex items-center gap-2 px-3 py-1 bg-emerald-50 border border-emerald-200 rounded-md">
                <span className="w-2 h-2 rounded-full bg-emerald-500 animate-ping" />
                <span className="text-xs font-semibold text-emerald-800">FastAPI & AI Agent Live</span>
              </div>
            </Space>
          </Header>

          {/* Page Content */}
          <Content style={{ padding: '24px 28px', minHeight: 'calc(100vh - 60px)' }}>
            <Routes>
              <Route path="/" element={<Overview />} />
              <Route path="/cases" element={<Cases />} />
              <Route path="/cases/:caseId" element={<CaseDetail />} />
              <Route path="/review" element={<HumanReview />} />
              <Route path="/evaluation" element={<Evaluation />} />
            </Routes>
          </Content>
        </Layout>
      </Layout>
    </ConfigProvider>
  );
}
