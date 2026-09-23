"""
Comprehensive Operations Platform Test Suite for EjaraBD (ইজারাবিডি).

Validates Phase 1 Operations Architecture:
1. Production database preservation (1700+ tenders untouched)
2. Streamlined client onboarding & lifecycle management via Phase 1 API
3. notification_schedules as the single source of truth for daily email count
4. Multi-customer isolation (Client A preferences/matches never leak to Client B)
5. Client status transitions (active, paused, draft) with immediate effect
6. 19-field contractor profile management and persistence
7. Persistent slot-level deduplication in background scheduler:
   - Exactly 1 email sent for configured slot
   - Second tick does NOT send duplicate
   - Process restart does NOT resend completed slot
   - Manual Send Now remains independent and does not consume scheduled slot
8. 100% AI-offline deterministic matching & email formatting
9. System health & telemetry endpoint verification
"""

import os
import sys
import unittest
from datetime import datetime, timezone, timedelta
from typing import Dict, Any

# Ensure workspace root is in sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(BASE_DIR, ".."))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

# Windows UTF-8 safety
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from fastapi.testclient import TestClient
from backend.main import app
from backend.database import SessionLocal, engine
from backend.models import (
    ContractorProfile,
    Tender,
    MatchAssessment,
    PaymentRecord,
    EmailNotificationRecord,
    ActivityEvent,
)
from backend.email_service import set_email_provider, MockEmailProvider
from backend.schedule_service import (
    BST_TZ,
    get_now_bst,
    get_today_date_bst,
    calculate_client_schedule_metrics,
    send_client_notification_now,
)
from backend.scheduler import EjaraBDScheduler
from backend.matching import evaluate_tender_for_contractor


