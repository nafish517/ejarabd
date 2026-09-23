import React, { useState, useMemo } from 'react';
import {
  Search,
  Eye,
  CheckCircle2,
  AlertCircle,
  Send
} from 'lucide-react';
import type { EmailNotificationRecord } from '../types';

interface CommunicationsViewProps {
  emails: EmailNotificationRecord[];
  onOpenTestEmailModal: () => void;
  onPreviewEmail: (email: EmailNotificationRecord) => void;
}

export const CommunicationsView: React.FC<CommunicationsViewProps> = ({
  emails,
  onOpenTestEmailModal,
  onPreviewEmail,
}) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [triggerFilter, setTriggerFilter] = useState('all');

  const filteredEmails = useMemo(() => {
    return emails.filter((e) => {
      const matchSearch =
        e.recipient_email.toLowerCase().includes(searchQuery.toLowerCase()) ||
        (e.recipient_name && e.recipient_name.toLowerCase().includes(searchQuery.toLowerCase())) ||
        e.subject.toLowerCase().includes(searchQuery.toLowerCase());

      if (!matchSearch) return false;

      if (triggerFilter !== 'all' && e.trigger_type !== triggerFilter) return false;

      return true;
    });
  }, [emails, searchQuery, triggerFilter]);

  return (
    <div>
      {/* Header & Controls */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '20px', flexWrap: 'wrap', gap: '12px' }}>
        <div>
          <h2 style={{ fontSize: '20px', fontWeight: 600, color: 'var(--text-primary)' }}>
            Communications Log & Audit Trail (ইমেইল অডিট)
          </h2>
          <p style={{ fontSize: '13px', color: 'var(--text-muted)' }}>
            Strict audit logging of all automated schedule slots and manual operator dispatches.
          </p>
        </div>

        <button className="btn btn-secondary" onClick={onOpenTestEmailModal}>
          <Send size={14} />
          <span>Send Test Email</span>
        </button>
      </div>

      {/* Filter Bar */}
      <div className="panel" style={{ marginBottom: '20px' }}>
        <div className="panel-body" style={{ padding: '14px 20px', display: 'flex', alignItems: 'center', gap: '16px', flexWrap: 'wrap' }}>
          {/* Search */}
          <div style={{ position: 'relative', flex: 1, minWidth: '240px' }}>
            <Search size={15} style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
            <input
              type="text"
              className="form-input"
              style={{ paddingLeft: '36px' }}
              placeholder="Search by recipient email, contractor name, or subject..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </div>

          {/* Trigger Filter */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Trigger Type:</span>
            <select
              className="form-select"
              style={{ width: 'auto' }}
              value={triggerFilter}
              onChange={(e) => setTriggerFilter(e.target.value)}
            >
              <option value="all">All Triggers</option>
              <option value="scheduled_automation">Scheduled Automation (শিডিউল)</option>
              <option value="manual_operator_send">Manual Operator Send (ম্যানুয়াল)</option>
              <option value="manual_test_send">Test Send (টেস্ট)</option>
            </select>
          </div>
        </div>
      </div>

      {/* Email Audit Table */}
      <div className="panel">
        <div className="table-container">
          <table className="data-table">
            <thead>
              <tr>
                <th>Recipient / Client</th>
                <th>Subject</th>
                <th>Trigger Source</th>
                <th>Schedule Slot</th>
                <th>Sent Timestamp (BST)</th>
                <th>Status</th>
                <th style={{ textAlign: 'right' }}>Preview</th>
              </tr>
            </thead>
            <tbody>
              {filteredEmails.length === 0 ? (
                <tr>
                  <td colSpan={7} style={{ textAlign: 'center', padding: '40px', color: 'var(--text-muted)' }}>
                    No communication records found matching your filters.
                  </td>
                </tr>
              ) : (
                filteredEmails.map((email) => {
                  return (
                    <tr key={email.id}>
                      <td>
                        <div style={{ display: 'flex', flexDirection: 'column' }}>
                          <span style={{ fontWeight: 600, color: 'var(--text-primary)' }} className="mono-cell">
                            {email.recipient_email}
                          </span>
                          <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                            {email.recipient_name || email.contractor_name || 'Client'}
                          </span>
                        </div>
                      </td>

                      <td style={{ maxWidth: '340px' }}>
                        <span style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>
                          {email.subject}
                        </span>
                      </td>

                      <td>
                        {email.trigger_type === 'scheduled_automation' ? (
                          <span className="badge badge-cyan">Scheduled</span>
                        ) : email.trigger_type === 'manual_operator_send' ? (
                          <span className="badge badge-indigo">Manual Send Now</span>
                        ) : (
                          <span className="badge badge-slate">Test Dispatch</span>
                        )}
                      </td>

                      <td>
                        {email.schedule_slot ? (
                          <span className="badge badge-slate mono-cell">
                            {email.schedule_slot}
                          </span>
                        ) : (
                          <span style={{ color: 'var(--text-muted)', fontSize: '12px' }}>Independent</span>
                        )}
                      </td>

                      <td>
                        <span className="mono-cell" style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
                          {email.sent_at ? new Date(email.sent_at).toLocaleString('bn-BD', { dateStyle: 'short', timeStyle: 'short' }) : '—'}
                        </span>
                      </td>

                      <td>
                        {email.status === 'sent' ? (
                          <span className="badge badge-emerald">
                            <CheckCircle2 size={11} /> Sent
                          </span>
                        ) : (
                          <span className="badge badge-rose" title={email.error_message || 'Failed'}>
                            <AlertCircle size={11} /> Failed
                          </span>
                        )}
                      </td>

                      <td style={{ textAlign: 'right' }}>
                        <button
                          className="btn btn-secondary btn-sm"
                          onClick={() => onPreviewEmail(email)}
                          title="View Rendered Email Preview"
                        >
                          <Eye size={13} />
                          <span>View</span>
                        </button>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
