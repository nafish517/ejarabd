import React, { useState, useEffect } from 'react';
import { X, Building2, MapPin, Briefcase, Bell, CheckCircle2, AlertCircle } from 'lucide-react';
import type { Client } from '../types';


interface ClientFormModalProps {
  isOpen: boolean;
  client: Client | null; // null if adding new, Client object if editing
  onClose: () => void;
  onSubmit: (payload: Partial<Client>) => Promise<void>;
}

export const ClientFormModal: React.FC<ClientFormModalProps> = ({
  isOpen,
  client,
  onClose,
  onSubmit,
}) => {
  const isEditing = Boolean(client);

  // Form State for 19 Fields
  const [businessName, setBusinessName] = useState('');
  const [contactPerson, setContactPerson] = useState('');
  const [email, setEmail] = useState('');
  const [phone, setPhone] = useState('');
  const [preferredLanguage, setPreferredLanguage] = useState('bn');
  const [district, setDistrict] = useState('');

  // Location & Category
  const [preferredDistricts, setPreferredDistricts] = useState('');
  const [preferredUpazilas, setPreferredUpazilas] = useState('');
  const [workCategories, setWorkCategories] = useState('');
  const [preferredAgencies, setPreferredAgencies] = useState('');
  const [excludedAreas, setExcludedAreas] = useState('');

  // Financial & Experience
  const [minProjectValue, setMinProjectValue] = useState<string>('');
  const [maxProjectValue, setMaxProjectValue] = useState<string>('');
  const [yearsExperience, setYearsExperience] = useState<string>('');
  const [previousProjectTypes, setPreviousProjectTypes] = useState('');
  const [similarWorkExperience, setSimilarWorkExperience] = useState('');
  const [approxTurnover, setApproxTurnover] = useState<string>('');

  // Technical & Equipment
  const [availableEquipment, setAvailableEquipment] = useState('');
  const [availableManpower, setAvailableManpower] = useState('');
  const [licensesCertifications, setLicensesCertifications] = useState('');

  // Notification & Lifecycle
  const [notificationPreference, setNotificationPreference] = useState('daily_email');
  const [notificationSchedules, setNotificationSchedules] = useState('12:00, 19:00');
  const [clientStatus, setClientStatus] = useState<'draft' | 'active' | 'paused'>('active');
  const [isDemo, setIsDemo] = useState(false);
  const [experienceNotes, setExperienceNotes] = useState('');
  const [knownConstraints, setKnownConstraints] = useState('');

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Reset or populate fields when modal opens or client changes
  useEffect(() => {
    if (client) {
      setBusinessName(client.business_name || '');
      setContactPerson(client.contact_person || '');
      setEmail(client.email || '');
      setPhone(client.phone || '');
      setPreferredLanguage(client.preferred_language || 'bn');
      setDistrict(client.district || '');

      setPreferredDistricts((client.preferred_districts || []).join(', '));
      setPreferredUpazilas((client.preferred_upazilas || []).join(', '));
      setWorkCategories((client.work_categories || []).join(', '));
      setPreferredAgencies((client.preferred_agencies || []).join(', '));
      setExcludedAreas((client.excluded_areas_or_categories || []).join(', '));

      setMinProjectValue(client.min_project_value_bdt != null ? String(client.min_project_value_bdt) : '');
      setMaxProjectValue(client.max_project_value_bdt != null ? String(client.max_project_value_bdt) : '');
      setYearsExperience(client.years_of_experience != null ? String(client.years_of_experience) : '');
      setPreviousProjectTypes((client.previous_project_types || []).join(', '));
      setSimilarWorkExperience(client.similar_work_experience || '');
      setApproxTurnover(client.approx_annual_turnover_bdt != null ? String(client.approx_annual_turnover_bdt) : '');

      setAvailableEquipment((client.available_equipment || []).join(', '));
      setAvailableManpower((client.available_manpower || []).join(', '));
      setLicensesCertifications((client.licenses_certifications || []).join(', '));

      setNotificationPreference(client.notification_preference || 'daily_email');
      setNotificationSchedules((client.notification_schedules || ['12:00', '19:00']).join(', '));
      setClientStatus(client.client_status || 'active');
      setIsDemo(Boolean(client.is_demo));
      setExperienceNotes(client.experience_notes || '');
      setKnownConstraints(client.known_constraints || '');
    } else {
      // Defaults for new client
      setBusinessName('');
      setContactPerson('');
      setEmail('');
      setPhone('');
      setPreferredLanguage('bn');
      setDistrict('Dinajpur');

      setPreferredDistricts('Dinajpur');
      setPreferredUpazilas('');
      setWorkCategories('Civil Works, Road Construction');
      setPreferredAgencies('LGED, RHD');
      setExcludedAreas('');

      setMinProjectValue('');
      setMaxProjectValue('');
      setYearsExperience('');
      setPreviousProjectTypes('');
      setSimilarWorkExperience('');
      setApproxTurnover('');

      setAvailableEquipment('');
      setAvailableManpower('');
      setLicensesCertifications('');

      setNotificationPreference('daily_email');
      setNotificationSchedules('12:00, 19:00');
      setClientStatus('active');
      setIsDemo(false);
      setExperienceNotes('');
      setKnownConstraints('');
    }
    setErrorMessage(null);
  }, [client, isOpen]);

  if (!isOpen) return null;

  const parseList = (str: string) =>
    str
      .split(',')
      .map((s) => s.trim())
      .filter(Boolean);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!businessName.trim() || !contactPerson.trim() || !email.trim()) {
      setErrorMessage('প্রতিষ্ঠান, যোগাযোগের ব্যক্তি এবং ইমেইল ঠিকানা অবশ্যই পূরণ করতে হবে।');
      return;
    }

    setIsSubmitting(true);
    setErrorMessage(null);

    try {
      const payload: Partial<Client> = {
        business_name: businessName.trim(),
        contact_person: contactPerson.trim(),
        email: email.trim(),
        phone: phone.trim() || null,
        preferred_language: preferredLanguage,
        district: district.trim() || null,

        preferred_districts: parseList(preferredDistricts),
        preferred_upazilas: parseList(preferredUpazilas),
        work_categories: parseList(workCategories),
        preferred_agencies: parseList(preferredAgencies),
        excluded_areas_or_categories: parseList(excludedAreas),

        min_project_value_bdt: minProjectValue ? parseFloat(minProjectValue) : null,
        max_project_value_bdt: maxProjectValue ? parseFloat(maxProjectValue) : null,
        years_of_experience: yearsExperience ? parseInt(yearsExperience, 10) : null,
        previous_project_types: parseList(previousProjectTypes),
        similar_work_experience: similarWorkExperience.trim() || null,
        approx_annual_turnover_bdt: approxTurnover ? parseFloat(approxTurnover) : null,

        available_equipment: parseList(availableEquipment),
        available_manpower: parseList(availableManpower),
        licenses_certifications: parseList(licensesCertifications),

        notification_preference: notificationPreference,
        notification_schedules: parseList(notificationSchedules),
        client_status: clientStatus,
        is_demo: isDemo,
        experience_notes: experienceNotes.trim() || null,
        known_constraints: knownConstraints.trim() || null,
      };

      await onSubmit(payload);
      onClose();
    } catch (err: any) {
      setErrorMessage(err.message || 'সাবমিট করতে সমস্যা হয়েছে।');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div
        className="modal-content"
        style={{ maxWidth: '840px', width: '92%', maxHeight: '90vh', display: 'flex', flexDirection: 'column' }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="modal-header">
          <div>
            <h3 className="modal-title" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Building2 size={20} color="var(--primary)" />
              <span>{isEditing ? `ক্লায়েন্ট প্রোফাইল এডিট (#${client?.id})` : 'নতুন ক্লায়েন্ট অনবোর্ডিং (Add Client)'}</span>
            </h3>
            <p style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '2px' }}>
              ১৯টি প্রয়োজনীয় বৈশিষ্ট্য সহ ঠিকাদার প্রোফাইল ও দরপত্র মেলানোর শর্তাবলি
            </p>
          </div>
          <button className="btn btn-secondary btn-icon" onClick={onClose} disabled={isSubmitting}>
            <X size={16} />
          </button>
        </div>

        {/* Error Notification */}
        {errorMessage && (
          <div style={{ margin: '16px 24px 0', background: 'rgba(239, 68, 68, 0.1)', border: '1px solid rgba(239, 68, 68, 0.3)', padding: '10px 14px', borderRadius: '8px', display: 'flex', alignItems: 'center', gap: '8px', color: '#f87171', fontSize: '13px' }}>
            <AlertCircle size={16} />
            <span>{errorMessage}</span>
          </div>
        )}

        {/* Form Body */}
        <form onSubmit={handleSubmit} style={{ overflowY: 'auto', padding: '20px 24px', flex: 1 }}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>

            {/* ১. প্রাতিষ্ঠানিক পরিচয় ও যোগাযোগ */}
            <div style={{ background: 'var(--bg-subtle)', border: '1px solid var(--border-subtle)', borderRadius: '10px', padding: '16px' }}>
              <div style={{ fontSize: '13px', fontWeight: 600, color: 'var(--primary)', textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: '12px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                <Building2 size={15} />
                <span>১. প্রাতিষ্ঠানিক তথ্য ও যোগাযোগ (Company & Contact)</span>
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(230px, 1fr))', gap: '12px' }}>
                <div className="form-group">
                  <label className="form-label">প্রতিষ্ঠানের নাম (Company Name) *</label>
                  <input
                    type="text"
                    required
                    className="form-input"
                    placeholder="যেমন: রূপালী বিল্ডার্স অ্যান্ড সাপ্লায়ার্স"
                    value={businessName}
                    onChange={(e) => setBusinessName(e.target.value)}
                  />
                </div>

                <div className="form-group">
                  <label className="form-label">যোগাযোগের ব্যক্তি (Contact Person) *</label>
                  <input
                    type="text"
                    required
                    className="form-input"
                    placeholder="যেমন: আলহাজ্ব মোঃ ঠিকাদার সাহেব"
                    value={contactPerson}
                    onChange={(e) => setContactPerson(e.target.value)}
                  />
                </div>

                <div className="form-group">
                  <label className="form-label">ক্লায়েন্ট ইমেইল (Client Email) *</label>
                  <input
                    type="email"
                    required
                    className="form-input"
                    placeholder="যেমন: contractor@gmail.com"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                  />
                </div>

                <div className="form-group">
                  <label className="form-label">ফোন নম্বর (Phone Number)</label>
                  <input
                    type="text"
                    className="form-input"
                    placeholder="যেমন: +8801711000000"
                    value={phone}
                    onChange={(e) => setPhone(e.target.value)}
                  />
                </div>

                <div className="form-group">
                  <label className="form-label">প্রধান কার্যালয়ের জেলা (Head District)</label>
                  <input
                    type="text"
                    className="form-input"
                    placeholder="যেমন: Dinajpur"
                    value={district}
                    onChange={(e) => setDistrict(e.target.value)}
                  />
                </div>

                <div className="form-group">
                  <label className="form-label">পছন্দের ভাষা (Preferred Language)</label>
                  <select
                    className="form-input"
                    value={preferredLanguage}
                    onChange={(e) => setPreferredLanguage(e.target.value)}
                  >
                    <option value="bn">বাংলা (Bengali)</option>
                    <option value="en">ইংরেজি (English)</option>
                  </select>
                </div>
              </div>
            </div>

            {/* ২. কাজের পছন্দ ও ভৌগোলিক এলাকা */}
            <div style={{ background: 'var(--bg-subtle)', border: '1px solid var(--border-subtle)', borderRadius: '10px', padding: '16px' }}>
              <div style={{ fontSize: '13px', fontWeight: 600, color: 'var(--emerald-text)', textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: '12px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                <MapPin size={15} />
                <span>২. ভৌগোলিক এলাকা ও কাজের পছন্দ (Work Preferences)</span>
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(230px, 1fr))', gap: '12px' }}>
                <div className="form-group">
                  <label className="form-label">পছন্দের জেলাসমূহ (Preferred Districts)</label>
                  <input
                    type="text"
                    className="form-input"
                    placeholder="কমা দিয়ে লিখুন: Dinajpur, Rangpur, Bogura"
                    value={preferredDistricts}
                    onChange={(e) => setPreferredDistricts(e.target.value)}
                  />
                  <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>কমা দিয়ে একাধিক জেলা দেওয়া যাবে</span>
                </div>

                <div className="form-group">
                  <label className="form-label">পছন্দের উপজেলাসমূহ (Preferred Upazilas)</label>
                  <input
                    type="text"
                    className="form-input"
                    placeholder="যেমন: বীরগঞ্জ, কাহারোল, ফুলবাড়ী"
                    value={preferredUpazilas}
                    onChange={(e) => setPreferredUpazilas(e.target.value)}
                  />
                </div>

                <div className="form-group">
                  <label className="form-label">কাজের ধরণ / ক্যাটাগরি (Work Categories)</label>
                  <input
                    type="text"
                    className="form-input"
                    placeholder="যেমন: Civil Works, Road Construction, Bridge"
                    value={workCategories}
                    onChange={(e) => setWorkCategories(e.target.value)}
                  />
                </div>

                <div className="form-group">
                  <label className="form-label">পছন্দের সংস্থা (Preferred Agencies)</label>
                  <input
                    type="text"
                    className="form-input"
                    placeholder="যেমন: LGED, RHD, PWD, EED, BWDB"
                    value={preferredAgencies}
                    onChange={(e) => setPreferredAgencies(e.target.value)}
                  />
                </div>

                <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                  <label className="form-label">বাদ দেওয়ার এলাকা বা ক্যাটাগরি (Exclusions)</label>
                  <input
                    type="text"
                    className="form-input"
                    placeholder="যেসব এলাকা বা কাজ বাদ দিতে চান: Drainage, Chittagong, Sylhet"
                    value={excludedAreas}
                    onChange={(e) => setExcludedAreas(e.target.value)}
                  />
                  <span style={{ fontSize: '11px', color: 'var(--amber-text)' }}>এই এলাকা বা ক্যাটাগরি ম্যাচিং থেকে বাদ পড়বে</span>
                </div>
              </div>
            </div>

            {/* ৩. আর্থিক ও কারিগরি সামর্থ্য */}
            <div style={{ background: 'var(--bg-subtle)', border: '1px solid var(--border-subtle)', borderRadius: '10px', padding: '16px' }}>
              <div style={{ fontSize: '13px', fontWeight: 600, color: 'var(--amber-text)', textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: '12px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                <Briefcase size={15} />
                <span>৩. আর্থিক ও কারিগরি সামর্থ্য (Capacity & Experience)</span>
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(230px, 1fr))', gap: '12px' }}>
                <div className="form-group">
                  <label className="form-label">ন্যূনতম টেন্ডার সাইজ (Min BDT)</label>
                  <input
                    type="number"
                    className="form-input"
                    placeholder="যেমন: 1000000 (১০ লাখ)"
                    value={minProjectValue}
                    onChange={(e) => setMinProjectValue(e.target.value)}
                  />
                </div>

                <div className="form-group">
                  <label className="form-label">সর্বোচ্চ টেন্ডার সাইজ (Max BDT)</label>
                  <input
                    type="number"
                    className="form-input"
                    placeholder="যেমন: 20000000 (২ কোটি)"
                    value={maxProjectValue}
                    onChange={(e) => setMaxProjectValue(e.target.value)}
                  />
                </div>

                <div className="form-group">
                  <label className="form-label">কাজের অভিজ্ঞতা (Years of Experience)</label>
                  <input
                    type="number"
                    className="form-input"
                    placeholder="যেমন: 15"
                    value={yearsExperience}
                    onChange={(e) => setYearsExperience(e.target.value)}
                  />
                </div>

                <div className="form-group">
                  <label className="form-label">গড় বার্ষিক টার্নওভার (Turnover BDT)</label>
                  <input
                    type="number"
                    className="form-input"
                    placeholder="যেমন: 50000000 (৫ কোটি)"
                    value={approxTurnover}
                    onChange={(e) => setApproxTurnover(e.target.value)}
                  />
                </div>

                <div className="form-group">
                  <label className="form-label">পূর্ববর্তী প্রকল্পের ধরণ (Previous Project Types)</label>
                  <input
                    type="text"
                    className="form-input"
                    placeholder="যেমন: Bituminous Road, RCC Bridge, School Building"
                    value={previousProjectTypes}
                    onChange={(e) => setPreviousProjectTypes(e.target.value)}
                  />
                </div>

                <div className="form-group">
                  <label className="form-label">লাইসেন্স ও সনদ (Licenses & Certifications)</label>
                  <input
                    type="text"
                    className="form-input"
                    placeholder="যেমন: Enlistment Class-1, Trade License, Tax Clearance"
                    value={licensesCertifications}
                    onChange={(e) => setLicensesCertifications(e.target.value)}
                  />
                </div>

                <div className="form-group">
                  <label className="form-label">নিজস্ব যন্ত্রপাতি (Available Equipment)</label>
                  <input
                    type="text"
                    className="form-input"
                    placeholder="যেমন: 2 Road Rollers, 1 Excavator, Concrete Mixer"
                    value={availableEquipment}
                    onChange={(e) => setAvailableEquipment(e.target.value)}
                  />
                </div>

                <div className="form-group">
                  <label className="form-label">নিজস্ব জনবল (Available Manpower)</label>
                  <input
                    type="text"
                    className="form-input"
                    placeholder="যেমন: 3 Civil Engineers, 2 Surveyors, 20 Labors"
                    value={availableManpower}
                    onChange={(e) => setAvailableManpower(e.target.value)}
                  />
                </div>

                <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                  <label className="form-label">অনুরূপ কাজের অভিজ্ঞতা (Similar-work Experience Details)</label>
                  <textarea
                    className="form-input"
                    rows={2}
                    placeholder="বিগত ৫ বছরে সম্পন্ন প্রধান প্রধান অনুরূপ কাজের সংক্ষেপ বিবরণ..."
                    value={similarWorkExperience}
                    onChange={(e) => setSimilarWorkExperience(e.target.value)}
                  />
                </div>
              </div>
            </div>

            {/* ৪. নোটিফিকেশন ও স্থিতি */}
            <div style={{ background: 'var(--bg-subtle)', border: '1px solid var(--border-subtle)', borderRadius: '10px', padding: '16px' }}>
              <div style={{ fontSize: '13px', fontWeight: 600, color: 'var(--cyan-text)', textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: '12px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                <Bell size={15} />
                <span>৪. নোটিফিকেশন ও ক্লায়েন্ট স্ট্যাটাস (Notification & Status)</span>
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(230px, 1fr))', gap: '12px' }}>
                <div className="form-group">
                  <label className="form-label">নোটিফিকেশন পছন্দ (Notification Preference)</label>
                  <select
                    className="form-input"
                    value={notificationPreference}
                    onChange={(e) => setNotificationPreference(e.target.value)}
                  >
                    <option value="daily_email">দৈনিক শিডিউল ইমেইল (Daily Email Digest)</option>
                    <option value="instant_email">তাৎক্ষণিক অ্যালার্ট (Instant Alert)</option>
                    <option value="summary_only">সাপ্তাহিক সারসংক্ষেপ (Weekly Summary)</option>
                  </select>
                </div>

                <div className="form-group">
                  <label className="form-label">দৈনিক শিডিউল স্লট (Schedules BST)</label>
                  <input
                    type="text"
                    className="form-input"
                    placeholder="12:00, 19:00"
                    value={notificationSchedules}
                    onChange={(e) => setNotificationSchedules(e.target.value)}
                  />
                  <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>বাংলাদেশ সময় ২৪-ঘণ্টা ফরম্যাটে (কমা দিয়ে)</span>
                </div>

                <div className="form-group">
                  <label className="form-label">ক্লায়েন্ট স্থিতি (Client Status) *</label>
                  <select
                    className="form-input"
                    value={clientStatus}
                    onChange={(e) => setClientStatus(e.target.value as any)}
                  >
                    <option value="active">সক্রিয় (Active - ম্যাচিং ও ইমেইল সচল)</option>
                    <option value="paused">স্থগিত (Paused - সাময়িক বন্ধ)</option>
                    <option value="draft">খসড়া (Draft - অসম্পূর্ণ প্রোফাইল)</option>
                  </select>
                </div>

                <div className="form-group" style={{ display: 'flex', alignItems: 'center', marginTop: '24px' }}>
                  <label style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer', fontSize: '13px' }}>
                    <input
                      type="checkbox"
                      checked={isDemo}
                      onChange={(e) => setIsDemo(e.target.checked)}
                      style={{ width: '16px', height: '16px', accentColor: 'var(--amber-text)' }}
                    />
                    <span>ডেমো বা টেস্ট প্রোফাইল হিসেবে চিহ্নিত করুন (Is Demo)</span>
                  </label>
                </div>
              </div>
            </div>

          </div>

          {/* Footer Actions */}
          <div className="modal-footer" style={{ marginTop: '24px', borderTop: '1px solid var(--border-subtle)', paddingTop: '16px' }}>
            <button type="button" className="btn btn-secondary" onClick={onClose} disabled={isSubmitting}>
              বাতিল (Cancel)
            </button>
            <button type="submit" className="btn btn-primary" disabled={isSubmitting}>
              <CheckCircle2 size={16} />
              <span>{isSubmitting ? 'সংরক্ষণ হচ্ছে...' : isEditing ? 'আপডেট সম্পন্ন করুন' : 'ক্লায়েন্ট সংরক্ষণ করুন'}</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
