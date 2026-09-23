import os
import sys

# Ensure workspace root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import unittest
from datetime import datetime
import httpx

# Windows কনসোলে UTF-8 এনকোডিং
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from fastapi.testclient import TestClient
from backend.main import app
from backend.database import SessionLocal
from backend.models import Tender, NotificationDraft, ContractorProfile, MatchAssessment
from backend.ai_engine import LocalAIEngine

class TestMilestone3Backend(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.db = SessionLocal()

    def tearDown(self):
        self.client.close()
        self.db.close()

    def test_1_ai_status(self):
        """Test 1: Call GET /api/ai/status and verify response structure and safety"""
        print("\n--- Running Test 1: AI Status ---")
        res = self.client.get("/api/ai/status")
        self.assertEqual(res.status_code, 200, f"Expected 200, got {res.status_code}")
        data = res.json()
        self.assertIsInstance(data, dict)
        self.assertIn("is_available", data)
        self.assertIn("server", data)
        self.assertIn("installed_models", data)
        self.assertIn("active_model", data)
        self.assertIn("gpu_accelerated", data)
        print(f"✓ AI Status Test Passed. Server: {data['server']}, is_available: {data['is_available']}")

    def test_2_invalid_draft_handling(self):
        """Test 2: Call POST /api/drafts/999999/ai-polish and verify proper 404"""
        print("\n--- Running Test 2: Invalid Draft Handling ---")
        res = self.client.post("/api/drafts/999999/ai-polish")
        self.assertEqual(res.status_code, 404, f"Expected 404 for non-existent draft, got {res.status_code}")
        data = res.json()
        self.assertIn("detail", data)
        self.assertEqual(data["detail"], "বার্তার ড্রাফট পাওয়া যায়নি")
        print("✓ Invalid Draft Handling Test Passed (Proper 404 returned without crashing).")

    def test_3_and_4_existing_draft_and_data_integrity(self):
        """Test 3 & 4: Call POST /api/drafts/{real_id}/ai-polish and verify data integrity"""
        print("\n--- Running Test 3 & 4: Existing Draft Polish & Data Integrity ---")
        draft = self.db.query(NotificationDraft).first()
        self.assertIsNotNone(draft, "At least one draft must exist in seed data")
        draft_id = draft.id
        tender = draft.tender

        # Capture original tender fields before polish
        orig_title = tender.title
        orig_tender_id = tender.tender_id
        orig_closing_date = tender.closing_date
        orig_source_url = tender.source_url
        orig_estimated_value = tender.estimated_value_bdt
        orig_security = tender.tender_security_bdt

        res = self.client.post(f"/api/drafts/{draft_id}/ai-polish")
        self.assertEqual(res.status_code, 200, f"Expected 200, got {res.status_code}: {res.text}")
        data = res.json()

        # Verify response structure
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["draft_id"], draft_id)
        self.assertIn("draft_message_bn", data)
        self.assertTrue(len(data["draft_message_bn"]) > 20, "Polished draft message should not be empty")
        self.assertIn("ai_generated", data)

        # Verify DB commit
        self.db.expire_all()
        updated_draft = self.db.query(NotificationDraft).filter_by(id=draft_id).first()
        self.assertEqual(updated_draft.draft_message_bn, data["draft_message_bn"])

        # TEST 4: DATA INTEGRITY CHECKS
        updated_tender = self.db.query(Tender).filter_by(id=tender.id).first()
        self.assertEqual(updated_tender.title, orig_title, "Tender title must NOT change!")
        self.assertEqual(updated_tender.tender_id, orig_tender_id, "Tender ID must NOT change!")
        self.assertEqual(updated_tender.closing_date, orig_closing_date, "Tender closing date must NOT change!")
        self.assertEqual(updated_tender.source_url, orig_source_url, "Tender source URL must NOT change!")
        self.assertEqual(updated_tender.estimated_value_bdt, orig_estimated_value, "Tender estimated value must NOT change!")
        self.assertEqual(updated_tender.tender_security_bdt, orig_security, "Tender security must NOT change!")

        print(f"✓ Existing Draft Test Passed (Draft ID: {draft_id}, ai_generated: {data['ai_generated']}).")
        print("✓ Data Integrity Test Passed (All core tender attributes are strictly preserved).")

    def test_5_fallback_when_ollama_unavailable(self):
        """Test 5: Verify fallback engine operates seamlessly when Ollama is unavailable"""
        print("\n--- Running Test 5: Fallback When Ollama Unavailable ---")
        import asyncio

        # Create engine pointing to a guaranteed non-existent port (e.g. 11439)
        mock_engine = LocalAIEngine(base_url="http://localhost:11439")

        # 1. Test status fallback
        status = asyncio.run(mock_engine.get_status())
        self.assertFalse(status["is_available"])
        self.assertIn("Fallback", status["server"])

        # 2. Test polish fallback
        contractor = self.db.query(ContractorProfile).first()
        tender = self.db.query(Tender).first()
        assessment_data = {
            "preference_fit_status": "fits",
            "preference_reasons": ["কাজের এলাকা দিনাজপুর"],
            "qualification_status": "meets_known_criteria",
            "known_mismatches": [],
            "unknown_items_to_verify": ["লাইসেন্স হালনাগাদ"],
            "overall_fit_explanation_bn": "টেস্ট ব্যাখ্যা"
        }

        polish_result = asyncio.run(mock_engine.polish_whatsapp_draft_ai(
            contractor=contractor,
            tender=tender,
            assessment_data=assessment_data
        ))

        self.assertIsInstance(polish_result, dict)
        self.assertFalse(polish_result["ai_generated"], "ai_generated must be False during fallback")
        self.assertIsNone(polish_result["model_used"])
        self.assertIn("আসসালামু আলাইকুম", polish_result["draft_message_bn"])
        self.assertTrue(len(polish_result["draft_message_bn"]) > 50)
        print("✓ Fallback Engine Test Passed (Safe fallback executed, ai_generated=False, valid Bengali template returned).")

if __name__ == "__main__":
    unittest.main()
