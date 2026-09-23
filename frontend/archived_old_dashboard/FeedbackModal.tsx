import React, { useState } from 'react';
import { X, ThumbsUp, Save, HelpCircle } from 'lucide-react';
import type { Tender, FeedbackPayload } from '../types';

interface FeedbackModalProps {
  tender: Tender | null;
  onClose: () => void;
  onSubmitFeedback: (payload: FeedbackPayload) => Promise<void>;
  onShowToast: (msg: string) => void;
}

export const FeedbackModal: React.FC<FeedbackModalProps> = ({
  tender,
  onClose,
  onSubmitFeedback,
  onShowToast
}) => {
  const [feedbackType, setFeedbackType] = useState<'worth_reviewing' | 'not_relevant' | 'already_known' | 'needs_more_info'>('worth_reviewing');
  const [rejectionReason, setRejectionReason] = useState('');
  const [nextActionTaken, setNextActionTaken] = useState('');
  const [operatorNotes, setOperatorNotes] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  if (!tender || !tender.assessment?.id) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    try {
      await onSubmitFeedback({
        assessment_id: tender.assessment!.id!,
        feedback_type: feedbackType,
        rejection_reason: feedbackType === 'not_relevant' ? rejectionReason : undefined,
        next_action_taken: nextActionTaken || undefined,
        operator_notes: operatorNotes || undefined
      });
      onShowToast('✓ ঠিকাদারের প্রতিক্রিয়া সফলভাবে সংরক্ষিত হয়েছে');
      onClose();
    } catch {
      onShowToast('প্রতিক্রিয়া সংরক্ষণ ব্যর্থ হয়েছে');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div
        className="modal-container"
        style={{ maxWidth: '600px' }}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="modal-header">
          <div>
            <h3 className="modal-title" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <ThumbsUp size={20} color="#7c3aed" />
              ঠিকাদারের প্রতিক্রিয়া রেকর্ড করুন
            </h3>
            <p style={{ fontSize: '0.84rem', color: '#64748b' }}>
              টেন্ডার: <strong>{tender.tender_id}</strong>
            </p>
          </div>
          <button className="close-btn" onClick={onClose} aria-label="Close modal">
            <X size={20} />
          </button>
        </div>

        <form onSubmit={handleSubmit}>
          <div className="modal-body">
            {/* Feedback Type Selection */}
            <div className="form-group">
              <label className="form-label">ঠিকাদারের মতামত ক্যাটাগরি *</label>
              <select
                className="form-select"
                value={feedbackType}
                onChange={(e) => setFeedbackType(e.target.value as any)}
                required
              >
                <option value="worth_reviewing">উপযুক্ত ও বিবেচ্য (কাজে আগ্রহ প্রকাশ করেছেন / শিডিউল কিনবেন)</option>
                <option value="not_relevant">প্রাসঙ্গিক নয় (বাজেট কম, এলাকা দূরবর্তী, বা কাজের ধরনের অমিল)</option>
                <option value="already_known">আগেই জানা ছিল (অন্য সোর্স থেকে নোটিশ পেয়েছেন)</option>
                <option value="needs_more_info">আরও তথ্যের প্রয়োজন (অফিসে খোঁজ নিচ্ছেন / সাইট ভিজিট)</option>
              </select>
            </div>

            {/* Rejection reason if not relevant */}
            {feedbackType === 'not_relevant' && (
              <div className="form-group">
                <label className="form-label">বাতিল বা অমিলের নির্দিষ্ট কারণ</label>
                <input
                  type="text"
                  className="form-input"
                  placeholder="যেমন: বাজেট অনেক কম, অন্য উপজেলায় কাজ করতে চান না..."
                  value={rejectionReason}
                  onChange={(e) => setRejectionReason(e.target.value)}
                />
              </div>
            )}

            {/* Next Action Taken */}
            <div className="form-group">
              <label className="form-label">পরবর্তী পদক্ষেপ (Next Action Taken)</label>
              <input
                type="text"
                className="form-input"
                placeholder="যেমন: শিডিউল কিনেছেন, সাব-কন্ট্রাক্টরের সাথে আলোচনা করছেন..."
                value={nextActionTaken}
                onChange={(e) => setNextActionTaken(e.target.value)}
              />
            </div>

            {/* Operator Notes */}
            <div className="form-group">
              <label className="form-label">অপারেটরের ব্যক্তিগত পর্যবেক্ষণ বা নোট</label>
              <textarea
                className="form-textarea"
                rows={3}
                placeholder="পরবর্তী ফলো-আপের জন্য কোনো মন্তব্য থাকলে লিখুন..."
                value={operatorNotes}
                onChange={(e) => setOperatorNotes(e.target.value)}
              />
            </div>

            <div style={{ fontSize: '0.8rem', color: '#64748b', display: 'flex', alignItems: 'center', gap: '6px' }}>
              <HelpCircle size={14} />
              <span>এই প্রতিক্রিয়া পাইলট টেস্টিং ফলাফল সমৃদ্ধ করতে ডাটাবেজে সংরক্ষিত হবে।</span>
            </div>
          </div>

          <div className="modal-footer">
            <button type="button" className="btn btn-outline" onClick={onClose} disabled={isSubmitting}>
              বাতিল
            </button>
            <button type="submit" className="btn btn-primary" disabled={isSubmitting}>
              <Save size={16} />
              <span>{isSubmitting ? 'সংরক্ষণ হচ্ছে...' : 'প্রতিক্রিয়া সংরক্ষণ করুন'}</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
