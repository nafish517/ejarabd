import React from 'react';
import {
  ExternalLink,
  MapPin,
  Calendar,
  AlertTriangle,
  CheckCircle,
  XCircle,
  Clock,
  MessageCircle,
  ThumbsUp,
  FileCheck,
  Check,
  X,
  Info
} from 'lucide-react';
import type { Tender } from '../types';
import {
  formatBDT,
  formatSecurityBDT,
  formatBSTDate,
  getRemainingDaysBadge
} from '../utils/formatters';

interface TenderCardProps {
  tender: Tender;
  onOpenWhatsApp: (tender: Tender) => void;
  onOpenDetails: (tender: Tender) => void;
  onOpenFeedback: (tender: Tender) => void;
  onUpdateStatus: (assessmentId: number, status: 'shortlisted' | 'rejected' | 'pending') => void;
}

export const TenderCard: React.FC<TenderCardProps> = ({
  tender,
  onOpenWhatsApp,
  onOpenDetails,
  onOpenFeedback,
  onUpdateStatus
}) => {
  const assessment = tender.assessment;
  const draft = tender.draft;
  const timeBadge = getRemainingDaysBadge(tender.closing_date);

  const getFitBadge = () => {
    if (!assessment) return null;
    switch (assessment.preference_fit_status) {
      case 'fits':
        return <span className="badge badge-fit-fits">✓ কাজের সাথে পূর্ণ মিল</span>;
      case 'partial':
        return <span className="badge badge-fit-partial">⚠️ আংশিক সামঞ্জস্যপূর্ণ</span>;
      case 'outside':
        return <span className="badge badge-fit-outside">✕ পছন্দের বাইরে</span>;
      default:
        return null;
    }
  };

  const getReviewStatusBadge = () => {
    if (!assessment) return null;
    switch (assessment.operator_review_status) {
      case 'shortlisted':
        return (
          <span className="badge" style={{ background: '#dcfce7', color: '#15803d', border: '1px solid #86efac' }}>
            ★ শর্টলিস্টেড
          </span>
        );
      case 'rejected':
        return (
          <span className="badge" style={{ background: '#fee2e2', color: '#b91c1c', border: '1px solid #fca5a5' }}>
            ✕ বাতিলকৃত
          </span>
        );
      case 'needs_more_info':
        return (
          <span className="badge" style={{ background: '#fef3c7', color: '#b45309', border: '1px solid #fde68a' }}>
            ? তথ্য প্রয়োজন
          </span>
        );
      default:
        return (
          <span className="badge" style={{ background: '#f1f5f9', color: '#475569', border: '1px solid #cbd5e1' }}>
            ● পর্যালোচনার অপেক্ষায়
          </span>
        );
    }
  };

  return (
    <div className="tender-card">
      {/* Header */}
      <div className="tender-card-header">
        <div className="tender-badges">
          <span className="badge badge-id">ID: {tender.tender_id}</span>
          <span className="badge badge-agency">{tender.agency}</span>
          <span className="badge badge-district">
            <MapPin size={12} /> {tender.project_location_district}
            {tender.project_location_details ? ` (${tender.project_location_details})` : ''}
          </span>
          {tender.is_amendment && (
            <span className="badge badge-amendment">
              <AlertTriangle size={12} /> সংশোধনী নোটিশ
            </span>
          )}
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          {getFitBadge()}
          {getReviewStatusBadge()}
        </div>
      </div>

      {/* Body */}
      <div className="tender-card-body">
        <h2 className="tender-title">{tender.title}</h2>
        <p style={{ fontSize: '0.85rem', color: '#64748b', marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '6px' }}>
          <span>দরপত্র আহবানকারী: {tender.procuring_entity_office}</span>
        </p>

        {/* Metadata Grid */}
        <div className="tender-meta-grid">
          <div className="meta-item">
            <span className="meta-label">আনুমানিক কাজের বাজেট</span>
            <span className={`meta-val ${tender.estimated_value_bdt ? 'meta-val-highlight' : ''}`}>
              {formatBDT(tender.estimated_value_bdt)}
            </span>
          </div>

          <div className="meta-item">
            <span className="meta-label">টেন্ডার সিকিউরিটি</span>
            <span className="meta-val">
              {formatSecurityBDT(tender.tender_security_bdt)}
            </span>
          </div>

          <div className="meta-item">
            <span className="meta-label">শিডিউল ক্রয় মূল্য</span>
            <span className="meta-val">
              {tender.document_price_bdt ? `৳ ${tender.document_price_bdt.toLocaleString('en-IN')}` : 'নোটিশে উল্লেখ নেই'}
            </span>
          </div>

          <div className="meta-item">
            <span className="meta-label">
              <Calendar size={13} /> দরপত্র জমার শেষ সময় (BST)
            </span>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
              <span className="meta-val" style={{ fontSize: '0.92rem' }}>
                {formatBSTDate(tender.closing_date)}
              </span>
              <span
                className="badge"
                style={{
                  backgroundColor: timeBadge.isUrgent ? '#fee2e2' : '#f1f5f9',
                  color: timeBadge.isUrgent ? '#dc2626' : '#475569',
                  fontSize: '0.74rem'
                }}
              >
                <Clock size={11} /> {timeBadge.text}
              </span>
            </div>
          </div>
        </div>

        {/* Amendment Banner if applicable */}
        {tender.is_amendment && tender.amendment_details && (
          <div className="amendment-banner">
            <AlertTriangle size={20} color="#d97706" style={{ flexShrink: 0, marginTop: '2px' }} />
            <div>
              <div style={{ fontWeight: 700, marginBottom: '2px' }}>সংশোধনী বিবরণ:</div>
              <div>{tender.amendment_details}</div>
            </div>
          </div>
        )}

        {/* Transparent Assessment Box */}
        {assessment && (
          <div className="assessment-summary-box">
            <div className="assessment-header">
              <div className="assessment-title">
                <FileCheck size={18} color="#0f243e" />
                <span>স্বচ্ছ শর্তভিত্তিক মূল্যায়ন (কোনো কৃত্রিম শতকরা স্কোর নয়):</span>
              </div>
            </div>

            <ul className="assessment-points-list">
              {assessment.preference_reasons?.map((reason, idx) => (
                <li key={`reason-${idx}`} className="assessment-point positive">
                  <CheckCircle size={16} color="#059669" style={{ flexShrink: 0, marginTop: '3px' }} />
                  <span>{reason}</span>
                </li>
              ))}

              {assessment.known_mismatches?.map((mismatch, idx) => (
                <li key={`mismatch-${idx}`} className="assessment-point mismatch">
                  <XCircle size={16} color="#e11d48" style={{ flexShrink: 0, marginTop: '3px' }} />
                  <span>{mismatch}</span>
                </li>
              ))}

              {assessment.unknown_items_to_verify?.map((unknown, idx) => (
                <li key={`unknown-${idx}`} className="assessment-point verify">
                  <Info size={16} color="#d97706" style={{ flexShrink: 0, marginTop: '3px' }} />
                  <span><strong>যাচাই প্রয়োজন:</strong> {unknown}</span>
                </li>
              ))}
            </ul>

            {assessment.overall_fit_explanation_bn && (
              <div className="explanation-text">
                💡 <strong>সার্বিক পর্যালোচনা:</strong> {assessment.overall_fit_explanation_bn}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Card Footer Actions */}
      <div className="tender-card-footer">
        <div className="footer-left-actions">
          {/* Operator Decision Buttons */}
          {assessment && (
            <>
              {assessment.operator_review_status !== 'shortlisted' ? (
                <button
                  className="btn btn-shortlist btn-sm"
                  onClick={() => onUpdateStatus(assessment.id!, 'shortlisted')}
                  title="এই টেন্ডারটি ঠিকাদারের জন্য শর্টলিস্ট করুন"
                >
                  <Check size={15} />
                  <span>শর্টলিস্ট করুন</span>
                </button>
              ) : (
                <button
                  className="btn btn-reject btn-sm"
                  onClick={() => onUpdateStatus(assessment.id!, 'rejected')}
                  title="শর্টলিস্ট বাতিল করুন"
                >
                  <X size={15} />
                  <span>বাতিল করুন</span>
                </button>
              )}

              {assessment.operator_review_status === 'pending' && (
                <button
                  className="btn btn-reject btn-sm"
                  onClick={() => onUpdateStatus(assessment.id!, 'rejected')}
                  title="অপ্রাসঙ্গিক বা অনুপযুক্ত বিবেচনায় বাতিল করুন"
                >
                  <X size={15} />
                  <span>বাতিল</span>
                </button>
              )}
            </>
          )}

          <button
            className="btn btn-outline btn-sm"
            onClick={() => onOpenDetails(tender)}
          >
            <span>সম্পূর্ণ নোটিশ ও শর্তাবলি</span>
          </button>

          <a
            href={tender.source_url}
            target="_blank"
            rel="noopener noreferrer"
            className="btn btn-outline btn-sm"
            style={{ color: '#2563eb' }}
            title="সরকারি মূল দরপত্র নোটিশ পেজে যান"
          >
            <ExternalLink size={14} />
            <span>অফিসিয়াল সোর্স লিংক</span>
          </a>
        </div>

        <div className="footer-right-actions">
          {/* WhatsApp Button */}
          <button
            className="btn btn-whatsapp btn-sm"
            onClick={() => onOpenWhatsApp(tender)}
          >
            <MessageCircle size={15} />
            <span>হোয়াটসঅ্যাপ মেসেজ</span>
            {draft && (
              <span
                style={{
                  backgroundColor: draft.manual_send_recorded
                    ? '#064e3b'
                    : draft.approval_status === 'approved'
                    ? '#047857'
                    : '#065f46',
                  color: '#ffffff',
                  fontSize: '0.72rem',
                  padding: '2px 8px',
                  borderRadius: '9999px',
                  marginLeft: '4px'
                }}
              >
                {draft.manual_send_recorded
                  ? 'পাঠানো সম্পন্ন'
                  : draft.approval_status === 'approved'
                  ? 'অনুমোদিত'
                  : 'খসড়া প্রস্তুত'}
              </span>
            )}
          </button>

          {/* Feedback Button */}
          <button
            className="btn btn-outline btn-sm"
            onClick={() => onOpenFeedback(tender)}
            title="ঠিকাদারের সাথে কথা বলে প্রতিক্রিয়া লগ করুন"
          >
            <ThumbsUp size={14} />
            <span>প্রতিক্রিয়া লগ</span>
          </button>
        </div>
      </div>
    </div>
  );
};
