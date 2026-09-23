from datetime import datetime
from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    Boolean,
    DateTime,
    Text,
    ForeignKey,
    JSON
)
from sqlalchemy.orm import relationship
from .database import Base

class ContractorProfile(Base):
    """ঠিকাদারের প্রোফাইল (পাইলটের প্রথম ধাপে আপনার বাবার কাজের তথ্য)"""
    __tablename__ = "contractor_profiles"

    id = Column(Integer, primary_key=True, index=True)
    business_name = Column(String(255), nullable=False)
    contact_person = Column(String(255), nullable=False)
    preferred_language = Column(String(10), default="bn")
    whatsapp_number = Column(String(50), nullable=True)
    
    # যোগাযোগের তথ্য ও অবস্থান
    email = Column(String(255), nullable=True)
    phone = Column(String(50), nullable=True)
    district = Column(String(100), nullable=True)

    # কাস্টমার লাইফসাইকেল ও স্ট্যাটাস (draft, active, paused)
    client_status = Column(String(50), default="active", nullable=False) # draft, active, paused
    account_status = Column(String(50), default="active", nullable=False)
    # payment_status: none, pending, submitted, confirmed, rejected
    payment_status = Column(String(50), default="confirmed", nullable=False)
    # subscription_status: inactive, active, trial, paused, expired
    subscription_status = Column(String(50), default="active", nullable=False)
    subscription_expires_at = Column(DateTime, nullable=True)

    # অনবোর্ডিং অবস্থা: not_started, started, partially_completed, complete, needs_verification
    onboarding_status = Column(String(50), default="complete", nullable=False)
    onboarding_data = Column(JSON, nullable=True)

    # ডেমো নাকি রিয়েল প্রোডাকশন ক্লায়েন্ট
    is_demo = Column(Boolean, default=False, nullable=False)

    # ইমেইল নোটিফিকেশন শিডিউল ও পছন্দ
    notification_schedules = Column(JSON, default=lambda: ["12:00", "19:00"])
    notification_preference = Column(String(50), default="daily_email") # daily_email, instant_email, summary_only

    # পছন্দসমূহ (JSON লিস্ট আকারে জেলা, উপজেলা ও কাজের ধরণ)
    preferred_districts = Column(JSON, default=lambda: ["Dinajpur"])
    preferred_upazilas = Column(JSON, default=lambda: [])
    work_categories = Column(JSON, default=lambda: ["Civil Works", "Road Construction"])
    preferred_agencies = Column(JSON, default=lambda: ["LGED", "RHD"])
    
    # প্রকল্পের আকার (টাকা)
    min_project_value_bdt = Column(Float, nullable=True)
    max_project_value_bdt = Column(Float, nullable=True)
    
    # অভিজ্ঞতা ও কারিগরি তথ্যাবলি (Phase 1 19-Field Onboarding Spec)
    years_of_experience = Column(Integer, nullable=True)
    previous_project_types = Column(JSON, default=lambda: [])
    similar_work_experience = Column(Text, nullable=True)
    approx_annual_turnover_bdt = Column(Float, nullable=True)
    available_equipment = Column(JSON, default=lambda: [])
    available_manpower = Column(JSON, default=lambda: [])
    licenses_certifications = Column(JSON, default=lambda: [])
    excluded_areas_or_categories = Column(JSON, default=lambda: [])

    # অভিজ্ঞতা ও সীমাবদ্ধতার নোট (স্বঘোষিত)
    experience_notes = Column(Text, nullable=True)
    known_constraints = Column(Text, nullable=True)
    
    # মেসেজিং সম্মতি ও ফ্রিকোয়েন্সি
    message_frequency = Column(String(50), default="daily_digest")
    messaging_consent = Column(Boolean, default=True)

    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # দৈনিক ইমেইলের সংখ্যা শিডিউলের দৈর্ঘ্য থেকে নিশ্চিতভাবে গণনাকৃত
    @property
    def daily_email_count(self) -> int:
        if isinstance(self.notification_schedules, list):
            return len(self.notification_schedules)
        return 0

    # রিলেশনশিপ
    assessments = relationship("MatchAssessment", back_populates="contractor")
    notifications = relationship("NotificationDraft", back_populates="contractor")
    feedbacks = relationship("Feedback", back_populates="contractor")
    payments = relationship("PaymentRecord", back_populates="contractor", cascade="all, delete-orphan")
    email_records = relationship("EmailNotificationRecord", back_populates="contractor", cascade="all, delete-orphan")
    activities = relationship("ActivityEvent", back_populates="contractor")



