import os
import sys
import unittest
from fastapi.testclient import TestClient

# Add project root and backend to sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.main import app
from backend.database import get_db, SessionLocal
from backend.models import ContractorProfile, Tender

client = TestClient(app)

class TestClientEndpoints(unittest.TestCase):
    def test_01_health(self):
        res = client.get("/api/health")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "healthy")

    def test_02_list_clients(self):
        res = client.get("/api/clients")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIsInstance(data, list)
        self.assertGreaterEqual(len(data), 1)
        # Check pilot client is present
        pilot = next((c for c in data if c["id"] == 1), None)
        self.assertIsNotNone(pilot)
        self.assertIn("Dinajpur", pilot["preferred_districts"])

    def test_03_create_and_duplicate_prevention(self):
        test_email = "unique_phase1_test@example.com"
        payload = {
            "business_name": "ইউনিক ফেজ ১ কন্সট্রাকশন",
            "contact_person": "মোঃ জামান হোসেন",
            "email": test_email,
            "phone": "+8801700112233",
            "preferred_language": "bn",
            "preferred_districts": ["Dinajpur", "Rangpur"],
            "preferred_upazilas": ["Birganj"],
            "work_categories": ["Civil Works", "Road Construction"],
            "preferred_agencies": ["LGED", "RHD"],
            "min_project_value_bdt": 2000000.0,
            "max_project_value_bdt": 15000000.0,
            "years_of_experience": 12,
            "previous_project_types": ["Roads", "Bridges"],
            "similar_work_experience": "১০ কোটি টাকার সড়ক কাজ সম্পন্ন",
            "approx_annual_turnover_bdt": 25000000.0,
            "available_equipment": ["Roller", "Excavator", "Mixer"],
            "available_manpower": ["2 Project Engineers", "10 Technicians"],
            "licenses_certifications": ["Trade License 2026", "TIN Updated"],
            "excluded_areas_or_categories": ["Drainage"],
            "notification_preference": "daily_email",
            "client_status": "active"
        }

        # First creation must succeed
        res = client.post("/api/clients", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "success")
        new_id = data["client"]["id"]
        self.assertEqual(data["client"]["years_of_experience"], 12)
        self.assertEqual(data["client"]["preferred_upazilas"], ["Birganj"])

        # Duplicate email creation MUST be rejected with HTTP 400
        dup_res = client.post("/api/clients", json=payload)
        self.assertEqual(dup_res.status_code, 400)
        self.assertIn("ইতোমধ্যে", dup_res.json()["detail"])

        # Test pause status
        pause_res = client.patch(f"/api/clients/{new_id}/status", json={"client_status": "paused"})
        self.assertEqual(pause_res.status_code, 200)
        self.assertEqual(pause_res.json()["client_status"], "paused")

        # Test resume status
        resume_res = client.patch(f"/api/clients/{new_id}/status", json={"client_status": "active"})
        self.assertEqual(resume_res.status_code, 200)
        self.assertEqual(resume_res.json()["client_status"], "active")

        # Clean up created test client
        db = SessionLocal()
        created_client = db.query(ContractorProfile).filter_by(id=new_id).first()
        if created_client:
            db.delete(created_client)
            db.commit()
        db.close()

    def test_04_matching_and_client_matches(self):
        # Trigger matching for pilot client #1
        res = client.post("/api/match/run?client_id=1")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "success")

        # Retrieve matches
        matches_res = client.get("/api/clients/1/matches")
        self.assertEqual(matches_res.status_code, 200)
        matches_data = matches_res.json()
        self.assertIn("matches", matches_data)
        self.assertGreater(matches_data["total"], 0)

    def test_05_test_email_dispatch(self):
        # Trigger test email for client #1 (in dev mode, it safely suppresses real dispatch or delivers to SAFE_TEST_EMAIL)
        res = client.post("/api/clients/1/test-email", json={"recipient_email": "ejarabd@gmail.com"})
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "success")

if __name__ == "__main__":
    unittest.main()
