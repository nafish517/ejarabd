import os
import sys

# Ensure workspace root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import unittest
from datetime import datetime, timedelta
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
from backend.models import Tender, ContractorProfile, MatchAssessment
from backend.ingestion import (
    normalize_tender_payload,
    validate_tender_payload,
    ingest_single_tender,
    ingest_tenders_batch,
    filter_relevant_tenders,
    get_clean_tender_summary_for_ai
)
from backend.matching import evaluate_tender_for_contractor, run_matching_pipeline

class TestIngestionLayer(unittest.TestCase):
    def setUp(self):
        self.db = SessionLocal()
        self.client = TestClient(app)

    def tearDown(self):
        self.client.close()
        self.db.close()

    def test_1_parse_known_sample(self):
        """TEST 1: Known sample tender data (Dict and HTML) parses into valid structure"""
        print("\n--- Running TEST 1: Parse Known Sample Tender Data ---")
        sample_dict = {
            "tender_id": "eGP-2000001",
            "title": "দিনাজপুর বীরগঞ্জ সড়কের পুনর্নির্মাণ ও বিটুমিনাস সারফেসিং কাজ",
            "agency": "Local Government Engineering Department (LGED)",
            "procuring_entity_office": "উপজেলা প্রকৌশলীর কার্যালয়, বীরগঞ্জ, দিনাজপুর",
            "project_location_district": "Dinajpur",
            "category": "Road Construction",
            "estimated_value_bdt": "৳ ৪,৫০০,০০০", # বাংলা ও মুদ্রা চিহ্ন সহ
            "tender_security_bdt": "১,২০,০০০",
            "closing_date": "2026-11-20 14:00:00",
            "source_url": "https://eprocure.gov.bd/resources/sample-tenders/2000001",
            "raw_eligibility_text": "<p>ন্যূনতম ৩ বছরের অভিজ্ঞতা আবশ্যক।</p>"
        }

        norm = normalize_tender_payload(sample_dict)
        is_valid, errors = validate_tender_payload(norm)
        self.assertTrue(is_valid, f"Validation should succeed, errors: {errors}")
        self.assertEqual(norm["tender_id"], "eGP-2000001")
        self.assertEqual(norm["project_location_district"], "Dinajpur")
        self.assertEqual(norm["estimated_value_bdt"], 4500000.0)
        self.assertEqual(norm["tender_security_bdt"], 120000.0)
        self.assertIsInstance(norm["closing_date"], datetime)
        self.assertEqual(norm["closing_date"].year, 2026)
        # HTML tag should be cleaned in raw_eligibility_text
        self.assertNotIn("<p>", norm["raw_eligibility_text"])
        self.assertIn("ন্যূনতম ৩ বছরের অভিজ্ঞতা আবশ্যক", norm["raw_eligibility_text"])

        # Also test HTML snippet parsing
        sample_html = """
        <div class="tender-card" data-tender-id="eGP-HTML-999">
            <h2 class="tender-title">দিনাজপুর খানসামা ব্রিজের সংযোগ সড়ক সংস্কার</h2>
            <span class="agency">RHD</span>
            <span class="district">Dinajpur</span>
            <span class="category">Bridge & Road</span>
            <span class="estimated-value">৳ ২,৫০০,০০০</span>
            <span class="tender-security">৳ ৭৫,০০০</span>
            <span class="closing-date">2026-11-25 15:30:00</span>
            <a href="https://eprocure.gov.bd/notice/HTML-999">নোটিশ দেখুন</a>
            <div class="eligibility">হালনাগাদ ঠিকাদারি লাইসেন্স প্রযোজ্য।</div>
        </div>
        """
        html_norm = normalize_tender_payload(sample_html)
        is_valid_html, html_errors = validate_tender_payload(html_norm)
        self.assertTrue(is_valid_html, f"HTML parse validation failed: {html_errors}")
        self.assertEqual(html_norm["tender_id"], "eGP-HTML-999")
        self.assertEqual(html_norm["estimated_value_bdt"], 2500000.0)
        self.assertEqual(html_norm["tender_security_bdt"], 75000.0)
        self.assertEqual(html_norm["source_url"], "https://eprocure.gov.bd/notice/HTML-999")
        print("✓ TEST 1 Passed: Both Dict and HTML payload parsed with 100% accuracy.")

    def test_2_missing_data_no_invented_facts(self):
        """TEST 2: When project value is missing, parser leaves it None (no invented value)"""
        print("\n--- Running TEST 2: Missing Data Handling (No Invented Facts) ---")
        sample_no_val = {
            "tender_id": "eGP-2000002",
            "title": "দিনাজপুর উপশহর প্রাথমিক বিদ্যালয় ভবন মেরামত",
            "agency": "Education Engineering Department (EED)",
            "closing_date": "2026-11-15 13:00:00",
            "source_url": "https://eprocure.gov.bd/notice/2000002",
            "estimated_value_bdt": "উল্লেখ নেই", # Explicit missing indicator
            "tender_security_bdt": "৫০,০০০"
        }

        norm = normalize_tender_payload(sample_no_val)
        self.assertIsNone(norm["estimated_value_bdt"], "Missing project value MUST be None, never fabricated!")
        self.assertEqual(norm["tender_security_bdt"], 50000.0)

        # Ingest into DB and verify DB record
        res = ingest_single_tender(self.db, norm)
        self.assertEqual(res["status"], "success")

        self.db.expire_all()
        tender_db = self.db.query(Tender).filter_by(tender_id="eGP-2000002").first()
        self.assertIsNotNone(tender_db)
        self.assertIsNone(tender_db.estimated_value_bdt, "Database field estimated_value_bdt must be NULL/None!")
        print("✓ TEST 2 Passed: Missing budget correctly persisted as None; zero invented facts.")

    def test_3_security_vs_project_value_separation(self):
        """TEST 3: Tender security is NEVER saved as project value"""
        print("\n--- Running TEST 3: Security vs Project Value Separation ---")
        sample_security_only = {
            "tender_id": "eGP-2000003",
            "title": "বোচাগঞ্জ উপজেলা ড্রেনেজ লাইন সংস্কার",
            "agency": "LGED",
            "closing_date": "2026-11-18 14:00:00",
            "source_url": "https://eprocure.gov.bd/notice/2000003",
            "tender_security_bdt": 80000.0
            # estimated_value_bdt intentionally omitted
        }

        norm = normalize_tender_payload(sample_security_only)
        self.assertIsNone(norm["estimated_value_bdt"])
        self.assertEqual(norm["tender_security_bdt"], 80000.0)

        res = ingest_single_tender(self.db, norm)
        self.assertEqual(res["status"], "success")

        self.db.expire_all()
        tender_db = self.db.query(Tender).filter_by(tender_id="eGP-2000003").first()
        self.assertIsNotNone(tender_db)
        self.assertEqual(tender_db.tender_security_bdt, 80000.0)
        self.assertIsNone(tender_db.estimated_value_bdt, "estimated_value_bdt must not take tender_security_bdt value!")
        self.assertNotEqual(tender_db.tender_security_bdt, tender_db.estimated_value_bdt)
        print("✓ TEST 3 Passed: Tender security and project value strictly segregated.")

    def test_4_deduplication(self):
        """TEST 4: Ingesting the same tender twice produces exactly 1 record in database"""
        print("\n--- Running TEST 4: Deduplication Mechanism ---")
        sample_dup = {
            "tender_id": "eGP-DUP-100",
            "title": "দিনাজপুর চিরিরবন্দর কালভার্ট নির্মাণ কাজ",
            "agency": "LGED",
            "project_location_district": "Dinajpur",
            "closing_date": "2026-12-01 12:00:00",
            "estimated_value_bdt": 1800000.0,
            "source_url": "https://eprocure.gov.bd/notice/DUP-100"
        }

        # First ingestion
        res1 = ingest_single_tender(self.db, sample_dup)
        self.assertEqual(res1["status"], "success")
        self.assertIn(res1["action"], ["created", "updated"])

        # Count in DB
        self.db.expire_all()
        count_after_1 = self.db.query(Tender).filter_by(tender_id="eGP-DUP-100").count()
        self.assertEqual(count_after_1, 1)

        # Second ingestion with slightly updated title
        sample_dup_updated = dict(sample_dup)
        sample_dup_updated["title"] = "দিনাজপুর চিরিরবন্দর কালভার্ট নির্মাণ কাজ (সংশোধিত)"
        res2 = ingest_single_tender(self.db, sample_dup_updated, update_existing=True)
        self.assertEqual(res2["status"], "success")
        self.assertEqual(res2["action"], "updated")

        # Count must STILL be exactly 1
        self.db.expire_all()
        count_after_2 = self.db.query(Tender).filter_by(tender_id="eGP-DUP-100").count()
        self.assertEqual(count_after_2, 1, "Duplicate tender_id must NOT create a second record!")

        updated_record = self.db.query(Tender).filter_by(tender_id="eGP-DUP-100").first()
        self.assertEqual(updated_record.title, "দিনাজপুর চিরিরবন্দর কালভার্ট নির্মাণ কাজ (সংশোধিত)")
        print("✓ TEST 4 Passed: Deduplication verified. Same tender ingested twice resulted in exactly 1 record.")

    def test_5_multiple_tenders_batch_ingestion(self):
        """TEST 5: Ingest at least 10 sample tenders; verify count, IDs, titles, URLs"""
        print("\n--- Running TEST 5: Multiple Tenders Ingestion (10+ Items) ---")
        batch_samples = [
            {
                "tender_id": f"eGP-BATCH-30{i:02d}",
                "title": f"দিনাজপুর প্যাকেজ-{i}: বিভিন্ন গ্রামীণ সড়ক ও অবকাঠামো উন্নয়ন কাজ",
                "agency": "LGED",
                "procuring_entity_office": "নির্বাহী প্রকৌশলীর কার্যালয়, দিনাজপুর",
                "project_location_district": "Dinajpur",
                "category": "Road Construction",
                "estimated_value_bdt": 2000000.0 + (i * 500000.0),
                "tender_security_bdt": 50000.0 + (i * 10000.0),
                "closing_date": f"2026-11-{(10 + i):02d} 14:00:00",
                "source_url": f"https://eprocure.gov.bd/tenders/batch-30{i:02d}"
            }
            for i in range(1, 11) # 10 items
        ]

        # Use API endpoint POST /api/tenders/ingest
        res = self.client.post("/api/tenders/ingest", json={"tenders": batch_samples, "auto_match": False})
        self.assertEqual(res.status_code, 200, f"API ingest failed: {res.text}")
        data = res.json()
        self.assertEqual(data["status"], "success")
        ingest_data = data["data"]
        self.assertEqual(ingest_data["total"], 10)
        self.assertEqual(ingest_data["failed"], 0)

        # Verify in DB: all 10 exist with correct attributes
        self.db.expire_all()
        for sample in batch_samples:
            t = self.db.query(Tender).filter_by(tender_id=sample["tender_id"]).first()
            self.assertIsNotNone(t, f"Tender {sample['tender_id']} must exist in DB")
            self.assertEqual(t.title, sample["title"])
            self.assertEqual(t.source_url, sample["source_url"])
            self.assertEqual(t.estimated_value_bdt, sample["estimated_value_bdt"])
            self.assertEqual(t.tender_security_bdt, sample["tender_security_bdt"])

        print(f"✓ TEST 5 Passed: 10/10 batch tenders successfully ingested and verified with correct IDs and URLs.")

    def test_6_malformed_tender_handling(self):
        """TEST 6: Incomplete or malformed data does not crash application or corrupt DB"""
        print("\n--- Running TEST 6: Malformed / Incomplete Tender Handling ---")
        malformed_cases = [
            {}, # Completely empty
            {"tender_id": ""}, # Missing title & closing date
            {"title": "শুধু শিরোনাম আছে", "closing_date": "invalid-date-format"}, # Missing ID & invalid date
            "<html><body>Broken HTML with no tender info whatsoever</body></html>",
            {"tender_id": "eGP-VALID-FAIL-1", "title": "বৈধ কিন্তু তারিখ নেই", "closing_date": None}
        ]

        batch_result = ingest_tenders_batch(self.db, malformed_cases, auto_run_matching=False)
        self.assertIsInstance(batch_result, dict)
        self.assertEqual(batch_result["total"], len(malformed_cases))
        self.assertEqual(batch_result["failed"], len(malformed_cases), "All malformed inputs should safely fail validation")
        self.assertEqual(batch_result["created"], 0)

        # Database must still be alive and responsive
        contractor = self.db.query(ContractorProfile).first()
        self.assertIsNotNone(contractor, "Database must remain healthy and uncorrupted")
        print("✓ TEST 6 Passed: Malformed payloads safely rejected with zero crashes or DB corruption.")

    def test_7_database_integrity_preservation(self):
        """TEST 7: Seeded tenders are not corrupted or deleted by ingestion runs"""
        print("\n--- Running TEST 7: Seeded Database Integrity Preservation ---")
        seeded_ids = ["eGP-1092341", "eGP-1095582", "eGP-1088920"]
        for sid in seeded_ids:
            t = self.db.query(Tender).filter_by(tender_id=sid).first()
            self.assertIsNotNone(t, f"Original seeded tender {sid} must remain intact in DB!")
            self.assertTrue(len(t.title) > 10)
            self.assertIsNotNone(t.closing_date)
            self.assertTrue(t.source_url.startswith("https://eprocure.gov.bd"))

        # Verify pilot contractor profile is also 100% intact
        pilot = self.db.query(ContractorProfile).first()
        self.assertIsNotNone(pilot)
        self.assertIn("Dinajpur", pilot.preferred_districts)
        print("✓ TEST 7 Passed: All initial seeded fixtures and contractor profiles preserved intact.")

    def test_8_filtering_with_matching_pipeline(self):
        """TEST 8: Ingested tenders correctly interact with existing deterministic matching logic"""
        print("\n--- Running TEST 8: Filtering & Matching Pipeline Integration ---")
        # Ingest a good match for Dinajpur road contractor
        good_match = {
            "tender_id": "eGP-FIT-001",
            "title": "দিনাজপুর কোতয়ালী এলাকায় আরসিসি ড্রেন ও সড়ক নির্মাণ",
            "agency": "LGED",
            "project_location_district": "Dinajpur",
            "category": "Road Construction",
            "estimated_value_bdt": 6000000.0, # Within contractor's 10L - 1.5Cr range
            "closing_date": "2026-11-30 14:00:00",
            "source_url": "https://eprocure.gov.bd/notice/FIT-001"
        }

        # Ingest an outside match (different district and category)
        outside_match = {
            "tender_id": "eGP-OUT-002",
            "title": "সিলেট জেলার গোয়াইনঘাটে রাবার ড্যাম মেরামত",
            "agency": "BWDB",
            "project_location_district": "Sylhet",
            "category": "Water Resources",
            "estimated_value_bdt": 40000000.0, # Outside value range
            "closing_date": "2026-11-30 14:00:00",
            "source_url": "https://eprocure.gov.bd/notice/OUT-002"
        }

        ingest_single_tender(self.db, good_match)
        ingest_single_tender(self.db, outside_match)

        # Run matching
        processed = run_matching_pipeline(self.db)
        self.assertTrue(processed > 0)

        # Check evaluations
        pilot = self.db.query(ContractorProfile).first()
        t_good = self.db.query(Tender).filter_by(tender_id="eGP-FIT-001").first()
        t_out = self.db.query(Tender).filter_by(tender_id="eGP-OUT-002").first()

        ass_good = self.db.query(MatchAssessment).filter_by(contractor_id=pilot.id, tender_id=t_good.id).first()
        ass_out = self.db.query(MatchAssessment).filter_by(contractor_id=pilot.id, tender_id=t_out.id).first()

        self.assertIsNotNone(ass_good)
        self.assertIsNotNone(ass_out)

        self.assertEqual(ass_good.preference_fit_status, "fits", "Good Dinajpur road tender must be 'fits'")
        self.assertEqual(ass_out.preference_fit_status, "outside", "Sylhet water dam tender must be 'outside'")

        # Test deterministic relevant filter helper
        relevant = filter_relevant_tenders(self.db, pilot.id)
        relevant_ids = [r["tender_id"] for r in relevant]
        self.assertIn("eGP-FIT-001", relevant_ids, "Relevant filter must include fits tender")
        self.assertNotIn("eGP-OUT-002", relevant_ids, "Relevant filter must exclude outside tender")

        # Test AI token protection helper
        clean_ai_summary = get_clean_tender_summary_for_ai(t_good)
        self.assertIsInstance(clean_ai_summary, dict)
        self.assertNotIn("<", clean_ai_summary["clean_eligibility_requirements"], "AI summary must contain no raw HTML tags")
        self.assertEqual(clean_ai_summary["tender_id"], "eGP-FIT-001")

        print("✓ TEST 8 Passed: Filtering and matching integration verified. Candidate triage functions accurately.")

if __name__ == "__main__":
    unittest.main()