class Tender(Base):
    """টেন্ডারের তথ্য ও বাস্তব উৎস রেকর্ড"""
    __tablename__ = "tenders"

    id = Column(Integer, primary_key=True, index=True)
    tender_id = Column(String(100), unique=True, index=True, nullable=False) # যেমন: e-GP Tender ID 1045231
    title = Column(Text, nullable=False)
    agency = Column(String(255), nullable=False) # যেমন: LGED, RHD, PWD
    procuring_entity_office = Column(String(255), nullable=False) # দরপত্র আহবানকারী অফিস (যেমন: নির্বাহী প্রকৌশলীর কার্যালয়, দিনাজপুর)
    
    # প্রকৃত কাজের এলাকা (নিয়ম: দরপত্র আহবানকারী অফিস ও কাজের এলাকা আলাদা ফিল্ড)
    project_location_district = Column(String(100), nullable=False) # যেমন: দিনাজপুর
    project_location_details = Column(String(255), nullable=True) # যেমন: বীরগঞ্জ উপজেলা
    category = Column(String(255), nullable=False) # কাজের ধরণ
    
    # আর্থিক তথ্য (নিয়ম: প্রাক্কলিত মূল্য ও সিকিউরিটি মানি আলাদা, সিকিউরিটি থেকে মূল্য অনুমান নিষিদ্ধ)
    estimated_value_bdt = Column(Float, nullable=True) # প্রাক্কলিত মূল্য না থাকলে স্পষ্ট Null থাকবে
    tender_security_bdt = Column(Float, nullable=True) # টেন্ডার সিকিউরিটির পরিমাণ
    document_price_bdt = Column(Float, nullable=True) # শিডিউল ক্রয় মূল্য
    
    # গুরুত্বপূর্ণ তারিখ ও সময় (বাংলাদেশ সময় BST)
    publication_date = Column(DateTime, nullable=True)
    document_last_selling_date = Column(DateTime, nullable=True) # শিডিউল কেনার শেষ সময়
    closing_date = Column(DateTime, nullable=False) # দরপত্র দাখিলের শেষ সময়
    opening_date = Column(DateTime, nullable=True) # খোলার সময়
    
    # উৎস এবং সত্যতা যাচাই
    source_url = Column(Text, nullable=False) # মূল e-GP বা অফিসিয়াল ওয়েবসাইটের লিঙ্ক
    source_type = Column(String(50), default="e-GP Sample")
    raw_eligibility_text = Column(Text, nullable=True) # মূল নোটিশের শর্তাবলি (অক্ষত রূপ)
    
    is_amendment = Column(Boolean, default=False)
    amendment_details = Column(Text, nullable=True)
    status = Column(String(50), default="active") # active, amended, cancelled, archived
    is_synthetic = Column(Boolean, default=False, nullable=False) # টেস্ট বা কাল্পনিক ডেটা আলাদা করার ফ্ল্যাগ
    
    last_checked_at = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)

    # রিলেশনশিপ
    assessments = relationship("MatchAssessment", back_populates="tender")
    notifications = relationship("NotificationDraft", back_populates="tender")
    feedbacks = relationship("Feedback", back_populates="tender")


