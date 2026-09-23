import React, { useState, useMemo } from 'react';
import {
  Search,
  Plus,
  MapPin,
  ChevronRight
} from 'lucide-react';
import type { Client } from '../types';

interface ClientsViewProps {
  clients: Client[];
  onSelectClient: (client: Client) => void;
  onOpenNewClientModal: () => void;
}

export const ClientsView: React.FC<ClientsViewProps> = ({
  clients,
  onSelectClient,
  onOpenNewClientModal,
}) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [typeFilter, setTypeFilter] = useState('all');

  const filteredClients = useMemo(() => {
    return clients.filter((c) => {
      // Search
      const matchSearch =
        c.business_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        c.contact_person.toLowerCase().includes(searchQuery.toLowerCase()) ||
        (c.email && c.email.toLowerCase().includes(searchQuery.toLowerCase())) ||
        (c.district && c.district.toLowerCase().includes(searchQuery.toLowerCase()));

      if (!matchSearch) return false;

      // Status
      if (statusFilter !== 'all' && c.account_status !== statusFilter) return false;

      // Type (Prod vs Demo)
      if (typeFilter === 'production' && c.is_demo) return false;
      if (typeFilter === 'demo' && !c.is_demo) return false;

      return true;
    });
  }, [clients, searchQuery, statusFilter, typeFilter]);

  const renderStatusBadge = (status?: string) => {
    switch (status) {
      case 'active':
        return <span className="badge badge-emerald">Active Delivery</span>;
      case 'onboarding':
        return <span className="badge badge-cyan">Onboarding</span>;
      case 'lead_payment_pending':
        return <span className="badge badge-amber">Payment Pending (lead)</span>;
      case 'suspended':
        return <span className="badge badge-rose">Suspended</span>;
      default:
        return <span className="badge badge-slate">{status || 'Pending'}</span>;
    }
  };

  const renderPaymentBadge = (status?: string) => {
    switch (status) {
      case 'confirmed':
        return <span className="badge badge-emerald">Paid (confirmed)</span>;
      case 'pending':
        return <span className="badge badge-amber">Verifying</span>;
      default:
        return <span className="badge badge-slate">Unpaid (none)</span>;
    }
  };

  return (
    <div>
      {/* Header with Search and Action */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '20px', flexWrap: 'wrap', gap: '12px' }}>
        <div>
          <h2 style={{ fontSize: '20px', fontWeight: 600, color: 'var(--text-primary)' }}>
            Clients & Subscribers (গ্রাহক ডিরেক্টরি)
          </h2>
          <p style={{ fontSize: '13px', color: 'var(--text-muted)' }}>
            Total {clients.length} registered contractors with strict isolated preferences & schedules.
          </p>
        </div>

        <button className="btn btn-primary" onClick={onOpenNewClientModal}>
          <Plus size={15} />
          <span>Add New Client</span>
        </button>
      </div>

      {/* Filter and Search Bar */}
      <div className="panel" style={{ marginBottom: '20px' }}>
        <div className="panel-body" style={{ padding: '14px 20px', display: 'flex', alignItems: 'center', gap: '16px', flexWrap: 'wrap' }}>
          {/* Search */}
          <div style={{ position: 'relative', flex: 1, minWidth: '240px' }}>
            <Search size={15} style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
            <input
              type="text"
              className="form-input"
              style={{ paddingLeft: '36px' }}
              placeholder="Search by business name, contact, email, or district..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </div>

          {/* Account Status Filter */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Status:</span>
            <select
              className="form-select"
              style={{ width: 'auto' }}
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
            >
              <option value="all">All Statuses</option>
              <option value="active">Active Delivery</option>
              <option value="onboarding">Onboarding</option>
              <option value="lead_payment_pending">Payment Pending</option>
              <option value="suspended">Suspended</option>
            </select>
          </div>

          {/* Type Filter */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Environment:</span>
            <select
              className="form-select"
              style={{ width: 'auto' }}
              value={typeFilter}
              onChange={(e) => setTypeFilter(e.target.value)}
            >
              <option value="all">All Clients</option>
              <option value="production">Production Only</option>
              <option value="demo">Demo Only</option>
            </select>
          </div>
        </div>
      </div>

      {/* Clients Table */}
      <div className="panel">
        <div className="table-container">
          <table className="data-table">
            <thead>
              <tr>
                <th>Client / Business</th>
                <th>District / Location</th>
                <th>Account Status</th>
                <th>Payment</th>
                <th>Daily Schedule</th>
                <th>Next Dispatch</th>
                <th>Type</th>
                <th style={{ textAlign: 'right' }}>Action</th>
              </tr>
            </thead>
            <tbody>
              {filteredClients.length === 0 ? (
                <tr>
                  <td colSpan={8} style={{ textAlign: 'center', padding: '40px', color: 'var(--text-muted)' }}>
                    No clients found matching your search or filters.
                  </td>
                </tr>
              ) : (
                filteredClients.map((client) => {
                  const schedules = client.notification_schedules || [];
                  const nextSlot = client.schedule_metrics?.next_scheduled_email?.slot;

                  return (
                    <tr
                      key={client.id}
                      className="clickable-row"
                      onClick={() => onSelectClient(client)}
                    >
                      <td>
                        <div style={{ display: 'flex', flexDirection: 'column' }}>
                          <span style={{ fontWeight: 600, color: 'var(--text-primary)' }}>
                            {client.business_name}
                          </span>
                          <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                            {client.contact_person} {client.email && `• ${client.email}`}
                          </span>
                        </div>
                      </td>

                      <td>
                        <span style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
                          <MapPin size={12} color="var(--text-muted)" />
                          {client.district || (client.preferred_districts?.[0] ?? 'Bangladesh')}
                        </span>
                      </td>

                      <td>{renderStatusBadge(client.account_status)}</td>

                      <td>{renderPaymentBadge(client.payment_status)}</td>

                      <td>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '4px', flexWrap: 'wrap' }}>
                          {schedules.length === 0 ? (
                            <span style={{ color: 'var(--text-muted)', fontSize: '11px' }}>No slots</span>
                          ) : (
                            schedules.map((slot) => (
                              <span key={slot} className="badge badge-slate mono-cell">
                                {slot}
                              </span>
                            ))
                          )}
                          <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                            ({schedules.length}/day)
                          </span>
                        </div>
                      </td>

                      <td>
                        {nextSlot ? (
                          <span className="badge badge-cyan mono-cell">
                            {nextSlot} BST
                          </span>
                        ) : (
                          <span style={{ color: 'var(--text-muted)', fontSize: '12px' }}>—</span>
                        )}
                      </td>

                      <td>
                        {client.is_demo ? (
                          <span className="badge badge-slate" style={{ fontSize: '10px' }}>DEMO</span>
                        ) : (
                          <span className="badge badge-emerald" style={{ fontSize: '10px' }}>PROD</span>
                        )}
                      </td>

                      <td style={{ textAlign: 'right' }}>
                        <button
                          className="btn btn-secondary btn-sm"
                          onClick={(e) => {
                            e.stopPropagation();
                            onSelectClient(client);
                          }}
                        >
                          <span>Manage</span>
                          <ChevronRight size={13} />
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
