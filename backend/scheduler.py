"""
EjaraBD (ইজারাবিডি) Background Email Scheduler.

Executes scheduled email jobs for active, eligible clients according to their
individual notification_schedules in Asia/Dhaka BST (UTC+6).

Features:
- Persistent slot-level deduplication at (contractor_id, schedule_date, schedule_slot)
- Zero duplicated sends across process restarts, clock checks, or multiple ticks
- Strict production vs demo data isolation
- 100% deterministic execution (zero AI calls)
- Honest running status reporting (never claims running unless active thread exists)
"""

import time
import threading
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

from backend.database import SessionLocal
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
from backend.schedule_service import (
    BST_TZ,
    get_now_bst,
    get_today_date_bst,
    format_bst_time_display,
)

logger = logging.getLogger("ejarabd.scheduler")


class EjaraBDScheduler:
    """
    নিরাপদ ও ডিটারমিনিস্টিক ব্যাকগ্রাউন্ড শিডিউলার।
    """

    def __init__(self, check_interval_seconds: int = 60):
        self.check_interval_seconds = check_interval_seconds
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._last_tick_time: Optional[datetime] = None
        self._last_tick_summary: Optional[Dict[str, Any]] = None
        self._lock = threading.Lock()

    def is_running(self) -> bool:
        """প্রকৃত ব্যাকগ্রাউন্ড থ্রেড সক্রিয় আছে কিনা তা সত্যবাদীভাবে যাচাই করে।"""
        return self._thread is not None and self._thread.is_alive()

    def start(self) -> bool:
        """ব্যাকগ্রাউন্ড শিডিউলার চালু করে।"""
        with self._lock:
            if self.is_running():
                logger.info("EjaraBD Scheduler is already running.")
                return False

            self._stop_event.clear()
            self._thread = threading.Thread(
                target=self._run_loop,
                name="EjaraBDSchedulerThread",
                daemon=True
            )
            self._thread.start()
            logger.info("EjaraBD Scheduler background worker started successfully.")
            return True

    def stop(self) -> bool:
        """ব্যাকগ্রাউন্ড শিডিউলার নিরাপদভাবে বন্ধ করে।"""
        with self._lock:
            if not self.is_running():
                logger.info("EjaraBD Scheduler is not running.")
                return False

            self._stop_event.set()
            if self._thread:
                self._thread.join(timeout=3.0)
            self._thread = None
            logger.info("EjaraBD Scheduler background worker stopped.")
            return True

    def get_status(self) -> Dict[str, Any]:
        """শিডিউলারের প্রকৃত কার্যক্ষম অবস্থা রিটার্ন করে (কোনো ভুয়া তথ্য নয়)।"""
        running = self.is_running()
        now_bst = get_now_bst()
        return {
            "status": "running" if running else "not_running",
            "is_running": running,
            "timezone": "Asia/Dhaka (BST, UTC+6)",
            "current_time_bst": now_bst.strftime("%Y-%m-%d %I:%M:%S %p BST"),
            "check_interval_seconds": self.check_interval_seconds,
            "last_tick_time": self._last_tick_time.isoformat() if self._last_tick_time else None,
            "last_tick_summary": self._last_tick_summary
        }

    def _run_loop(self):
        """ব্যাকগ্রাউন্ড লুপ যা প্রতি মিনিটে বাংলাদেশ সময় অনুযায়ী শিডিউল পরীক্ষা করে।"""
        logger.info("EjaraBD Scheduler run loop started.")
        while not self._stop_event.is_set():
            try:
                self.tick()
            except Exception as e:
                logger.error("Error in scheduler tick: %s", e, exc_info=True)

            # স্লিপ ইন্টারভাল (অপেক্ষা করার সময় স্টপ ইভেন্ট চেক)
            self._stop_event.wait(timeout=self.check_interval_seconds)
        logger.info("EjaraBD Scheduler run loop terminated.")

    def tick(
        self,
        now_bst: Optional[datetime] = None,
        db: Optional[Session] = None,
        process_demos: bool = False
    ) -> Dict[str, Any]:
        """
        একক শিডিউলার টিক এক্সিকিউশন:
        - টেস্ট বা ম্যানুয়াল ট্রিগারের জন্য now_bst ও db সরাসরি ইনজেক্ট করা যায়।
        - বাংলাদেশ সময় মিনিট (HH:MM) বের করে।
        - যোগ্য ক্লায়েন্টদের স্লট ম্যাচ ও ডাটাবেজ-লেভেল পারসিস্টেন্ট ডিডুপ্লিকেশন নিশ্চিত করে।
        """
        curr_bst = now_bst or get_now_bst()
        today_date = curr_bst.strftime("%Y-%m-%d")
        current_slot = curr_bst.strftime("%H:%M")

        own_session = False
        if db is None:
            db = SessionLocal()
            own_session = True

        processed_count = 0
        sent_count = 0
        skipped_count = 0
        details: List[Dict[str, Any]] = []

        try:
            # ১. শুধুমাত্র সক্রিয় ও প্রোডাকশন ক্লায়েন্টদের কুয়েরি (যদি না স্পষ্টভাবে process_demos=True হয়)
            query = db.query(ContractorProfile).filter(
                ContractorProfile.account_status == "active",
                ContractorProfile.payment_status == "confirmed",
                ContractorProfile.subscription_status == "active",
                ContractorProfile.onboarding_status == "complete",
                ContractorProfile.email.isnot(None),
                ContractorProfile.email != ""
            )
            if not process_demos:
                query = query.filter(ContractorProfile.is_demo == False)

            eligible_clients = query.all()

            for client in eligible_clients:
                processed_count += 1
                schedules: List[str] = client.notification_schedules or []
                if isinstance(schedules, str):
                    import json
                    try:
                        schedules = json.loads(schedules)
                    except Exception:
                        schedules = []

                # স্লটের ফরম্যাট মেলানো (যেমন "12:00" বা "08:30" বা "4:13")
                client_slots = []
                for s in schedules:
                    if isinstance(s, str):
                        clean_s = s.strip()
                        parts = clean_s.split(":")
                        if len(parts) == 2:
                            try:
                                client_slots.append(f"{int(parts[0]):02d}:{int(parts[1]):02d}")
                            except ValueError:
                                client_slots.append(clean_s)
                        else:
                            client_slots.append(clean_s)

                if current_slot not in client_slots:
                    # বর্তমান মিনিট এই ক্লায়েন্টের কোনো নির্ধারিত শিডিউল স্লট নয়
                    continue

                # ২. স্লট-লেভেল পারসিস্টেন্ট ডিডুপ্লিকেশন চেক (ডাটাবেজ ভিত্তিক)
                # একই client_id, schedule_date ও schedule_slot-এ ইতোমধ্যে পাঠানো থাকলে অবিলম্বে স্কিপ
                existing_record = db.query(EmailNotificationRecord).filter(
                    EmailNotificationRecord.contractor_id == client.id,
                    EmailNotificationRecord.schedule_date == today_date,
                    EmailNotificationRecord.schedule_slot == current_slot,
                    EmailNotificationRecord.trigger_type == "scheduled_automation",
                    EmailNotificationRecord.status.in_(["sent", "queued", "sending"])
                ).first()

                if existing_record:
                    skipped_count += 1
                    details.append({
                        "client_id": client.id,
                        "client_name": client.business_name,
                        "slot": current_slot,
                        "status": "already_sent_today",
                        "record_id": existing_record.id
                    })
                    continue

                # ৩. ক্লায়েন্টের জন্য সেরা আন-নোটিফায়েড ম্যাচিং টেন্ডার নির্বাচন
                sent_tender_ids = db.query(EmailNotificationRecord.tender_id).filter(
                    EmailNotificationRecord.contractor_id == client.id,
                    EmailNotificationRecord.status == "sent"
                ).all()
                sent_ids_set = {r[0] for r in sent_tender_ids if r[0]}

                match_query = db.query(MatchAssessment).join(Tender).filter(
                    MatchAssessment.contractor_id == client.id,
                    MatchAssessment.preference_fit_status.in_(["fits", "partial"]),
                    Tender.status == "active"
                )
                if sent_ids_set:
                    match_query = match_query.filter(~Tender.id.in_(sent_ids_set))

                best_match = match_query.order_by(Tender.closing_date.desc()).first()

                if not best_match:
                    # কোনো নতুন টেন্ডার নেই
                    skipped_count += 1
                    act = ActivityEvent(
                        timestamp=datetime.utcnow(),
                        event_type="scheduled_automation_skip",
                        contractor_id=client.id,
                        title=f"Scheduled slot {current_slot} skipped: No unnotified tenders",
                        description=f"Client: {client.business_name} ({client.email})"
                    )
                    db.add(act)
                    db.commit()
                    details.append({
                        "client_id": client.id,
                        "client_name": client.business_name,
                        "slot": current_slot,
                        "status": "no_unnotified_matches"
                    })
                    continue

                tender = best_match.tender
                draft = db.query(NotificationDraft).filter_by(assessment_id=best_match.id).first()

                # ৪. বাংলায় সম্পূর্ণ ডিটারমিনিস্টিক ইমেইল রেন্ডার (কোনো এআই হ্যালুসিনেশন নয়)
                subject, html_body, text_body = render_tender_notification_email(
                    tender=tender,
                    contractor=client,
                    assessment=best_match,
                    notification_draft=draft
                )

                # ৫. ইমেইল ডেলিভারি
                provider = get_email_provider()
                send_result = provider.send_email(
                    to_email=client.email.strip(),
                    subject=subject,
                    html_body=html_body,
                    text_body=text_body
                )

                now_utc = datetime.utcnow()

                # ৬. পারসিস্টেন্ট স্লট রেকর্ড তৈরি (যাতে রিস্টার্ট বা বারবার চেকে আর না পাঠায়)
                slot_hour, slot_min = map(int, current_slot.split(":"))
                slot_dt = datetime(curr_bst.year, curr_bst.month, curr_bst.day, slot_hour, slot_min, 0, tzinfo=BST_TZ)

                record = EmailNotificationRecord(
                    contractor_id=client.id,
                    tender_id=tender.id,
                    recipient_email=client.email.strip(),
                    subject=subject,
                    schedule_date=today_date,
                    schedule_slot=current_slot,
                    scheduled_time=slot_dt.astimezone(timezone.utc).replace(tzinfo=None),
                    sent_at=now_utc if send_result.success else None,
                    status="sent" if send_result.success else "failed",
                    trigger_type="scheduled_automation",
                    error_message=send_result.error if not send_result.success else None,
                    provider=send_result.provider,
                    html_preview=html_body
                )
                db.add(record)

                # ৭. অডিট অ্যাক্টিভিটি লগ
                act_title = (
                    f"Scheduled email delivered: {tender.tender_id} (Slot: {current_slot})"
                    if send_result.success
                    else f"Scheduled email failed: {tender.tender_id} (Slot: {current_slot})"
                )
                act = ActivityEvent(
                    timestamp=now_utc,
                    event_type="scheduled_automation",
                    contractor_id=client.id,
                    tender_id=tender.id,
                    title=act_title,
                    description=f"Recipient: {client.email} | Slot: {current_slot} | Provider: {send_result.provider}",
                    metadata_json={
                        "slot": current_slot,
                        "schedule_date": today_date,
                        "success": send_result.success,
                        "error": send_result.error
                    }
                )
                db.add(act)
                db.commit()

                if send_result.success:
                    sent_count += 1
                details.append({
                    "client_id": client.id,
                    "client_name": client.business_name,
                    "slot": current_slot,
                    "tender_id": tender.tender_id,
                    "status": "sent" if send_result.success else "failed",
                    "error": send_result.error
                })

            summary = {
                "timestamp_bst": curr_bst.strftime("%Y-%m-%d %I:%M:%S %p BST"),
                "date": today_date,
                "current_slot": current_slot,
                "eligible_clients_evaluated": processed_count,
                "emails_sent": sent_count,
                "skipped": skipped_count,
                "details": details
            }
            self._last_tick_time = datetime.utcnow()
            self._last_tick_summary = summary
            return summary

        finally:
            if own_session:
                db.close()


# গ্লোবাল শিডিউলার সিঙ্গলটন
scheduler = EjaraBDScheduler(check_interval_seconds=60)