class MatchAssessment(Base):
    """ঠিকাদারের সাথে টেন্ডারের মিল-অমিল বিশ্লেষণ (স্বচ্ছ শর্তভিত্তিক)"""
    __tablename__ = "match_assessments"

    id = Column(Integer, primary_key=True, index=True)
    contractor_id = Column(Integer, ForeignKey("contractor_profiles.id"), nullable=False)
    tender_id = Column(Integer, ForeignKey("tenders.id"), nullable=False)
    
    # পছন্দ ও মিলের অবস্থা
    preference_fit_status = Column(String(50), nullable=False) # fits, partial, outside
    preference_reasons = Column(JSON, nullable=True) # জেলা ও কাজের ধরণের মিলের ব্যাখ্যা
    
    # যোগ্যতার অবস্থা (শতকরা স্কোরিং নয়)
    # meets_known_criteria, does_not_meet, unknown_needs_verification
    qualification_status = Column(String(50), nullable=False)
    known_mismatches = Column(JSON, nullable=True) # স্পষ্ট গরমিল থাকলে তালিকা
    unknown_items_to_verify = Column(JSON, nullable=True) # কোন কোন শর্ত এখনো নিশ্চিত নয়
    
    # বাংলায় স্পষ্ট সার্বিক বিশ্লেষণ
    overall_fit_explanation_bn = Column(Text, nullable=False)
    
    # অপারেটর (আপনার) পর্যালোচনার অবস্থা
    operator_review_status = Column(String(50), default="pending") # pending, shortlisted, rejected, needs_more_info
    operator_notes = Column(Text, nullable=True)
    
    evaluated_at = Column(DateTime, default=datetime.utcnow)

    # রিলেশনশিপ
    contractor = relationship("ContractorProfile", back_populates="assessments")
    tender = relationship("Tender", back_populates="assessments")
    notifications = relationship("NotificationDraft", back_populates="assessment")
    feedbacks = relationship("Feedback", back_populates="assessment")


class NotificationDraft(Base):
    """WhatsApp-এর জন্য প্রস্তুতকৃত বার্তার খসড়া ও অপারেটর অনুমোদন"""
    __tablename__ = "notification_drafts"

    id = Column(Integer, primary_key=True, index=True)
    assessment_id = Column(Integer, ForeignKey("match_assessments.id"), nullable=False)
    contractor_id = Column(Integer, ForeignKey("contractor_profiles.id"), nullable=False)
    tender_id = Column(Integer, ForeignKey("tenders.id"), nullable=False)
    
    draft_message_bn = Column(Text, nullable=False) # সহজ বাংলায় সম্পূর্ণ তৈরি বার্তা
    approval_status = Column(String(50), default="draft") # draft, approved, rejected
    
    # ম্যানুয়াল পাঠানোর রেকর্ড
    manual_send_recorded = Column(Boolean, default=False)
    manual_send_recorded_at = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # রিলেশনশিপ
    assessment = relationship("MatchAssessment", back_populates="notifications")
    contractor = relationship("ContractorProfile", back_populates="notifications")
    tender = relationship("Tender", back_populates="notifications")


class Feedback(Base):
    """ঠিকাদারের কাছ থেকে প্রাপ্ত প্রতিক্রিয়া ও পাইলট ফলাফল"""
    __tablename__ = "feedbacks"

    id = Column(Integer, primary_key=True, index=True)
    assessment_id = Column(Integer, ForeignKey("match_assessments.id"), nullable=False)
    contractor_id = Column(Integer, ForeignKey("contractor_profiles.id"), nullable=False)
    tender_id = Column(Integer, ForeignKey("tenders.id"), nullable=False)
    
    # প্রতিক্রিয়া ক্যাটাগরি
    # worth_reviewing, not_relevant, already_known, needs_more_info
    feedback_type = Column(String(50), nullable=False)
    rejection_reason = Column(Text, nullable=True) # যেমন: "বাজেট অনেক কম", "অন্য উপজেলায় যেতে চাই না"
    next_action_taken = Column(String(100), nullable=True) # যেমন: শিডিউল কিনেছেন, খোঁজ নিচ্ছেন ইত্যাদি
    operator_notes = Column(Text, nullable=True)
    
    recorded_at = Column(DateTime, default=datetime.utcnow)

    # রিলেশনশিপ
    assessment = relationship("MatchAssessment", back_populates="feedbacks")
    contractor = relationship("ContractorProfile", back_populates="feedbacks")
    tender = relationship("Tender", back_populates="feedbacks")


