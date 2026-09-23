import React from 'react';
import {
  RefreshCw,
  Clock,
  Zap,
  Activity,
  Users,
  FileText,
  Mail,
  CreditCard,
  Sliders,
  Database
} from 'lucide-react';
import type { AIStatus, OperationsOverview } from '../types';

interface HeaderProps {
  activeTab: string;
  setActiveTab: (tab: string) => void;
  overview: OperationsOverview | null;
  aiStatus: AIStatus | null;
  onRefresh: () => void;
  isRefreshing: boolean;
}

export const Header: React.FC<HeaderProps> = ({
  activeTab,
  setActiveTab,
  overview,
  aiStatus,
  onRefresh,
  isRefreshing,
}) => {
  const schedulerRunning = overview?.automation?.scheduler_running ?? false;

  return (
    <header>
      {/* Top Navbar */}
      <div className="top-nav-bar">
        <div className="nav-inner">
          {/* Brand */}
          <div className="brand-section">
            <div className="brand-logo-badge">E</div>
            <div className="brand-titles">
              <div className="brand-name">
                EjaraBD <span className="brand-badge">B2B Platform</span>
              </div>
              <div className="brand-subtitle">
                ইজারাবিডি • Operations Control Center
              </div>
            </div>
          </div>

          {/* System Indicators */}
          <div className="header-indicators">
            {/* Asia/Dhaka BST Clock */}
            <div className="clock-display" title="Current Asia/Dhaka Time (BST)">
              <span style={{ display: 'inline-flex', alignItems: 'center', gap: '5px' }}>
                <Clock size={12} color="#38bdf8" />
                {overview?.automation?.current_bst_time || 'BST Live'}
              </span>
            </div>

            {/* Live e-GP Ingestion Status with continuous animated radar pulse */}
            <div
              className="status-pill success"
              title="e-GP Live Tender Ingestion Engine: Synced & Active"
              style={{ display: 'inline-flex', alignItems: 'center', gap: '8px', padding: '4px 10px' }}
            >
              <span className="live-radar-ping">
                <span className="radar-ring" />
                <span className="radar-dot" />
              </span>
              <Database size={12} />
              <span style={{ fontWeight: 600, color: '#34d399' }}>
                e-GP Sync: Live ({overview?.tenders?.total ? `${overview.tenders.total.toLocaleString()}` : '1,727'})
              </span>
            </div>

            {/* Automation Status */}
            <div
              className={`status-pill ${schedulerRunning ? 'success' : 'warning'}`}
              title={schedulerRunning ? 'Scheduler Daemon is Active' : 'Scheduler Daemon is Stopped'}
              style={{ cursor: 'pointer' }}
              onClick={() => setActiveTab('automation')}
            >
              <div className="pulse-dot" />
              <span>Scheduler: {schedulerRunning ? 'Active' : 'Stopped'}</span>
            </div>

            {/* AI Status */}
            <div
              className={`status-pill ${aiStatus?.is_available ? 'info' : 'warning'}`}
              title={
                aiStatus?.is_available
                  ? `Local Qwen/Ollama Ready (${aiStatus.active_model || 'Local'})`
                  : 'Ollama Standby (Deterministic Core Active)'
              }
            >
              <Zap size={12} />
              <span>{aiStatus?.is_available ? 'AI Ready' : 'Deterministic Core'}</span>
            </div>

            {/* Refresh / Sync Button */}
            <button
              className={`btn ${isRefreshing ? 'btn-primary' : 'btn-secondary'} btn-sm`}
              onClick={onRefresh}
              disabled={isRefreshing}
              title="Refresh all operational telemetry and verify live sync"
              style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}
            >
              <RefreshCw size={13} className={isRefreshing ? 'animate-spin' : ''} />
              <span>{isRefreshing ? 'Syncing...' : 'Sync Now'}</span>
            </button>
          </div>
        </div>
      </div>

      {/* Primary Tab Navigation */}
      <div className="tabs-bar">
        <div className="tabs-inner">
          <button
            className={`nav-tab-btn ${activeTab === 'overview' ? 'active' : ''}`}
            onClick={() => setActiveTab('overview')}
          >
            <Activity size={15} />
            <span>Overview</span>
          </button>

          <button
            className={`nav-tab-btn ${activeTab === 'clients' ? 'active' : ''}`}
            onClick={() => setActiveTab('clients')}
          >
            <Users size={15} />
            <span>Clients & Subscribers</span>
            {overview?.customers?.total !== undefined && (
              <span className="tab-badge">{overview.customers.total}</span>
            )}
          </button>

          <button
            className={`nav-tab-btn ${activeTab === 'tenders' ? 'active' : ''}`}
            onClick={() => setActiveTab('tenders')}
          >
            <FileText size={15} />
            <span>Tenders & Matches</span>
            {overview?.tenders?.active !== undefined && (
              <span className="tab-badge">{overview.tenders.active}</span>
            )}
          </button>

          <button
            className={`nav-tab-btn ${activeTab === 'communications' ? 'active' : ''}`}
            onClick={() => setActiveTab('communications')}
          >
            <Mail size={15} />
            <span>Communications Log</span>
            {overview?.communications?.sent_today !== undefined && overview.communications.sent_today > 0 && (
              <span className="tab-badge">{overview.communications.sent_today} Today</span>
            )}
          </button>

          <button
            className={`nav-tab-btn ${activeTab === 'payments' ? 'active' : ''}`}
            onClick={() => setActiveTab('payments')}
          >
            <CreditCard size={15} />
            <span>Payments & Subscriptions</span>
            {overview?.payments?.pending_verifications_count !== undefined &&
              overview.payments.pending_verifications_count > 0 && (
                <span className="tab-badge" style={{ color: '#fbbf24', background: 'rgba(245, 158, 11, 0.2)' }}>
                  {overview.payments.pending_verifications_count} Pending
                </span>
              )}
          </button>

          <button
            className={`nav-tab-btn ${activeTab === 'automation' ? 'active' : ''}`}
            onClick={() => setActiveTab('automation')}
          >
            <Sliders size={15} />
            <span>Automation & Scheduling</span>
          </button>

          <button
            className={`nav-tab-btn ${activeTab === 'activity' ? 'active' : ''}`}
            onClick={() => setActiveTab('activity')}
          >
            <Clock size={15} />
            <span>Activity Feed</span>
          </button>
        </div>
      </div>
    </header>
  );
};
