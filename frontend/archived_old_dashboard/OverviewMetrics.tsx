import React from 'react';
import {
  FileText,
  Clock,
  CheckCircle2,
  MessageSquare,
  Send,
  HelpCircle,
  AlertTriangle
} from 'lucide-react';
import type { OperatorOverview } from '../types';
import { toBnNumber } from '../utils/formatters';

interface OverviewMetricsProps {
  overview: OperatorOverview | null;
  selectedFilter: string;
  onSelectFilter: (filter: string) => void;
}

export const OverviewMetrics: React.FC<OverviewMetricsProps> = ({
  overview,
  selectedFilter,
  onSelectFilter
}) => {
  if (!overview) return null;

  const cards = [
    {
      id: 'all',
      label: 'মোট টেন্ডার',
      val: overview.total_tenders,
      icon: <FileText size={22} color="#0f243e" />,
      bg: '#e2e8f0',
      activeFilter: 'all'
    },
    {
      id: 'pending',
      label: 'পর্যালোচনার অপেক্ষায়',
      val: overview.awaiting_review,
      icon: <Clock size={22} color="#d97706" />,
      bg: '#fef3c7',
      activeFilter: 'pending'
    },
    {
      id: 'shortlisted',
      label: 'শর্টলিস্টেড',
      val: overview.shortlisted,
      icon: <CheckCircle2 size={22} color="#059669" />,
      bg: '#d1fae5',
      activeFilter: 'shortlisted'
    },
    {
      id: 'drafts',
      label: 'ড্রাফট প্রস্তুত',
      val: overview.drafts_awaiting_approval,
      icon: <MessageSquare size={22} color="#2563eb" />,
      bg: '#dbeafe',
      activeFilter: 'all'
    },
    {
      id: 'sent',
      label: 'পাঠানো সম্পন্ন',
      val: overview.manual_sent_count,
      icon: <Send size={22} color="#0d9488" />,
      bg: '#ccfbf1',
      activeFilter: 'all'
    },
    {
      id: 'feedback',
      label: 'সংগৃহীত ফিডব্যাক',
      val: overview.feedback_count,
      icon: <HelpCircle size={22} color="#7c3aed" />,
      bg: '#ede9fe',
      activeFilter: 'all'
    },
    {
      id: 'amendment',
      label: 'সংশোধনী অ্যালার্ট',
      val: overview.amendments_count,
      icon: <AlertTriangle size={22} color="#dc2626" />,
      bg: '#fee2e2',
      activeFilter: 'amendment'
    }
  ];

  return (
    <div className="metrics-grid">
      {cards.map((c) => {
        const isSelected = selectedFilter === c.activeFilter && c.activeFilter !== 'all';
        return (
          <div
            key={c.id}
            className="metric-card"
            style={{
              cursor: 'pointer',
              border: isSelected ? '2px solid var(--navy-800)' : undefined,
              backgroundColor: isSelected ? '#f8fafc' : undefined
            }}
            onClick={() => onSelectFilter(c.activeFilter)}
            title={`ক্লিক করে ${c.label} ফিল্টার করুন`}
          >
            <div className="metric-icon-wrap" style={{ backgroundColor: c.bg }}>
              {c.icon}
            </div>
            <div className="metric-info">
              <span className="metric-val">{toBnNumber(c.val)}</span>
              <span className="metric-label">{c.label}</span>
            </div>
          </div>
        );
      })}
    </div>
  );
};
