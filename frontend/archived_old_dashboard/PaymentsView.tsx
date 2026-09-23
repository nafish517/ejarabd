import React, { useState } from 'react';
import {
  CreditCard,
  Search,
  CheckCircle2,
  Clock,
  Plus,
  ShieldCheck
} from 'lucide-react';
import type { PaymentRecord, OperationsOverview } from '../types';

interface PaymentsViewProps {
  payments: PaymentRecord[];
  overview: OperationsOverview | null;
  onOpenRecordPayment: () => void;
  onConfirmPendingPayment: (payment: PaymentRecord) => void;
}

export const PaymentsView: React.FC<PaymentsViewProps> = ({
  payments,
  overview,
  onOpenRecordPayment,
  onConfirmPendingPayment,
}) => {
  const [searchQuery, setSearchQuery] = useState('');

  const filteredPayments = payments.filter((p) => {
    return (
      p.transaction_reference.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (p.contractor_name && p.contractor_name.toLowerCase().includes(searchQuery.toLowerCase())) ||
      (p.notes && p.notes.toLowerCase().includes(searchQuery.toLowerCase()))
    );
  });

  return (
    <div>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '20px', flexWrap: 'wrap', gap: '12px' }}>
        <div>
          <h2 style={{ fontSize: '20px', fontWeight: 600, color: 'var(--text-primary)' }}>
            Payments & Subscriptions (পেমেন্ট ও রাজস্ব)
          </h2>
          <p style={{ fontSize: '13px', color: 'var(--text-muted)' }}>
            bKash transaction verification, revenue audit, and subscription activation.
          </p>
        </div>

        <button className="btn btn-primary" onClick={onOpenRecordPayment}>
          <Plus size={14} />
          <span>Record bKash Payment</span>
        </button>
      </div>

      {/* Summary KPI Grid */}
      <div className="metrics-grid">
        <div className="metric-card">
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
              <span className="badge badge-emerald">{overview?.payments?.confirmed_count ?? 0} Confirmed Transactions</span>
            </div>
          </div>
        </div>

        <div className="metric-card">
          <div className="metric-header">
            <span className="metric-label">Pending Verifications</span>
            <div className="metric-icon-wrap">
              <Clock size={16} />
            </div>
          </div>
          <div>
            <div className="metric-value">
              {overview?.payments?.pending_verifications_count ?? 0}
            </div>
            <div className="metric-meta">
              <span className="badge badge-amber">Awaiting Operator Confirmation</span>
            </div>
          </div>
        </div>

        <div className="metric-card">
          <div className="metric-header">
            <span className="metric-label">Payment Architecture</span>
            <div className="metric-icon-wrap">
              <ShieldCheck size={16} />
            </div>
          </div>
          <div>
            <div style={{ fontSize: '14px', fontWeight: 600, color: 'var(--text-primary)' }}>
              Operator Controlled
            </div>
            <div className="metric-meta" style={{ marginTop: '6px' }}>
              <span style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>
                Safe manual review before granting access; ready for bKash webhook integration.
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Architectural Notice */}
      <div className="panel" style={{ marginBottom: '20px', background: 'rgba(2, 132, 199, 0.08)', borderColor: 'var(--primary-border)' }}>
        <div className="panel-body" style={{ padding: '14px 18px', display: 'flex', alignItems: 'center', gap: '12px' }}>
          <ShieldCheck size={20} color="#38bdf8" />
          <div style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
            <strong style={{ color: '#f8fafc' }}>Production Safety Rule:</strong> New clients never default to paid. Every client requires explicit payment confirmation via TrxID review before moving from <code className="mono-cell" style={{ color: '#fbbf24' }}>lead_payment_pending</code> to <code className="mono-cell" style={{ color: '#34d399' }}>onboarding/active</code>.
          </div>
        </div>
      </div>

      {/* Payments Table */}
      <div className="panel">
        <div className="panel-header">
          <div style={{ position: 'relative', width: '320px' }}>
            <Search size={14} style={{ position: 'absolute', left: '10px', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
            <input
              type="text"
              className="form-input"
              style={{ paddingLeft: '32px', fontSize: '12px', padding: '6px 12px 6px 32px' }}
              placeholder="Filter by TrxID or client name..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </div>
          <span className="panel-subtitle">{filteredPayments.length} Total Records</span>
        </div>

        <div className="table-container">
          <table className="data-table">
            <thead>
              <tr>
                <th>Transaction Reference (TrxID)</th>
                <th>Client / Contractor</th>
                <th>Amount (BDT)</th>
                <th>Method</th>
                <th>Status</th>
                <th>Confirmed By</th>
                <th>Date</th>
                <th style={{ textAlign: 'right' }}>Action</th>
              </tr>
            </thead>
            <tbody>
              {filteredPayments.length === 0 ? (
                <tr>
                  <td colSpan={8} style={{ textAlign: 'center', padding: '36px', color: 'var(--text-muted)' }}>
                    No payment records found.
                  </td>
                </tr>
              ) : (
                filteredPayments.map((pay) => (
                  <tr key={pay.id}>
                    <td>
                      <code className="mono-cell" style={{ color: 'var(--border-focus)', fontWeight: 600 }}>
                        {pay.transaction_reference}
                      </code>
                    </td>

                    <td>
                      <span style={{ fontWeight: 500, color: 'var(--text-primary)' }}>
                        {pay.contractor_name || `Client #${pay.contractor_id}`}
                      </span>
                    </td>

                    <td>
                      <span className="mono-cell" style={{ fontWeight: 600, color: 'var(--text-primary)' }}>
                        ৳{pay.amount.toLocaleString()}
                      </span>
                    </td>

                    <td>
                      <span className="badge badge-slate">{pay.payment_method}</span>
                    </td>

                    <td>
                      {pay.payment_status === 'confirmed' ? (
                        <span className="badge badge-emerald">
                          <CheckCircle2 size={11} /> Confirmed
                        </span>
                      ) : (
                        <span className="badge badge-amber">
                          <Clock size={11} /> Pending Review
                        </span>
                      )}
                    </td>

                    <td>
                      <span style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
                        {pay.confirmed_by || '—'}
                      </span>
                    </td>

                    <td>
                      <span className="mono-cell" style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                        {new Date(pay.created_at).toLocaleDateString()}
                      </span>
                    </td>

                    <td style={{ textAlign: 'right' }}>
                      {pay.payment_status === 'pending' && (
                        <button
                          className="btn btn-outline-emerald btn-sm"
                          onClick={() => onConfirmPendingPayment(pay)}
                        >
                          <span>Confirm</span>
                        </button>
                      )}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