class PaymentRecord(Base):
    """কাস্টমারের সাবস্ক্রিপশন ও বিকাশ/ব্যাংক পেমেন্ট রেকর্ড"""
    __tablename__ = "payment_records"

    id = Column(Integer, primary_key=True, index=True)
    contractor_id = Column(Integer, ForeignKey("contractor_profiles.id"), nullable=False, index=True)
    payment_id = Column(String(100), unique=True, index=True, nullable=False) # যেমন: PAY-20260922-001
    amount = Column(Float, nullable=False)
    currency = Column(String(10), default="BDT", nullable=False)
    payment_method = Column(String(50), default="bKash", nullable=False) # bKash, Bank Transfer, Cash
    transaction_reference = Column(String(100), nullable=True) # যেমন: বিকাশ TrxID
    payment_status = Column(String(50), default="pending", nullable=False) # pending, submitted, confirmed, rejected, refunded, cancelled
    service_period_start = Column(DateTime, nullable=True)
    service_period_end = Column(DateTime, nullable=True)
    confirmed_at = Column(DateTime, nullable=True)
    confirmation_source = Column(String(100), default="Operator Manual") # Operator Manual, bKash Webhook
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # রিলেশনশিপ
    contractor = relationship("ContractorProfile", back_populates="payments")


class EmailNotificationRecord(Base):
    """ইমেইল নোটিফিকেশন ডেলিভারি, শিডিউল ও ট্র্যাকিং হিস্টোরি (স্লট ডিডুপ্লিকেশন সহ)"""
    __tablename__ = "email_notification_records"

    id = Column(Integer, primary_key=True, index=True)
    contractor_id = Column(Integer, ForeignKey("contractor_profiles.id"), nullable=False, index=True)
    tender_id = Column(Integer, ForeignKey("tenders.id"), nullable=True, index=True)
    recipient_email = Column(String(255), nullable=False)
    subject = Column(String(500), nullable=False)

    # স্লট-লেভেল ডিডুপ্লিকেশন ট্র্যাকিং (Asia/Dhaka BST ভিত্তিক)
    schedule_date = Column(String(20), nullable=True, index=True) # যেমন: '2026-09-22'
    schedule_slot = Column(String(10), nullable=True, index=True) # যেমন: '12:00'
    scheduled_time = Column(DateTime, nullable=True)
    sent_at = Column(DateTime, nullable=True, index=True)

    # অবস্থা: scheduled, queued, sending, sent, failed, cancelled
    status = Column(String(50), default="sent", nullable=False)
    # ট্রিগার ধরণ: scheduled_automation, manual_test_send, operator_triggered
    trigger_type = Column(String(50), default="scheduled_automation", nullable=False)

    error_message = Column(Text, nullable=True)
    provider = Column(String(50), default="smtp")
    html_preview = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # রিলেশনশিপ
    contractor = relationship("ContractorProfile", back_populates="email_records")
    tender = relationship("Tender")


class ActivityEvent(Base):
    """সিস্টেম ও অপারেটর কার্যক্রমের গ্লোবাল অডিট লগ"""
    __tablename__ = "activity_events"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    event_type = Column(String(100), nullable=False, index=True) 
    # event_types: client_created, payment_submitted, payment_confirmed, onboarding_started, 
    # onboarding_completed, tender_matched, email_sent, manual_test_send, operator_triggered, 
    # status_changed, egp_sync, schedule_updated

    contractor_id = Column(Integer, ForeignKey("contractor_profiles.id"), nullable=True, index=True)
    tender_id = Column(Integer, ForeignKey("tenders.id"), nullable=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    metadata_json = Column(JSON, nullable=True)

    # রিলেশনশিপ
    contractor = relationship("ContractorProfile", back_populates="activities")
    tender = relationship("Tender")

