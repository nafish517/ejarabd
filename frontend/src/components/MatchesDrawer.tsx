import React, { useState, useEffect } from 'react';
import { X, Send, ExternalLink, CheckCircle, AlertTriangle, HelpCircle, RefreshCw, FileText } from 'lucide-react';
import type { Client, MatchedTender } from '../types';

import { api } from '../services/api';

interface MatchesDrawerProps {
  client: Client | null;
  isOpen: boolean;
  onClose: () => void;
  onSendTestEmail: (clientId: number, tenderId?: number) => Promise<void>;
}

export const MatchesDrawer: React.FC<MatchesDrawerProps> = ({
  client,
  isOpen,
  onClose,
  onSendTestEmail,
}) => {
  const [matches, setMatches] = useState<MatchedTender[]>([]);
  const [fitFilter, setFitFilter] = useState<string>('');
  const [isLoading, setIsLoading] = useState(false);
  const [sendingTenderId, setSendingTenderId] = useState<number | null>(null);

  useEffect(() => {
    if (client && isOpen) {
      loadMatches();
    }
  }, [client, isOpen, fitFilter]);

  const loadMatches = async () => {
    if (!client) return;
    setIsLoading(true);
    try {
      const res = await api.getClientMatches(client.id, fitFilter || undefined);
      setMatches(res.matches || []);
    } catch (err) {
      console.error('Failed to load matches:', err);
    } finally {
      setIsLoading(false);
    }
  };

  if (!isOpen || !client) return null;

  const handleSendEmail = async (tenderId: number) => {
    setSendingTenderId(tenderId);
    try {
      await onSendTestEmail(client.id, tenderId);
    } finally {
      setSendingTenderId(null);
    }
  };

  const formatBDT = (amount: number | null | undefined) => {
    if (amount == null) return 'অজ্ঞাত / নোটিশে অপ্রকাশিত';
    if (amount >= 10000000) return `৳ ${(amount / 10000000).toFixed(2)} কোটি`;
    if (amount >= 100000) return `৳ ${(amount / 100000).toFixed(2)} লাখ`;
    return `৳ ${amount.toLocaleString()}`;
  };

  const formatBST = (dateStr: string | null | undefined) => {
    if (!dateStr) return 'নোটিশে সময় উল্লেখ নেই';
    try {
      const dt = new Date(dateStr);
      return dt.toLocaleString('bn-BD', {
        day: 'numeric',
        month: 'short',
        year: 'numeric',
        hour: 'numeric',
        minute: 'numeric',
        hour12: true,
      }) + ' (BST)';
    } catch {
      return dateStr;
    }
  };

  return (
    <div className="modal-backdrop" onClick={onClose} style={{ justifyContent: 'flex-end', alignItems: 'stretch' }}>
      <div
        className="modal-content"
        style={{
          width: '780px',
          maxWidth: '100%',
          height: '100vh',
          maxHeight: '100vh',
          borderRadius: '0',
          display: 'flex',
          flexDirection: 'column',
          borderLeft: '1px solid var(--border-subtle)',
          boxShadow: 'var(--shadow-drawer)',
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Drawer Header */}
        <div className="modal-header" style={{ borderBottom: '1px solid var(--border-subtle)' }}>
          <div>
            <h3 className="modal-title" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <FileText size={18} color="var(--primary)" />
              <span>ম্যাচ হওয়া দরপত্রসমূহ — {client.business_name}</span>
            </h3>
            <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '3px', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span>গ্রাহক ID: #{client.id}</span>
              <span>•</span>
              <span>পছন্দের জেলা: {(client.preferred_districts || []).join(', ') || 'Dinajpur'}</span>
            </div>
          </div>
          <button className="btn btn-secondary btn-icon" onClick={onClose}>
            <X size={16} />
          </button>
        </div>

        {/* Filter Bar */}
        <div style={{ padding: '12px 20px', background: 'var(--bg-subtle)', borderBottom: '1px solid var(--border-subtle)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div style={{ display: 'flex', gap: '8px' }}>
            <button
              className={`btn btn-sm ${fitFilter === '' ? 'btn-primary' : 'btn-secondary'}`}
              onClick={() => setFitFilter('')}
            >
              সব উপযুক্ত টেন্ডার
            </button>
            <button
              className={`btn btn-sm ${fitFilter === 'fits' ? 'btn-primary' : 'btn-secondary'}`}
              onClick={() => setFitFilter('fits')}
            >
              পূর্ণ মিল (Fits)
            </button>
            <button
              className={`btn btn-sm ${fitFilter === 'partial' ? 'btn-primary' : 'btn-secondary'}`}
              onClick={() => setFitFilter('partial')}
            >
              আংশিক মিল (Partial)
            </button>
            <button
              className={`btn btn-sm ${fitFilter === 'outside' ? 'btn-primary' : 'btn-secondary'}`}
              onClick={() => setFitFilter('outside')}
            >
              তালিকার বাইরে (Outside)
            </button>
          </div>

          <button className="btn btn-secondary btn-sm" onClick={loadMatches} disabled={isLoading} title="রিফ্রেশ">
            <RefreshCw size={13} className={isLoading ? 'spin' : ''} />
          </button>
        </div>

        {/* Tenders List */}
        <div style={{ flex: 1, overflowY: 'auto', padding: '20px' }}>
          {isLoading ? (
            <div style={{ padding: '60px', textAlign: 'center', color: 'var(--text-muted)' }}>
              ম্যাচিং দরপত্র লোড হচ্ছে...
            </div>
          ) : matches.length === 0 ? (
            <div style={{ padding: '60px', textAlign: 'center', color: 'var(--text-muted)', background: 'var(--bg-subtle)', borderRadius: '12px', border: '1px dashed var(--border-subtle)' }}>
              <FileText size={36} style={{ margin: '0 auto 12px', opacity: 0.4 }} />
              <div style={{ fontSize: '15px', fontWeight: 600, color: 'var(--text-secondary)' }}>কোনো দরপত্র মেলেনি</div>
              <div style={{ fontSize: '13px', marginTop: '4px' }}>
                পছন্দের জেলা বা কাজের ক্যাটাগরির সাথে মিলে এমন কোনো লাইভ টেন্ডার পাওয়া যায়নি। উপরে 'Run Matching' চালিয়ে দেখতে পারেন।
              </div>
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              {matches.map((item) => {
                const isFit = item.preference_fit_status === 'fits';
                const isPartial = item.preference_fit_status === 'partial';

                return (
                  <div
                    key={item.tender_id}
                    style={{
                      background: 'var(--bg-surface)',
                      border: '1px solid var(--border-subtle)',
                      borderRadius: '12px',
                      padding: '16px 18px',
                      transition: 'all 0.15s var(--ease)',
                    }}
                  >
                    {/* Top Row: Tender ID & Badges */}
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '10px', marginBottom: '8px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <span className="mono-cell" style={{ fontWeight: 700, color: 'var(--primary)', fontSize: '13px' }}>
                          ID: {item.official_tender_id}
                        </span>
                        <span className="badge badge-secondary" style={{ fontSize: '11px' }}>
                          {item.category}
                        </span>
                      </div>

                      <span
                        className={`badge ${isFit ? 'badge-emerald' : isPartial ? 'badge-amber' : 'badge-secondary'}`}
                        style={{ fontSize: '11px', display: 'flex', alignItems: 'center', gap: '4px' }}
                      >
                        {isFit ? <CheckCircle size={11} /> : isPartial ? <AlertTriangle size={11} /> : <HelpCircle size={11} />}
                        <span>{isFit ? 'পূর্ণ মিল (Fits)' : isPartial ? 'আংশিক মিল' : 'তালিকার বাইরে'}</span>
                      </span>
                    </div>

                    {/* Title */}
                    <h4 style={{ fontSize: '14px', fontWeight: 600, color: 'var(--text-primary)', lineHeight: 1.4, marginBottom: '10px' }}>
                      {item.title}
                    </h4>

                    {/* Meta specs grid */}
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '8px', fontSize: '12px', background: 'var(--bg-subtle)', padding: '10px 12px', borderRadius: '8px', marginBottom: '12px' }}>
                      <div>
                        <span style={{ color: 'var(--text-muted)' }}>🏢 সংস্থা: </span>
                        <strong style={{ color: 'var(--text-secondary)' }}>{item.agency}</strong>
                      </div>
                      <div>
                        <span style={{ color: 'var(--text-muted)' }}>📍 কাজের জেলা: </span>
                        <strong style={{ color: 'var(--text-secondary)' }}>{item.district} {item.location_details ? `(${item.location_details})` : ''}</strong>
                      </div>
                      <div>
                        <span style={{ color: 'var(--text-muted)' }}>💰 প্রাক্কলিত বাজেট: </span>
                        <span style={{ color: item.estimated_value_bdt ? 'var(--emerald-text)' : 'var(--text-muted)', fontWeight: 600 }}>
                          {formatBDT(item.estimated_value_bdt)}
                        </span>
                      </div>
                      <div>
                        <span style={{ color: 'var(--text-muted)' }}>🔒 টেন্ডার সিকিউরিটি: </span>
                        <span style={{ color: 'var(--text-primary)', fontWeight: 600 }}>{formatBDT(item.tender_security_bdt)}</span>
                      </div>
                      <div style={{ gridColumn: '1 / -1' }}>
                        <span style={{ color: 'var(--text-muted)' }}>⏰ জমা দেওয়ার শেষ সময়: </span>
                        <span style={{ color: '#f87171', fontWeight: 600 }}>{formatBST(item.closing_date)}</span>
                      </div>
                    </div>

                    {/* Relevance Explanation */}
                    {item.preference_reasons?.length > 0 && (
                      <div style={{ marginBottom: '8px', fontSize: '12px', color: 'var(--emerald-text)' }}>
                        <strong>✓ কেন প্রাসঙ্গিক:</strong> {item.preference_reasons.join(' • ')}
                      </div>
                    )}

                    {item.known_mismatches?.length > 0 && (
                      <div style={{ marginBottom: '8px', fontSize: '12px', color: 'var(--amber-text)' }}>
                        <strong>⚠️ অমিল:</strong> {item.known_mismatches.join(' • ')}
                      </div>
                    )}

                    {/* Action Bar */}
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '12px', paddingTop: '10px', borderTop: '1px solid var(--border-subtle)' }}>
                      <a
                        href={item.source_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="btn btn-secondary btn-sm"
                        style={{ display: 'inline-flex', alignItems: 'center', gap: '6px', fontSize: '12px' }}
                      >
                        <ExternalLink size={13} />
                        <span>অফিসিয়াল e-GP নোটিশ</span>
                      </a>

                      <button
                        className="btn btn-primary btn-sm"
                        onClick={() => handleSendEmail(item.tender_id)}
                        disabled={sendingTenderId === item.tender_id}
                        style={{ display: 'inline-flex', alignItems: 'center', gap: '6px', fontSize: '12px' }}
                      >
                        <Send size={13} />
                        <span>{sendingTenderId === item.tender_id ? 'পাঠানো হচ্ছে...' : 'এই টেন্ডারটির টেস্ট ইমেইল পাঠান'}</span>
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
