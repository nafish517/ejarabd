import React, { useState } from 'react';
import {
  X,
  ExternalLink,
  MapPin,
  Building,
  Calendar,
  DollarSign,
  FileText,
  AlertTriangle,
  CheckCircle,
  XCircle,
  Info,
  Save,
  Sparkles,
  Mail
} from 'lucide-react';
import type { Tender, AIEvaluateResponse } from '../types';
import { api } from '../services/api';
import {
  formatBDT,
  formatSecurityBDT,
  formatBSTDate
} from '../utils/formatters';

interface TenderDetailModalProps {
  tender: Tender | null;
  onClose: () => void;
  onUpdateNotes: (assessmentId: number, notes: string) => Promise<void>;
  onAiEvaluate?: (assessmentId: number) => Promise<AIEvaluateResponse>;
  onShowToast: (msg: string) => void;
}

export const TenderDetailModal: React.FC<TenderDetailModalProps> = ({
  tender,
  onClose,
  onUpdateNotes,
  onAiEvaluate,
  onShowToast
}) => {
  const assessment = tender?.assessment;
  const [operatorNotes, setOperatorNotes] = useState(assessment?.operator_notes || '');
  const [isSaving, setIsSaving] = useState(false);
  const [isEvaluating, setIsEvaluating] = useState(false);
  const [isSendingEmail, setIsSendingEmail] = useState(false);
  const [aiEvalNotice, setAiEvalNotice] = useState<string | null>(null);

  const handleSendEmailTest = async () => {
    if (!tender) return;
    setIsSendingEmail(true);
    try {
      const res = await api.sendTenderEmailTest(tender.tender_id);
      onShowToast(`✓ টেন্ডার নোটিফিকেশন ইমেইল পাঠানো হয়েছে (${res.recipient})`);
    } catch (err: unknown) {
      const errorMsg = err instanceof Error ? err.message : 'সার্ভার কনফিগারেশন চেক করুন';
      onShowToast(`ইমেইল ব্যর্থ: ${errorMsg}`);
    } finally {
      setIsSendingEmail(false);
    }
  };

  const [prevAssessmentId, setPrevAssessmentId] = useState(assessment?.id);
  if (assessment && assessment.id !== prevAssessmentId) {
    setPrevAssessmentId(assessment.id);
    setOperatorNotes(assessment.operator_notes || '');
  }

  if (!tender) return null;

  const handleSaveNotes = async () => {
    if (!assessment?.id) return;
    setIsSaving(true);
    try {
      await onUpdateNotes(assessment.id, operatorNotes);
      onShowToast('✓ অপারেটর নোট সফলভাবে সংরক্ষিত হয়েছে');
    } catch {
      onShowToast('নোট সংরক্ষণ ব্যর্থ হয়েছে');
    } finally {
      setIsSaving(false);
    }
  };

  const handleAiEvaluate = async () => {
    if (!assessment?.id) return;
    setIsEvaluating(true);
    setAiEvalNotice(null);
    try {
      if (onAiEvaluate) {
        const res = await onAiEvaluate(assessment.id);
        if (res.assessment.ai_generated) {
          setAiEvalNotice(`✓ এআই (${res.assessment.model_used || 'Ollama'}) দ্বারা গভীর যোগ্যতা বিশ্লেষণ সম্পন্ন হয়েছে`);
          onShowToast('✓ এআই দ্বারা গভীর যোগ্যতা বিশ্লেষণ সম্পন্ন হয়েছে');
        } else {
          setAiEvalNotice('✓ ব্যাকআপ রুল ইঞ্জিন দ্বারা বিশ্লেষণ সম্পন্ন হয়েছে');
          onShowToast('✓ ব্যাকআপ রুল ইঞ্জিন দ্বারা বিশ্লেষণ সম্পন্ন হয়েছে');
        }
      }
    } catch (err) {
      console.error('AI evaluate error:', err);
      onShowToast('এআই বিশ্লেষণে সমস্যা হয়েছে, পুনরায় চেষ্টা করুন');
    } finally {
      setIsEvaluating(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div
        className="modal-container"
        style={{ maxWidth: '840px' }}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="modal-header">
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
              <span className="badge badge-id">ID: {tender.tender_id}</span>
              <span className="badge badge-agency">{tender.agency}</span>
              {tender.is_amendment && (
                <span className="badge badge-amendment">
                  <AlertTriangle size={12} /> সংশোধিত
                </span>
              )}
            </div>
            <h3 className="modal-title">{tender.title}</h3>
          </div>
          <button className="close-btn" onClick={onClose} aria-label="Close modal">
            <X size={20} />
          </button>
        </div>

        <div className="modal-body">
          {/* Official Location & Office */}
          <div style={{ background: '#f8fafc', padding: '16px', borderRadius: '8px', marginBottom: '20px', border: '1px solid #e2e8f0' }}>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '14px' }}>
              <div>
                <span style={{ fontSize: '0.8rem', color: '#64748b', display: 'flex', alignItems: 'center', gap: '4px' }}>
                  <Building size={14} /> আহবানকারী অফিস:
                </span>
                <span style={{ fontWeight: 600, color: '#0f243e' }}>{tender.procuring_entity_office}</span>
              </div>

              <div>
                <span style={{ fontSize: '0.8rem', color: '#64748b', display: 'flex', alignItems: 'center', gap: '4px' }}>
                  <MapPin size={14} /> কাজের প্রকৃত এলাকা:
                </span>
                <span style={{ fontWeight: 600, color: '#0f243e' }}>
                  {tender.project_location_district} {tender.project_location_details ? `(${tender.project_location_details})` : ''}
                </span>
              </div>
            </div>
          </div>

          {/* Financials & BST Deadlines */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '14px', marginBottom: '20px' }}>
            <div style={{ background: '#ecfdf5', padding: '14px', borderRadius: '8px', border: '1px solid #a7f3d0' }}>
              <span style={{ fontSize: '0.8rem', color: '#047857', display: 'flex', alignItems: 'center', gap: '4px' }}>
                <DollarSign size={14} /> প্রাক্কলিত মূল্য (আনুমানিক বাজেট)
              </span>
              <span style={{ fontSize: '1.1rem', fontWeight: 700, color: '#065f46', marginTop: '4px', display: 'block' }}>
                {formatBDT(tender.estimated_value_bdt)}
              </span>
            </div>

            <div style={{ background: '#f8fafc', padding: '14px', borderRadius: '8px', border: '1px solid #e2e8f0' }}>
              <span style={{ fontSize: '0.8rem', color: '#475569' }}>টেন্ডার সিকিউরিটি (জামানত)</span>
              <span style={{ fontSize: '1.05rem', fontWeight: 700, color: '#1e293b', marginTop: '4px', display: 'block' }}>
                {formatSecurityBDT(tender.tender_security_bdt)}
              </span>
              <span style={{ fontSize: '0.74rem', color: '#64748b' }}>*সিকিউরিটিকে প্রজেক্ট ভ্যালু ধরা যাবে না</span>
            </div>

            <div style={{ background: '#fffbeb', padding: '14px', borderRadius: '8px', border: '1px solid #fde68a' }}>
              <span style={{ fontSize: '0.8rem', color: '#92400e', display: 'flex', alignItems: 'center', gap: '4px' }}>
                <Calendar size={14} /> দাখিলের শেষ সময় (BST)
              </span>
              <span style={{ fontSize: '0.95rem', fontWeight: 700, color: '#b45309', marginTop: '4px', display: 'block' }}>
                {formatBSTDate(tender.closing_date)}
              </span>
            </div>
          </div>

          {/* Raw Eligibility Notice */}
          {tender.raw_eligibility_text && (
            <div style={{ marginBottom: '20px' }}>
              <div style={{ fontSize: '0.95rem', fontWeight: 700, color: '#0f243e', marginBottom: '8px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                <FileText size={16} />
                <span>অফিসিয়াল নোটিশের শর্তাবলি (অক্ষত রূপ):</span>
              </div>
              <div
                style={{
                  background: '#f8fafc',
                  padding: '14px 18px',
                  borderRadius: '8px',
                  border: '1px solid #e2e8f0',
                  fontSize: '0.9rem',
                  lineHeight: '1.6',
                  color: '#334155'
                }}
              >
                {tender.raw_eligibility_text}
              </div>
            </div>
          )}

          {/* Assessment Deep Dive */}
          {assessment && (
            <div style={{ marginBottom: '20px' }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '12px', flexWrap: 'wrap', gap: '8px' }}>
                <div style={{ fontSize: '0.95rem', fontWeight: 700, color: '#0f243e', display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <span>ইজারাবিডি মূল্যায়ন সারসংক্ষেপ:</span>
                  {assessment.ai_generated ? (
                    <span style={{ fontSize: '0.74rem', background: '#ede9fe', color: '#6d28d9', padding: '2px 8px', borderRadius: '12px', fontWeight: 600 }}>
                      🤖 এআই বিশ্লেষিত ({assessment.model_used || 'Ollama'})
                    </span>
                  ) : (
                    <span style={{ fontSize: '0.74rem', background: '#f1f5f9', color: '#475569', padding: '2px 8px', borderRadius: '12px', fontWeight: 600 }}>
                      ⚙️ শর্তভিত্তিক ইঞ্জিন
                    </span>
                  )}
                </div>

                <button
                  id="btn-ai-evaluate"
                  className="btn btn-sm"
                  onClick={handleAiEvaluate}
                  disabled={isEvaluating}
                  style={{
                    background: isEvaluating ? '#94a3b8' : 'linear-gradient(135deg, #0284c7 0%, #2563eb 100%)',
                    color: '#ffffff',
                    border: 'none',
                    boxShadow: '0 2px 4px rgba(37, 99, 235, 0.25)',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '6px',
                    cursor: isEvaluating ? 'not-allowed' : 'pointer'
                  }}
                  title="লোকাল এআই দিয়ে টেন্ডার নোটিশের জটিল শর্ত ও যোগ্যতার গভীর বিশ্লেষণ চালান"
                >
                  <Sparkles size={14} className={isEvaluating ? 'animate-spin' : ''} />
                  <span>{isEvaluating ? 'বিশ্লেষণ চলছে...' : '🤖 এআই দিয়ে যোগ্যতা বিশ্লেষণ করুন'}</span>
                </button>
              </div>

              {aiEvalNotice && (
                <div
                  id="ai-eval-notice"
                  style={{
                    padding: '8px 12px',
                    borderRadius: '6px',
                    marginBottom: '12px',
                    backgroundColor: '#eff6ff',
                    border: '1px solid #bfdbfe',
                    color: '#1e40af',
                    fontSize: '0.84rem',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '6px'
                  }}
                >
                  <Sparkles size={14} color="#2563eb" />
                  <span>{aiEvalNotice}</span>
                </div>
              )}

              <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                {assessment.preference_reasons?.map((r, i) => (
                  <div key={i} style={{ display: 'flex', alignItems: 'flex-start', gap: '8px', color: '#065f46', fontSize: '0.9rem' }}>
                    <CheckCircle size={16} style={{ flexShrink: 0, marginTop: '3px' }} />
                    <span>{r}</span>
                  </div>
                ))}

                {assessment.known_mismatches?.map((m, i) => (
                  <div key={i} style={{ display: 'flex', alignItems: 'flex-start', gap: '8px', color: '#9f1239', fontSize: '0.9rem' }}>
                    <XCircle size={16} style={{ flexShrink: 0, marginTop: '3px' }} />
                    <span>{m}</span>
                  </div>
                ))}

                {assessment.unknown_items_to_verify?.map((u, i) => (
                  <div key={i} style={{ display: 'flex', alignItems: 'flex-start', gap: '8px', color: '#92400e', fontSize: '0.9rem' }}>
                    <Info size={16} style={{ flexShrink: 0, marginTop: '3px' }} />
                    <span><strong>যাচাই করুন:</strong> {u}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Operator Internal Notes */}
          <div style={{ marginTop: '20px', borderTop: '1px solid #e2e8f0', paddingTop: '16px' }}>
            <label className="form-label">অপারেটরের অভ্যন্তরীণ পর্যবেক্ষণ ও নোট:</label>
            <div style={{ display: 'flex', gap: '10px', alignItems: 'flex-start' }}>
              <textarea
                className="form-textarea"
                rows={2}
                placeholder="এই টেন্ডার সম্পর্কে আপনার কোনো নিজস্ব মন্তব্য থাকলে লিখুন..."
                value={operatorNotes}
                onChange={(e) => setOperatorNotes(e.target.value)}
              />
              <button
                className="btn btn-navy"
                onClick={handleSaveNotes}
                disabled={isSaving}
                style={{ flexShrink: 0 }}
              >
                <Save size={16} />
                <span>{isSaving ? '...' : 'সেভ'}</span>
              </button>
            </div>
          </div>
        </div>

        <div className="modal-footer">
          <a
            href={tender.source_url}
            target="_blank"
            rel="noopener noreferrer"
            className="btn btn-outline"
            style={{ color: '#2563eb' }}
          >
            <ExternalLink size={16} />
            <span>মূল e-GP দরপত্র দেখুন</span>
          </a>

          <button
            className="btn btn-outline"
            onClick={handleSendEmailTest}
            disabled={isSendingEmail}
            style={{ color: '#0f766e', borderColor: '#99f6e4' }}
            title="কনফিগারকৃত ঠিকানার উদ্দেশ্যে এই টেন্ডারের বাংলা নোটিফিকেশন ইমেইল পাঠান"
          >
            <Mail size={16} />
            <span>{isSendingEmail ? 'পাঠানো হচ্ছে...' : 'ইমেইল টেস্ট'}</span>
          </button>

          <button className="btn btn-navy" onClick={onClose}>
            বন্ধ করুন
          </button>
        </div>
      </div>
    </div>
  );
};
