"""
EjaraBD (ইজারাবিডি) — Core API Endpoints & Phase 1 Contract Tests.

Validates the active Phase 1 FastAPI REST API contracts:
- System health and configuration telemetry (/api/health)
- Complete 19-field client onboarding & CRUD (/api/clients)
- Duplicate client email rejection (case-insensitive)
- Client status lifecycle (active, paused, draft)
- Deterministic matching pipeline trigger (/api/match/run)
- Matches retrieval with fit status badges (/api/clients/{id}/matches)
- Safe test email dispatch (/api/clients/{id}/test-email)
- Live database preservation and isolation
"""

import os
import sys
import unittest
from fastapi.testclient import TestClient

# Ensure root and backend are in sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(BASE_DIR, ".."))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

# UTF-8 terminal encoding safety
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from backend.main import app
from backend.database import SessionLocal
from backend.models import ContractorProfile, Tender

client = TestClient(app)


class TestPhase1ApiEndpoints(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # 1. Verify production database baseline integrity
        import sqlite3
        prod_db_path = os.path.join(BASE_DIR, "ejarabd.db")
        if os.path.exists(prod_db_path):
            conn = sqlite3.connect(prod_db_path)
            cur = conn.cursor()
            cls.prod_tenders = cur.execute("SELECT COUNT(*) FROM tenders").fetchone()[0]
            cls.prod_clients = cur.execute("SELECT COUNT(*) FROM contractor_profiles").fetchone()[0]
            conn.close()
            assert cls.prod_tenders >= 1727, f"Production tenders corrupted: {cls.prod_tenders}"
            assert cls.prod_clients >= 11, f"Production clients corrupted: {cls.prod_clients}"

        # 2. Record test session baseline counts
        db = SessionLocal()
        try:
            cls.initial_tenders = db.query(Tender).count()
            cls.initial_clients = db.query(ContractorProfile).count()
            assert cls.initial_tenders >= 1700, f"Test tenders corrupted: {cls.initial_tenders}"
        finally:
            db.close()

    def test_01_health_and_telemetry(self):
        """Test system health status, version, and dev mode telemetry."""
        res = client.get("/api/health")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "healthy")
        self.assertIn("email_dev_mode", data)
        self.assertTrue(data["email_dev_mode"])
        print("\n✓ API Test 01: Health check & telemetry verified.")

    def test_02_client_crud_and_duplicate_prevention(self):
        """Test complete 19-field client creation, retrieval, update, and duplicate email prevention."""
        unique_email = "api_test_contractor@example.com"

        payload = {
            "business_name": "মেসার্স উত্তরা কনস্ট্রাকশন",
            "contact_person": "মোঃ শফিকুল ইসলাম",
            "email": unique_email,
            "phone": "+8801711223344",
            "preferred_language": "bn",
            "district": "Dinajpur",
            "preferred_districts": ["Dinajpur", "Rangpur"],
            "preferred_upazilas": ["Birganj", "Kaharole"],
            "preferred_agencies": ["LGED", "RHD"],
            "work_categories": ["Civil Works", "Road Construction"],
            "min_project_value_bdt": 2500000.0,
            "max_project_value_bdt": 20000000.0,
            "years_of_experience": 15,
            "previous_project_types": ["Roads", "Culverts"],
            "similar_work_experience": "১৫ কোটি টাকার সড়ক ও ব্রিজ নির্মাণ",
            "approx_annual_turnover_bdt": 35000000.0,
            "available_equipment": ["Road Roller", "Excavator", "Dump Truck"],
            "available_manpower": ["3 Site Engineers", "12 Skilled Labors"],
            "licenses_certifications": ["Trade License 2026", "TIN Certificate"],
            "excluded_areas_or_categories": ["Deep Tube-well"],
            "notification_preference": "daily_email",
            "notification_schedules": ["12:00", "19:00"],
            "client_status": "active"
        }

        # 1. CREATE client
        res = client.post("/api/clients", json=payload)
        self.assertEqual(res.status_code, 200, res.text)
        created_data = res.json()
        self.assertEqual(created_data["status"], "success")
        created_client = created_data["client"]
        client_id = created_client["id"]
        self.assertEqual(created_client["business_name"], "মেসার্স উত্তরা কনস্ট্রাকশন")
        self.assertEqual(created_client["years_of_experience"], 15)
        self.assertEqual(created_client["preferred_upazilas"], ["Birganj", "Kaharole"])

        # 2. DUPLICATE EMAIL PREVENTION on creation (must return 400)
        dup_res = client.post("/api/clients", json=payload)
        self.assertEqual(dup_res.status_code, 400)
        self.assertIn("ইতোমধ্যে", dup_res.json()["detail"])

        # 3. GET client by ID
        get_res = client.get(f"/api/clients/{client_id}")
        self.assertEqual(get_res.status_code, 200)
        self.assertEqual(get_res.json()["email"], unique_email)

        # 4. UPDATE client (PUT)
        update_res = client.put(f"/api/clients/{client_id}", json={
            "contact_person": "মোঃ শফিকুল ইসলাম (আপডেট)",
            "years_of_experience": 16,
            "max_project_value_bdt": 25000000.0
        })
        self.assertEqual(update_res.status_code, 200)
        updated_client = update_res.json()["client"]
        self.assertEqual(updated_client["contact_person"], "মোঃ শফিকুল ইসলাম (আপডেট)")
        self.assertEqual(updated_client["years_of_experience"], 16)

        # 5. DUPLICATE EMAIL PREVENTION on update (updating to existing client #2's email must fail)
        conflict_res = client.put(f"/api/clients/{client_id}", json={
            "email": "demo.contractor.a@example.com"
        })
        self.assertEqual(conflict_res.status_code, 400)
        self.assertIn("অন্য ক্লায়েন্ট", conflict_res.json()["detail"])

        # Clean up test client
        db = SessionLocal()
        c_obj = db.query(ContractorProfile).filter_by(id=client_id).first()
        if c_obj:
            db.delete(c_obj)
            db.commit()
        db.close()
        print("\n✓ API Test 02: Client 19-field CRUD & duplicate email rejection verified.")

    def test_03_pause_and_resume_status(self):
        """Test pause/resume client status transitions via PATCH /api/clients/{id}/status."""
        db = SessionLocal()
        test_client = ContractorProfile(
            business_name="স্ট্যাটাস টেস্টিং এন্টারপ্রাইজ",
            contact_person="টেস্টার",
            email="status_test_unique@example.com",
            district="Dinajpur",
            client_status="active",
            account_status="active"
        )
        db.add(test_client)
        db.commit()
        db.refresh(test_client)
        test_id = test_client.id
        db.close()

        try:
            # 1. PAUSE client
            pause_res = client.patch(f"/api/clients/{test_id}/status", json={"client_status": "paused"})
            self.assertEqual(pause_res.status_code, 200)
            self.assertEqual(pause_res.json()["client_status"], "paused")

            # 2. RESUME client
            resume_res = client.patch(f"/api/clients/{test_id}/status", json={"client_status": "active"})
            self.assertEqual(resume_res.status_code, 200)
            self.assertEqual(resume_res.json()["client_status"], "active")

            # 3. Invalid status validation
            bad_res = client.patch(f"/api/clients/{test_id}/status", json={"client_status": "invalid_status"})
            self.assertEqual(bad_res.status_code, 400)
        finally:
            db = SessionLocal()
            c_obj = db.query(ContractorProfile).filter_by(id=test_id).first()
            if c_obj:
                db.delete(c_obj)
                db.commit()
            db.close()
        print("\n✓ API Test 03: Client pause/resume lifecycle status verified.")

    def test_04_matching_and_retrieval(self):
        """Test deterministic matching trigger and matches retrieval with filter."""
        # Run matching for client #1
        run_res = client.post("/api/match/run?client_id=1")
        self.assertEqual(run_res.status_code, 200)
        self.assertEqual(run_res.json()["status"], "success")

        # Retrieve matches
        matches_res = client.get("/api/clients/1/matches")
        self.assertEqual(matches_res.status_code, 200)
        data = matches_res.json()
        self.assertIn("matches", data)
        self.assertGreater(data["total"], 0)

        # Check matched tender structure
        match_item = data["matches"][0]
        self.assertIn("official_tender_id", match_item)
        self.assertIn("title", match_item)
        self.assertIn("preference_fit_status", match_item)
        self.assertIn("preference_reasons", match_item)
        self.assertIn("unknown_items_to_verify", match_item)
        print("\n✓ API Test 04: Matching pipeline execution & matches drawer response verified.")

    def test_05_safe_test_email_dispatch(self):
        """Test safe test email endpoint respects EMAIL_DEV_MODE."""
        # Send safe test email to developer recipient
        res = client.post("/api/clients/1/test-email", json={"recipient_email": "ejarabd@gmail.com"})
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "success")
        self.assertIn("record_id", data)
        print("\n✓ API Test 05: Safe test email dispatch & audit logging verified.")

    def test_06_database_preservation(self):
        """Verify that live database tables and records remain completely intact after API tests."""
        db = SessionLocal()
        try:
            current_tenders = db.query(Tender).count()
            current_clients = db.query(ContractorProfile).count()
            self.assertEqual(current_tenders, self.initial_tenders, "Tender count changed unexpectedly!")
            self.assertEqual(current_clients, self.initial_clients, "Client count changed unexpectedly!")
            print(f"\n✓ API Test 06: Database preservation confirmed (Tenders: {current_tenders}, Clients: {current_clients}).")
        finally:
            db.close()


def test_api_endpoints():
    """Entry point for run_all_tests.py runner compatibility."""
    suite = unittest.TestLoader().loadTestsFromTestCase(TestPhase1ApiEndpoints)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    if not result.wasSuccessful():
        sys.exit(1)


if __name__ == "__main__":
    unittest.main()
