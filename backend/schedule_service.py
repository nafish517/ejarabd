"""
EjaraBD (ইজারাবিডি) Schedule Service.

Provides explicit Asia/Dhaka (BST = UTC+6) timezone handling, client-specific
schedule metrics calculation (next email, sent today, remaining today), and
safe manual 'Send Now' testing without perturbing normal scheduled slots.
"""

import re
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional, Union
from sqlalchemy.orm import Session

from backend.models import (
    ContractorProfile,
    Tender,
    MatchAssessment,
    NotificationDraft,
    EmailNotificationRecord,
    ActivityEvent,
)
from backend.email_service import get_email_provider, send_email
from backend.email_templates import render_tender_notification_email

logger = logging.getLogger("ejarabd.scheduler")

# বাংলাদেশ স্ট্যান্ডার্ড টাইম (BST = UTC+6)
BST_OFFSET = timedelta(hours=6)
BST_TZ = timezone(BST_OFFSET, name="Asia/Dhaka")


def get_now_bst() -> datetime:
    """বর্তমান সময় বাংলাদেশ স্ট্যান্ডার্ড টাইমে (BST) রিটার্ন করে।"""
    return datetime.now(timezone.utc).astimezone(BST_TZ)


def get_today_date_bst(now_bst: Optional[datetime] = None) -> str:
    """আজকের তারিখ বাংলাদেশ সময় অনুযায়ী 'YYYY-MM-DD' ফরম্যাটে রিটার্ন করে।"""
    dt = now_bst or get_now_bst()
    return dt.strftime("%Y-%m-%d")


def format_bst_time_display(dt: Optional[datetime]) -> str:
    """তারিখ ও সময়কে 'Today 12:00 PM BST' বা '22-09-2026 12:00 PM BST' ফরম্যাটে দেখায়।"""
    if not dt:
        return "Not available"
    if dt.tzinfo is None:
        # Assume UTC if naive
        dt = dt.replace(tzinfo=timezone.utc).astimezone(BST_TZ)
    else:
        dt = dt.astimezone(BST_TZ)

    now = get_now_bst()
    time_str = dt.strftime("%I:%M %p BST")
    if dt.date() == now.date():
        return f"Today {time_str}"
    elif dt.date() == (now + timedelta(days=1)).date():
        return f"Tomorrow {time_str}"
    else:
        return f"{dt.strftime('%d-%m-%Y')} {time_str}"


def calculate_client_schedule_metrics(
    db: Session,
    contractor: ContractorProfile,
    now_bst: Optional[datetime] = None
) -> Dict[str, Any]:
    """
    নির্দিষ্ট ক্লায়েন্টের জন্য রিয়েল ডাটাবেজ রেকর্ড থেকে শিডিউল মেট্রিক্স গণনা করে।
    notification_schedules হলো দৈনিক ইমেইলের একমাত্র সোর্স অব ট্রুথ।
    """
    now = now_bst or get_now_bst()
    today_str = now.strftime("%Y-%m-%d")
    schedules: List[str] = contractor.notification_schedules or []
    if isinstance(schedules, str):
        import json
        try:
            schedules = json.loads(schedules)
        except Exception:
            schedules = []

    emails_per_day = len(schedules)

    # আজকের মধ্যরাত UTC হিসাব (যেহেতু DB-তে sent_at UTC হিসেবে থাকে)
    today_midnight_bst = datetime(now.year, now.month, now.day, 0, 0, 0, tzinfo=BST_TZ)
    today_midnight_utc = today_midnight_bst.astimezone(timezone.utc).replace(tzinfo=None)

    # ১. আজ এই ক্লায়েন্টকে পাঠানো মোট সফল ইমেইল সংখ্যা
    sent_today_count = db.query(EmailNotificationRecord).filter(
        EmailNotificationRecord.contractor_id == contractor.id,
        EmailNotificationRecord.status == "sent",
        EmailNotificationRecord.sent_at >= today_midnight_utc
    ).count()

    # ২. সর্বশেষ পাঠানো ইমেইল রেকর্ড
    last_sent_record = db.query(EmailNotificationRecord).filter(
        EmailNotificationRecord.contractor_id == contractor.id,
        EmailNotificationRecord.status == "sent"
    ).order_by(EmailNotificationRecord.sent_at.desc()).first()

    last_email_display = "None yet"
    last_email_iso = None
    if last_sent_record and last_sent_record.sent_at:
        last_email_display = format_bst_time_display(last_sent_record.sent_at)
        last_email_iso = last_sent_record.sent_at.isoformat()

    # ৩. পরবর্তী শিডিউলড ইমেইলের সময় গণনা
    next_email_display = "Not configured"
    next_email_iso = None

    if schedules and contractor.account_status == "active" and contractor.subscription_status == "active":
        # শিডিউল সময়সমূহ সাজানো (যেমন: ["12:00", "19:00"] বা ["4:13"])
        raw_slots = [s.strip() for s in schedules if re.match(r"^\d{1,2}:\d{2}$", s.strip())]
        normalized_slots = []
        for s in raw_slots:
            parts = s.split(":")
            normalized_slots.append(f"{int(parts[0]):02d}:{int(parts[1]):02d}")
        valid_slots = sorted(list(set(normalized_slots)))
        current_hm = now.strftime("%H:%M")

        # আজ ইতোমধ্যে যে যে স্লটে পাঠানো হয়েছে
        sent_slots_today = {
            r[0] for r in db.query(EmailNotificationRecord.schedule_slot).filter(
                EmailNotificationRecord.contractor_id == contractor.id,
                EmailNotificationRecord.schedule_date == today_str,
                EmailNotificationRecord.status == "sent"
            ).all() if r[0]
        }

        # আজকের বাকি স্লট যা এখনও পার হয়নি এবং পাঠানো হয়নি
        upcoming_slot = None
        for slot in valid_slots:
            if slot > current_hm and slot not in sent_slots_today:
                upcoming_slot = slot
                break

        if upcoming_slot:
            hour, minute = map(int, upcoming_slot.split(":"))
            slot_dt = datetime(now.year, now.month, now.day, hour, minute, 0, tzinfo=BST_TZ)
            time_formatted = slot_dt.strftime("%I:%M %p BST")
            next_email_display = f"Today {time_formatted}"
            next_email_iso = slot_dt.isoformat()
        elif valid_slots:
            # আজকের সব স্লট শেষ বা পাঠানো সম্পন্ন; আগামীকালের প্রথম স্লট
            first_slot = valid_slots[0]
            hour, minute = map(int, first_slot.split(":"))
            tomorrow = now + timedelta(days=1)
            slot_dt = datetime(tomorrow.year, tomorrow.month, tomorrow.day, hour, minute, 0, tzinfo=BST_TZ)
            time_formatted = slot_dt.strftime("%I:%M %p BST")
            next_email_display = f"Tomorrow {time_formatted}"
            next_email_iso = slot_dt.isoformat()
    elif contractor.account_status != "active":
        next_email_display = f"Paused ({contractor.account_status})"
    elif contractor.subscription_status != "active":
        next_email_display = f"Subscription {contractor.subscription_status}"

    emails_remaining_today = max(0, emails_per_day - sent_today_count)

    return {
        "emails_per_day": emails_per_day,
        "schedules": schedules,
        "emails_sent_today": sent_today_count,
        "emails_remaining_today": emails_remaining_today,
        "next_email_display": next_email_display,
        "next_email_iso": next_email_iso,
        "last_email_display": last_email_display,
        "last_email_iso": last_email_iso,
    }


