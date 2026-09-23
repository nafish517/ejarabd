import React, { useState, useMemo } from 'react';
import {
  Search,
  Users,
  Send,
  ExternalLink,
  MapPin,
  HelpCircle
} from 'lucide-react';
import type { Tender, Client } from '../types';

interface TendersViewProps {
  tenders: Tender[];
  clients: Client[];
  selectedClient: Client | null;
  onSelectClient: (client: Client | null) => void;
  onViewMatchExplanation: (tenderId: number, contractorId?: number) => void;
  onSendTenderEmail: (tender: Tender, client?: Client) => void;
}

export const TendersView: React.FC<TendersViewProps> = ({
  tenders,
  clients,
  selectedClient,
  onSelectClient,
  onViewMatchExplanation,
  onSendTenderEmail,
}) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [districtFilter, setDistrictFilter] = useState('all');
  const [fitFilter, setFitFilter] = useState('all');

  // Extract unique districts
  const districts = useMemo(() => {
    const set = new Set<string>();
    tenders.forEach((t) => {
      if (t.project_location_district) set.add(t.project_location_district);
    });
    return Array.from(set).sort();
  }, [tenders]);

  const filteredTenders = useMemo(() => {
    return tenders.filter((t) => {
      // Search
      const matchSearch =
        t.tender_id.toLowerCase().includes(searchQuery.toLowerCase()) ||
        t.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
        t.agency.toLowerCase().includes(searchQuery.toLowerCase()) ||
        t.category.toLowerCase().includes(searchQuery.toLowerCase());

      if (!matchSearch) return false;

      // District filter
      if (districtFilter !== 'all' && t.project_location_district !== districtFilter) {
        return false;
      }

      // Fit filter
      const fitStatus = t.assessment?.preference_fit_status || 'unassessed';
      if (fitFilter !== 'all' && fitStatus !== fitFilter) {
        return false;
      }

      return true;
    });
  }, [tenders, searchQuery, districtFilter, fitFilter]);

  return (
    <div>
      {/* Header & Client Isolation Bar */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '20px', flexWrap: 'wrap', gap: '12px' }}>
        <div>
          <h2 style={{ fontSize: '20px', fontWeight: 600, color: 'var(--text-primary)' }}>
            Tenders & Rule-Based Matching (দরপত্র ও ম্যাচিং)
          </h2>
          <p style={{ fontSize: '13px', color: 'var(--text-muted)' }}>
            Showing {filteredTenders.length} tenders from the preserved e-GP tender database.
          </p>
        </div>

        {/* Client Selector for isolated match evaluation */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', background: 'var(--bg-card)', padding: '6px 14px', borderRadius: '8px', border: '1px solid var(--border-subtle)' }}>
          <Users size={14} color="#38bdf8" />
          <span style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>Matching for:</span>
          <select
            className="form-select"
            style={{ width: 'auto', padding: '4px 8px', fontSize: '12px' }}
            value={selectedClient?.id || ''}
            onChange={(e) => {
              const id = parseInt(e.target.value, 10);
              const found = clients.find((c) => c.id === id) || null;
              onSelectClient(found);
            }}
          >
            {clients.map((c) => (
              <option key={c.id} value={c.id}>
                {c.business_name} ({c.district || c.preferred_districts?.[0] || 'All'})
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="panel" style={{ marginBottom: '20px' }}>
        <div className="panel-body" style={{ padding: '14px 20px', display: 'flex', alignItems: 'center', gap: '16px', flexWrap: 'wrap' }}>
          {/* Search Input */}
          <div style={{ position: 'relative', flex: 1, minWidth: '240px' }}>
            <Search size={15} style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
            <input
              type="text"
              className="form-input"
              style={{ paddingLeft: '36px' }}
              placeholder="Search by tender ID, title, agency, or work type..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </div>

          {/* District Filter */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>District:</span>
            <select
              className="form-select"
              style={{ width: 'auto' }}
              value={districtFilter}
              onChange={(e) => setDistrictFilter(e.target.value)}
            >
              <option value="all">All Districts</option>
              {districts.map((d) => (
                <option key={d} value={d}>{d}</option>
              ))}
            </select>
          </div>

          {/* Fit Status Filter */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Fit:</span>
            <select
              className="form-select"
              style={{ width: 'auto' }}
              value={fitFilter}
              onChange={(e) => setFitFilter(e.target.value)}
            >
              <option value="all">All Fits</option>
              <option value="fits">উপযুক্ত (Fits)</option>
              <option value="partial">আংশিক (Partial)</option>
              <option value="outside">বাইরে (Outside)</option>
            </select>
          </div>
        </div>
      </div>

      {/* Tenders Table */}
      <div className="panel">
        <div className="table-container">
          <table className="data-table">
            <thead>
              <tr>
                <th>Tender ID & Title</th>
                <th>Agency / Office</th>
                <th>District</th>
                <th>Estimated Value</th>
                <th>Closing Date</th>
                <th>Client Fit</th>
                <th style={{ textAlign: 'right' }}>Action</th>
              </tr>
            </thead>
            <tbody>
              {filteredTenders.length === 0 ? (
                <tr>
                  <td colSpan={7} style={{ textAlign: 'center', padding: '40px', color: 'var(--text-muted)' }}>
                    No tenders match the specified filters.
                  </td>
                </tr>
              ) : (
                filteredTenders.slice(0, 50).map((tender) => {
                  const fit = tender.assessment?.preference_fit_status || 'unassessed';

                  return (
                    <tr key={tender.id}>
                      <td style={{ maxWidth: '380px' }}>
                        <div>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '3px' }}>
                            <span className="mono-cell" style={{ fontSize: '12px', color: 'var(--border-focus)', fontWeight: 600 }}>
                              #{tender.tender_id}
                            </span>
                            {tender.is_amendment && (
                              <span className="badge badge-amber" style={{ fontSize: '10px' }}>সংশোধিত</span>
                            )}
                          </div>
                          <div style={{ fontSize: '13px', fontWeight: 500, color: 'var(--text-primary)', lineHeight: 1.3 }}>
                            {tender.title}
                          </div>
                          <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '2px' }}>
                            {tender.category}
                          </div>
                        </div>
                      </td>

                      <td>
                        <span style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
                          {tender.agency}
                        </span>
                      </td>

                      <td>
                        <span style={{ display: 'inline-flex', alignItems: 'center', gap: '4px', fontSize: '12px' }}>
                          <MapPin size={12} color="var(--text-muted)" />
                          {tender.project_location_district}
                        </span>
                      </td>

                      <td>
                        {tender.estimated_value_bdt ? (
                          <span className="mono-cell" style={{ fontSize: '12px', color: 'var(--text-primary)', fontWeight: 500 }}>
                            ৳{(tender.estimated_value_bdt / 100000).toFixed(1)}L
                          </span>
                        ) : (
                          <span style={{ color: 'var(--text-muted)', fontSize: '11px' }}>অনির্দিষ্ট</span>
                        )}
                      </td>

                      <td>
                        <span className="mono-cell" style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
                          {tender.closing_date}
                        </span>
                      </td>

                      <td>
                        {fit === 'fits' ? (
                          <span className="badge badge-emerald">উপযুক্ত (Fits)</span>
                        ) : fit === 'partial' ? (
                          <span className="badge badge-amber">আংশিক (Partial)</span>
                        ) : (
                          <span className="badge badge-slate">বাইরে (Outside)</span>
                        )}
                      </td>

                      <td style={{ textAlign: 'right' }}>
                        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '6px' }}>
                          <button
                            className="btn btn-secondary btn-sm"
                            title="Why did this tender match or not match this client?"
                            onClick={() => onViewMatchExplanation(tender.id, selectedClient?.id)}
                          >
                            <HelpCircle size={13} />
                            <span>Why?</span>
                          </button>

                          <button
                            className="btn btn-primary btn-sm"
                            title="Send email notification now"
                            onClick={() => onSendTenderEmail(tender, selectedClient || undefined)}
                          >
                            <Send size={12} />
                            <span>Send</span>
                          </button>

                          {tender.source_url && (
                            <a
                              href={tender.source_url}
                              target="_blank"
                              rel="noreferrer"
                              className="btn btn-secondary btn-sm"
                              title="Open on e-GP portal"
                            >
                              <ExternalLink size={12} />
                            </a>
                          )}
                        </div>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
