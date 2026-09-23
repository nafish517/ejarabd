import React, { useState, useEffect } from 'react';
import {
  X,
  Send,
  CheckCircle2,
  Clock,
  Plus,
  Zap,
  Sliders,
  Timer
} from 'lucide-react';
import type {
  Client,
  EmailNotificationRecord,
  MatchExplanation,
  PaymentRecord
} from '../types';
import { getNextDispatchCountdown } from '../utils/countdown';

/* ==========================================================================
   1. Create Client Modal
   ========================================================================== */
interface CreateClientModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (payload: Partial<Client>) => Promise<void>;
}

export const CreateClientModal: React.FC<CreateClientModalProps> = ({
  isOpen,
  onClose,
  onSubmit,
}) => {
  const [businessName, setBusinessName] = useState('');
  const [contactPerson, setContactPerson] = useState('');
  const [email, setEmail] = useState('');
  const [phone, setPhone] = useState('');
  const [district, setDistrict] = useState('');
  const [preferredDistricts, setPreferredDistricts] = useState('');
  const [categories, setCategories] = useState('');
  const [schedules, setSchedules] = useState('12:00, 19:00');
  const [isDemo, setIsDemo] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!businessName || !contactPerson) return;

    setIsSubmitting(true);
    try {
      const scheduleList = schedules
        .split(',')
        .map((s) => s.trim())
        .filter(Boolean);

      await onSubmit({
        business_name: businessName,
        contact_person: contactPerson,
        email: email || undefined,
        phone: phone || undefined,
        district: district || undefined,
        preferred_districts: preferredDistricts
          ? preferredDistricts.split(',').map((s) => s.trim()).filter(Boolean)
          : undefined,
        work_categories: categories
          ? categories.split(',').map((s) => s.trim()).filter(Boolean)
          : undefined,
        notification_schedules: scheduleList.length ? scheduleList : ['12:00'],
        is_demo: isDemo,
      });
      onClose();
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h3 className="modal-title">Register New Client (নতুন গ্রাহক)</h3>
          <button className="btn btn-secondary btn-icon" onClick={onClose}>
            <X size={16} />
          </button>
        </div>

        <form onSubmit={handleSubmit}>
          <div className="modal-body">
            <div style={{ background: 'rgba(245, 158, 11, 0.1)', border: '1px solid rgba(245, 158, 11, 0.25)', borderRadius: '8px', padding: '10px 14px', marginBottom: '16px', fontSize: '12px', color: '#fbbf24' }}>
              <strong>Safe Initial Lifecycle:</strong> New clients automatically default to <code className="mono-cell">lead_payment_pending</code> and <code className="mono-cell">payment_status = 'none'</code>. Subscription is only activated after payment confirmation.
            </div>

            <div className="form-group">
              <label className="form-label">Business / Firm Name *</label>
              <input
                type="text"
                required
                className="form-input"
                placeholder="e.g. রূপালী বিল্ডার্স এন্ড কনস্ট্রাকশন"
                value={businessName}
                onChange={(e) => setBusinessName(e.target.value)}
              />
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
              <div className="form-group">
                <label className="form-label">Contact Person *</label>
                <input
                  type="text"
                  required
                  className="form-input"
                  placeholder="e.g. জনাব মোঃ হাসিবুল করিম"
                  value={contactPerson}
                  onChange={(e) => setContactPerson(e.target.value)}
                />
              </div>

              <div className="form-group">
                <label className="form-label">Primary District</label>
                <input
                  type="text"
                  className="form-input"
                  placeholder="e.g. Bogura, Dinajpur"
                  value={district}
                  onChange={(e) => setDistrict(e.target.value)}
                />
              </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
              <div className="form-group">
                <label className="form-label">Email Address (Tender Delivery)</label>
                <input
                  type="email"
                  className="form-input"
                  placeholder="e.g. client@example.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                />
              </div>

              <div className="form-group">
                <label className="form-label">Phone / WhatsApp</label>
                <input
                  type="text"
                  className="form-input"
                  placeholder="e.g. +8801700000000"
                  value={phone}
                  onChange={(e) => setPhone(e.target.value)}
                />
              </div>
            </div>

            <div className="form-group">
              <label className="form-label">Preferred Districts (Comma separated)</label>
              <input
                type="text"
                className="form-input"
                placeholder="e.g. Bogura, Naogaon, Sirajganj"
                value={preferredDistricts}
                onChange={(e) => setPreferredDistricts(e.target.value)}
              />
            </div>

            <div className="form-group">
              <label className="form-label">Work Categories (Comma separated)</label>
              <input
                type="text"
                className="form-input"
                placeholder="e.g. Civil Works, Road Construction, Bridge"
                value={categories}
                onChange={(e) => setCategories(e.target.value)}
              />
            </div>

            <div className="form-group">
              <label className="form-label">Daily Notification Schedules (Comma separated BST 24h)</label>
              <input
                type="text"
                className="form-input mono-cell"
                placeholder="e.g. 12:00, 19:00"
                value={schedules}
                onChange={(e) => setSchedules(e.target.value)}
              />
              <div style={{ display: 'flex', gap: '6px', marginTop: '6px', flexWrap: 'wrap' }}>
                <button type="button" className="time-pill-btn" onClick={() => setSchedules('12:00')}>১২:০০ (১ বার)</button>
                <button type="button" className="time-pill-btn" onClick={() => setSchedules('09:00, 17:00')}>০৯:০০, ১৭:০০ (২ বার)</button>
                <button type="button" className="time-pill-btn" onClick={() => setSchedules('09:00, 13:00, 18:00')}>০৯:০০, ১৩:০০, ১৮:০০ (৩ বার)</button>
              </div>
              <span className="form-help">Single source of truth: যতটি স্লট নির্বাচন করবেন দৈনিক ঠিক ততটি ইমেইল যাবে।</span>
            </div>

            <div style={{ marginTop: '12px' }}>
              <label style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer', fontSize: '13px', color: 'var(--text-secondary)' }}>
                <input
                  type="checkbox"
                  checked={isDemo}
                  onChange={(e) => setIsDemo(e.target.checked)}
                />
                <span>Mark as Demo Client (Isolated from production automation)</span>
              </label>
            </div>
          </div>

          <div className="modal-footer">
            <button type="button" className="btn btn-secondary" onClick={onClose} disabled={isSubmitting}>
              Cancel
            </button>
            <button type="submit" className="btn btn-primary" disabled={isSubmitting}>
              {isSubmitting ? 'Creating...' : 'Register Client'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

/* ==========================================================================
   2. Confirm Payment Modal
   ========================================================================== */
interface ConfirmPaymentModalProps {
  isOpen: boolean;
  client: Client | null;
  pendingPayment?: PaymentRecord | null;
  onClose: () => void;
  onConfirm: (payload: {
    amount: number;
    payment_method: string;
    transaction_reference: string;
    service_months: number;
    notes?: string;
  }) => Promise<void>;
}

export const ConfirmPaymentModal: React.FC<ConfirmPaymentModalProps> = ({
  isOpen,
  client,
  pendingPayment,
  onClose,
  onConfirm,
}) => {
  const [amount, setAmount] = useState('3000');
  const [method, setMethod] = useState('bKash');
  const [trxId, setTrxId] = useState(pendingPayment?.transaction_reference || '');
  const [serviceMonths, setServiceMonths] = useState(1);
  const [notes, setNotes] = useState('Verified in bKash merchant statement');
  const [isSubmitting, setIsSubmitting] = useState(false);

  if (!isOpen || !client) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!trxId) return;

    setIsSubmitting(true);
    try {
      await onConfirm({
        amount: parseFloat(amount) || 3000,
        payment_method: method,
        transaction_reference: trxId,
        service_months: serviceMonths,
        notes,
      });
      onClose();
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h3 className="modal-title">Confirm bKash Payment & Activate</h3>
          <button className="btn btn-secondary btn-icon" onClick={onClose}>
            <X size={16} />
          </button>
        </div>

        <form onSubmit={handleSubmit}>
          <div className="modal-body">
            <div style={{ background: 'var(--bg-card)', padding: '12px 16px', borderRadius: '8px', border: '1px solid var(--border-subtle)', marginBottom: '16px' }}>
              <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Client:</div>
              <div style={{ fontSize: '14px', fontWeight: 600, color: 'var(--text-primary)' }}>
                {client.business_name} ({client.contact_person})
              </div>
              <div style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
                Status: <span className="badge badge-amber">{client.account_status}</span>
              </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
              <div className="form-group">
                <label className="form-label">Amount (BDT) *</label>
                <input
                  type="number"
                  required
                  className="form-input mono-cell"
                  value={amount}
                  onChange={(e) => setAmount(e.target.value)}
                />
              </div>

              <div className="form-group">
                <label className="form-label">Payment Method</label>
                <select className="form-select" value={method} onChange={(e) => setMethod(e.target.value)}>
                  <option value="bKash">bKash Merchant / Personal</option>
                  <option value="Nagad">Nagad</option>
                  <option value="Bank">Bank Transfer</option>
                </select>
              </div>
            </div>

            <div className="form-group">
              <label className="form-label">bKash Transaction ID (TrxID) *</label>
              <input
                type="text"
                required
                className="form-input mono-cell"
                placeholder="e.g. BKASH9X87261A"
                value={trxId}
                onChange={(e) => setTrxId(e.target.value)}
              />
              <span className="form-help">Enter the exact transaction reference from the bKash SMS or merchant portal.</span>
            </div>

            <div className="form-group">
              <label className="form-label">Subscription Duration (Months)</label>
              <select
                className="form-select"
                value={serviceMonths}
                onChange={(e) => setServiceMonths(parseInt(e.target.value, 10))}
              >
                <option value={1}>1 Month (Monthly)</option>
                <option value={3}>3 Months (Quarterly)</option>
                <option value={6}>6 Months (Half-Yearly)</option>
                <option value={12}>12 Months (Annual)</option>
              </select>
            </div>

            <div className="form-group">
              <label className="form-label">Operator Verification Notes</label>
              <input
                type="text"
                className="form-input"
                placeholder="e.g. Confirmed with client over phone"
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
              />
            </div>
          </div>

          <div className="modal-footer">
            <button type="button" className="btn btn-secondary" onClick={onClose} disabled={isSubmitting}>
              Cancel
            </button>
            <button type="submit" className="btn btn-outline-emerald" disabled={isSubmitting}>
              <CheckCircle2 size={14} />
              <span>{isSubmitting ? 'Confirming...' : 'Confirm & Progress Lifecycle'}</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

/* ==========================================================================
   3. Send Now Modal (Immediate Tender Notification)
   ========================================================================== */
interface SendNowModalProps {
  isOpen: boolean;
  client: Client | null;
  tenderId?: number;
  onClose: () => void;
  onSend: (payload: { tender_id?: number; force?: boolean }) => Promise<void>;
}

export const SendNowModal: React.FC<SendNowModalProps> = ({
  isOpen,
  client,
  tenderId,
  onClose,
  onSend,
}) => {
  const selectedTenderId = tenderId ? String(tenderId) : '';
  const [force, setForce] = useState(false);
  const [isSending, setIsSending] = useState(false);

  if (!isOpen || !client) return null;

  const handleSend = async () => {
    setIsSending(true);
    try {
      await onSend({
        tender_id: selectedTenderId ? parseInt(selectedTenderId, 10) : undefined,
        force,
      });
      onClose();
    } finally {
      setIsSending(false);
    }
  };

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h3 className="modal-title">Manual Immediate Send (ইমেইল পাঠান)</h3>
          <button className="btn btn-secondary btn-icon" onClick={onClose}>
            <X size={16} />
          </button>
        </div>

        <div className="modal-body">
          <div style={{ background: 'rgba(99, 102, 241, 0.1)', border: '1px solid rgba(99, 102, 241, 0.25)', borderRadius: '8px', padding: '12px 14px', marginBottom: '16px', fontSize: '12px', color: '#818cf8' }}>
            <strong>Independent Dispatch:</strong> Manual "Send Now" is tracked under <code className="mono-cell">manual_operator_send</code>. It will <strong>NOT</strong> consume or alter normal scheduled slots ({JSON.stringify(client.notification_schedules)}).
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', fontSize: '13px' }}>
            <div>
              <span style={{ color: 'var(--text-muted)' }}>Recipient Client: </span>
              <strong style={{ color: 'var(--text-primary)' }}>{client.business_name}</strong>
            </div>
            <div>
              <span style={{ color: 'var(--text-muted)' }}>Delivery Email: </span>
              <code className="mono-cell" style={{ color: 'var(--border-focus)' }}>{client.email || 'No email configured!'}</code>
            </div>
            {tenderId && (
              <div>
                <span style={{ color: 'var(--text-muted)' }}>Specific Tender: </span>
                <span className="mono-cell">ID #{tenderId}</span>
              </div>
            )}
          </div>

          <div style={{ marginTop: '16px' }}>
            <label style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer', fontSize: '12px', color: 'var(--text-secondary)' }}>
              <input
                type="checkbox"
                checked={force}
                onChange={(e) => setForce(e.target.checked)}
              />
              <span>Bypass recent duplicate guard (Allow sending even if sent in last 6 hours)</span>
            </label>
          </div>
        </div>

        <div className="modal-footer">
          <button className="btn btn-secondary" onClick={onClose} disabled={isSending}>
            Cancel
          </button>
          <button className="btn btn-primary" onClick={handleSend} disabled={isSending || !client.email}>
            <Send size={14} />
            <span>{isSending ? 'Sending Dispatch...' : 'Dispatch Email Now'}</span>
          </button>
        </div>
      </div>
    </div>
  );
};

/* ==========================================================================
   4. Edit Schedules Modal (with Interactive Clock, Sliders & Quick Presets)
   ========================================================================== */
interface EditSchedulesModalProps {
  isOpen: boolean;
  client: Client | null;
  onClose: () => void;
  onSave: (schedules: string[]) => Promise<void>;
}

const formatSlot12h = (slot: string) => {
  const parts = slot.split(':');
  if (parts.length !== 2) return slot;
  const h = parseInt(parts[0], 10);
  const m = parseInt(parts[1], 10);
  if (isNaN(h) || isNaN(m)) return slot;
  const period = h >= 12 ? 'PM' : 'AM';
  const h12 = h % 12 === 0 ? 12 : h % 12;
  const banglaPeriod = h < 6 ? 'রাত' : h < 12 ? 'সকাল' : h < 15 ? 'দুপুর' : h < 18 ? 'বিকাল' : h < 20 ? 'সন্ধ্যা' : 'রাত';
  return `${banglaPeriod} ${h12}:${String(m).padStart(2, '0')} ${period}`;
};

const normalizeSlot = (s: string): string => {
  const parts = s.trim().split(':');
  if (parts.length === 2) {
    const h = parseInt(parts[0], 10);
    const m = parseInt(parts[1], 10);
    if (!isNaN(h) && !isNaN(m) && h >= 0 && h < 24 && m >= 0 && m < 60) {
      return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}`;
    }
  }
  return s.trim();
};

export const EditSchedulesModal: React.FC<EditSchedulesModalProps> = ({
  isOpen,
  client,
  onClose,
  onSave,
}) => {
  const [slots, setSlots] = useState<string[]>([]);
  const [selectedHour, setSelectedHour] = useState<number>(12);
  const [selectedMinute, setSelectedMinute] = useState<number>(0);
  const [isSaving, setIsSaving] = useState(false);
  const [showManualInput, setShowManualInput] = useState(false);
  const [manualText, setManualText] = useState('');

  const [modalCountdown, setModalCountdown] = useState(() => getNextDispatchCountdown([]));

  // Synchronize initial state when modal opens
  useEffect(() => {
    if (client?.notification_schedules) {
      const clean = (client.notification_schedules || []).map(normalizeSlot).filter(Boolean);
      const unique = Array.from(new Set(clean)).sort();
      setSlots(unique.length > 0 ? unique : ['12:00']);
      setManualText(unique.join(', '));
      if (unique[0]) {
        const parts = unique[0].split(':');
        setSelectedHour(parseInt(parts[0], 10) || 12);
        setSelectedMinute(parseInt(parts[1], 10) || 0);
      }
    }
  }, [client, isOpen]);

  // Live stopwatch ticking every second
  useEffect(() => {
    setModalCountdown(getNextDispatchCountdown(slots));
    const timer = setInterval(() => {
      setModalCountdown(getNextDispatchCountdown(slots));
    }, 1000);
    return () => clearInterval(timer);
  }, [slots]);

  if (!isOpen || !client) return null;

  const currentPickerSlot = `${String(selectedHour).padStart(2, '0')}:${String(selectedMinute).padStart(2, '0')}`;
  const isCurrentSlotAlreadyAdded = slots.includes(currentPickerSlot);
  const isPM = selectedHour >= 12;

  const handleAddCurrentSlot = () => {
    if (!slots.includes(currentPickerSlot)) {
      const updated = [...slots, currentPickerSlot].sort();
      setSlots(updated);
      setManualText(updated.join(', '));
    }
  };

  const handleRemoveSlot = (slotToRemove: string) => {
    const updated = slots.filter((s) => s !== slotToRemove);
    setSlots(updated);
    setManualText(updated.join(', '));
  };

  const handleApplyPreset = (presetSlots: string[]) => {
    const cleaned = presetSlots.map(normalizeSlot);
    setSlots(cleaned);
    setManualText(cleaned.join(', '));
  };

  const handleAddTestMinutes = (minsAhead: number = 3) => {
    // Calculate Bangladesh Time (UTC+6)
    const now = new Date();
    const utcTime = now.getTime() + now.getTimezoneOffset() * 60000;
    const bstDate = new Date(utcTime + 6 * 3600000);
    bstDate.setMinutes(bstDate.getMinutes() + minsAhead);

    const h = bstDate.getHours();
    const m = bstDate.getMinutes();
    setSelectedHour(h);
    setSelectedMinute(m);

    const slotStr = `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}`;
    if (!slots.includes(slotStr)) {
      const updated = [...slots, slotStr].sort();
      setSlots(updated);
      setManualText(updated.join(', '));
    }
  };

  const handleSave = async () => {
    if (slots.length === 0) return;

    setIsSaving(true);
    try {
      await onSave(slots);
      onClose();
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal-content" style={{ maxWidth: '620px' }} onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Clock size={18} color="#38bdf8" />
            <h3 className="modal-title">ডেলিভারি শিডিউল ও ক্লক কনফিগারেশন</h3>
          </div>
          <button className="btn btn-secondary btn-icon" onClick={onClose}>
            <X size={16} />
          </button>
        </div>

        <div className="modal-body" style={{ maxHeight: '75vh', overflowY: 'auto' }}>
          {/* Active Configured Slots Section */}
          <div style={{ background: 'var(--bg-card)', padding: '14px', borderRadius: '10px', border: '1px solid var(--border-subtle)', marginBottom: '18px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
              <span style={{ fontSize: '13px', fontWeight: 600, color: 'var(--text-primary)' }}>
                সক্রিয় দৈনিক ডেলিভারি স্লট ({slots.length}টি/দিন)
              </span>
              {slots.length > 0 && (
                <button
                  type="button"
                  onClick={() => { setSlots([]); setManualText(''); }}
                  style={{ background: 'transparent', border: 'none', color: '#f87171', fontSize: '11px', cursor: 'pointer' }}
                >
                  সব মুছুন (Clear All)
                </button>
              )}
            </div>

            {slots.length === 0 ? (
              <div style={{ padding: '12px', textAlign: 'center', color: '#f87171', fontSize: '12px', background: 'rgba(239, 68, 68, 0.08)', borderRadius: '6px' }}>
                কমপক্ষে একটি ডেলিভারি সময় স্লট যুক্ত করুন।
              </div>
            ) : (
              <div className="schedule-chips-container">
                {slots.map((slot) => (
                  <div key={slot} className="schedule-chip">
                    <Clock size={12} />
                    <span>{formatSlot12h(slot)}</span>
                    <span style={{ opacity: 0.65, fontSize: '11px', fontFamily: 'var(--font-mono)' }}>({slot})</span>
                    <button
                      type="button"
                      className="schedule-chip-remove"
                      onClick={() => handleRemoveSlot(slot)}
                      title="Remove slot"
                    >
                      <X size={13} />
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Live Dispatch Countdown Stopwatch */}
          {slots.length > 0 && (
            <div
              style={{
                background: 'linear-gradient(135deg, rgba(6, 78, 59, 0.4), rgba(15, 23, 42, 0.95))',
                border: '1px solid rgba(52, 211, 153, 0.45)',
                borderRadius: '10px',
                padding: '12px 16px',
                marginBottom: '18px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                boxShadow: '0 4px 14px rgba(16, 185, 129, 0.15)',
              }}
            >
              <div>
                <div style={{ fontSize: '11px', color: '#34d399', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '5px', textTransform: 'uppercase' }}>
                  <Timer size={13} />
                  <span>পরবর্তী ইমেইল যাওয়ার স্টপওয়াচ (Countdown):</span>
                </div>
                <div style={{ fontSize: '13px', color: 'var(--text-secondary)', marginTop: '3px' }}>
                  পরবর্তী স্লট: <strong style={{ color: '#fff' }}>{modalCountdown.targetSlot} BST</strong> ({modalCountdown.dayLabel}, {modalCountdown.targetSlot12h})
                </div>
              </div>
              <div style={{ textAlign: 'right' }}>
                <div
                  style={{
                    fontSize: '22px',
                    fontWeight: 700,
                    color: '#38bdf8',
                    fontFamily: 'var(--font-mono)',
                    letterSpacing: '1px',
                    textShadow: '0 0 12px rgba(56, 189, 248, 0.4)',
                  }}
                >
                  {modalCountdown.formatted}
                </div>
                <div style={{ fontSize: '10px', color: 'var(--text-muted)' }}>সময় বাকি (Live)</div>
              </div>
            </div>
          )}

          {/* Interactive Clock & Sliders Section */}
          <div style={{ background: 'var(--bg-surface)', padding: '18px', borderRadius: '12px', border: '1px solid var(--border-subtle)', marginBottom: '18px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
              <span style={{ fontSize: '13px', fontWeight: 600, color: '#38bdf8', display: 'flex', alignItems: 'center', gap: '6px' }}>
                <Sliders size={14} />
                ইন্টারেক্টিভ ক্লক ও স্লাইডার দিয়ে সময় নির্বাচন
              </span>

              {/* AM / PM Toggle */}
              <div style={{ display: 'flex', gap: '4px', background: 'var(--bg-card)', padding: '2px', borderRadius: '6px', border: '1px solid var(--border-subtle)' }}>
                <button
                  type="button"
                  className={`time-pill-btn ${!isPM ? 'active' : ''}`}
                  onClick={() => setSelectedHour((h) => (h >= 12 ? h - 12 : h))}
                >
                  AM
                </button>
                <button
                  type="button"
                  className={`time-pill-btn ${isPM ? 'active' : ''}`}
                  onClick={() => setSelectedHour((h) => (h < 12 ? h + 12 : h))}
                >
                  PM
                </button>
              </div>
            </div>

            {/* Glowing Digital Clock Display */}
            <div className="clock-preview-card">
              <div className="digital-clock-time">
                <span>{String(selectedHour).padStart(2, '0')}</span>
                <span>:</span>
                <span>{String(selectedMinute).padStart(2, '0')}</span>
                <span style={{ fontSize: '16px', color: '#10b981', marginLeft: '6px' }}>
                  {isPM ? 'PM' : 'AM'}
                </span>
              </div>
              <div className="digital-clock-sub">
                {formatSlot12h(currentPickerSlot)} (বাংলাদেশ সময় BST, 24h: {currentPickerSlot})
              </div>
            </div>

            {/* Hour Slider */}
            <div className="slider-group">
              <div className="slider-header">
                <span>ঘণ্টা (Hour: 0 - 23)</span>
                <span className="slider-badge">{String(selectedHour).padStart(2, '0')}:00</span>
              </div>
              <input
                type="range"
                min={0}
                max={23}
                step={1}
                value={selectedHour}
                onChange={(e) => setSelectedHour(Number(e.target.value))}
                className="time-range-slider"
              />
              <div className="quick-steppers">
                {[
                  { label: 'সকাল ৯টা', h: 9 },
                  { label: 'সকাল ১১টা', h: 11 },
                  { label: 'দুপুর ১২টা', h: 12 },
                  { label: 'বিকাল ৩টা', h: 15 },
                  { label: 'সন্ধ্যা ৬টা', h: 18 },
                  { label: 'রাত ৯টা', h: 21 },
                ].map((item) => (
                  <button
                    key={item.h}
                    type="button"
                    className={`time-pill-btn ${selectedHour === item.h ? 'active' : ''}`}
                    onClick={() => setSelectedHour(item.h)}
                  >
                    {item.label}
                  </button>
                ))}
              </div>
            </div>

            {/* Minute Slider */}
            <div className="slider-group" style={{ marginTop: '14px', marginBottom: '14px' }}>
              <div className="slider-header">
                <span>মিনিট (Minute: 0 - 59)</span>
                <span className="slider-badge">:{String(selectedMinute).padStart(2, '0')}</span>
              </div>
              <input
                type="range"
                min={0}
                max={59}
                step={1}
                value={selectedMinute}
                onChange={(e) => setSelectedMinute(Number(e.target.value))}
                className="time-range-slider"
              />
              <div className="quick-steppers">
                <button type="button" className="time-pill-btn" onClick={() => setSelectedMinute((m) => Math.max(0, m - 5))}>-5m</button>
                <button type="button" className="time-pill-btn" onClick={() => setSelectedMinute((m) => Math.max(0, m - 1))}>-1m</button>
                <button type="button" className={`time-pill-btn ${selectedMinute === 0 ? 'active' : ''}`} onClick={() => setSelectedMinute(0)}>:00</button>
                <button type="button" className={`time-pill-btn ${selectedMinute === 15 ? 'active' : ''}`} onClick={() => setSelectedMinute(15)}>:15</button>
                <button type="button" className={`time-pill-btn ${selectedMinute === 30 ? 'active' : ''}`} onClick={() => setSelectedMinute(30)}>:30</button>
                <button type="button" className={`time-pill-btn ${selectedMinute === 45 ? 'active' : ''}`} onClick={() => setSelectedMinute(45)}>:45</button>
                <button type="button" className="time-pill-btn" onClick={() => setSelectedMinute((m) => Math.min(59, m + 1))}>+1m</button>
                <button type="button" className="time-pill-btn" onClick={() => setSelectedMinute((m) => Math.min(59, m + 5))}>+5m</button>
              </div>
            </div>

            {/* Add Slot Button */}
            <button
              type="button"
              className="btn btn-primary"
              style={{ width: '100%', justifyContent: 'center', marginTop: '10px' }}
              onClick={handleAddCurrentSlot}
              disabled={isCurrentSlotAlreadyAdded}
            >
              <Plus size={15} />
              <span>{isCurrentSlotAlreadyAdded ? 'এই সময় স্লটটি ইতোমধ্যে যুক্ত আছে' : `এই সময় স্লটটি যুক্ত করুন (+ ${currentPickerSlot})`}</span>
            </button>
          </div>

          {/* Quick Smart Presets */}
          <div style={{ marginBottom: '16px' }}>
            <span style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-secondary)', display: 'flex', alignItems: 'center', gap: '5px', marginBottom: '8px' }}>
              <Zap size={13} color="#f59e0b" />
              এক-ক্লিকে স্মার্ট প্রিসেট শিডিউল:
            </span>
            <div className="preset-card-grid">
              <button
                type="button"
                className="preset-card-btn"
                style={{ borderColor: 'rgba(56, 189, 248, 0.4)', background: 'rgba(56, 189, 248, 0.06)' }}
                onClick={() => handleAddTestMinutes(3)}
                title="টেস্টের জন্য বর্তমান সময়ের ৩ মিনিট পরের স্লট যুক্ত করুন"
              >
                <div className="preset-title" style={{ color: '#38bdf8' }}>⚡ এখনই টেস্ট (BST +3m)</div>
                <div className="preset-sub">বর্তমান সময়ের ৩ মিনিট পর</div>
              </button>

              <button
                type="button"
                className="preset-card-btn"
                onClick={() => handleApplyPreset(['12:00'])}
              >
                <div className="preset-title">একক ডাইজেস্ট (১ বার)</div>
                <div className="preset-sub">দুপুর ১২:০০</div>
              </button>

              <button
                type="button"
                className="preset-card-btn"
                onClick={() => handleApplyPreset(['09:00', '17:00'])}
              >
                <div className="preset-title">সকাল ও বিকাল (২ বার)</div>
                <div className="preset-sub">০৯:০০, ১৭:০০</div>
              </button>

              <button
                type="button"
                className="preset-card-btn"
                onClick={() => handleApplyPreset(['09:00', '13:00', '18:00'])}
              >
                <div className="preset-title">৩টি দৈনিক স্লট</div>
                <div className="preset-sub">০৯:০০, ১৩:০০, ১৮:০০</div>
              </button>
            </div>
          </div>

          {/* Collapsible Manual Input (if needed) */}
          <div style={{ marginTop: '10px' }}>
            <button
              type="button"
              style={{ background: 'transparent', border: 'none', color: 'var(--text-muted)', fontSize: '11px', cursor: 'pointer', textDecoration: 'underline' }}
              onClick={() => setShowManualInput(!showManualInput)}
            >
              {showManualInput ? 'ম্যানুয়াল টেক্সট ইনপুট লুকান' : 'প্রয়োজনে ম্যানুয়ালি টাইপ করতে চাইলে এখানে ক্লিক করুন'}
            </button>
            {showManualInput && (
              <div style={{ marginTop: '6px' }}>
                <input
                  type="text"
                  className="form-input mono-cell"
                  placeholder="e.g. 05:15, 12:00"
                  value={manualText}
                  onChange={(e) => {
                    setManualText(e.target.value);
                    const list = e.target.value.split(',').map(normalizeSlot).filter(Boolean);
                    setSlots(list);
                  }}
                />
              </div>
            )}
          </div>
        </div>

        <div className="modal-footer" style={{ borderTop: '1px solid var(--border-subtle)' }}>
          <button className="btn btn-secondary" onClick={onClose} disabled={isSaving}>
            Cancel
          </button>
          <button className="btn btn-primary" onClick={handleSave} disabled={isSaving || slots.length === 0}>
            <CheckCircle2 size={14} />
            <span>{isSaving ? 'সংরক্ষণ হচ্ছে...' : `শিডিউল সংরক্ষণ করুন (${slots.length}টি/দিন)`}</span>
          </button>
        </div>
      </div>
    </div>
  );
};

/* ==========================================================================
   5. Email Preview Modal
   ========================================================================== */
interface EmailPreviewModalProps {
  isOpen: boolean;
  email: EmailNotificationRecord | null;
  onClose: () => void;
}

export const EmailPreviewModal: React.FC<EmailPreviewModalProps> = ({
  isOpen,
  email,
  onClose,
}) => {
  if (!isOpen || !email) return null;

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal-content" style={{ maxWidth: '640px' }} onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h3 className="modal-title">Dispatched Email Preview</h3>
          <button className="btn btn-secondary btn-icon" onClick={onClose}>
            <X size={16} />
          </button>
        </div>

        <div className="modal-body">
          <div style={{ background: 'var(--bg-card)', padding: '14px', borderRadius: '8px', border: '1px solid var(--border-subtle)', marginBottom: '16px', display: 'flex', flexDirection: 'column', gap: '6px', fontSize: '12px' }}>
            <div>
              <span style={{ color: 'var(--text-muted)' }}>To: </span>
              <strong className="mono-cell" style={{ color: 'var(--text-primary)' }}>{email.recipient_email}</strong>
              {email.recipient_name && <span> ({email.recipient_name})</span>}
            </div>
            <div>
              <span style={{ color: 'var(--text-muted)' }}>Subject: </span>
              <strong style={{ color: 'var(--border-focus)' }}>{email.subject}</strong>
            </div>
            <div style={{ display: 'flex', gap: '12px', marginTop: '4px' }}>
              <span>Trigger: <span className="badge badge-slate">{email.trigger_type}</span></span>
              {email.schedule_slot && <span>Slot: <span className="badge badge-cyan mono-cell">{email.schedule_slot}</span></span>}
              <span>Sent: <span className="mono-cell">{email.sent_at ? new Date(email.sent_at).toLocaleTimeString('bn-BD') : ''} BST</span></span>
            </div>
          </div>

          <div style={{ border: '1px solid var(--border-subtle)', borderRadius: '8px', overflow: 'hidden', background: '#ffffff', color: '#0f172a', padding: '20px' }}>
            <div style={{ fontSize: '16px', fontWeight: 700, color: '#0f172a', borderBottom: '2px solid #0284c7', paddingBottom: '8px', marginBottom: '12px' }}>
              ইজারাবিডি • নতুন টেন্ডার নোটিফিকেশন
            </div>
            <p style={{ fontSize: '13px', lineHeight: 1.6, color: '#334155' }}>
              প্রিয় গ্রাহক,<br />
              আপনার ব্যবসার পছন্দের সাথে মিল থাকা নতুন একটি সরকারি ই-জিপি দরপত্র প্রকাশিত হয়েছে। নিচে বিস্তারিত তুলে ধরা হলো:
            </p>
            <div style={{ background: '#f8fafc', border: '1px solid #e2e8f0', borderRadius: '6px', padding: '12px', margin: '14px 0', fontSize: '12px' }}>
              <div style={{ fontWeight: 600, color: '#0f172a' }}>{email.subject}</div>
              <div style={{ color: '#64748b', marginTop: '4px' }}>টেন্ডার আইডি ও বিস্তারিত যাচাই করতে ইজারাবিডি পোর্টালে লগইন করুন।</div>
            </div>
            <div style={{ fontSize: '11px', color: '#94a3b8', borderTop: '1px solid #e2e8f0', paddingTop: '8px' }}>
              স্বয়ংক্রিয়ভাবে প্রেরিত • EjaraBD B2B Tender Operations System
            </div>
          </div>
        </div>

        <div className="modal-footer">
          <button className="btn btn-secondary" onClick={onClose}>
            Close
          </button>
        </div>
      </div>
    </div>
  );
};

/* ==========================================================================
   6. Match Explanation Modal (Why this matched?)
   ========================================================================== */
interface MatchExplanationModalProps {
  isOpen: boolean;
  explanation: MatchExplanation | null;
  onClose: () => void;
}

export const MatchExplanationModal: React.FC<MatchExplanationModalProps> = ({
  isOpen,
  explanation,
  onClose,
}) => {
  if (!isOpen || !explanation) return null;

  const reasons: string[] = Array.isArray(explanation.reasons)
    ? explanation.reasons
    : (Array.isArray((explanation as any).preference_reasons) ? (explanation as any).preference_reasons : []);
  const mismatches: string[] = Array.isArray(explanation.mismatches)
    ? explanation.mismatches
    : (Array.isArray((explanation as any).known_mismatches) ? (explanation as any).known_mismatches : []);
  const unknowns: string[] = Array.isArray(explanation.unknowns)
    ? explanation.unknowns
    : (Array.isArray((explanation as any).unknown_items_to_verify) ? (explanation as any).unknown_items_to_verify : []);
  const explanationText = explanation.explanation_bn || (explanation as any).overall_fit_explanation_bn || 'শর্তভিত্তিক বিশ্লেষণ প্রস্তুত রয়েছে।';
  const clientName = explanation.contractor_name || (explanation as any).client_name || 'Client';

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h3 className="modal-title">Match Explanation (ম্যাচিং কারণ ও বিশ্লেষণ)</h3>
          <button className="btn btn-secondary btn-icon" onClick={onClose}>
            <X size={16} />
          </button>
        </div>

        <div className="modal-body">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px' }}>
            <span style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>
              Contractor: <strong>{clientName}</strong>
            </span>
            <span className="mono-cell" style={{ fontSize: '12px', color: 'var(--border-focus)' }}>
              #{explanation.tender_id}
            </span>
          </div>

          <div style={{ background: 'var(--bg-card)', padding: '14px', borderRadius: '8px', border: '1px solid var(--border-subtle)', marginBottom: '16px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
              <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Status:</span>
              {explanation.preference_fit_status === 'fits' ? (
                <span className="badge badge-emerald">উপযুক্ত (Fits)</span>
              ) : explanation.preference_fit_status === 'partial' ? (
                <span className="badge badge-amber">আংশিক (Partial)</span>
              ) : (
                <span className="badge badge-slate">বাইরে (Outside)</span>
              )}
            </div>
            <div style={{ fontSize: '13px', color: 'var(--text-primary)', lineHeight: 1.5 }}>
              {explanationText}
            </div>
          </div>

          {/* Condition Reasons */}
          <div style={{ marginBottom: '12px' }}>
            <div style={{ fontSize: '12px', fontWeight: 600, color: 'var(--emerald-text)', marginBottom: '6px' }}>
              ✓ মিল থাকা শর্তসমূহ (Matching Criteria):
            </div>
            {reasons.length === 0 ? (
              <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>কোনো নির্দিষ্ট শর্ত সরাসরি মেলেনি।</div>
            ) : (
              <ul style={{ paddingLeft: '20px', fontSize: '12px', color: 'var(--text-secondary)', lineHeight: 1.6 }}>
                {reasons.map((r, i) => (
                  <li key={i}>{r}</li>
                ))}
              </ul>
            )}
          </div>

          {/* Mismatches */}
          {mismatches.length > 0 && (
            <div style={{ marginBottom: '12px' }}>
              <div style={{ fontSize: '12px', fontWeight: 600, color: 'var(--rose-text)', marginBottom: '6px' }}>
                ✕ অমিল থাকা শর্তসমূহ (Mismatches):
              </div>
              <ul style={{ paddingLeft: '20px', fontSize: '12px', color: 'var(--text-secondary)', lineHeight: 1.6 }}>
                {mismatches.map((m, i) => (
                  <li key={i}>{m}</li>
                ))}
              </ul>
            </div>
          )}

          {/* Unknowns */}
          {unknowns.length > 0 && (
            <div>
              <div style={{ fontSize: '12px', fontWeight: 600, color: 'var(--amber-text)', marginBottom: '6px' }}>
                ? যাচাইযোগ্য অজানা তথ্য (Unknowns to Verify):
              </div>
              <ul style={{ paddingLeft: '20px', fontSize: '12px', color: 'var(--text-secondary)', lineHeight: 1.6 }}>
                {unknowns.map((u, i) => (
                  <li key={i}>{u}</li>
                ))}
              </ul>
            </div>
          )}
        </div>

        <div className="modal-footer">
          <button className="btn btn-secondary" onClick={onClose}>
            Close
          </button>
        </div>
      </div>
    </div>
  );
};
