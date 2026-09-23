import React, { useState } from 'react';
import {
  Clock,
  Search,
  CreditCard,
  Mail,
  Users
} from 'lucide-react';
import type { ActivityEvent } from '../types';

interface ActivityViewProps {
  events: ActivityEvent[];
}

export const ActivityView: React.FC<ActivityViewProps> = ({ events }) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [typeFilter, setTypeFilter] = useState('all');

  const filteredEvents = events.filter((ev) => {
    const matchSearch =
      ev.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (ev.contractor_name && ev.contractor_name.toLowerCase().includes(searchQuery.toLowerCase()));

    if (!matchSearch) return false;

    if (typeFilter !== 'all' && !ev.event_type.includes(typeFilter)) {
      return false;
    }

    return true;
  });

  return (
    <div>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '20px', flexWrap: 'wrap', gap: '12px' }}>
        <div>
          <h2 style={{ fontSize: '20px', fontWeight: 600, color: 'var(--text-primary)' }}>
            System & Operator Activity Audit Feed (অ্যাক্টিভিটি হিস্ট্রি)
          </h2>
          <p style={{ fontSize: '13px', color: 'var(--text-muted)' }}>
            Chronological audit trail of all operator modifications, payment confirmations, and automation ticks.
          </p>
        </div>
      </div>

      {/* Filter and Search */}
      <div className="panel" style={{ marginBottom: '20px' }}>
        <div className="panel-body" style={{ padding: '14px 20px', display: 'flex', alignItems: 'center', gap: '16px', flexWrap: 'wrap' }}>
          <div style={{ position: 'relative', flex: 1, minWidth: '240px' }}>
            <Search size={15} style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
            <input
              type="text"
              className="form-input"
              style={{ paddingLeft: '36px' }}
              placeholder="Search activity by title or contractor..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Category:</span>
            <select
              className="form-select"
              style={{ width: 'auto' }}
              value={typeFilter}
              onChange={(e) => setTypeFilter(e.target.value)}
            >
              <option value="all">All Events</option>
              <option value="payment">Payments</option>
              <option value="email">Communications & Emails</option>
              <option value="client">Clients & Onboarding</option>
              <option value="scheduler">Scheduler & Automation</option>
            </select>
          </div>
        </div>
      </div>

      {/* Activity Timeline List */}
      <div className="panel">
        <div className="panel-body" style={{ padding: '12px 24px' }}>
          {filteredEvents.length === 0 ? (
            <div style={{ padding: '40px', textAlign: 'center', color: 'var(--text-muted)' }}>
              No activity records found matching your filters.
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column' }}>
              {filteredEvents.map((ev) => (
                <div
                  key={ev.id}
                  style={{
                    padding: '16px 0',
                    borderBottom: '1px solid var(--border-subtle)',
                    display: 'flex',
                    alignItems: 'flex-start',
                    gap: '16px',
                  }}
                >
                  <div
                    style={{
                      width: '32px',
                      height: '32px',
                      borderRadius: '8px',
                      background: 'var(--bg-surface-hover)',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      marginTop: '2px',
                    }}
                  >
                    {ev.event_type.includes('payment') ? (
                      <CreditCard size={15} color="#34d399" />
                    ) : ev.event_type.includes('email') ? (
                      <Mail size={15} color="#38bdf8" />
                    ) : ev.event_type.includes('client') ? (
                      <Users size={15} color="#818cf8" />
                    ) : (
                      <Clock size={15} color="#94a3b8" />
                    )}
                  </div>

                  <div style={{ flex: 1 }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                      <div style={{ fontSize: '14px', fontWeight: 600, color: 'var(--text-primary)' }}>
                        {ev.title}
                      </div>
                      <span className="mono-cell" style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                        {new Date(ev.created_at).toLocaleString('bn-BD', { dateStyle: 'short', timeStyle: 'short' })} BST
                      </span>
                    </div>

                    <div style={{ fontSize: '12px', color: 'var(--text-secondary)', marginTop: '4px', display: 'flex', gap: '10px' }}>
                      {ev.contractor_name && <span>Client: <strong>{ev.contractor_name}</strong></span>}
                      <span>•</span>
                      <span className="badge badge-slate" style={{ fontSize: '10px' }}>{ev.event_type}</span>
                    </div>

                    {ev.details && Object.keys(ev.details).length > 0 && (
                      <div style={{ background: 'var(--bg-card)', padding: '8px 12px', borderRadius: '6px', marginTop: '8px', fontSize: '11px', color: 'var(--text-muted)' }} className="mono-cell">
                        {JSON.stringify(ev.details)}
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
