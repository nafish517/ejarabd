import React, { useState, useEffect, useCallback, useMemo } from 'react';
import {
  Building2,
  Plus,
  Play,
  Pause,
  Edit2,
  Send,
  Eye,
  Search,
  CheckCircle2,
  AlertCircle,
  ShieldCheck,
  FileText,
  UserCheck,
  ExternalLink,
  Database,
  ChevronLeft,
  ChevronRight,
  MapPin
} from 'lucide-react';
import { api } from './services/api';
import type { Client, HealthStatus, StoredTender } from './types';
import { formatBDT, formatBSTDate } from './utils/formatters';
import { ClientFormModal } from './components/ClientFormModal';
import { MatchesDrawer } from './components/MatchesDrawer';

export const App: React.FC = () => {
  // Navigation State
  const [activeTab, setActiveTab] = useState<'clients' | 'tenders'>('clients');

  // Client Data States
  const [clients, setClients] = useState<Client[]>([]);
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isMatchingRunning, setIsMatchingRunning] = useState(false);

  // Stored Tenders Data States
  const [tenders, setTenders] = useState<StoredTender[]>([]);
  const [tendersTotal, setTendersTotal] = useState(0);
  const [tendersLoading, setTendersLoading] = useState(false);
  const [tendersSearch, setTendersSearch] = useState('');
  const [tendersDistrict, setTendersDistrict] = useState('');
  const [tendersPage, setTendersPage] = useState(0);
  const TENDERS_PER_PAGE = 20;

  // Search & Filter for Clients
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<'all' | 'active' | 'paused' | 'draft' | 'demo'>('all');

  // Modals & Drawers
  const [isFormOpen, setIsFormOpen] = useState(false);
  const [selectedClientForEdit, setSelectedClientForEdit] = useState<Client | null>(null);

  const [isMatchesDrawerOpen, setIsMatchesDrawerOpen] = useState(false);
  const [selectedClientForMatches, setSelectedClientForMatches] = useState<Client | null>(null);

  // Toast Notification
  const [toastMessage, setToastMessage] = useState<{ text: string; type: 'success' | 'error' } | null>(null);

  const showToast = useCallback((text: string, type: 'success' | 'error' = 'success') => {
    setToastMessage({ text, type });
    setTimeout(() => {
      setToastMessage((cur) => (cur?.text === text ? null : cur));
    }, 4500);
  }, []);

  // Tenders Loader
  const loadTenders = useCallback(async (page: number = 0, search: string = '', district: string = '') => {
    setTendersLoading(true);
    try {
      const res = await api.getTenders({
        limit: TENDERS_PER_PAGE,
        offset: page * TENDERS_PER_PAGE,
        search: search.trim() || undefined,
        district: district.trim() || undefined,
      });
      setTenders(res.items || []);
      setTendersTotal(res.total || 0);
      setTendersPage(page);
    } catch (err: any) {
      showToast(`দরপত্র তালিকা লোড করতে ব্যর্থ: ${err.message}`, 'error');
    } finally {
      setTendersLoading(false);
    }
  }, [showToast]);

  // Main Data Loader
  const loadData = useCallback(async () => {
    try {
      const [clientsRes, healthRes] = await Promise.all([
        api.getClients(),
        api.getHealth().catch(() => null),
      ]);
      setClients(Array.isArray(clientsRes) ? clientsRes : []);
      if (healthRes) setHealth(healthRes);
    } catch (err: any) {
      showToast(`ডাটা লোড করতে ব্যর্থ: ${err.message}`, 'error');
    } finally {
      setIsLoading(false);
    }
  }, [showToast]);

  useEffect(() => {
    void loadData();
    void loadTenders(0, '', '');
  }, [loadData, loadTenders]);

  // Client CRUD Handlers
  const handleOpenAdd = () => {
    setSelectedClientForEdit(null);
    setIsFormOpen(true);
  };

  const handleOpenEdit = (client: Client) => {
    setSelectedClientForEdit(client);
    setIsFormOpen(true);
  };

  const handleFormSubmit = async (payload: Partial<Client>) => {
    if (selectedClientForEdit) {
      // Edit
      const res = await api.updateClient(selectedClientForEdit.id, payload);
      showToast(res.message, 'success');
    } else {
      // Create
      const res = await api.createClient(payload);
      showToast(res.message, 'success');
    }
    await loadData();
  };

  const handleToggleStatus = async (client: Client) => {
    const nextStatus = client.client_status === 'active' ? 'paused' : 'active';
    try {
      const res = await api.updateClientStatus(client.id, nextStatus);
      showToast(res.message, 'success');
      await loadData();
    } catch (err: any) {
      showToast(`স্ট্যাটাস পরিবর্তন ব্যর্থ: ${err.message}`, 'error');
    }
  };

  // Run Matching
  const handleRunMatching = async (clientId?: number) => {
    setIsMatchingRunning(true);
    try {
      const res = await api.runMatching(clientId);
      showToast(`✓ ${res.message}`, 'success');
      await loadData();
    } catch (err: any) {
      showToast(`ম্যাচিং ব্যর্থ: ${err.message}`, 'error');
    } finally {
      setIsMatchingRunning(false);
    }
  };

  // View Matches Drawer
  const handleOpenMatches = (client: Client) => {
    setSelectedClientForMatches(client);
    setIsMatchesDrawerOpen(true);
  };

  // Send Safe Test Email
  const handleSendTestEmail = async (clientId: number, tenderId?: number) => {
    try {
      const res = await api.sendTestEmail(clientId, undefined, tenderId);
      showToast(`✓ ${res.message} [প্রেরক: ${res.recipient}]`, 'success');
    } catch (err: any) {
      showToast(`টেস্ট ইমেইল ব্যর্থ: ${err.message}`, 'error');
    }
  };

  // Filtered Client List
  const filteredClients = useMemo(() => {
    return clients.filter((c) => {
      // Status filter
      if (statusFilter === 'active' && c.client_status !== 'active') return false;
      if (statusFilter === 'paused' && c.client_status !== 'paused') return false;
      if (statusFilter === 'draft' && c.client_status !== 'draft') return false;
      if (statusFilter === 'demo' && !c.is_demo) return false;

      // Search query
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase();
        const matchName = c.business_name.toLowerCase().includes(q);
        const matchContact = c.contact_person.toLowerCase().includes(q);
        const matchEmail = (c.email || '').toLowerCase().includes(q);
        const matchPhone = (c.phone || '').toLowerCase().includes(q);
        const matchDistrict = (c.district || '').toLowerCase().includes(q);
        const matchDistricts = (c.preferred_districts || []).some((d) => d.toLowerCase().includes(q));
        if (!matchName && !matchContact && !matchEmail && !matchPhone && !matchDistrict && !matchDistricts) {
          return false;
        }
      }

      return true;
    });
  }, [clients, statusFilter, searchQuery]);

  // Statistics
  const activeCount = useMemo(() => clients.filter((c) => c.client_status === 'active').length, [clients]);
  const pausedCount = useMemo(() => clients.filter((c) => c.client_status === 'paused').length, [clients]);
  const demoCount = useMemo(() => clients.filter((c) => c.is_demo).length, [clients]);

  return (
    <div style={{ minHeight: '100vh', background: 'var(--bg-app)', color: 'var(--text-primary)', display: 'flex', flexDirection: 'column' }}>
      
      {/* Toast Notification */}
      {toastMessage && (
        <div
          style={{
            position: 'fixed',
            bottom: '24px',
            right: '24px',
            zIndex: 9999,
            background: toastMessage.type === 'success' ? '#065f46' : '#991b1b',
            color: '#ffffff',
            padding: '12px 18px',
            borderRadius: '8px',
            boxShadow: 'var(--shadow-lg)',
            display: 'flex',
            alignItems: 'center',
            gap: '10px',
            fontSize: '13px',
            fontWeight: 500,
            border: `1px solid ${toastMessage.type === 'success' ? '#10b981' : '#f87171'}`,
          }}
        >
          {toastMessage.type === 'success' ? <CheckCircle2 size={16} /> : <AlertCircle size={16} />}
          <span>{toastMessage.text}</span>
        </div>
      )}

      {/* Top Header */}
      <header
        style={{
          background: 'var(--bg-surface)',
          borderBottom: '1px solid var(--border-subtle)',
          padding: '16px 32px',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
          <div
            style={{
              width: '38px',
              height: '38px',
              borderRadius: '8px',
              background: 'linear-gradient(135deg, var(--primary), #1e3a8a)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              boxShadow: '0 2px 8px rgba(2, 132, 199, 0.3)',
            }}
          >
            <Building2 size={22} color="#ffffff" />
          </div>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <h1 style={{ fontSize: '18px', fontWeight: 700, letterSpacing: '-0.3px', color: '#ffffff' }}>
                ইজারাবিডি (EjaraBD)
              </h1>
              <span className="badge badge-emerald" style={{ fontSize: '11px', padding: '2px 8px' }}>
                Phase 1 Core
              </span>
            </div>
            <p style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
              ক্লায়েন্ট অনবোর্ডিং, রুল-বেসড ম্যাচিং ও নোটিফিকেশন সিস্টেম
            </p>
          </div>
        </div>

        {/* Action Controls */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          {/* Dev Mode Indicator */}
          {health?.email_dev_mode && (
            <div
              style={{
                fontSize: '11px',
                padding: '4px 10px',
                borderRadius: '6px',
                background: 'rgba(245, 158, 11, 0.12)',
                border: '1px solid rgba(245, 158, 11, 0.3)',
                color: '#fbbf24',
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
              }}
              title="EMAIL_DEV_MODE active: Real client emails are safely suppressed"
            >
              <ShieldCheck size={13} />
              <span>Email Dev Mode (Safe)</span>
            </div>
          )}

          {/* Manual Run Matching Button */}
          <button
            className="btn btn-secondary btn-sm"
            onClick={() => handleRunMatching()}
            disabled={isMatchingRunning}
            style={{ display: 'flex', alignItems: 'center', gap: '6px' }}
          >
            <Play size={13} color="var(--primary)" />
            <span>{isMatchingRunning ? 'ম্যাচিং চলছে...' : 'Run Matching (ম্যাচিং চালান)'}</span>
          </button>

          {/* Add New Client Button */}
          <button
            className="btn btn-primary btn-sm"
            onClick={handleOpenAdd}
            style={{ display: 'flex', alignItems: 'center', gap: '6px' }}
          >
            <Plus size={14} />
            <span>+ নতুন ক্লায়েন্ট যোগ করুন (Add Client)</span>
          </button>
        </div>
      </header>

      {/* Subheader Navigation Bar */}
      <div
        style={{
          background: 'var(--bg-surface)',
          borderBottom: '1px solid var(--border-subtle)',
          padding: '0 32px',
          display: 'flex',
          gap: '8px',
        }}
      >
        <button
          onClick={() => setActiveTab('clients')}
          style={{
            padding: '12px 18px',
            fontSize: '13px',
            fontWeight: 600,
            background: 'transparent',
            border: 'none',
            borderBottom: activeTab === 'clients' ? '2px solid var(--primary)' : '2px solid transparent',
            color: activeTab === 'clients' ? 'var(--primary)' : 'var(--text-muted)',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            transition: 'all 0.15s ease',
          }}
        >
          <Building2 size={16} />
          <span>ক্লায়েন্ট তালিকা ও অনবোর্ডিং (Clients)</span>
          <span className="badge badge-secondary" style={{ fontSize: '11px' }}>{clients.length}</span>
        </button>

        <button
          onClick={() => setActiveTab('tenders')}
          style={{
            padding: '12px 18px',
            fontSize: '13px',
            fontWeight: 600,
            background: 'transparent',
            border: 'none',
            borderBottom: activeTab === 'tenders' ? '2px solid var(--primary)' : '2px solid transparent',
            color: activeTab === 'tenders' ? 'var(--primary)' : 'var(--text-muted)',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            transition: 'all 0.15s ease',
          }}
        >
          <Database size={16} />
          <span>সংরক্ষিত ই-জিপি দরপত্র ভান্ডার (e-GP Tenders)</span>
          <span className="badge badge-cyan" style={{ fontSize: '11px' }}>{tendersTotal || 1727}</span>
        </button>
      </div>

      {/* Main Content Area */}
      <main style={{ flex: 1, padding: '24px 32px', display: 'flex', flexDirection: 'column', gap: '20px' }}>
        
        {activeTab === 'clients' ? (
          <>
            {/* Statistics & Filter Bar */}
            <div
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                gap: '16px',
                flexWrap: 'wrap',
              }}
            >
              {/* Status Tabs */}
              <div style={{ display: 'flex', gap: '6px', background: 'var(--bg-surface)', padding: '4px', borderRadius: '8px', border: '1px solid var(--border-subtle)' }}>
                <button
                  className={`btn btn-sm ${statusFilter === 'all' ? 'btn-primary' : 'btn-ghost'}`}
                  onClick={() => setStatusFilter('all')}
                  style={{ fontSize: '12px' }}
                >
                  সকল ক্লায়েন্ট ({clients.length})
                </button>
                <button
                  className={`btn btn-sm ${statusFilter === 'active' ? 'btn-primary' : 'btn-ghost'}`}
                  onClick={() => setStatusFilter('active')}
                  style={{ fontSize: '12px' }}
                >
                  সক্রিয় ({activeCount})
                </button>
                <button
                  className={`btn btn-sm ${statusFilter === 'paused' ? 'btn-primary' : 'btn-ghost'}`}
                  onClick={() => setStatusFilter('paused')}
                  style={{ fontSize: '12px' }}
                >
                  স্থগিত ({pausedCount})
                </button>
                <button
                  className={`btn btn-sm ${statusFilter === 'demo' ? 'btn-primary' : 'btn-ghost'}`}
                  onClick={() => setStatusFilter('demo')}
                  style={{ fontSize: '12px' }}
                >
                  ডেমো / টেস্ট ({demoCount})
                </button>
              </div>

              {/* Search Input */}
              <div style={{ position: 'relative', width: '320px' }}>
                <Search
                  size={15}
                  style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }}
                />
                <input
                  type="text"
                  className="form-input"
                  style={{ paddingLeft: '34px', fontSize: '13px' }}
                  placeholder="কোম্পানি, নাম, জেলা বা ইমেইল খুঁজুন..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                />
              </div>
            </div>

            {/* Client Table Container */}
            <div
              style={{
                background: 'var(--bg-surface)',
                border: '1px solid var(--border-subtle)',
                borderRadius: '12px',
                overflow: 'hidden',
                boxShadow: 'var(--shadow-sm)',
              }}
            >
              {isLoading ? (
                <div style={{ padding: '80px', textAlign: 'center', color: 'var(--text-muted)' }}>
                  ক্লায়েন্ট তালিকা লোড হচ্ছে...
                </div>
              ) : filteredClients.length === 0 ? (
                <div style={{ padding: '80px', textAlign: 'center', color: 'var(--text-muted)' }}>
                  <UserCheck size={40} style={{ margin: '0 auto 12px', opacity: 0.3 }} />
                  <div style={{ fontSize: '16px', fontWeight: 600, color: 'var(--text-secondary)' }}>কোনো ক্লায়েন্ট পাওয়া যায়নি</div>
                  <p style={{ fontSize: '13px', marginTop: '6px' }}>নতুন ক্লায়েন্ট যোগ করতে "+ নতুন ক্লায়েন্ট যোগ করুন" বাটনে চাপুন।</p>
                </div>
              ) : (
                <div style={{ overflowX: 'auto' }}>
                  <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '13px' }}>
                    <thead>
                      <tr style={{ background: 'var(--bg-subtle)', borderBottom: '1px solid var(--border-subtle)', color: 'var(--text-muted)', textTransform: 'uppercase', fontSize: '11px', letterSpacing: '0.5px' }}>
                        <th style={{ padding: '12px 18px' }}>আইডি ও প্রতিষ্ঠান (Company)</th>
                        <th style={{ padding: '12px 18px' }}>যোগাযোগ (Contact)</th>
                        <th style={{ padding: '12px 18px' }}>কাজের জেলা ও ক্যাটাগরি (Preferences)</th>
                        <th style={{ padding: '12px 18px' }}>স্থিতি (Status)</th>
                        <th style={{ padding: '12px 18px' }}>ম্যাচিং টেন্ডার (Matches)</th>
                        <th style={{ padding: '12px 18px', textAlign: 'right' }}>কার্যক্রম (Actions)</th>
                      </tr>
                    </thead>
                    <tbody>
                      {filteredClients.map((client) => {
                        const isActive = client.client_status === 'active';
                        const isPaused = client.client_status === 'paused';

                        return (
                          <tr
                            key={client.id}
                            style={{
                              borderBottom: '1px solid var(--border-subtle)',
                              transition: 'background 0.15s var(--ease)',
                            }}
                            onMouseEnter={(e) => (e.currentTarget.style.background = 'var(--bg-surface-hover)')}
                            onMouseLeave={(e) => (e.currentTarget.style.background = 'transparent')}
                          >
                            {/* Company & ID */}
                            <td style={{ padding: '14px 18px' }}>
                              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                                <span className="mono-cell" style={{ color: 'var(--text-muted)', fontSize: '12px', fontWeight: 600 }}>
                                  #{client.id}
                                </span>
                                <span style={{ fontWeight: 600, color: 'var(--text-primary)' }}>
                                  {client.business_name}
                                </span>
                                {client.is_demo && (
                                  <span className="badge badge-amber" style={{ fontSize: '10px', padding: '1px 6px' }}>
                                    DEMO
                                  </span>
                                )}
                                {client.id === 1 && (
                                  <span className="badge badge-emerald" style={{ fontSize: '10px', padding: '1px 6px' }}>
                                    PILOT
                                  </span>
                                )}
                              </div>
                              <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '2px' }}>
                                অভিজ্ঞতা: {client.years_of_experience ? `${client.years_of_experience} বছর` : 'উল্লেখ নেই'} | নোটিফিকেশন: {client.notification_preference || 'daily_email'}
                              </div>
                            </td>

                            {/* Contact Person & Email */}
                            <td style={{ padding: '14px 18px' }}>
                              <div style={{ fontWeight: 500, color: 'var(--text-primary)' }}>{client.contact_person}</div>
                              <div style={{ fontSize: '12px', color: 'var(--border-focus)', marginTop: '2px' }} className="mono-cell">
                                {client.email || 'No email configured'}
                              </div>
                              {client.phone && (
                                <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '1px' }}>
                                  {client.phone}
                                </div>
                              )}
                            </td>

                            {/* Preferences */}
                            <td style={{ padding: '14px 18px' }}>
                              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px', marginBottom: '4px' }}>
                                {(client.preferred_districts || ['Dinajpur']).map((d) => (
                                  <span key={d} className="badge badge-secondary" style={{ fontSize: '11px' }}>
                                    {d}
                                  </span>
                                ))}
                                {(client.preferred_upazilas || []).map((u) => (
                                  <span key={u} className="badge badge-cyan" style={{ fontSize: '11px' }}>
                                    {u}
                                  </span>
                                ))}
                              </div>
                              <div style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>
                                {(client.work_categories || ['Civil Works']).join(', ')}
                              </div>
                            </td>

                            {/* Status */}
                            <td style={{ padding: '14px 18px' }}>
                              <span
                                className={`badge ${isActive ? 'badge-emerald' : isPaused ? 'badge-amber' : 'badge-secondary'}`}
                                style={{ fontSize: '11px', textTransform: 'capitalize' }}
                              >
                                {isActive ? 'সক্রিয় (Active)' : isPaused ? 'স্থগিত (Paused)' : 'খসড়া (Draft)'}
                              </span>
                            </td>

                            {/* Match Count & Trigger */}
                            <td style={{ padding: '14px 18px' }}>
                              <button
                                className="btn btn-secondary btn-sm"
                                onClick={() => handleOpenMatches(client)}
                                style={{ display: 'inline-flex', alignItems: 'center', gap: '6px', fontSize: '12px' }}
                                title="এই ক্লায়েন্টের ম্যাচিং টেন্ডার দেখুন"
                              >
                                <FileText size={12} color="var(--primary)" />
                                <span>{client.total_matches || 0} টি টেন্ডার</span>
                                <Eye size={12} />
                              </button>
                            </td>

                            {/* Actions */}
                            <td style={{ padding: '14px 18px', textAlign: 'right' }}>
                              <div style={{ display: 'inline-flex', alignItems: 'center', gap: '8px' }}>
                                {/* Send Test Email Button */}
                                <button
                                  className="btn btn-secondary btn-icon"
                                  onClick={() => handleSendTestEmail(client.id)}
                                  title="নিরাপদ টেস্ট ইমেইল পাঠান (Send Test Email)"
                                  style={{ width: '32px', height: '32px' }}
                                >
                                  <Send size={14} color="var(--primary)" />
                                </button>

                                {/* Pause / Resume Button */}
                                <button
                                  className="btn btn-secondary btn-icon"
                                  onClick={() => handleToggleStatus(client)}
                                  title={isActive ? 'ক্লায়েন্ট স্থগিত করুন (Pause)' : 'ক্লায়েন্ট সক্রিয় করুন (Resume)'}
                                  style={{ width: '32px', height: '32px' }}
                                >
                                  {isActive ? <Pause size={14} color="#fbbf24" /> : <Play size={14} color="#34d399" />}
                                </button>

                                {/* Edit Button */}
                                <button
                                  className="btn btn-secondary btn-icon"
                                  onClick={() => handleOpenEdit(client)}
                                  title="প্রোফাইল এডিট করুন (Edit)"
                                  style={{ width: '32px', height: '32px' }}
                                >
                                  <Edit2 size={14} />
                                </button>
                              </div>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </>
        ) : (
          /* Stored e-GP Tenders Explorer */
          <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            {/* Search & Filter Bar for Tenders */}
            <div
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                gap: '16px',
                flexWrap: 'wrap',
                background: 'var(--bg-surface)',
                padding: '16px 20px',
                borderRadius: '12px',
                border: '1px solid var(--border-subtle)',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flex: 1, flexWrap: 'wrap' }}>
                <div style={{ position: 'relative', width: '340px' }}>
                  <Search
                    size={15}
                    style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }}
                  />
                  <input
                    type="text"
                    className="form-input"
                    style={{ paddingLeft: '34px', fontSize: '13px' }}
                    placeholder="টেন্ডার আইডি, শিরোনাম বা সংস্থা দিয়ে খুঁজুন..."
                    value={tendersSearch}
                    onChange={(e) => setTendersSearch(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') void loadTenders(0, tendersSearch, tendersDistrict);
                    }}
                  />
                </div>

                <div style={{ width: '200px' }}>
                  <input
                    type="text"
                    className="form-input"
                    style={{ fontSize: '13px' }}
                    placeholder="জেলা (যেমন: Dinajpur, Dhaka)..."
                    value={tendersDistrict}
                    onChange={(e) => setTendersDistrict(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') void loadTenders(0, tendersSearch, tendersDistrict);
                    }}
                  />
                </div>

                <button
                  className="btn btn-primary btn-sm"
                  onClick={() => void loadTenders(0, tendersSearch, tendersDistrict)}
                  style={{ display: 'flex', alignItems: 'center', gap: '6px' }}
                >
                  <Search size={14} />
                  <span>অনুসন্ধান করুন</span>
                </button>

                {(tendersSearch || tendersDistrict) && (
                  <button
                    className="btn btn-secondary btn-sm"
                    onClick={() => {
                      setTendersSearch('');
                      setTendersDistrict('');
                      void loadTenders(0, '', '');
                    }}
                  >
                    রিসেট
                  </button>
                )}
              </div>

              <div style={{ fontSize: '13px', color: 'var(--text-muted)' }}>
                মোট সংরক্ষিত দরপত্র: <strong style={{ color: 'var(--text-primary)' }}>{tendersTotal.toLocaleString()}টি</strong>
              </div>
            </div>

            {/* Tenders Table */}
            <div
              style={{
                background: 'var(--bg-surface)',
                border: '1px solid var(--border-subtle)',
                borderRadius: '12px',
                overflow: 'hidden',
                boxShadow: 'var(--shadow-sm)',
              }}
            >
              {tendersLoading ? (
                <div style={{ padding: '80px', textAlign: 'center', color: 'var(--text-muted)' }}>
                  দরপত্র ভান্ডার লোড হচ্ছে...
                </div>
              ) : tenders.length === 0 ? (
                <div style={{ padding: '80px', textAlign: 'center', color: 'var(--text-muted)' }}>
                  <Database size={40} style={{ margin: '0 auto 12px', opacity: 0.3 }} />
                  <div style={{ fontSize: '16px', fontWeight: 600, color: 'var(--text-secondary)' }}>কোনো দরপত্র পাওয়া যায়নি</div>
                  <p style={{ fontSize: '13px', marginTop: '6px' }}>অনুসন্ধান শর্ত পরিবর্তন করে আবার চেষ্টা করুন।</p>
                </div>
              ) : (
                <div style={{ overflowX: 'auto' }}>
                  <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '13px' }}>
                    <thead>
                      <tr style={{ background: 'var(--bg-subtle)', borderBottom: '1px solid var(--border-subtle)', color: 'var(--text-muted)', textTransform: 'uppercase', fontSize: '11px', letterSpacing: '0.5px' }}>
                        <th style={{ padding: '12px 18px', width: '120px' }}>টেন্ডার ID</th>
                        <th style={{ padding: '12px 18px' }}>কাজের শিরোনাম ও সংস্থা (Title & Agency)</th>
                        <th style={{ padding: '12px 18px' }}>অবস্থান (Location)</th>
                        <th style={{ padding: '12px 18px' }}>ক্যাটাগরি</th>
                        <th style={{ padding: '12px 18px' }}>জমাদানের শেষ সময়</th>
                        <th style={{ padding: '12px 18px' }}>প্রাক্কলিত বাজেট</th>
                        <th style={{ padding: '12px 18px', textAlign: 'right' }}>লিংক</th>
                      </tr>
                    </thead>
                    <tbody>
                      {tenders.map((t) => (
                        <tr
                          key={t.id}
                          style={{
                            borderBottom: '1px solid var(--border-subtle)',
                            transition: 'background 0.15s var(--ease)',
                          }}
                          onMouseEnter={(e) => (e.currentTarget.style.background = 'var(--bg-surface-hover)')}
                          onMouseLeave={(e) => (e.currentTarget.style.background = 'transparent')}
                        >
                          <td style={{ padding: '14px 18px' }}>
                            <span className="mono-cell" style={{ fontWeight: 600, color: 'var(--primary)', fontSize: '12px' }}>
                              #{t.tender_id}
                            </span>
                          </td>
                          <td style={{ padding: '14px 18px', maxWidth: '380px' }}>
                            <div style={{ fontWeight: 600, color: 'var(--text-primary)', lineHeight: 1.4 }}>
                              {t.title}
                            </div>
                            <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '3px' }}>
                              {t.agency} {t.office ? `• ${t.office}` : ''}
                            </div>
                          </td>
                          <td style={{ padding: '14px 18px' }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                              <MapPin size={12} color="var(--primary)" />
                              <span style={{ fontWeight: 500 }}>{t.district || 'Dinajpur'}</span>
                            </div>
                            {t.location_details && (
                              <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '2px' }}>
                                {t.location_details}
                              </div>
                            )}
                          </td>
                          <td style={{ padding: '14px 18px' }}>
                            <span className="badge badge-secondary" style={{ fontSize: '11px' }}>
                              {t.category || 'Works'}
                            </span>
                          </td>
                          <td style={{ padding: '14px 18px' }}>
                            <div style={{ fontSize: '12px', color: t.closing_date ? '#f87171' : 'var(--text-muted)' }}>
                              {formatBSTDate(t.closing_date)}
                            </div>
                          </td>
                          <td style={{ padding: '14px 18px' }}>
                            <div style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-primary)' }}>
                              {formatBDT(t.estimated_value_bdt)}
                            </div>
                            {t.tender_security_bdt != null && t.tender_security_bdt > 0 && (
                              <div style={{ fontSize: '11px', color: '#34d399', marginTop: '2px' }}>
                                সিকিউরিটি: {formatBDT(t.tender_security_bdt)}
                              </div>
                            )}
                          </td>
                          <td style={{ padding: '14px 18px', textAlign: 'right' }}>
                            {t.source_url ? (
                              <a
                                href={t.source_url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="btn btn-secondary btn-icon"
                                title="e-GP পোর্টালে সরাসরি দেখুন"
                                style={{ width: '30px', height: '30px', display: 'inline-flex', alignItems: 'center', justifyContent: 'center' }}
                              >
                                <ExternalLink size={13} color="var(--primary)" />
                              </a>
                            ) : (
                              <span style={{ color: 'var(--text-muted)', fontSize: '11px' }}>N/A</span>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}

              {/* Pagination Controls */}
              {tendersTotal > TENDERS_PER_PAGE && (
                <div
                  style={{
                    padding: '14px 20px',
                    background: 'var(--bg-subtle)',
                    borderTop: '1px solid var(--border-subtle)',
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                  }}
                >
                  <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                    পৃষ্ঠা {tendersPage + 1} / {Math.ceil(tendersTotal / TENDERS_PER_PAGE)}
                  </div>
                  <div style={{ display: 'flex', gap: '8px' }}>
                    <button
                      className="btn btn-secondary btn-sm"
                      disabled={tendersPage === 0 || tendersLoading}
                      onClick={() => void loadTenders(tendersPage - 1, tendersSearch, tendersDistrict)}
                      style={{ display: 'flex', alignItems: 'center', gap: '4px' }}
                    >
                      <ChevronLeft size={14} />
                      <span>পূর্ববর্তী</span>
                    </button>
                    <button
                      className="btn btn-secondary btn-sm"
                      disabled={(tendersPage + 1) * TENDERS_PER_PAGE >= tendersTotal || tendersLoading}
                      onClick={() => void loadTenders(tendersPage + 1, tendersSearch, tendersDistrict)}
                      style={{ display: 'flex', alignItems: 'center', gap: '4px' }}
                    >
                      <span>পরবর্তী</span>
                      <ChevronRight size={14} />
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}
      </main>

      {/* 19-Field Add/Edit Client Modal */}
      <ClientFormModal
        isOpen={isFormOpen}
        client={selectedClientForEdit}
        onClose={() => setIsFormOpen(false)}
        onSubmit={handleFormSubmit}
      />

      {/* Matched Tenders Drawer */}
      <MatchesDrawer
        client={selectedClientForMatches}
        isOpen={isMatchesDrawerOpen}
        onClose={() => setIsMatchesDrawerOpen(false)}
        onSendTestEmail={handleSendTestEmail}
      />
    </div>
  );
};

export default App;
