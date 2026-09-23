import os
import sys
import time
import unittest
from unittest.mock import MagicMock, patch
from datetime import datetime
import httpx
from bs4 import BeautifulSoup

# Add root directory to sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(BASE_DIR)
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

# Windows কনসোলে UTF-8 এনকোডিং
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from backend.database import SessionLocal
from backend.models import Tender, ContractorProfile
from backend.ingestion import (
    clean_text,
    clean_numeric_value,
    clean_datetime_value,
    to_en_number,
    ingest_single_tender
)
from backend.egp_client import (
    EGPClient,
    EGPSessionError,
    EGP_SEARCH_SERVLET_URL,
    EGP_VIEW_TENDER_URL
)
from backend.egp_ingestion_service import (
    run_egp_sync,
    is_candidate_relevant_prefilter
)

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")


class TestEGPClient(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.listing_fixture_path = os.path.join(FIXTURES_DIR, "egp_listing_rows.html")
        cls.view_fixture_path = os.path.join(FIXTURES_DIR, "egp_view_tender_1336788.html")
        
        with open(cls.listing_fixture_path, "r", encoding="utf-8") as f:
            cls.listing_html = f.read()

        with open(cls.view_fixture_path, "r", encoding="utf-8") as f:
            cls.view_html = f.read()

    def setUp(self):
        self.db = SessionLocal()

    def tearDown(self):
        self.db.close()

    # 1. Listing parsing
    def test_1_listing_parsing(self):
        """1. লিস্টিং টেবিল থেকে টেন্ডার ফিল্ডসমূহ সঠিকভাবে পার্স করা"""
        tenders = EGPClient.parse_listing_html(self.listing_html)
        self.assertEqual(len(tenders), 10, "১০টি সারির ফিক্সচার থেকে ১০টি টেন্ডার পাওয়া উচিত")
        
        # Row 0: 1338179
        first = tenders[0]
        self.assertEqual(first["tender_id"], "1338179")
        self.assertEqual(first["reference_no"], "27.11.0000.304.27.303.26")
        self.assertIn("Hathazari", first["title"])
        self.assertEqual(first["procurement_nature"], "Physical Services")
        self.assertEqual(first["procurement_type"], "NCT")
        self.assertEqual(first["procurement_method"], "OTM")
        self.assertEqual(first["status"], "active")
        self.assertIn("1338179", first["source_url"])

        # Row 1: 1336788 (Paturia Ferry Ghat works)
        second = tenders[1]
        self.assertEqual(second["tender_id"], "1336788")
        self.assertEqual(second["reference_no"], "18.11.56.78.270.037.032.26")
        self.assertIn("Paturia", second["title"])
        self.assertEqual(second["procurement_nature"], "Works")
        self.assertEqual(second["status"], "active")

    # 2. Detailed tender parsing
    def test_2_detailed_tender_parsing(self):
        """2. ViewTender.jsp থেকে বিস্তারিত তথ্য পার্স করা"""
        details = EGPClient.parse_tender_details_html(self.view_html, tender_id="1336788")
        
        self.assertEqual(details["tender_id"], "1336788")
        self.assertIn("Prime Contractor", details["raw_eligibility_text"])
        self.assertIn("Geo-tubes", details["raw_eligibility_text"])
        self.assertEqual(details["tender_security_bdt"], 350000.0)
        self.assertEqual(details["procuring_entity_district"], "Manikganj")
        self.assertEqual(details["location"], "Paturia Ferry Ghat and Launch Ghat")
        self.assertEqual(details["document_price_bdt"], 2500.0)
        self.assertEqual(details["document_last_selling_date"].strftime("%Y-%m-%d"), "2026-10-06")
        self.assertEqual(details["opening_date"].strftime("%Y-%m-%d"), "2026-10-06")

    # 3. Bengali/BDT number normalization
    def test_3_bengali_number_normalization(self):
        """3. বাংলা সংখ্যা ও BDT কারেন্সি স্ট্রিং সঠিকভাবে ফ্লোটে রূপান্তর"""
        self.assertEqual(clean_numeric_value("৩,৫০,০০০.০০"), 350000.0)
        self.assertEqual(clean_numeric_value("BDT 2,000.00"), 2000.0)
        self.assertEqual(clean_numeric_value("৭৫,০০,০০০"), 7500000.0)
        self.assertEqual(to_en_number("১২৩৪৫৬৭৮৯০"), "1234567890")

    # 4. Missing estimated value
    def test_4_missing_estimated_value(self):
        """4. সরকারি বিধিমোতাবেক পাবলিক নোটিশে প্রাক্কলিত মূল্য না থাকলে estimated_value_bdt কঠোরভাবে None"""
        details = EGPClient.parse_tender_details_html(self.view_html, tender_id="1336788")
        self.assertIsNone(details.get("estimated_value_bdt"), "পাবলিক নোটিশে প্রাক্কলিত মূল্য না থাকলে None হতে হবে")

    # 5. Security/value separation
    def test_5_security_value_separation(self):
        """5. সিকিউরিটি অর্থকে কখনোই প্রাক্কলিত মূল্য হিসেবে অ্যাসাইন বা অনুমান করা যাবে না"""
        details = EGPClient.parse_tender_details_html(self.view_html, tender_id="1336788")
        self.assertEqual(details["tender_security_bdt"], 350000.0)
        self.assertIsNone(details.get("estimated_value_bdt"))
        self.assertNotEqual(details.get("estimated_value_bdt"), details.get("tender_security_bdt"))

    # 6. Tender ID extraction
    def test_6_tender_id_extraction(self):
        """6. নোটিশ লিংক ও তালিকা থেকে সঠিকভাবে টেন্ডার আইডি নিষ্কাশন"""
        html_snippet = """
        <tr>
          <td class="t-align-center">1</td>
          <td class="t-align-center">
            998877,<br/>
            REF/LGED/2026,<br/>
            <label>Live</label>
          </td>
          <td>
            <form id="viewtenderform_0">
              <input type="hidden" name="id" value="998877" />
              <a href="javascript:viewTender('998877')">Test Road Construction</a>
            </form>
          </td>
          <td>LGED Dinajpur</td>
          <td>NCT, OTM</td>
          <td>21-Mar-2026, 05-Apr-2026</td>
        </tr>
        """
        rows = EGPClient.parse_listing_html(html_snippet)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["tender_id"], "998877")
        self.assertEqual(rows[0]["reference_no"], "REF/LGED/2026")

    # 7. Pagination logic
    def test_7_pagination_logic(self):
        """7. পেজিনেশন লজিক: পৃষ্ঠা শেষ হলে বা কোনো নতুন রেকর্ড না থাকলে থামবে"""
        client = EGPClient(delay_min=0.0, delay_max=0.0)

        page1_tenders = [
            {"tender_id": f"T{i}", "title": f"Tender {i}", "published_date": "2026-03-21", "closing_date": "2026-04-05"}
            for i in range(1, 6)
        ]
        page2_tenders = [
            {"tender_id": f"T{i}", "title": f"Tender {i}", "published_date": "2026-03-21", "closing_date": "2026-04-05"}
            for i in range(6, 11)
        ]

        def mock_search_page(page, page_size, **kwargs):
            if page == 1:
                return page1_tenders
            elif page == 2:
                return page2_tenders
            return []

        client._search_page_raw = MagicMock(side_effect=mock_search_page)

        all_tenders = client.search_tenders(max_pages=5, page_size=5)
        self.assertEqual(len(all_tenders), 10)
        self.assertEqual(client._search_page_raw.call_count, 3)  # Page 1, Page 2, Page 3 (empty -> stop)

    # 8. Duplicate tender IDs
    def test_8_duplicate_tender_ids(self):
        """8. বিভিন্ন পৃষ্ঠায় ডুপ্লিকেট টেন্ডার আইডি আসলে ফিল্টার করে ইউনিক রাখা"""
        client = EGPClient(delay_min=0.0, delay_max=0.0)

        page1_tenders = [{"tender_id": "T1", "title": "A"}, {"tender_id": "T2", "title": "B"}]
        page2_tenders = [{"tender_id": "T2", "title": "B duplicate"}, {"tender_id": "T3", "title": "C"}]

        def mock_search_page(page, page_size, **kwargs):
            if page == 1:
                return page1_tenders
            elif page == 2:
                return page2_tenders
            return []

        client._search_page_raw = MagicMock(side_effect=mock_search_page)

        all_tenders = client.search_tenders(max_pages=3, page_size=2)
        self.assertEqual(len(all_tenders), 3)
        ids = [t["tender_id"] for t in all_tenders]
        self.assertEqual(ids, ["T1", "T2", "T3"])

    # 9. Malformed response handling
    def test_9_malformed_response(self):
        """9. ত্রুটিপূর্ণ বা অসম্পূর্ণ HTML হ্যান্ডলিং"""
        malformed_html = "<div><p>Broken content without table or columns</p></div>"
        res = EGPClient.parse_listing_html(malformed_html)
        self.assertEqual(res, [])

        details = EGPClient.parse_tender_details_html("<html><body>Empty</body></html>", tender_id="000")
        self.assertEqual(details["tender_id"], "000")
        self.assertIsNone(details.get("tender_security_bdt"))

    # 10. Session timeout handling
    def test_10_session_timeout_handling(self):
        """10. সেশন টাইমআউট সনাক্তকরণ ও রিকভারি নিশ্চিতকরণ"""
        client = EGPClient(delay_min=0.0, delay_max=0.0)
        
        timeout_html = "<html><head><title>Session Expired</title></head><body>Your session has been expired. Please re-login.</body></html>"
        self.assertTrue(client.is_session_timed_out(timeout_html, 200))
        self.assertTrue(client.is_session_timed_out("", 302))

        init_mock = MagicMock()
        client.init_session = init_mock
        client.recover_session_if_needed()
        init_mock.assert_called_once()

    # 11. Retry limit
    def test_11_retry_limit(self):
        """11. নেটওয়ার্ক ব্যর্থতায় নির্ধারিত রিট্রাই সংখ্যা (max_retries) অতিক্রম না করা"""
        client = EGPClient(delay_min=0.0, delay_max=0.0, max_retries=2)
        client.session_initialized = True
        
        # Mock client.client.request to fail
        client.client.request = MagicMock(side_effect=httpx.ConnectError("Connection refused"))

        with self.assertRaises(httpx.HTTPError):
            client._safe_request("GET", "https://www.eprocure.gov.bd/fail")
        
        # 1 initial + 2 retries = 3 calls
        self.assertEqual(client.client.request.call_count, 3)

    # 12. Rate-limit configuration
    def test_12_rate_limit_configuration(self):
        """12. নম্র ক্রলিংয়ের জন্য কনফিগারযোগ্য বিলম্ব (Rate Limiting) যাচাই"""
        client = EGPClient(delay_min=0.05, delay_max=0.1)
        self.assertEqual(client.delay_min, 0.05)
        self.assertEqual(client.delay_max, 0.1)

        client.polite_delay() # Prime last_request_time
        t0 = time.time()
        client.polite_delay()
        elapsed = time.time() - t0
        self.assertGreaterEqual(elapsed, 0.04)

    # 13. Failed individual tender does not crash batch
    def test_13_failed_tender_does_not_crash_batch(self):
        """13. একক কোনো টেন্ডার বিস্তারিত আনতে ব্যর্থ হলে সম্পূর্ণ ব্যাচ ক্র্যাশ করবে না"""
        client = EGPClient(delay_min=0.0, delay_max=0.0)

        # Mock search returning 3 tenders
        mock_listings = [
            {"tender_id": "1001", "title": "Tender 1001", "procurement_nature": "Works", "published_date": "2026-03-21", "closing_date": "2026-04-05", "agency": "LGED"},
            {"tender_id": "1002", "title": "Tender 1002", "procurement_nature": "Works", "published_date": "2026-03-21", "closing_date": "2026-04-05", "agency": "LGED"},
            {"tender_id": "1003", "title": "Tender 1003", "procurement_nature": "Works", "published_date": "2026-03-21", "closing_date": "2026-04-05", "agency": "LGED"},
        ]
        client.search_tenders = MagicMock(return_value=mock_listings)

        # Mock get_tender_details: fail for 1002, succeed for 1001 & 1003
        def mock_details(t_id):
            if t_id == "1002":
                raise httpx.RequestError("Network glitch on detail view")
            return {
                "tender_id": t_id,
                "eligibility_criteria": "LGED Registered",
                "raw_eligibility_text": "LGED Registered",
                "tender_security_bdt": 50000.0,
                "procuring_entity_district": "Dinajpur",
                "location": "Dinajpur Sadar"
            }

        client.get_tender_details = MagicMock(side_effect=mock_details)

        stats = run_egp_sync(
            db=self.db,
            client=client,
            page_size=3,
            max_pages=1,
            prefilter=False,
            auto_match=False
        )

        self.assertEqual(stats["listings_discovered"], 3)
        self.assertEqual(stats["details_fetched"], 2)
        self.assertEqual(stats["failed_details_count"], 1)
        failed_ids = [f["tender_id"] for f in stats["failed_details"]]
        self.assertIn("1002", failed_ids)
        self.assertGreaterEqual(stats["successfully_ingested"], 2)

    # 14. Ingestion integration
    def test_14_ingestion_integration(self):
        """14. e-GP থেকে সংগৃহীত ও পার্সকৃত টেন্ডারকে ingestion.py এর মাধ্যমে ডাটাবেজে সংরক্ষণ"""
        listing = EGPClient.parse_listing_html(self.listing_html)[1] # 1336788
        details = EGPClient.parse_tender_details_html(self.view_html, tender_id="1336788")
        
        # Merge details into listing
        combined = {**listing, **details}
        combined["source_portal"] = "e-GP"

        res = ingest_single_tender(self.db, combined)
        self.assertEqual(res["status"], "success")
        self.assertIn(res["action"], ["inserted", "updated"])
        
        tender_obj = self.db.query(Tender).filter_by(tender_id="1336788").first()
        self.assertIsNotNone(tender_obj)
        self.assertEqual(tender_obj.tender_id, "1336788")
        self.assertEqual(tender_obj.category, "Works")
        self.assertEqual(tender_obj.tender_security_bdt, 350000.0)
        self.assertIsNone(tender_obj.estimated_value_bdt)
        self.assertEqual(tender_obj.project_location_district, "Manikganj")

    # 15. End-to-end fixture batch
    def test_15_end_to_end_fixture_batch(self):
        """15. ফিক্সচার ব্যবহার করে সম্পূর্ণ ব্যাচ সিঙ্ক পাইপলাইনের এন্ড-টু-এন্ড যাচাই"""
        client = EGPClient(delay_min=0.0, delay_max=0.0)
        
        listings = EGPClient.parse_listing_html(self.listing_html)
        client.search_tenders = MagicMock(return_value=listings)

        details_1336788 = EGPClient.parse_tender_details_html(self.view_html, tender_id="1336788")
        def mock_get_details(t_id):
            res = dict(details_1336788)
            res["tender_id"] = t_id
            return res

        client.get_tender_details = MagicMock(side_effect=mock_get_details)

        stats = run_egp_sync(
            db=self.db,
            client=client,
            max_pages=1,
            page_size=10,
            prefilter=False,
            auto_match=True
        )

        self.assertEqual(stats["listings_discovered"], 10)
        self.assertEqual(stats["unique_tenders"], 10)
        self.assertEqual(stats["details_fetched"], 10)
        self.assertEqual(stats["failed_details_count"], 0)
        self.assertGreaterEqual(stats["successfully_ingested"], 10)

    # 16. Small conservative live smoke test
    def test_16_live_smoke_test(self):
        """16. লাইভ e-GP পোর্টালে একটি ছোট ও নিরাপদ স্মোক টেস্ট (1 page, page_size=2)"""
        print("\n--- Running TEST 16: Conservative Live e-GP Smoke Test ---")
        client = EGPClient(delay_min=1.0, delay_max=1.5, timeout=20.0)
        try:
            client.init_session()
            self.assertTrue(client.has_active_session, "e-GP সেশন সক্রিয় হতে হবে")

            # Search 1 page with page_size=2 for Works
            results = client.search_tenders(
                procurement_nature="2",
                max_pages=1,
                page_size=2
            )
            print(f"Live search returned {len(results)} live tenders.")
            self.assertGreater(len(results), 0, "লাইভ সার্চ থেকে অন্তত ১টি টেন্ডার পাওয়া উচিত")
            
            first = results[0]
            print(f"Live tender ID: {first['tender_id']}, Title: {first['title'][:60]}...")
            self.assertTrue(first["tender_id"].isdigit())

            # Fetch details for the first live tender
            details = client.get_tender_details(first["tender_id"])
            print(f"Fetched details for {first['tender_id']}: district={details.get('procuring_entity_district')}, security={details.get('tender_security_bdt')}")
            self.assertEqual(details["tender_id"], first["tender_id"])
            self.assertIsNone(details.get("estimated_value_bdt"), "Estimated value must remain None")
            print("--- Live Smoke Test Passed Successfully! ---")
        except (httpx.ConnectError, httpx.TimeoutException) as net_err:
            print(f"Warning: Live e-GP portal network unreachable or timed out ({net_err}). Skipping live assertion.")
        finally:
            client.close()


if __name__ == "__main__":
    unittest.main()
