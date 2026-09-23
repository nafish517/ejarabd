import React, { useState, useEffect } from 'react';
import {
  Sliders,
  Play,
  Square,
  Clock,
  CheckCircle2,
  ShieldCheck,
  RefreshCw,
  Zap,
  Database
} from 'lucide-react';
import type { AutomationStatus } from '../types';
import { api } from '../services/api';

interface AutomationViewProps {
  onShowToast: (msg: string) => void;
  onRefreshOverview: () => void;
}

export const AutomationView: React.FC<AutomationViewProps> = ({
  onShowToast,
  onRefreshOverview,
}) => {
  const [status, setStatus] = useState<AutomationStatus | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isToggling, setIsToggling] = useState(false);

  const fetchStatus = async () => {
    try {
      setIsLoading(true);
      const res = await api.getAutomationStatus();
      setStatus(res);
    } catch (err) {
      console.error('Failed to load automation status:', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    let isMounted = true;
    const poll = async () => {
      try {
        const res = await api.getAutomationStatus();
        if (isMounted) setStatus(res);
      } catch (err) {
        console.error('Failed to load automation status:', err);
      }
    };

    void poll();
    const interval = setInterval(poll, 15000);
    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, []);

  const handleToggleScheduler = async () => {
    if (!status) return;
    setIsToggling(true);
    try {
      if (status.scheduler_running) {
        await api.stopScheduler();
        onShowToast('■ Background scheduler daemon stopped.');
      } else {
        await api.startScheduler();
        onShowToast('▶ Background scheduler daemon started (Asia/Dhaka BST).');
      }
      await fetchStatus();
      onRefreshOverview();
    } catch {
      onShowToast('Failed to toggle scheduler.');
    } finally {
      setIsToggling(false);
    }
  };

  const isRunning = status?.scheduler_running ?? false;

  return (
    <div>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '20px', flexWrap: 'wrap', gap: '12px' }}>
        <div>
          <h2 style={{ fontSize: '20px', fontWeight: 600, color: 'var(--text-primary)' }}>
            Automation & Background Scheduling (অটোমেশন কন্ট্রোল)
          </h2>
          <p style={{ fontSize: '13px', color: 'var(--text-muted)' }}>
            Asia/Dhaka (BST) background scheduler daemon with persistent slot deduplication.
          </p>
        </div>

        <div style={{ display: 'flex', gap: '10px' }}>
          <button className="btn btn-secondary btn-sm" onClick={fetchStatus} disabled={isLoading}>
            <RefreshCw size={13} className={isLoading ? 'animate-spin' : ''} />
            <span>Refresh Telemetry</span>
          </button>

          <button
            className={`btn ${isRunning ? 'btn-danger' : 'btn-outline-emerald'}`}
            onClick={handleToggleScheduler}
            disabled={isToggling}
          >
            {isRunning ? <Square size={14} /> : <Play size={14} />}
            <span>{isRunning ? 'Stop Scheduler Daemon' : 'Start Scheduler Daemon'}</span>
          </button>
        </div>
      </div>

      {/* Scheduler Status Grid */}
      <div className="metrics-grid">
        <div className="metric-card">
          <div className="metric-header">
            <span className="metric-label">Scheduler Daemon</span>
            <div className="metric-icon-wrap">
              <Sliders size={16} />
            </div>
          </div>
          <div>
            <div className="metric-value" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <div className={`pulse-dot ${isRunning ? 'text-emerald-400' : 'text-slate-400'}`} />
              <span>{isRunning ? 'Running' : 'Stopped'}</span>
            </div>
            <div className="metric-meta">
              <span>Truthful process status ({status?.active_threads ?? 0} active threads)</span>
            </div>
          </div>
        </div>

        <div className="metric-card">
          <div className="metric-header">
            <span className="metric-label">Timezone Standard</span>
            <div className="metric-icon-wrap">
              <Clock size={16} />
            </div>
          </div>
          <div>
            <div className="metric-value mono-cell" style={{ fontSize: '20px' }}>
              {status?.current_time_bst || 'Loading...'}
            </div>
            <div className="metric-meta">
              <span className="badge badge-slate">{status?.timezone || 'Asia/Dhaka (UTC+6)'}</span>
            </div>
          </div>
        </div>

        <div className="metric-card">
          <div className="metric-header">
            <span className="metric-label">Eligible Clients in Scope</span>
            <div className="metric-icon-wrap">
              <ShieldCheck size={16} />
            </div>
          </div>
          <div>
            <div className="metric-value">
              {status?.active_clients_in_scope ?? 0}
            </div>
            <div className="metric-meta">
              <span className="badge badge-emerald">Paid + Onboarded + Prod</span>
            </div>
          </div>
        </div>

        <div className="metric-card">
          <div className="metric-header">
            <span className="metric-label">Check Interval</span>
            <div className="metric-icon-wrap">
              <Zap size={16} />
            </div>
          </div>
          <div>
            <div className="metric-value mono-cell">
              {status?.check_interval_seconds ?? 60}s
            </div>
            <div className="metric-meta">
              <span>Deterministic slot checks</span>
            </div>
          </div>
        </div>
      </div>

      {/* Architecture Deep Dive Panel */}
      <div className="panel" style={{ marginTop: '24px' }}>
        <div className="panel-header">
          <div className="panel-title-wrap">
            <Database size={16} color="#38bdf8" />
            <h3 className="panel-title">Production Reliability & Deduplication Architecture</h3>
          </div>
          <span className="badge badge-emerald">Deterministic Guarantees</span>
        </div>
        <div className="panel-body">
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '20px' }}>
            <div style={{ background: 'var(--bg-card)', padding: '16px', borderRadius: '10px', border: '1px solid var(--border-subtle)' }}>
              <h4 style={{ fontSize: '14px', fontWeight: 600, color: 'var(--text-primary)', marginBottom: '8px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                <CheckCircle2 size={14} color="#34d399" />
                Persistent Slot-Level Deduplication
              </h4>
              <p style={{ fontSize: '12px', color: 'var(--text-secondary)', lineHeight: 1.6 }}>
                The background scheduler checks each client's <code className="mono-cell" style={{ color: 'var(--border-focus)' }}>notification_schedules</code> slots (e.g. 12:00, 19:00). Before sending an email, it queries the database for an existing record with composite key <code className="mono-cell" style={{ color: 'var(--border-focus)' }}>(contractor_id, schedule_date, schedule_slot)</code>. If found, it skips immediately.
              </p>
            </div>

            <div style={{ background: 'var(--bg-card)', padding: '16px', borderRadius: '10px', border: '1px solid var(--border-subtle)' }}>
              <h4 style={{ fontSize: '14px', fontWeight: 600, color: 'var(--text-primary)', marginBottom: '8px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                <CheckCircle2 size={14} color="#34d399" />
                Process Restart Resilience
              </h4>
              <p style={{ fontSize: '12px', color: 'var(--text-secondary)', lineHeight: 1.6 }}>
                Deduplication state is stored in SQLite (<code className="mono-cell">email_notification_records</code>), never in transient memory. If the backend server restarts, crashes, or reloads at 12:01, it will never re-send the 12:00 slot because the database already recorded it as sent.
              </p>
            </div>

            <div style={{ background: 'var(--bg-card)', padding: '16px', borderRadius: '10px', border: '1px solid var(--border-subtle)' }}>
              <h4 style={{ fontSize: '14px', fontWeight: 600, color: 'var(--text-primary)', marginBottom: '8px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                <CheckCircle2 size={14} color="#34d399" />
                Manual "Send Now" Independence
              </h4>
              <p style={{ fontSize: '12px', color: 'var(--text-secondary)', lineHeight: 1.6 }}>
                When an operator clicks "Send Now", it creates a record with <code className="mono-cell">schedule_date = None</code> and <code className="mono-cell">schedule_slot = None</code> under trigger type <code className="mono-cell">manual_operator_send</code>. It never consumes or affects the scheduled slots for that day.
              </p>
            </div>

            <div style={{ background: 'var(--bg-card)', padding: '16px', borderRadius: '10px', border: '1px solid var(--border-subtle)' }}>
              <h4 style={{ fontSize: '14px', fontWeight: 600, color: 'var(--text-primary)', marginBottom: '8px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                <CheckCircle2 size={14} color="#34d399" />
                100% Deterministic Core (AI-Offline)
              </h4>
              <p style={{ fontSize: '12px', color: 'var(--text-secondary)', lineHeight: 1.6 }}>
                Automated matching, schedule evaluation, and Bengali email template generation run entirely offline using deterministic Python rules. Local Ollama (Qwen) is reserved exclusively for optional, manual operator deep-dives.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