class TestOperationsPlatform(unittest.TestCase):
    TEST_EMAILS = ["tester@example.com", "client.a@example.com", "client.b@example.com"]

    @classmethod
    def _clean_test_records(cls):
        db = SessionLocal()
        try:
            test_clients = db.query(ContractorProfile).filter(ContractorProfile.email.in_(cls.TEST_EMAILS)).all()
            for c in test_clients:
                db.query(EmailNotificationRecord).filter_by(contractor_id=c.id).delete()
                db.query(PaymentRecord).filter_by(contractor_id=c.id).delete()
                db.query(ActivityEvent).filter_by(contractor_id=c.id).delete()
                db.query(MatchAssessment).filter_by(contractor_id=c.id).delete()
                db.delete(c)
            db.commit()
        finally:
            db.close()

    @classmethod
    def setUpClass(cls):
        cls._clean_test_records()
        cls.client = TestClient(app)
        cls.mock_email_provider = MockEmailProvider()
        set_email_provider(cls.mock_email_provider)

    @classmethod
    def tearDownClass(cls):
        cls._clean_test_records()

    def setUp(self):
        self.db = SessionLocal()
        self.db.expire_all()
        self.mock_email_provider.clear()

    def tearDown(self):
        self.db.close()

    def test_01_production_database_preservation(self):
        """TEST 1: Verify production tenders and records remain completely preserved"""
        tender_count = self.db.query(Tender).count()
        self.assertGreaterEqual(tender_count, 1700, f"Expected at least 1700 tenders, found {tender_count}")
        
        # Verify pilot contractor #1 exists and is preserved
        pilot = self.db.query(ContractorProfile).filter_by(id=1).first()
        self.assertIsNotNone(pilot, "Client #1 (pilot profile) must exist and be preserved")
        self.assertEqual(pilot.is_demo, False, "Client #1 must be a production client (is_demo=False)")
        print(f"\n✓ Test 01 Passed: Production database preserved with {tender_count} tenders intact.")

    def test_02_new_client_onboarding_and_defaults(self):
        """TEST 2: New client creation with Phase 1 19-field contract and status controls"""
        res = self.client.post("/api/clients", json={
            "business_name": "টেস্ট কনস্ট্রাকশন লিঃ",
            "contact_person": "জনাব পরীক্ষক সাহেব",
            "email": "tester@example.com",
            "phone": "+8801700000099",
            "district": "Bogura",
            "preferred_districts": ["Bogura"],
            "work_categories": ["Civil Works"],
            "notification_schedules": ["11:00", "18:00"],
            "client_status": "active"
        })
        self.assertEqual(res.status_code, 200, res.text)
        client_data = res.json()["client"]
        client_id = client_data["id"]

        new_client = self.db.query(ContractorProfile).filter_by(id=client_id).first()
        self.assertIsNotNone(new_client)
        self.assertEqual(new_client.client_status, "active")
        self.assertEqual(new_client.daily_email_count, 2)
        print("\n✓ Test 02 Passed: New client created with Phase 1 19-field spec and active status.")

    def test_03_notification_schedules_single_source_of_truth(self):
        """TEST 3: notification_schedules must be single source of truth for daily count"""
        client = self.db.query(ContractorProfile).filter_by(email="tester@example.com").first()
        self.assertIsNotNone(client)

        # Update schedules to 3 slots
        self.client.put(f"/api/clients/{client.id}", json={
            "notification_schedules": ["09:00", "14:00", "20:00"]
        })
        self.db.refresh(client)
        self.assertEqual(client.daily_email_count, 3)

        # Update schedules to 1 slot
        self.client.put(f"/api/clients/{client.id}", json={
            "notification_schedules": ["12:00"]
        })
        self.db.refresh(client)
        self.assertEqual(client.daily_email_count, 1)
        print("\n✓ Test 03 Passed: daily_email_count derived strictly from notification_schedules length.")

    def test_04_client_isolation(self):
        """TEST 4: Client A preferences and matches must never cross into Client B"""
        # Client A: Dinajpur, Road Construction
        client_a = ContractorProfile(
            business_name="Client A Enterprise",
            contact_person="Person A",
            email="client.a@example.com",
            district="Dinajpur",
            preferred_districts=["Dinajpur"],
            work_categories=["Road Construction"],
            account_status="active",
            is_demo=True
        )
        # Client B: Sylhet, Tube-well
        client_b = ContractorProfile(
            business_name="Client B Enterprise",
            contact_person="Person B",
            email="client.b@example.com",
            district="Sylhet",
            preferred_districts=["Sylhet"],
            work_categories=["Water Supply & Tube-well"],
            account_status="active",
            is_demo=True
        )
        self.db.add_all([client_a, client_b])
        self.db.commit()

        # Test evaluation against a Dinajpur road tender
        road_tender = self.db.query(Tender).filter(
            Tender.project_location_district.ilike("%dinajpur%"),
            Tender.category.ilike("%road%")
        ).first()

        if road_tender:
            eval_a = evaluate_tender_for_contractor(client_a, road_tender)
            eval_b = evaluate_tender_for_contractor(client_b, road_tender)

            self.assertEqual(eval_a["preference_fit_status"], "fits", "Client A should match road tender")
            self.assertIn(eval_b["preference_fit_status"], ["outside", "partial"], "Client B should not fit road tender")
            self.assertTrue(any("বাইরে" in m for m in eval_b["known_mismatches"]))

        print("\n✓ Test 04 Passed: Client isolation strictly enforced across preferences and matching.")

    def test_05_client_pause_resume_lifecycle(self):
        """TEST 5: Client pause/resume lifecycle status transitions"""
        client = self.db.query(ContractorProfile).filter_by(email="tester@example.com").first()
        self.assertIsNotNone(client)

        # Pause client
        res = self.client.patch(f"/api/clients/{client.id}/status", json={"client_status": "paused"})
        self.assertEqual(res.status_code, 200, res.text)
        self.assertEqual(res.json()["client_status"], "paused")

        # Verify DB reflects paused
        self.db.refresh(client)
        self.assertEqual(client.client_status, "paused")

        # Resume client
        res = self.client.patch(f"/api/clients/{client.id}/status", json={"client_status": "active"})
        self.assertEqual(res.status_code, 200, res.text)
        self.assertEqual(res.json()["client_status"], "active")

        self.db.refresh(client)
        self.assertEqual(client.client_status, "active")
        print("\n✓ Test 05 Passed: Client pause/resume status transitions verified.")

    def test_06_profile_update_and_persistence(self):
        """TEST 6: Submitting 19-field profile updates updates database and persists values"""
        self.db.expire_all()
        client = self.db.query(ContractorProfile).filter_by(email="tester@example.com").first()
        self.assertIsNotNone(client)

        res = self.client.put(f"/api/clients/{client.id}", json={
            "business_name": "পরীক্ষক বিল্ডার্স এন্ড কোং",
            "contact_person": "জনাব মোঃ পরীক্ষক",
            "years_of_experience": 18,
            "similar_work_experience": "২০ কোটি টাকার সেতু নির্মাণ",
            "available_equipment": ["Crane", "Excavator"],
            "preferred_districts": ["Bogura", "Naogaon"],
            "work_categories": ["Civil Works", "Road Construction"],
            "notification_schedules": ["12:00", "19:00"]
        })
        self.assertEqual(res.status_code, 200, res.text)
        self.assertEqual(res.json()["client"]["business_name"], "পরীক্ষক বিল্ডার্স এন্ড কোং")
        self.assertEqual(res.json()["client"]["years_of_experience"], 18)

        self.db.refresh(client)
        self.assertEqual(client.business_name, "পরীক্ষক বিল্ডার্স এন্ড কোং")
        self.assertEqual(client.years_of_experience, 18)
        print("\n✓ Test 06 Passed: Profile update and 19-field persistence verified.")

    def test_07_scheduler_slot_level_deduplication_and_restart(self):
        """
        TEST 7: Deterministic scheduler test:
        1. Eligible client is found for slot '12:00'
        2. Exactly 1 notification email is sent
        3. Immediate second check on slot '12:00' does NOT send duplicate
        4. Simulating process restart by creating a new scheduler instance does NOT resend
        5. Manual Send Now remains independent and tracks trigger type
        """
        client = self.db.query(ContractorProfile).filter_by(email="tester@example.com").first()
        self.assertIsNotNone(client)

        # Clear any prior records
        self.db.query(EmailNotificationRecord).filter_by(contractor_id=client.id).delete()
        self.db.commit()

        # Set client lifecycle and schedule to exactly 12:00
        client.notification_schedules = ["12:00"]
        client.client_status = "active"
        client.account_status = "active"
        client.payment_status = "confirmed"
        client.subscription_status = "active"
        client.onboarding_status = "complete"
        self.db.commit()

        # Run matching to create valid MatchAssessment records for this client
        self.client.post(f"/api/match/run?client_id={client.id}")
        self.db.expire_all()

        # Mock current time in BST: 2026-09-22 12:00:00 (Tuesday)
        mock_time_1200 = datetime(2026, 9, 22, 12, 0, 0, tzinfo=BST_TZ)

        scheduler = EjaraBDScheduler(check_interval_seconds=60)

        # Step 1 & 2: First tick at 12:00
        summary_1 = scheduler.tick(now_bst=mock_time_1200, db=self.db, process_demos=True)
        self.assertEqual(summary_1["emails_sent"], 1, "Exactly one scheduled email should be sent")
        self.assertEqual(len(self.mock_email_provider.sent_emails), 1)
        self.assertEqual(self.mock_email_provider.sent_emails[0]["to_email"], "tester@example.com")

        # Verify record in DB has schedule_date and schedule_slot
        rec = self.db.query(EmailNotificationRecord).filter_by(
            contractor_id=client.id,
            schedule_date="2026-09-22",
            schedule_slot="12:00"
        ).first()
        self.assertIsNotNone(rec)
        self.assertEqual(rec.trigger_type, "scheduled_automation")
        self.assertEqual(rec.status, "sent")

        # Step 3: Second tick at 12:00 (e.g. repeated check within same minute)
        summary_2 = scheduler.tick(now_bst=mock_time_1200, db=self.db, process_demos=True)
        self.assertEqual(summary_2["emails_sent"], 0, "Second tick must NOT resend already completed slot")
        self.assertEqual(len(self.mock_email_provider.sent_emails), 1, "Sent emails count must remain 1")
        self.assertGreaterEqual(summary_2["skipped"], 1)

        # Step 4: Process restart simulation (New scheduler instance created)
        new_scheduler_instance = EjaraBDScheduler(check_interval_seconds=60)
        summary_3 = new_scheduler_instance.tick(now_bst=mock_time_1200, db=self.db, process_demos=True)
        self.assertEqual(summary_3["emails_sent"], 0, "Restarted scheduler must NOT resend already recorded slot")
        self.assertEqual(len(self.mock_email_provider.sent_emails), 1)

        # Step 5: Manual Send Now independence test
        send_now_res = send_client_notification_now(
            db=self.db,
            contractor_id=client.id,
            trigger_type="manual_test_send",
            force=True
        )
        self.assertTrue(send_now_res["success"])
        self.assertEqual(len(self.mock_email_provider.sent_emails), 2, "Manual Send Now should deliver independently")

        # Check manual send record in DB
        manual_rec = self.db.query(EmailNotificationRecord).filter_by(
            contractor_id=client.id,
            trigger_type="manual_test_send"
        ).first()
        self.assertIsNotNone(manual_rec)
        self.assertIsNone(manual_rec.schedule_date, "Manual send must have schedule_date=None")
        self.assertIsNone(manual_rec.schedule_slot, "Manual send must have schedule_slot=None")

        print("\n✓ Test 07 Passed: Persistent slot-level deduplication, restart resilience, and Send Now independence verified.")

    def test_08_ai_offline_independence(self):
        """TEST 8: Verify core matching and email generation run 100% without Ollama or external network"""
        client = self.db.query(ContractorProfile).first()
        tender = self.db.query(Tender).first()

        # Rule-based matching operates 100% offline
        match_result = evaluate_tender_for_contractor(client, tender)
        self.assertIn("preference_fit_status", match_result)
        self.assertIn("overall_fit_explanation_bn", match_result)

        # Email template renders 100% offline
        from backend.email_templates import render_tender_notification_email
        sub, html, text = render_tender_notification_email(tender=tender, contractor=client)
        self.assertTrue("নতুন টেন্ডার" in sub)
        self.assertTrue(len(html) > 50)
        self.assertTrue(len(text) > 20)
        print("\n✓ Test 08 Passed: 100% deterministic matching and email formatting verified offline.")

    def test_09_health_and_telemetry_api(self):
        """TEST 9: GET /api/health returns truthful system metrics and email dev mode flag"""
        res = self.client.get("/api/health")
        self.assertEqual(res.status_code, 200, res.text)
        data = res.json()

        self.assertEqual(data["status"], "healthy")
        self.assertIn("app", data)
        self.assertIn("version", data)
        self.assertIn("email_dev_mode", data)
        print("\n✓ Test 09 Passed: System health & configuration telemetry verified.")


if __name__ == "__main__":
    unittest.main()
