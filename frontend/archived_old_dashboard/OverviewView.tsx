import React from 'react';
import {
  Users,
  FileText,
  Mail,
  CreditCard,
  Sliders,
  Play,
  Square,
  ArrowUpRight,
  ShieldCheck,
  Clock,
  Sparkles
} from 'lucide-react';
import type { OperationsOverview, ActivityEvent } from '../types';

interface OverviewViewProps {
  overview: OperationsOverview | null;
  activityEvents: ActivityEvent[];
  onNavigateTab: (tab: string) => void;
  onOpenNewClientModal: () => void;
  onToggleScheduler: () => void;
  onRunMatching: () => void;
  isMatchingRunning: boolean;
}

export const OverviewView: React.FC<OverviewViewProps> = ({
  overview,
  activityEvents,
  onNavigateTab,
  onOpenNewClientModal,
  onToggleScheduler,
  onRunMatching,
  isMatchingRunning,
}) => {
  const schedulerRunning = overview?.automation?.scheduler_running ?? false;

  return (
    <div>
      {/* Top Metrics Grid */}
      <div className="metrics-grid">
        {/* Clients KPI */}
        <div className="metric-card" style={{ cursor: 'pointer' }} onClick={() => onNavigateTab('clients')}>
          <div className="metric-header">
            <span className="metric-label">Active Clients</span>
            <div className="metric-icon-wrap">
              <Users size={16} />
            </div>
          </div>
          <div>
            <div className="metric-value">
              {overview?.customers?.active ?? 0}
              <span style={{ fontSize: '15px', color: 'var(--text-muted)', fontWeight: 400 }}>
                {' '}/ {overview?.customers?.total ?? 0} Total
              </span>
            </div>
            <div className="metric-meta">
              <span className="badge badge-amber">{overview?.customers?.lead_payment_pending ?? 0} Leads Pending</span>
              <span className="badge badge-cyan">{overview?.customers?.onboarding ?? 0} Onboarding</span>
            </div>
          </div>
        </div>

        {/* Tenders KPI */}
        <div className="metric-card" style={{ cursor: 'pointer' }} onClick={() => onNavigateTab('tenders')}>
          <div className="metric-header">
            <span className="metric-label">Database Tenders</span>
            <div className="metric-icon-wrap">
              <FileText size={16} />
            </div>
          </div>
          <div>
            <div className="metric-value">
              {(overview?.tenders?.total ?? 0).toLocaleString()}
            </div>
            <div className="metric-meta">
              <span className="badge badge-emerald">{overview?.tenders?.active ?? 0} Active e-GP Tenders</span>
              <span style={{ color: 'var(--text-muted)' }}>Preserved</span>
            </div>
          </div>
        </div>

        {/* Communications KPI */}
        <div className="metric-card" style={{ cursor: 'pointer' }} onClick={() => onNavigateTab('communications')}>
          <div className="metric-header">
            <span className="metric-label">Emails Dispatched Today</span>
            <div className="metric-icon-wrap">
              <Mail size={16} />
            </div>
          </div>
          <div>
            <div className="metric-value">
              {overview?.communications?.sent_today ?? 0}
            </div>
            <div className="metric-meta">
              <span className="badge badge-cyan">{overview?.communications?.scheduled_sent_today ?? 0} Scheduled</span>
              <span className="badge badge-indigo">{overview?.communications?.manual_sent_today ?? 0} Manual</span>
            </div>
          </div>
        </div>

        {/* Payments KPI */}
        <div className="metric-card" style={{ cursor: 'pointer' }} onClick={() => onNavigateTab('payments')}>
          <div className="metric-header">
            <span className="metric-label">Confirmed Revenue</span>
            <div className="metric-icon-wrap">
              <CreditCard size={16} />
            </div>
          </div>
          <div>
            <div className="metric-value">
              ৳{(overview?.payments?.confirmed_revenue_bdt ?? 0).toLocaleString()}
            </div>
            <div className="metric-meta">
              {overview?.payments?.pending_verifications_count ? (
                <span className="badge badge-amber">{overview.payments.pending_verifications_count} Pending Review</span>
              ) : (
                <span className="badge badge-emerald">All payments verified</span>
              )}
            </div>
          </div>
        </div>

        {/* Scheduler KPI */}
        <div className="metric-card" style={{ cursor: 'pointer' }} onClick={() => onNavigateTab('automation')}>
          <div className="metric-header">
            <span className="metric-label">Asia/Dhaka Scheduler</span>
            <div className="metric-icon-wrap">
              <Sliders size={16} />
            </div>
          </div>
          <div>
            <div className="metric-value" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span className={`pulse-dot ${schedulerRunning ? 'text-emerald-400' : 'text-slate-400'}`} />
              <span style={{ fontSize: '20px' }}>{schedulerRunning ? 'Running' : 'Stopped'}</span>
            </div>
            <div className="metric-meta">
              <span className="badge badge-slate">{overview?.automation?.processed_slots_today ?? 0} Slots Run Today</span>
            </div>
          </div>
        </div>
      </div>

      {/* Operational Quick Actions Panel */}
      <div className="panel" style={{ marginBottom: '24px' }}>
        <div className="panel-header">
          <div className="panel-title-wrap">
            <ShieldCheck size={16} color="#38bdf8" />
            <h2 className="panel-title">Operator Control Actions</h2>
          </div>
          <span className="panel-subtitle">Deterministic Operations & Controls</span>
        </div>
        <div className="panel-body" style={{ display: 'flex', flexWrap: 'wrap', gap: '12px' }}>
          <button className="btn btn-primary" onClick={onOpenNewClientModal}>
            <Users size={14} />
            <span>+ New Client Onboarding</span>
          </button>

          <button
            className="btn btn-secondary"
            onClick={onRunMatching}
            disabled={isMatchingRunning}
          >
            <Sparkles size={14} color="#38bdf8" />
            <span>{isMatchingRunning ? 'Matching Running...' : 'Execute Deterministic Matching'}</span>
          </button>

          <button
            className={`btn ${schedulerRunning ? 'btn-danger' : 'btn-outline-emerald'}`}
            onClick={onToggleScheduler}
          >
            {schedulerRunning ? <Square size={14} /> : <Play size={14} />}
            <span>{schedulerRunning ? 'Stop Scheduler Daemon' : 'Start Scheduler Daemon'}</span>
          </button>

          <button className="btn btn-secondary" onClick={() => onNavigateTab('communications')}>
            <Mail size={14} />
            <span>View Communication Audit Log</span>
            <ArrowUpRight size={13} />
          </button>
        </div>
      </div>

      {/* Two Column Layout: System Status & Live Activity */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(400px, 1fr))', gap: '20px' }}>
        {/* System Architecture & Status */}
        <div className="panel">
          <div className="panel-header">
            <h3 className="panel-title">Platform Architecture Status</h3>
            <span className="badge badge-emerald">Verified</span>
          </div>
          <div className="panel-body">
            <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', paddingBottom: '10px', borderBottom: '1px solid var(--border-subtle)' }}>
                <span style={{ color: 'var(--text-secondary)', fontSize: '13px' }}>Multi-Client Isolation</span>
                <span className="badge badge-emerald">Enforced (Separate Profiles)</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', paddingBottom: '10px', borderBottom: '1px solid var(--border-subtle)' }}>
                <span style={{ color: 'var(--text-secondary)', fontSize: '13px' }}>New Client Initial State</span>
                <span className="badge badge-amber">lead_payment_pending / unconfirmed</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', paddingBottom: '10px', borderBottom: '1px solid var(--border-subtle)' }}>
                <span style={{ color: 'var(--text-secondary)', fontSize: '13px' }}>Daily Email Schedule Truth</span>
                <span className="mono-cell" style={{ color: 'var(--border-focus)' }}>notification_schedules array</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', paddingBottom: '10px', borderBottom: '1px solid var(--border-subtle)' }}>
                <span style={{ color: 'var(--text-secondary)', fontSize: '13px' }}>Slot Deduplication</span>
                <span className="badge badge-cyan">(contractor_id, date, slot)</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', paddingBottom: '10px', borderBottom: '1px solid var(--border-subtle)' }}>
                <span style={{ color: 'var(--text-secondary)', fontSize: '13px' }}>Timezone Standard</span>
                <span className="mono-cell" style={{ color: '#f8fafc' }}>Asia/Dhaka (BST, UTC+6)</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--text-secondary)', fontSize: '13px' }}>Automated AI Dependencies</span>
                <span className="badge badge-slate">Zero (100% Deterministic Core)</span>
              </div>
            </div>
          </div>
        </div>

        {/* Recent Activity Log */}
        <div className="panel">
          <div className="panel-header">
            <h3 className="panel-title">Recent Operational Activity</h3>
            <button className="btn btn-secondary btn-sm" onClick={() => onNavigateTab('activity')}>
              <span>View All</span>
              <ArrowUpRight size={12} />
            </button>
          </div>
          <div className="panel-body" style={{ padding: '0 20px' }}>
            {!Array.isArray(activityEvents) || activityEvents.length === 0 ? (
              <div style={{ padding: '32px 0', textAlign: 'center', color: 'var(--text-muted)', fontSize: '13px' }}>
                No activity recorded yet.
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column' }}>
                {(Array.isArray(activityEvents) ? activityEvents : []).slice(0, 7).map((ev) => (
                  <div
                    key={ev.id}
                    style={{
                      padding: '12px 0',
                      borderBottom: '1px solid var(--border-subtle)',
                      display: 'flex',
                      alignItems: 'flex-start',
                      gap: '12px',
                    }}
                  >
                    <div style={{ marginTop: '2px' }}>
                      {ev.event_type.includes('payment') ? (
                        <CreditCard size={14} color="#34d399" />
                      ) : ev.event_type.includes('email') ? (
                        <Mail size={14} color="#38bdf8" />
                      ) : ev.event_type.includes('client') ? (
                        <Users size={14} color="#818cf8" />
                      ) : (
                        <Clock size={14} color="#94a3b8" />
                      )}
                    </div>
                    <div style={{ flex: 1 }}>
                      <div style={{ fontSize: '13px', fontWeight: 500, color: 'var(--text-primary)' }}>
                        {ev.title}
                      </div>
                      <div style={{ fontSize: '11px', color: 'var(--text-muted)', display: 'flex', gap: '8px' }}>
                        {ev.contractor_name && <span>Client: {ev.contractor_name}</span>}
                        <span>•</span>
                        <span>{new Date(ev.created_at).toLocaleTimeString('bn-BD', { hour: '2-digit', minute: '2-digit' })} BST</span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