def send_client_notification_now(
    db: Session,
    contractor_id: int,
    tender_id: Optional[Union[int, str]] = None,
    trigger_type: str = "manual_test_send", # manual_test_send অথবা operator_triggered
    force: bool = False
) -> Dict[str, Any]:
    """
    ম্যানুয়াল 'Send Now' এক্সিকিউশন:
    - নির্বাচিত ক্লায়েন্টের নির্ধারিত ইমেইলে সরাসরি নোটিফিকেশন পাঠায়।
    - ক্লায়েন্টের নরমাল শিডিউল, শিডিউল অ্যারে বা দৈনিক স্লট কাউন্ট কখনো পরিবর্তন করে না।
    - schedule_date ও schedule_slot ফিল্ড ফাঁকা (None) রাখে যাতে নরমাল স্লট অপরিবর্তিত থাকে।
    - অসাবধানতাবশত ডুপ্লিকেট পাঠানো প্রতিরোধ করে (যদি না force=True হয়)।
    """
    if trigger_type not in ("manual_test_send", "operator_triggered"):
        trigger_type = "operator_triggered"

    # ১. ক্লায়েন্ট নিশ্চিতকরণ
    contractor = db.query(ContractorProfile).filter_by(id=contractor_id).first()
    if not contractor:
        raise ValueError(f"ক্লায়েন্ট আইডি {contractor_id} পাওয়া যায়নি")

    # ২. গ্রহীতার ইমেইল সমাধান
    to_email = (contractor.email or "").strip()
    if not to_email or not re.match(r"[^@]+@[^@]+\.[^@]+", to_email):
        raise ValueError(
            f"ক্লায়েন্ট '{contractor.business_name}'-এর কোনো বৈধ ইমেইল ঠিকানা নেই। "
            "অনুগ্রহ করে ক্লায়েন্ট প্রোফাইলে ইমেইল যুক্ত করুন।"
        )

    # ৩. টেন্ডার নির্ধারণ
    tender = None
    if tender_id:
        if str(tender_id).isdigit():
            tender = db.query(Tender).filter(Tender.id == int(tender_id)).first()
        if not tender:
            tender = db.query(Tender).filter(Tender.tender_id == str(tender_id)).first()
        if not tender:
            raise ValueError(f"টেন্ডার আইডি '{tender_id}' ডাটাবেজে পাওয়া যায়নি")
    else:
        # ক্লায়েন্টের জন্য সেরা ও এখনও না পাঠানো ম্যাচিং টেন্ডার খোঁজা
        sent_tender_ids = db.query(EmailNotificationRecord.tender_id).filter(
            EmailNotificationRecord.contractor_id == contractor.id,
            EmailNotificationRecord.status == "sent"
        ).all()
        sent_ids_set = {r[0] for r in sent_tender_ids if r[0]}

        query = db.query(MatchAssessment).join(Tender).filter(
            MatchAssessment.contractor_id == contractor.id,
            MatchAssessment.preference_fit_status.in_(["fits", "partial"]),
            Tender.status == "active"
        )
        if sent_ids_set:
            query = query.filter(~Tender.id.in_(sent_ids_set))
        
        assessment = query.order_by(Tender.closing_date.desc()).first()

        if assessment:
            tender = assessment.tender
        else:
            # কোনো আন-নোটিফায়েড না থাকলে যে কোনো সেরা একটিভ ম্যাচ
            fallback_ass = db.query(MatchAssessment).join(Tender).filter(
                MatchAssessment.contractor_id == contractor.id,
                Tender.status == "active"
            ).order_by(Tender.id.desc()).first()
            if fallback_ass:
                tender = fallback_ass.tender

    if not tender:
        raise ValueError(f"ক্লায়েন্ট '{contractor.business_name}'-এর জন্য কোনো উপযুক্ত টেন্ডার পাওয়া যায়নি")

    # ৪. ডুপ্লিকেট সেন্ড গার্ড (গত ৭ দিনের মধ্যে পাঠানো হয়েছে কিনা)
    if not force:
        seven_days_ago = datetime.utcnow() - timedelta(days=7)
        recent_send = db.query(EmailNotificationRecord).filter(
            EmailNotificationRecord.contractor_id == contractor.id,
            EmailNotificationRecord.tender_id == tender.id,
            EmailNotificationRecord.status == "sent",
            EmailNotificationRecord.sent_at >= seven_days_ago
        ).first()

        if recent_send:
            raise ValueError(
                f"সতর্কতা: টেন্ডার '{tender.tender_id}' ইতোমধ্যেই এই ক্লায়েন্টকে পাঠানো হয়েছে "
                f"({format_bst_time_display(recent_send.sent_at)})। পুনরায় পাঠাতে 'force=true' ব্যবহার করুন।"
            )

    # ৫. প্রাসঙ্গিক MatchAssessment ও NotificationDraft লোড
    assessment = db.query(MatchAssessment).filter_by(
        contractor_id=contractor.id,
        tender_id=tender.id
    ).first()

    draft = None
    if assessment:
        draft = db.query(NotificationDraft).filter_by(assessment_id=assessment.id).first()

    # ৬. বাংলায় সম্পূর্ণ ডিটারমিনিস্টিক নোটিফিকেশন রেন্ডার (কোনো এআই হ্যালুসিনেশন নয়)
    subject, html_body, text_body = render_tender_notification_email(
        tender=tender,
        contractor=contractor,
        assessment=assessment,
        notification_draft=draft
    )

    # ৭. ইমেইল ডেলিভারি
    provider = get_email_provider()
    send_result = provider.send_email(
        to_email=to_email,
        subject=subject,
        html_body=html_body,
        text_body=text_body
    )

    # ৮. ডেলিভারি হিস্টোরিতে সংরক্ষণ (স্লট ফিল্ড ফাঁকা থাকবে, নরমাল শিডিউল অক্ষত)
    now_utc = datetime.utcnow()
    record = EmailNotificationRecord(
        contractor_id=contractor.id,
        tender_id=tender.id,
        recipient_email=to_email,
        subject=subject,
        schedule_date=None, # ম্যানুয়াল পাঠালে শিডিউল স্লট ব্যবহৃত হয় না
        schedule_slot=None,
        scheduled_time=None,
        sent_at=now_utc if send_result.success else None,
        status="sent" if send_result.success else "failed",
        trigger_type=trigger_type,
        error_message=send_result.error if not send_result.success else None,
        provider=send_result.provider,
        html_preview=html_body
    )
    db.add(record)

    # ৯. গ্লোবাল অ্যাক্টিভিটি লগ সংরক্ষণ
    act_title = (
        f"Manual email sent: {tender.tender_id}"
        if send_result.success
        else f"Manual email failed: {tender.tender_id}"
    )
    act = ActivityEvent(
        timestamp=now_utc,
        event_type=trigger_type,
        contractor_id=contractor.id,
        tender_id=tender.id,
        title=act_title,
        description=f"Recipient: {to_email} | Client: {contractor.business_name} | Provider: {send_result.provider}",
        metadata_json={
            "recipient": to_email,
            "tender_id": tender.tender_id,
            "trigger_type": trigger_type,
            "success": send_result.success,
            "error": send_result.error
        }
    )
    db.add(act)
    db.commit()
    db.refresh(record)

    return {
        "success": send_result.success,
        "message": send_result.message,
        "record_id": record.id,
        "recipient": to_email,
        "tender_id": tender.tender_id,
        "tender_title": tender.title,
        "trigger_type": trigger_type,
        "provider": send_result.provider,
        "error": send_result.error,
        "sent_at": record.sent_at.isoformat() if record.sent_at else None
    }
