import os
import sys

# Ensure workspace root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import unittest
from datetime import datetime
import httpx
import asyncio

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

class TestAIEvaluation(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.db = SessionLocal()

    def tearDown(self):
        self.client.close()
        self.db.close()

    def test_1_valid_ai_evaluation_response(self):
        """TEST 1: Run AI evaluation on a seeded assessment and verify contract"""
        print("\n--- Running TEST 1: Valid AI Response & Output Contract ---")
        assessment = self.db.query(MatchAssessment).first()
        self.assertIsNotNone(assessment, "Seeded assessment must exist")
        ass_id = assessment.id

        res = self.client.post(f"/api/assessments/{ass_id}/ai-evaluate")
        self.assertEqual(res.status_code, 200, f"Expected 200, got {res.status_code}: {res.text}")
        data = res.json()

        self.assertEqual(data["status"], "success")
        ass_data = data["assessment"]
        self.assertEqual(ass_data["id"], ass_id)
        self.assertIn(ass_data["preference_fit_status"], ["fits", "partial", "outside"])
        self.assertIn(ass_data["qualification_status"], ["meets_known_criteria", "does_not_meet", "unknown_needs_verification"])
        self.assertIsInstance(ass_data["preference_reasons"], list)
        self.assertIsInstance(ass_data["known_mismatches"], list)
        self.assertIsInstance(ass_data["unknown_items_to_verify"], list)
        self.assertIsInstance(ass_data["overall_fit_explanation_bn"], str)
        self.assertTrue(len(ass_data["overall_fit_explanation_bn"]) > 5, "Bengali explanation must not be empty")
        self.assertIn("ai_generated", ass_data)

        # Verify DB commit
        self.db.expire_all()
        db_ass = self.db.query(MatchAssessment).filter_by(id=ass_id).first()
        self.assertEqual(db_ass.overall_fit_explanation_bn, ass_data["overall_fit_explanation_bn"])
        print(f"✓ TEST 1 Passed: Assessment ID {ass_id} successfully evaluated (ai_generated: {ass_data['ai_generated']}).")

    def test_2_no_invented_project_value(self):
        """TEST 2: When tender estimated value is None, verify AI does not invent a value"""
        print("\n--- Running TEST 2: No Invented Project Value ---")
        # Tender 2 in seed data has estimated_value_bdt = None
        tender_no_budget = self.db.query(Tender).filter_by(estimated_value_bdt=None).first()
        self.assertIsNotNone(tender_no_budget, "Seeded tender without estimated value must exist")

        assessment = self.db.query(MatchAssessment).filter_by(tender_id=tender_no_budget.id).first()
        self.assertIsNotNone(assessment, f"Assessment for tender {tender_no_budget.tender_id} must exist")

        res = self.client.post(f"/api/assessments/{assessment.id}/ai-evaluate")
        self.assertEqual(res.status_code, 200)
        data = res.json()["assessment"]

        # Tender in DB must remain None (no fact fabrication in DB)
        self.db.expire_all()
        db_tender = self.db.query(Tender).filter_by(id=tender_no_budget.id).first()
        self.assertIsNone(db_tender.estimated_value_bdt, "Tender estimated_value_bdt must remain None in DB!")

        # Verify that missing budget is documented in unknown_items_to_verify or explanation
        all_text = " ".join(data["unknown_items_to_verify"]) + " " + data["overall_fit_explanation_bn"]
        has_missing_budget_flag = any(kw in all_text for kw in ["প্রাক্কলিত", "মূল্য", "বাজেট", "উল্লেখ নেই", "যাচাই"])
        self.assertTrue(has_missing_budget_flag, "Missing project value must be semantically marked as unknown / needs verification!")
        print("✓ TEST 2 Passed: Missing project value correctly treated as unknown / needs verification; no value invented.")

    def test_3_security_vs_project_value_distinction(self):
        """TEST 3: Verify tender security and project value are strictly distinct"""
        print("\n--- Running TEST 3: Security vs Project Value Distinction ---")
        tender = self.db.query(Tender).filter(Tender.estimated_value_bdt.isnot(None), Tender.tender_security_bdt.isnot(None)).first()
        self.assertIsNotNone(tender)

        self.assertNotEqual(tender.estimated_value_bdt, tender.tender_security_bdt)
        orig_estimated = tender.estimated_value_bdt
        orig_security = tender.tender_security_bdt

        assessment = self.db.query(MatchAssessment).filter_by(tender_id=tender.id).first()
        res = self.client.post(f"/api/assessments/{assessment.id}/ai-evaluate")
        self.assertEqual(res.status_code, 200)

        # Re-query tender to ensure neither field was corrupted or conflated
        self.db.expire_all()
        re_tender = self.db.query(Tender).filter_by(id=tender.id).first()
        self.assertEqual(re_tender.estimated_value_bdt, orig_estimated)
        self.assertEqual(re_tender.tender_security_bdt, orig_security)
        print("✓ TEST 3 Passed: Tender security and project value strictly separated and intact.")

    def test_4_missing_qualification_kept_in_unknown(self):
        """TEST 4: Missing eligibility information must be tracked in unknown_items_to_verify"""
        print("\n--- Running TEST 4: Missing Qualifications Tracked in Unknown Items ---")
        assessment = self.db.query(MatchAssessment).first()
        res = self.client.post(f"/api/assessments/{assessment.id}/ai-evaluate")
        self.assertEqual(res.status_code, 200)
        data = res.json()["assessment"]

        self.assertIsInstance(data["unknown_items_to_verify"], list)
        self.assertTrue(len(data["unknown_items_to_verify"]) > 0, "unknown_items_to_verify must capture items to verify")
        for item in data["unknown_items_to_verify"]:
            self.assertIsInstance(item, str)
            self.assertTrue(len(item.strip()) > 0)
        print(f"✓ TEST 4 Passed: {len(data['unknown_items_to_verify'])} items safely tracked in unknown_items_to_verify.")

    def test_5_fallback_when_ollama_offline(self):
        """TEST 5: Verify fallback engine operates safely and does not crash when Ollama is unreachable"""
        print("\n--- Running TEST 5: Fallback When Ollama Offline ---")
        mock_engine = LocalAIEngine(base_url="http://localhost:11439") # unreachable port
        contractor = self.db.query(ContractorProfile).first()
        tender = self.db.query(Tender).first()

        result = asyncio.run(mock_engine.evaluate_eligibility_ai(contractor, tender))
        self.assertIsInstance(result, dict)
        self.assertFalse(result["ai_generated"], "ai_generated must be False during fallback")
        self.assertIsNone(result["model_used"])
        self.assertIn("preference_fit_status", result)
        self.assertIn("qualification_status", result)
        self.assertIn("overall_fit_explanation_bn", result)
        print("✓ TEST 5 Passed: Fallback rule engine safely produced assessment with ai_generated=False.")

    def test_6_invalid_assessment_id_handling(self):
        """TEST 6: Call POST /api/assessments/999999/ai-evaluate and verify 404"""
        print("\n--- Running TEST 6: Invalid Assessment ID (404) ---")
        res = self.client.post("/api/assessments/999999/ai-evaluate")
        self.assertEqual(res.status_code, 404)
        data = res.json()
        self.assertIn("detail", data)
        self.assertEqual(data["detail"], "মূল্যায়ন রেকর্ড পাওয়া যায়নি")
        print("✓ TEST 6 Passed: Proper 404 returned without backend crash.")

    def test_7_data_integrity_preservation(self):
        """TEST 7: Verify all tender core fields remain 100% untouched before and after evaluation"""
        print("\n--- Running TEST 7: Data Integrity Preservation ---")
        assessment = self.db.query(MatchAssessment).first()
        tender = assessment.tender

        orig_title = tender.title
        orig_id = tender.tender_id
        orig_closing = tender.closing_date
        orig_url = tender.source_url
        orig_est = tender.estimated_value_bdt
        orig_sec = tender.tender_security_bdt

        res = self.client.post(f"/api/assessments/{assessment.id}/ai-evaluate")
        self.assertEqual(res.status_code, 200)

        self.db.expire_all()
        refreshed = self.db.query(Tender).filter_by(id=tender.id).first()
        self.assertEqual(refreshed.title, orig_title)
        self.assertEqual(refreshed.tender_id, orig_id)
        self.assertEqual(refreshed.closing_date, orig_closing)
        self.assertEqual(refreshed.source_url, orig_url)
        self.assertEqual(refreshed.estimated_value_bdt, orig_est)
        self.assertEqual(refreshed.tender_security_bdt, orig_sec)
        print("✓ TEST 7 Passed: Data integrity verified. Core tender facts are 100% unaltered.")

if __name__ == "__main__":
    unittest.main()
