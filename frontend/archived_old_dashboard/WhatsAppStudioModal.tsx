import React, { useState } from 'react';
import {
  X,
  Copy,
  ExternalLink,
  Check,
  Edit3,
  Save,
  CheckCircle,
  Phone,
  Send,
  MessageSquare,
  Sparkles
} from 'lucide-react';
import type { Tender, ContractorProfile, AIPolishResponse } from '../types';

interface WhatsAppStudioModalProps {
  tender: Tender | null;
  contractor: ContractorProfile | null;
  onClose: () => void;
  onUpdateDraftMessage: (draftId: number, newText: string) => Promise<void>;
  onApproveDraft: (draftId: number) => Promise<void>;
  onMarkDraftSent: (draftId: number) => Promise<void>;
  onPolishWithAI?: (draftId: number) => Promise<AIPolishResponse>;
  onShowToast: (msg: string) => void;
}

export const WhatsAppStudioModal: React.FC<WhatsAppStudioModalProps> = ({
  tender,
  contractor,
  onClose,
  onUpdateDraftMessage,
  onApproveDraft,
  onMarkDraftSent,
  onPolishWithAI,
  onShowToast
}) => {
  const draft = tender?.draft;
  const [isEditing, setIsEditing] = useState(false);
  const [messageText, setMessageText] = useState(draft?.draft_message_bn || '');
  const [isSaving, setIsSaving] = useState(false);
  const [isApproved, setIsApproved] = useState(draft?.approval_status === 'approved');
  const [isSent, setIsSent] = useState(draft?.manual_send_recorded ?? false);
  const [copied, setCopied] = useState(false);
  const [isPolishing, setIsPolishing] = useState(false);
  const [aiNotice, setAiNotice] = useState<string | null>(null);

  const [prevDraftId, setPrevDraftId] = useState(draft?.id);
  if (draft && draft.id !== prevDraftId) {
    setPrevDraftId(draft.id);
    setMessageText(draft.draft_message_bn || '');
    setIsApproved(draft.approval_status === 'approved');
    setIsSent(draft.manual_send_recorded);
  }

  if (!tender || !draft) return null;

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(messageText);
      setCopied(true);
      onShowToast('✓ হোয়াটসঅ্যাপ বার্তা ক্লিপবোর্ডে কপি করা হয়েছে');
      setTimeout(() => setCopied(false), 2500);
    } catch {
      onShowToast('কপি করতে ব্যর্থ হয়েছে, ম্যানুয়ালি সিলেক্ট করে কপি করুন');
    }
  };

  const handleSaveEdit = async () => {
    if (!draft.id) return;
    setIsSaving(true);
    try {
      await onUpdateDraftMessage(draft.id, messageText);
      setIsEditing(false);
      onShowToast('✓ বার্তার খসড়া সফলভাবে হালনাগাদ করা হয়েছে');
    } catch {
      onShowToast('সংরক্ষণ ব্যর্থ হয়েছে');
    } finally {
      setIsSaving(false);
    }
  };

  const handleApprove = async () => {
    if (!draft.id) return;
    try {
      await onApproveDraft(draft.id);
      setIsApproved(true);
      onShowToast('✓ বার্তা ড্রাফট অনুমোদিত হয়েছে');
    } catch {
      onShowToast('অনুমোদন ব্যর্থ হয়েছে');
    }
  };

  const handleMarkSent = async () => {
    if (!draft.id) return;
    try {
      await onMarkDraftSent(draft.id);
      setIsSent(true);
      onShowToast('✓ হোয়াটসঅ্যাপে পাঠানো সম্পন্ন হিসেবে চিহ্নিত করা হয়েছে');
    } catch {
      onShowToast('স্ট্যাটাস আপডেট ব্যর্থ হয়েছে');
    }
  };

  const handlePolishAI = async () => {
    if (!draft.id) return;
    setIsPolishing(true);
    setAiNotice(null);
    try {
      if (onPolishWithAI) {
        const res = await onPolishWithAI(draft.id);
        setMessageText(res.draft_message_bn);
        if (res.ai_generated) {
          setAiNotice(`✓ এআই (${res.model_used || 'Ollama'}) দ্বারা বার্তা মার্জিত করা হয়েছে`);
          onShowToast('✓ এআই দ্বারা বার্তা মার্জিত করা হয়েছে');
        } else {
          setAiNotice('✓ ব্যাকআপ ইঞ্জিন দ্বারা বার্তা প্রস্তুত করা হয়েছে');
          onShowToast('✓ ব্যাকআপ ইঞ্জিন দ্বারা বার্তা প্রস্তুত করা হয়েছে');
        }
      }
    } catch (err) {
      console.error('AI polish error:', err);
      onShowToast('এআই মার্জিতকরণে সমস্যা হয়েছে, পুনরায় চেষ্টা করুন');
    } finally {
      setIsPolishing(false);
    }
  };

  // WhatsApp Web Send URL
  const phone = contractor?.whatsapp_number?.replace(/[^0-9]/g, '') || '8801711000000';
  const whatsappUrl = `https://wa.me/${phone}?text=${encodeURIComponent(messageText)}`;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div
        className="modal-container"
        style={{ maxWidth: '780px' }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Modal Header */}
        <div className="modal-header">
          <div>
            <h3 className="modal-title" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <MessageSquare size={20} color="#059669" />
              হোয়াটসঅ্যাপ বার্তা স্টুডিও (WhatsApp Assistant)
            </h3>
            <p style={{ fontSize: '0.84rem', color: '#64748b' }}>
              টেন্ডার আইডি: <strong>{tender.tender_id}</strong> | প্রাপক: <strong>{contractor?.contact_person}</strong>
            </p>
          </div>
          <button className="close-btn" onClick={onClose} aria-label="Close modal">
            <X size={20} />
          </button>
        </div>

        {/* Modal Body */}
        <div className="modal-body" style={{ background: '#f8fafc', padding: '20px' }}>
          {/* Status Alert */}
          <div
            style={{
              padding: '10px 16px',
              borderRadius: '8px',
              marginBottom: '16px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              backgroundColor: isSent ? '#d1fae5' : isApproved ? '#ecfdf5' : '#fef3c7',
              border: `1px solid ${isSent ? '#6ee7b7' : isApproved ? '#a7f3d0' : '#fde68a'}`,
              fontSize: '0.88rem'
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              {isSent ? (
                <CheckCircle size={18} color="#047857" />
              ) : isApproved ? (
                <Check size={18} color="#059669" />
              ) : (
                <Edit3 size={18} color="#d97706" />
              )}
              <span>
                <strong>অবস্থা:</strong>{' '}
                {isSent
                  ? 'ঠিকাদারকে পাঠানো সম্পন্ন হয়েছে'
                  : isApproved
                  ? 'অপারেটর দ্বারা অনুমোদিত (পাঠানোর জন্য প্রস্তুত)'
                  : 'খসড়া ড্রাফট অবস্থায় রয়েছে'}
              </span>
            </div>

            <div style={{ display: 'flex', gap: '8px' }}>
              {!isEditing ? (
                <button
                  className="btn btn-outline btn-sm"
                  onClick={() => setIsEditing(true)}
                  style={{ background: 'white' }}
                >
                  <Edit3 size={14} />
                  <span>টেক্সট এডিট করুন</span>
                </button>
              ) : (
                <button
                  className="btn btn-primary btn-sm"
                  onClick={handleSaveEdit}
                  disabled={isSaving}
                >
                  <Save size={14} />
                  <span>{isSaving ? 'সংরক্ষণ হচ্ছে...' : 'সংরক্ষণ করুন'}</span>
                </button>
              )}
            </div>
          </div>

          {aiNotice && (
            <div
              id="ai-polish-notice"
              style={{
                padding: '8px 14px',
                borderRadius: '8px',
                marginBottom: '12px',
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                backgroundColor: '#ede9fe',
                border: '1px solid #c4b5fd',
                color: '#5b21b6',
                fontSize: '0.86rem',
                fontWeight: 500
              }}
            >
              <Sparkles size={16} color="#7c3aed" />
              <span>{aiNotice}</span>
            </div>
          )}

          {/* WhatsApp Realistic Chat Frame */}
          <div className="whatsapp-chat-card">
            {/* WA Header */}
            <div className="whatsapp-chat-header">
              <div className="whatsapp-chat-header-info">
                <div className="wa-avatar">
                  {contractor?.contact_person ? contractor.contact_person[0] : 'ঠ'}
                </div>
                <div>
                  <div style={{ fontWeight: 600, fontSize: '0.98rem' }}>
                    {contractor?.contact_person || 'পাইলট ঠিকাদার'}
                  </div>
                  <div style={{ fontSize: '0.78rem', opacity: 0.9, display: 'flex', alignItems: 'center', gap: '4px' }}>
                    <Phone size={11} /> {contractor?.whatsapp_number || '+8801711000000'} (অনলাইন)
                  </div>
                </div>
              </div>
              <div style={{ fontSize: '0.78rem', background: 'rgba(0,0,0,0.2)', padding: '4px 10px', borderRadius: '12px' }}>
                ইজারাবিডি প্রিভিউ
              </div>
            </div>

            {/* WA Message Bubble */}
            <div className="whatsapp-body">
              {isEditing ? (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                  <textarea
                    className="form-textarea"
                    rows={15}
                    value={messageText}
                    onChange={(e) => setMessageText(e.target.value)}
                    style={{
                      fontFamily: 'inherit',
                      fontSize: '0.92rem',
                      lineHeight: '1.6',
                      background: '#ffffff'
                    }}
                  />
                  <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px' }}>
                    <button className="btn btn-outline btn-sm" onClick={() => setIsEditing(false)}>
                      বাতিল
                    </button>
                    <button className="btn btn-primary btn-sm" onClick={handleSaveEdit} disabled={isSaving}>
                      <Save size={14} /> পরিবর্তন সংরক্ষণ
                    </button>
                  </div>
                </div>
              ) : (
                <div className="whatsapp-bubble" id="whatsapp-message-bubble">
                  {messageText}
                  <div className="whatsapp-time">
                    <span>আজ BST</span>
                    {isSent ? (
                      <span style={{ color: '#53bdeb', display: 'flex' }}>✓✓</span>
                    ) : (
                      <span>✓</span>
                    )}
                  </div>
                </div>
              )}
            </div>

            {/* WA Action Bar */}
            <div className="whatsapp-actions-bar">
              <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', alignItems: 'center' }}>
                {/* AI Polish Button */}
                <button
                  id="btn-ai-polish"
                  className="btn btn-sm"
                  onClick={handlePolishAI}
                  disabled={isPolishing}
                  style={{
                    background: isPolishing ? '#94a3b8' : 'linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%)',
                    color: '#ffffff',
                    border: 'none',
                    boxShadow: '0 2px 4px rgba(79, 70, 229, 0.25)',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '6px',
                    cursor: isPolishing ? 'not-allowed' : 'pointer'
                  }}
                  title="এআই বা ব্যাকআপ ইঞ্জিন ব্যবহার করে বার্তাটি আরও সাবলীল ও মার্জিত করুন"
                >
                  <Sparkles size={15} className={isPolishing ? 'animate-spin' : ''} />
                  <span>{isPolishing ? 'মার্জিত করা হচ্ছে...' : '✨ এআই দিয়ে মার্জিত করুন'}</span>
                </button>

                {/* Copy Button */}
                <button
                  className="btn btn-outline btn-sm"
                  onClick={handleCopy}
                  style={{ background: 'white' }}
                >
                  {copied ? <Check size={16} color="#059669" /> : <Copy size={16} />}
                  <span>{copied ? 'কপি হয়েছে!' : 'মেসেজ কপি করুন'}</span>
                </button>

                {/* Approve Draft Button */}
                {!isApproved && (
                  <button
                    className="btn btn-outline btn-sm"
                    onClick={handleApprove}
                    style={{ background: '#ecfdf5', color: '#047857', borderColor: '#a7f3d0' }}
                  >
                    <CheckCircle size={15} />
                    <span>ড্রাফট অনুমোদন করুন</span>
                  </button>
                )}
              </div>

              <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                {/* Direct WhatsApp Web Link */}
                <a
                  href={whatsappUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="btn btn-whatsapp btn-sm"
                  title="WhatsApp Web এ প্রি-ফিল্ড বার্তা সহ চ্যাট খুলুন"
                >
                  <ExternalLink size={15} />
                  <span>হোয়াটসঅ্যাপে পাঠান</span>
                </a>

                {/* Mark Sent Button */}
                {!isSent && (
                  <button
                    className="btn btn-primary btn-sm"
                    onClick={handleMarkSent}
                    title="হোয়াটসঅ্যাপে পাঠানো সম্পন্ন হয়েছে বলে চিহ্নিত করুন"
                  >
                    <Send size={15} />
                    <span>পাঠানো সম্পন্ন হিসেবে মার্ক করুন</span>
                  </button>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* Modal Footer */}
        <div className="modal-footer">
          <button className="btn btn-outline" onClick={onClose}>
            বন্ধ করুন
          </button>
        </div>
      </div>
    </div>
  );
};
