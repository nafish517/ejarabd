import React, { useState, useEffect } from 'react';
import {
  X,
  Clock,
  Send,
  CreditCard,
  FileText,
  Mail,
  Sliders,
  ShieldCheck,
  CheckCircle2,
  Timer
} from 'lucide-react';
import type {
  Client,
  Tender,
  EmailNotificationRecord,
  PaymentRecord
} from '../types';
import { api } from '../services/api';
import { getNextDispatchCountdown } from '../utils/countdown';

interface ClientDrawerProps {
  client: Client | null;
  onClose: () => void;
  onOpenConfirmPayment: (client: Client) => void;
  onOpenSendNow: (client: Client, tenderId?: number) => void;
  onOpenEditSchedules: (client: Client) => void;
  onOpenOnboarding: (client: Client) => void;
  onViewMatchExplanation: (tenderId: number, contractorId: number) => void;
}

export const ClientDrawer: React.FC<ClientDrawerProps> = ({
  client,
  onClose,
  onOpenConfirmPayment,
  onOpenSendNow,
  onOpenEditSchedules,
  onOpenOnboarding,
  onViewMatchExplanation,
}) => {
  const [activeInnerTab, setActiveInnerTab] = useState<'matches' | 'emails' | 'payments' | 'profile'>('matches');
  const [clientTenders, setClientTenders] = useState<Tender[]>([]);
  const [clientEmails, setClientEmails] = useState<EmailNotificationRecord[]>([]);
  const [clientPayments, setClientPayments] = useState<PaymentRecord[]>([]);
  const clientId = client?.id;
  const [loadedClientId, setLoadedClientId] = useState<number | null>(null);

  useEffect(() => {
    if (!clientId) return;

    let isMounted = true;

    const loadClientData = async () => {
      try {
        const [tendersRes, emailsRes, paymentsRes] = await Promise.all([
          api.getTenders({ contractor_id: clientId, limit: 30 }).catch(() => []),
          api.getEmails({ contractor_id: clientId, limit: 20 }).catch(() => []),
          api.getPayments({ contractor_id: clientId, limit: 10 }).catch(() => []),
        ]);

        if (isMounted) {
          setClientTenders(Array.isArray(tendersRes) ? tendersRes : []);
          setClientEmails(Array.isArray(emailsRes) ? emailsRes : ((emailsRes as any)?.items || []));
          setClientPayments(Array.isArray(paymentsRes) ? paymentsRes : []);
          setLoadedClientId(clientId);
        }
      } catch (err) {
        console.error('Failed to load drawer data:', err);
      }
    };

    void loadClientData();

    return () => {
      isMounted = false;
    };
  }, [clientId]);

  const schedules = client?.notification_schedules || [];
  const metrics = client?.schedule_metrics;

  const [countdown, setCountdown] = useState(() => getNextDispatchCountdown(schedules));

  useEffect(() => {
    if (!client) return;
    setCountdown(getNextDispatchCountdown(schedules));
    const timer = setInterval(() => {
      setCountdown(getNextDispatchCountdown(schedules));
    }, 1000);
    return () => clearInterval(timer);
  }, [client, schedules]);

  const isLoading = client !== null && loadedClientId !== clientId;

  if (!client) return null;

  return (
    <div className="drawer-backdrop" onClick={onClose}>
      <div className="drawer-container" onClick={(e) => e.stopPropagation()}>
        {/* Drawer Header */}
        <div className="drawer-header">
          <div style={{ flex: 1 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px' }}>
              <h2 className="drawer-title">{client.business_name}</h2>
              {client.is_demo ? (
                <span className="badge badge-slate" style={{ fontSize: '10px' }}>DEMO</span>
              ) : (
                <span className="badge badge-emerald" style={{ fontSize: '10px' }}>PRODUCTION</span>
              )}
              {client.account_status === 'lead_payment_pending' ? (
                <span className="badge badge-amber" style={{ fontSize: '10px' }}>Payment Pending (lead_payment_pending)</span>
              ) : client.account_status === 'onboarding' ? (
                <span className="badge badge-cyan" style={{ fontSize: '10px' }}>Onboarding</span>
              ) : client.account_status === 'active' ? (
                <span className="badge badge-emerald" style={{ fontSize: '10px' }}>Active Delivery</span>
              ) : (
                <span className="badge badge-slate" style={{ fontSize: '10px' }}>{client.account_status}</span>
              )}
            </div>
            <div className="drawer-subtitle">
              <span>{client.contact_person}</span>
              <span>•</span>
              <span className="mono-cell">{client.email || 'No email registered'}</span>
              {client.phone && (
                <>
                  <span>•</span>
                  <span className="mono-cell">{client.phone}</span>
                </>
              )}
            </div>
          </div>
          <button className="btn btn-secondary btn-icon" onClick={onClose} title="Close Panel">
            <X size={18} />
          </button>
        </div>

        {/* Action Button Toolbar */}
        <div style={{ padding: '14px 24px', background: 'var(--bg-card)', borderBottom: '1px solid var(--border-subtle)', display: 'flex', flexWrap: 'wrap', gap: '10px' }}>
          {/* Confirm Payment button - only visible if payment is NOT confirmed */}
          {client.payment_status !== 'confirmed' ? (
            <button
              className="btn btn-outline-emerald btn-sm"
              onClick={() => onOpenConfirmPayment(client)}
              title="Confirm bKash Payment & Activate Subscription"
            >
              <CreditCard size={13} />
              <span>Confirm Payment</span>
            </button>
          ) : (
            <div
              className="badge badge-emerald"
              style={{ display: 'inline-flex', alignItems: 'center', gap: '5px', padding: '6px 12px', fontSize: '12px' }}
              title="bKash Payment Verified & Subscription Active"
            >
              <CheckCircle2 size={13} />
              <span>Payment Confirmed</span>
            </div>
          )}

          {/* Send Now button */}
          <button
            className="btn btn-primary btn-sm"
            onClick={() => onOpenSendNow(client)}
            title="Dispatch immediate tender email (Independent of scheduled slots)"
          >
            <Send size={13} />
            <span>Send Now (ইমেইল পাঠান)</span>
          </button>

          {/* Edit Schedules button */}
          <button
            className="btn btn-secondary btn-sm"
            onClick={() => onOpenEditSchedules(client)}
            title="Edit daily delivery schedule slots"
          >
            <Clock size={13} />
            <span>Edit Schedules ({schedules.length}/day)</span>
          </button>

          {/* Onboarding button */}
          {client.onboarding_status !== 'complete' && (
            <button
              className="btn btn-outline-amber btn-sm"
              onClick={() => onOpenOnboarding(client)}
            >
              <ShieldCheck size={13} />
              <span>Complete Onboarding</span>
            </button>
          )}
        </div>

        {/* Schedule & Daily Quota Status Cards */}
        <div style={{ padding: '16px 24px', background: 'var(--bg-subtle)', borderBottom: '1px solid var(--border-subtle)', display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '12px' }}>
          <div style={{ background: 'var(--bg-surface)', padding: '10px 12px', borderRadius: '8px', border: '1px solid var(--border-subtle)' }}>
            <div style={{ fontSize: '11px', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Daily Slots</div>
            <div style={{ fontSize: '16px', fontWeight: 600, color: 'var(--text-primary)', marginTop: '2px' }}>
              {schedules.length} / day
            </div>
            <div style={{ fontSize: '11px', color: 'var(--text-secondary)', marginTop: '2px' }} className="mono-cell">
              {schedules.join(', ') || 'None'}
            </div>
          </div>

          <div style={{ background: 'var(--bg-surface)', padding: '10px 12px', borderRadius: '8px', border: '1px solid var(--border-subtle)' }}>
            <div style={{ fontSize: '11px', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Sent Today (BST)</div>
            <div style={{ fontSize: '16px', fontWeight: 600, color: 'var(--text-primary)', marginTop: '2px' }}>
              {metrics?.sent_today_count ?? 0}
            </div>
            <div style={{ fontSize: '11px', color: 'var(--emerald-text)', marginTop: '2px' }}>
              {metrics?.today_completed_slots?.length ? `${metrics.today_completed_slots.join(', ')}` : 'No slots yet'}
            </div>
          </div>

          <div style={{ background: 'var(--bg-surface)', padding: '10px 12px', borderRadius: '8px', border: '1px solid var(--border-subtle)' }}>
            <div style={{ fontSize: '11px', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Remaining Today</div>
            <div style={{ fontSize: '16px', fontWeight: 600, color: 'var(--text-primary)', marginTop: '2px' }}>
              {metrics?.remaining_today_count ?? schedules.length}
            </div>
            <div style={{ fontSize: '11px', color: 'var(--text-secondary)', marginTop: '2px' }}>
              Pending slots
            </div>
          </div>

          {/* Next Dispatch & Live Countdown Stopwatch */}
          <div
            style={{
              background: 'linear-gradient(135deg, rgba(15, 23, 42, 0.95), rgba(6, 78, 59, 0.35))',
              padding: '10px 12px',
              borderRadius: '8px',
              border: '1px solid rgba(52, 211, 153, 0.4)',
              boxShadow: '0 2px 10px rgba(16, 185, 129, 0.1)',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div style={{ fontSize: '11px', color: '#34d399', textTransform: 'uppercase', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '4px' }}>
                <Timer size={12} color="#34d399" />
                <span>Next Dispatch</span>
              </div>
              <span className="badge badge-emerald" style={{ fontSize: '9px', padding: '1px 5px', animation: 'live-pulse-dot 2s infinite' }}>
                LIVE
              </span>
            </div>
            <div
              style={{
                fontSize: '15px',
                fontWeight: 700,
                color: '#38bdf8',
                marginTop: '3px',
                letterSpacing: '0.5px',
                fontFamily: 'var(--font-mono)',
              }}
            >
              {countdown.formatted}
            </div>
            <div style={{ fontSize: '11px', color: 'var(--text-secondary)', marginTop: '2px', display: 'flex', alignItems: 'center', gap: '4px' }}>
              <span>স্লট: {countdown.targetSlot}</span>
              <span style={{ opacity: 0.5 }}>•</span>
              <span style={{ color: countdown.isToday ? '#34d399' : '#fbbf24' }}>
                {countdown.dayLabel}
              </span>
            </div>
          </div>
        </div>

        {/* Onboarding Notice Banner if Incomplete */}
        {client.onboarding_status !== 'complete' && (
          <div
            style={{
              padding: '8px 24px',
              background: 'rgba(245, 158, 11, 0.12)',
              borderBottom: '1px solid rgba(245, 158, 11, 0.3)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              fontSize: '12px',
              color: '#fbbf24',
            }}
          >
            <span>
              ⚠️ <strong>অনবোর্ডিং পেন্ডিং:</strong> টাইমার শেষ হওয়ার সময়ে স্বয়ংক্রিয় মেইল পেতে হলে উপরের <strong>"Complete Onboarding"</strong> বাটনটি সম্পন্ন করুন।
            </span>
          </div>
        )}

        {/* Drawer Inner Navigation Tabs */}
        <div style={{ display: 'flex', borderBottom: '1px solid var(--border-subtle)', background: 'var(--bg-surface)' }}>
          <button
            className={`nav-tab-btn ${activeInnerTab === 'matches' ? 'active' : ''}`}
            onClick={() => setActiveInnerTab('matches')}
            style={{ flex: 1, justifyContent: 'center' }}
          >
            <FileText size={14} />
            <span>Matching Tenders ({clientTenders.length})</span>
          </button>

          <button
            className={`nav-tab-btn ${activeInnerTab === 'emails' ? 'active' : ''}`}
            onClick={() => setActiveInnerTab('emails')}
            style={{ flex: 1, justifyContent: 'center' }}
          >
            <Mail size={14} />
            <span>Dispatched Emails ({clientEmails.length})</span>
          </button>

          <button
            className={`nav-tab-btn ${activeInnerTab === 'payments' ? 'active' : ''}`}
            onClick={() => setActiveInnerTab('payments')}
            style={{ flex: 1, justifyContent: 'center' }}
          >
            <CreditCard size={14} />
            <span>Payments ({clientPayments.length})</span>
          </button>

          <button
            className={`nav-tab-btn ${activeInnerTab === 'profile' ? 'active' : ''}`}
            onClick={() => setActiveInnerTab('profile')}
            style={{ flex: 1, justifyContent: 'center' }}
          >
            <Sliders size={14} />
            <span>Client Profile</span>
          </button>
        </div>

        {/* Drawer Body */}
        <div className="drawer-body">
          {isLoading ? (
            <div style={{ padding: '40px', textAlign: 'center', color: 'var(--text-muted)' }}>
              Loading client telemetry...
            </div>
          ) : activeInnerTab === 'matches' ? (
            <div>
              <div style={{ marginBottom: '16px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>
                  Isolated tender evaluations for <strong>{client.business_name}</strong>
                </span>
                <span className="badge badge-emerald">Rule-Based Evaluation</span>
              </div>

              {clientTenders.length === 0 ? (
                <div style={{ padding: '32px', textAlign: 'center', color: 'var(--text-muted)', background: 'var(--bg-card)', borderRadius: '10px' }}>
                  No matching tenders currently evaluated for this profile.
                </div>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                  {clientTenders.map((tender) => {
                    const fitStatus = tender.assessment?.preference_fit_status || 'unassessed';
                    return (
                      <div
                        key={tender.id}
                        style={{
                          background: 'var(--bg-card)',
                          border: '1px solid var(--border-subtle)',
                          borderRadius: '10px',
                          padding: '16px',
                        }}
                      >
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '8px' }}>
                          <span className="mono-cell" style={{ fontSize: '12px', color: 'var(--border-focus)' }}>
                            Tender ID: {tender.tender_id}
                          </span>
                          <div style={{ display: 'flex', gap: '6px' }}>
                            {fitStatus === 'fits' ? (
                              <span className="badge badge-emerald">উপযুক্ত (Fits)</span>
                            ) : fitStatus === 'partial' ? (
                              <span className="badge badge-amber">আংশিক (Partial)</span>
                            ) : (
                              <span className="badge badge-slate">বাইরে (Outside)</span>
                            )}
                          </div>
                        </div>

                        <h4 style={{ fontSize: '14px', fontWeight: 600, color: 'var(--text-primary)', marginBottom: '8px', lineHeight: 1.4 }}>
                          {tender.title}
                        </h4>

                        <div style={{ display: 'flex', gap: '12px', fontSize: '12px', color: 'var(--text-muted)', marginBottom: '12px', flexWrap: 'wrap' }}>
                          <span>{tender.agency}</span>
                          <span>•</span>
                          <span>{tender.project_location_district}</span>
                          {tender.estimated_value_bdt && (
                            <>
                              <span>•</span>
                              <span className="mono-cell" style={{ color: 'var(--text-secondary)' }}>
                                ৳{(tender.estimated_value_bdt / 100000).toFixed(1)} লাখ
                              </span>
                            </>
                          )}
                          <span>•</span>
                          <span>জমা: {tender.closing_date}</span>
                        </div>

                        {tender.assessment?.overall_fit_explanation_bn && (
                          <div style={{ background: 'var(--bg-surface)', padding: '8px 12px', borderRadius: '6px', fontSize: '12px', color: 'var(--text-secondary)', marginBottom: '12px', borderLeft: '3px solid var(--border-focus)' }}>
                            {tender.assessment.overall_fit_explanation_bn}
                          </div>
                        )}

                        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px' }}>
                          <button
                            className="btn btn-secondary btn-sm"
                            onClick={() => onViewMatchExplanation(tender.id, client.id)}
                          >
                            <span>Why This Matched?</span>
                          </button>

                          <button
                            className="btn btn-primary btn-sm"
                            onClick={() => onOpenSendNow(client, tender.id)}
                          >
                            <Send size={12} />
                            <span>Send This Tender Now</span>
                          </button>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          ) : activeInnerTab === 'emails' ? (
            <div>
              <div style={{ marginBottom: '16px', fontSize: '13px', color: 'var(--text-secondary)' }}>
                Audit history of all notifications sent to <strong>{client.email}</strong>
              </div>

              {clientEmails.length === 0 ? (
                <div style={{ padding: '32px', textAlign: 'center', color: 'var(--text-muted)', background: 'var(--bg-card)', borderRadius: '10px' }}>
                  No emails have been dispatched to this client yet.
                </div>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                  {clientEmails.map((email) => (
                    <div
                      key={email.id}
                      style={{
                        background: 'var(--bg-card)',
                        border: '1px solid var(--border-subtle)',
                        borderRadius: '8px',
                        padding: '14px',
                      }}
                    >
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                          {email.trigger_type === 'scheduled_automation' ? (
                            <span className="badge badge-cyan">Scheduled ({email.schedule_slot || 'Auto'})</span>
                          ) : email.trigger_type === 'manual_operator_send' ? (
                            <span className="badge badge-indigo">Manual Send Now</span>
                          ) : (
                            <span className="badge badge-slate">Test Send</span>
                          )}
                          <span className={`badge ${email.status === 'sent' ? 'badge-emerald' : 'badge-rose'}`}>
                            {email.status}
                          </span>
                        </div>
                        <span className="mono-cell" style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                          {email.sent_at ? new Date(email.sent_at).toLocaleTimeString('bn-BD') : ''} BST
                        </span>
                      </div>

                      <div style={{ fontSize: '13px', fontWeight: 600, color: 'var(--text-primary)', marginBottom: '4px' }}>
                        {email.subject}
                      </div>

                      <div style={{ fontSize: '11px', color: 'var(--text-muted)', display: 'flex', gap: '12px' }}>
                        <span>Provider: {email.email_provider || 'Mock/SMTP'}</span>
                        {email.schedule_date && <span>Date: {email.schedule_date}</span>}
                        {email.schedule_slot && <span>Slot: {email.schedule_slot}</span>}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          ) : activeInnerTab === 'payments' ? (
            <div>
              <div style={{ marginBottom: '16px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>
                  bKash Payment & Subscription History
                </span>
                <button className="btn btn-outline-emerald btn-sm" onClick={() => onOpenConfirmPayment(client)}>
                  <CreditCard size={12} />
                  <span>Record Payment</span>
                </button>
              </div>

              {clientPayments.length === 0 ? (
                <div style={{ padding: '32px', textAlign: 'center', color: 'var(--text-muted)', background: 'var(--bg-card)', borderRadius: '10px' }}>
                  No payment records found for this client.
                </div>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                  {clientPayments.map((pay) => (
                    <div
                      key={pay.id}
                      style={{
                        background: 'var(--bg-card)',
                        border: '1px solid var(--border-subtle)',
                        borderRadius: '8px',
                        padding: '14px',
                      }}
                    >
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                          <span style={{ fontSize: '15px', fontWeight: 700, color: 'var(--text-primary)' }} className="mono-cell">
                            ৳{pay.amount.toLocaleString()}
                          </span>
                          <span className="badge badge-slate">{pay.payment_method}</span>
                          <span className={`badge ${pay.payment_status === 'confirmed' ? 'badge-emerald' : 'badge-amber'}`}>
                            {pay.payment_status}
                          </span>
                        </div>
                        <span className="mono-cell" style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                          {new Date(pay.created_at).toLocaleDateString()}
                        </span>
                      </div>

                      <div style={{ fontSize: '12px', color: 'var(--text-secondary)', display: 'flex', gap: '10px', marginTop: '4px' }}>
                        <span>TrxID: <code className="mono-cell" style={{ color: 'var(--border-focus)' }}>{pay.transaction_reference}</code></span>
                        {pay.confirmed_by && <span>• Confirmed by: {pay.confirmed_by}</span>}
                      </div>

                      {pay.notes && (
                        <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '6px' }}>
                          Notes: {pay.notes}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          ) : (
            /* Client Profile JSON & Preferences */
            <div>
              <div style={{ background: 'var(--bg-card)', padding: '16px', borderRadius: '10px', border: '1px solid var(--border-subtle)', marginBottom: '16px' }}>
                <h4 style={{ fontSize: '14px', fontWeight: 600, color: 'var(--text-primary)', marginBottom: '12px' }}>
                  Configured Criteria & Filtering Rules
                </h4>

                <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', fontSize: '13px' }}>
                  <div>
                    <span style={{ color: 'var(--text-muted)' }}>Preferred Districts: </span>
                    <span style={{ color: 'var(--text-primary)', fontWeight: 500 }}>
                      {client.preferred_districts?.join(', ') || client.district || 'Any'}
                    </span>
                  </div>

                  <div>
                    <span style={{ color: 'var(--text-muted)' }}>Work Categories: </span>
                    <span style={{ color: 'var(--text-primary)', fontWeight: 500 }}>
                      {client.work_categories?.join(', ') || 'Any'}
                    </span>
                  </div>

                  <div>
                    <span style={{ color: 'var(--text-muted)' }}>Preferred Agencies: </span>
                    <span style={{ color: 'var(--text-primary)', fontWeight: 500 }}>
                      {client.preferred_agencies?.join(', ') || 'Any (e.g. LGED, RHD, PWD)'}
                    </span>
                  </div>

                  <div>
                    <span style={{ color: 'var(--text-muted)' }}>Value Range: </span>
                    <span style={{ color: 'var(--text-primary)', fontWeight: 500 }}>
                      {client.min_project_value_bdt ? `৳${client.min_project_value_bdt.toLocaleString()}` : '0'}
                      {' - '}
                      {client.max_project_value_bdt ? `৳${client.max_project_value_bdt.toLocaleString()}` : 'Unlimited'}
                    </span>
                  </div>

                  <div>
                    <span style={{ color: 'var(--text-muted)' }}>Delivery Slots (Single Source of Truth): </span>
                    <span className="mono-cell" style={{ color: 'var(--border-focus)', fontWeight: 600 }}>
                      {JSON.stringify(schedules)} ({schedules.length} emails / day)
                    </span>
                  </div>
                </div>
              </div>

              {/* Raw JSON viewer for deterministic verification */}
              <div style={{ background: 'var(--bg-subtle)', padding: '12px', borderRadius: '8px', border: '1px solid var(--border-subtle)' }}>
                <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginBottom: '6px', textTransform: 'uppercase' }}>
                  Raw Contractor Profile Record (DB)
                </div>
                <pre className="mono-cell" style={{ fontSize: '11px', color: 'var(--text-secondary)', overflowX: 'auto' }}>
                  {JSON.stringify(client, null, 2)}
                </pre>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
