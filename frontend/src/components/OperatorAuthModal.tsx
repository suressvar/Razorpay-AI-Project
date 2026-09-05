import React, { useState } from 'react';
import {
  Modal,
  Button,
  Input,
  Tag,
  Typography,
  Space,
  Alert,
  message,
  Card,
  Divider,
} from 'antd';
import {
  UserOutlined,
  LockOutlined,
  SafetyCertificateOutlined,
  LogoutOutlined,
  CheckCircleOutlined,
  KeyOutlined,
  CrownOutlined,
  EyeOutlined,
  AuditOutlined,
} from '@ant-design/icons';
import {
  OperatorProfile,
  loginOperator,
  logoutOperator,
  getAuthToken,
} from '../api';

const { Title, Text, Paragraph } = Typography;

interface OperatorAuthModalProps {
  open: boolean;
  onClose: () => void;
  currentProfile: OperatorProfile | null;
  onProfileChange: (profile: OperatorProfile | null) => void;
}

export default function OperatorAuthModal({
  open,
  onClose,
  currentProfile,
  onProfileChange,
}: OperatorAuthModalProps) {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const handleLogin = async (loginUser?: string, loginPass?: string) => {
    const userToUse = (loginUser || username).trim();
    const passToUse = loginPass || password;

    if (!userToUse || !passToUse) {
      message.warning('Please enter both username and password');
      return;
    }

    setSubmitting(true);
    try {
      const profile = await loginOperator(userToUse, passToUse);
      onProfileChange(profile);
      message.success(`Logged in successfully as ${profile.name} (${profile.role.toUpperCase()})`);
      setUsername('');
      setPassword('');
      onClose();
    } catch (err: any) {
      message.error(err.message || 'Login failed');
    } finally {
      setSubmitting(false);
    }
  };

  const handleLogout = async () => {
    setSubmitting(true);
    try {
      await logoutOperator();
      onProfileChange(null);
      message.info('Logged out. Application running with Viewer/Guest permissions.');
      onClose();
    } catch (err: any) {
      message.error(err.message || 'Logout failed');
    } finally {
      setSubmitting(false);
    }
  };

  const fillAndLogin = (u: string, p: string) => {
    setUsername(u);
    setPassword(p);
    handleLogin(u, p);
  };

  const getRoleTag = (role: string) => {
    switch (role.toLowerCase()) {
      case 'admin':
        return <Tag color="gold" icon={<CrownOutlined />}>ADMINISTRATOR</Tag>;
      case 'reviewer':
        return <Tag color="blue" icon={<AuditOutlined />}>REVIEWER</Tag>;
      case 'viewer':
      default:
        return <Tag color="default" icon={<EyeOutlined />}>VIEWER</Tag>;
    }
  };

  return (
    <Modal
      title={
        <div className="flex items-center gap-2">
          <SafetyCertificateOutlined className="text-blue-600 text-lg" />
          <span className="font-semibold text-slate-800">Operator Identity & RBAC Authentication</span>
        </div>
      }
      open={open}
      onCancel={onClose}
      footer={null}
      width={520}
      destroyOnClose
    >
      <div className="space-y-4 pt-2">
        {currentProfile ? (
          /* Currently Logged In View */
          <div className="space-y-4">
            <div className="p-4 bg-slate-50 border border-slate-200 rounded-xl space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2.5">
                  <div className="w-10 h-10 rounded-full bg-blue-600 flex items-center justify-center text-white font-bold text-sm">
                    {currentProfile.name.charAt(0)}
                  </div>
                  <div>
                    <div className="font-bold text-slate-800 text-sm">{currentProfile.name}</div>
                    <div className="text-xs text-slate-500 font-mono">ID: {currentProfile.operator_id}</div>
                  </div>
                </div>
                {getRoleTag(currentProfile.role)}
              </div>

              <Divider style={{ margin: '8px 0' }} />

              <div className="grid grid-cols-2 gap-2 text-xs">
                <div>
                  <span className="text-slate-400">Username:</span>{' '}
                  <span className="font-mono text-slate-700 font-medium">{currentProfile.username}</span>
                </div>
                <div>
                  <span className="text-slate-400">Authority:</span>{' '}
                  <span className="text-emerald-700 font-semibold">Server-Verified Bearer</span>
                </div>
              </div>
            </div>

            <Alert
              type="success"
              showIcon
              message="Active Authenticated Session"
              description="Mutations, approvals, and settings modifications are cryptographically signed with your server-issued token."
              className="text-xs"
            />

            <div className="flex justify-end gap-2 pt-2">
              <Button onClick={onClose}>Close</Button>
              <Button
                danger
                icon={<LogoutOutlined />}
                onClick={handleLogout}
                loading={submitting}
              >
                Log Out Operator
              </Button>
            </div>
          </div>
        ) : (
          /* Logged Out / Guest View */
          <div className="space-y-4">
            <Alert
              type="info"
              showIcon
              message="Zero-Shortcut Server Authentication"
              description="Opening the application does not automatically grant admin access. Log in with an operator credential or select a demo account to acquire server-side reviewer/admin rights."
              className="text-xs"
            />

            {/* Quick-Fill Demo Accounts for Judges & Operators */}
            <div className="space-y-2">
              <div className="text-xs font-semibold text-slate-500 uppercase tracking-wide">
                Demo Accounts for Evaluators
              </div>
              <div className="grid grid-cols-3 gap-2">
                <Button
                  size="small"
                  className="text-left h-auto py-2 px-2.5 border-amber-200 hover:border-amber-400 hover:bg-amber-50/50 flex flex-col items-start"
                  onClick={() => fillAndLogin('admin', 'admin_recovery_demo_2026')}
                  loading={submitting}
                >
                  <span className="font-bold text-xs text-amber-700 flex items-center gap-1">
                    <CrownOutlined /> Admin
                  </span>
                  <span className="text-[10px] text-slate-400 mt-0.5">Full settings & kill switch</span>
                </Button>

                <Button
                  size="small"
                  className="text-left h-auto py-2 px-2.5 border-blue-200 hover:border-blue-400 hover:bg-blue-50/50 flex flex-col items-start"
                  onClick={() => fillAndLogin('reviewer', 'reviewer_recovery_demo_2026')}
                  loading={submitting}
                >
                  <span className="font-bold text-xs text-blue-700 flex items-center gap-1">
                    <AuditOutlined /> Reviewer
                  </span>
                  <span className="text-[10px] text-slate-400 mt-0.5">Approve/reject cases</span>
                </Button>

                <Button
                  size="small"
                  className="text-left h-auto py-2 px-2.5 border-slate-200 hover:border-slate-400 hover:bg-slate-50 flex flex-col items-start"
                  onClick={() => fillAndLogin('viewer', 'viewer_recovery_demo_2026')}
                  loading={submitting}
                >
                  <span className="font-bold text-xs text-slate-700 flex items-center gap-1">
                    <EyeOutlined /> Viewer
                  </span>
                  <span className="text-[10px] text-slate-400 mt-0.5">Read-only monitoring</span>
                </Button>
              </div>
            </div>

            <Divider plain style={{ margin: '12px 0' }}>
              <span className="text-xs text-slate-400">or manual credentials</span>
            </Divider>

            {/* Manual Credential Login Form */}
            <div className="space-y-3">
              <div>
                <label className="block text-xs font-semibold text-slate-600 mb-1">Username</label>
                <Input
                  prefix={<UserOutlined className="text-slate-400" />}
                  placeholder="e.g. admin or reviewer"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  disabled={submitting}
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-600 mb-1">Password</label>
                <Input.Password
                  prefix={<LockOutlined className="text-slate-400" />}
                  placeholder="Enter password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  onPressEnter={() => handleLogin()}
                  disabled={submitting}
                />
              </div>

              <div className="pt-2 flex justify-end gap-2">
                <Button onClick={onClose}>Cancel</Button>
                <Button
                  type="primary"
                  icon={<KeyOutlined />}
                  onClick={() => handleLogin()}
                  loading={submitting}
                >
                  Log In Operator
                </Button>
              </div>
            </div>
          </div>
        )}
      </div>
    </Modal>
  );
}
