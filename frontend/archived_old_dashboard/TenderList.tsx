import React, { useState, useMemo } from 'react';
import { Search, Filter, AlertTriangle, Layers, RotateCcw } from 'lucide-react';
import type { Tender } from '../types';
import { TenderCard } from './TenderCard';
import { toBnNumber } from '../utils/formatters';

interface TenderListProps {
  tenders: Tender[];
  activeFilter: string;
  onSelectFilter: (filter: string) => void;
  onOpenWhatsApp: (tender: Tender) => void;
  onOpenDetails: (tender: Tender) => void;
  onOpenFeedback: (tender: Tender) => void;
  onUpdateStatus: (assessmentId: number, status: 'shortlisted' | 'rejected' | 'pending') => void;
}

export const TenderList: React.FC<TenderListProps> = ({
  tenders,
  activeFilter,
  onSelectFilter,
  onOpenWhatsApp,
  onOpenDetails,
  onOpenFeedback,
  onUpdateStatus
}) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [fitFilter, setFitFilter] = useState<'all' | 'fits' | 'partial' | 'outside'>('all');
  const [onlyAmendments, setOnlyAmendments] = useState(false);

  // Filter logic
  const filteredTenders = useMemo(() => {
    return tenders.filter((t) => {
      // 1. Review status filter
      if (activeFilter === 'pending' && t.assessment?.operator_review_status !== 'pending') {
        return false;
      }
      if (activeFilter === 'shortlisted' && t.assessment?.operator_review_status !== 'shortlisted') {
        return false;
      }
      if (activeFilter === 'rejected' && t.assessment?.operator_review_status !== 'rejected') {
        return false;
      }
      if (activeFilter === 'needs_more_info' && t.assessment?.operator_review_status !== 'needs_more_info') {
        return false;
      }

      // 2. Fit filter
      if (fitFilter !== 'all' && t.assessment?.preference_fit_status !== fitFilter) {
        return false;
      }

      // 3. Amendments only filter (derived directly from checkbox or overview filter)
      const shouldFilterAmendments = onlyAmendments || activeFilter === 'amendment';
      if (shouldFilterAmendments && !t.is_amendment) {
        return false;
      }

      // 4. Search text
      if (searchQuery.trim()) {
        const query = searchQuery.toLowerCase();
        const matchTitle = t.title.toLowerCase().includes(query);
        const matchId = t.tender_id.toLowerCase().includes(query);
        const matchAgency = t.agency.toLowerCase().includes(query);
        const matchDistrict = t.project_location_district.toLowerCase().includes(query);
        if (!matchTitle && !matchId && !matchAgency && !matchDistrict) {
          return false;
        }
      }

      return true;
    });
  }, [tenders, activeFilter, fitFilter, onlyAmendments, searchQuery]);

  const handleResetFilters = () => {
    onSelectFilter('all');
    setFitFilter('all');
    setOnlyAmendments(false);
    setSearchQuery('');
  };

  return (
    <div>
      {/* Search & Filter Toolbar */}
      <div className="toolbar-card">
        {/* Search Input */}
        <div className="search-input-group">
          <Search size={18} color="#64748b" />
          <input
            type="text"
            placeholder="টেন্ডার আইডি, শিরোনাম, সংস্থা বা জেলা দিয়ে খুঁজুন..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
          {searchQuery && (
            <button
              onClick={() => setSearchQuery('')}
              style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#94a3b8' }}
            >
              ✕
            </button>
          )}
        </div>

        {/* Filter Pills */}
        <div className="filter-pills-group">
          <span style={{ fontSize: '0.84rem', color: '#64748b', display: 'flex', alignItems: 'center', gap: '4px' }}>
            <Filter size={14} /> স্ট্যাটাস:
          </span>

          <button
            className={`filter-pill ${activeFilter === 'all' ? 'active' : ''}`}
            onClick={() => onSelectFilter('all')}
          >
            সব ({toBnNumber(tenders.length)})
          </button>

          <button
            className={`filter-pill ${activeFilter === 'pending' ? 'active' : ''}`}
            onClick={() => onSelectFilter('pending')}
          >
            অপেক্ষায়
          </button>

          <button
            className={`filter-pill ${activeFilter === 'shortlisted' ? 'active' : ''}`}
            onClick={() => onSelectFilter('shortlisted')}
          >
            শর্টলিস্টেড
          </button>

          <button
            className={`filter-pill ${activeFilter === 'rejected' ? 'active' : ''}`}
            onClick={() => onSelectFilter('rejected')}
          >
            বাতিল
          </button>
        </div>

        {/* Secondary Fit & Amendment toggles */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap' }}>
          <select
            className="form-select"
            style={{ width: 'auto', padding: '6px 12px', fontSize: '0.84rem' }}
            value={fitFilter}
            onChange={(e) => setFitFilter(e.target.value as any)}
          >
            <option value="all">সব ধরনের মিল</option>
            <option value="fits">সরাসরি মিল (Fits)</option>
            <option value="partial">আংশিক মিল (Partial)</option>
            <option value="outside">পছন্দের বাইরে (Outside)</option>
          </select>

          <label
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              fontSize: '0.85rem',
              cursor: 'pointer',
              userSelect: 'none',
              padding: '6px 10px',
              borderRadius: '8px',
              backgroundColor: onlyAmendments ? '#fef3c7' : '#f8fafc',
              border: `1px solid ${onlyAmendments ? '#f59e0b' : '#e2e8f0'}`,
              color: onlyAmendments ? '#92400e' : '#475569'
            }}
          >
            <input
              type="checkbox"
              checked={onlyAmendments}
              onChange={(e) => setOnlyAmendments(e.target.checked)}
              style={{ accentColor: '#d97706' }}
            />
            <AlertTriangle size={14} color="#d97706" />
            <span>সংশোধনী নোটিশ</span>
          </label>
        </div>
      </div>

      {/* Section Header */}
      <div className="tenders-section-title">
        <h2 style={{ fontSize: '1.2rem', fontWeight: 700, color: 'var(--navy-900)', display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Layers size={20} color="#059669" />
          <span>উপলব্ধ দরপত্র তালিকা ({toBnNumber(filteredTenders.length)} টি)</span>
        </h2>

        {(activeFilter !== 'all' || fitFilter !== 'all' || onlyAmendments || searchQuery) && (
          <button
            className="btn btn-outline btn-sm"
            onClick={handleResetFilters}
            style={{ fontSize: '0.8rem' }}
          >
            <RotateCcw size={12} />
            <span>ফিল্টার রিসেট</span>
          </button>
        )}
      </div>

      {/* Tenders Grid */}
      {filteredTenders.length > 0 ? (
        <div className="tenders-grid">
          {filteredTenders.map((tender) => (
            <TenderCard
              key={tender.id}
              tender={tender}
              onOpenWhatsApp={onOpenWhatsApp}
              onOpenDetails={onOpenDetails}
              onOpenFeedback={onOpenFeedback}
              onUpdateStatus={onUpdateStatus}
            />
          ))}
        </div>
      ) : (
        <div
          style={{
            background: 'white',
            borderRadius: '12px',
            border: '1px solid #e2e8f0',
            padding: '48px 24px',
            textAlign: 'center',
            color: '#64748b'
          }}
        >
          <div style={{ fontSize: '2.5rem', marginBottom: '12px' }}>🔍</div>
          <h3 style={{ fontSize: '1.1rem', fontWeight: 600, color: '#0f243e', marginBottom: '8px' }}>
            কোনো টেন্ডার পাওয়া যায়নি
          </h3>
          <p style={{ fontSize: '0.9rem', maxWidth: '420px', margin: '0 auto 16px auto' }}>
            আপনার বর্তমান ফিল্টার বা সার্চ কোয়েরির সাথে কোনো টেন্ডার মিলেনি। ফিল্টার রিসেট করে আবার চেষ্টা করুন।
          </p>
          <button className="btn btn-navy btn-sm" onClick={handleResetFilters}>
            সব টেন্ডার দেখুন
          </button>
        </div>
      )}
    </div>
  );
};
