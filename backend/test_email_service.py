"""
Automated Unit and Integration Tests for EjaraBD Email Infrastructure.

Covers:
- Configuration handling (defaults, env overrides, missing config)
- Bengali email template rendering & zero-hallucination guarantees
- SMTP provider abstraction with mocked smtplib (success, auth error, connection error)
- MockEmailProvider for offline hermetic testing
- FastAPI endpoints (POST /api/email/test, POST /api/tenders/{tender_id}/email-test)

NEVER sends real emails. Uses mocked transports exclusively.
"""

import sys
import os

# Ensure workspace root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime
import smtplib
import socket

# Ensure UTF-8 output on Windows consoles
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from fastapi.testclient import TestClient
from backend.main import app
from backend.database import SessionLocal
from backend.models import Tender, ContractorProfile, MatchAssessment, NotificationDraft
from backend.email_service import (
    SMTPEmailProvider,
    MockEmailProvider,
    EmailSendResult,
    get_email_provider,
    set_email_provider
)
from backend.email_templates import (
    render_tender_notification_email,
    FALLBACK_VALUE
)


class TestEmailConfiguration(unittest.TestCase):
    """Test 1: Email configuration loading, defaults, and missing config detection."""

    def test_default_configuration(self):
        """Verify standard SMTP defaults when parameters are omitted."""
        provider = SMTPEmailProvider(host="", from_email="")
        self.assertFalse(provider.is_configured())
        self.assertEqual(provider.port, 587)
        self.assertTrue(provider.use_tls)
        self.assertEqual(provider.timeout, 10)
        self.assertEqual(provider.from_name, "EjaraBD")

    def test_valid_configuration(self):
        """Verify valid provider configuration when parameters are provided."""
        provider = SMTPEmailProvider(
            host="smtp.example.com",
            port=587,
            username="user@example.com",
            password="secret-password",
            from_email="notifications@ejarabd.com",
            from_name="EjaraBD Alerts",
            use_tls=True,
            timeout=15
        )
        self.assertTrue(provider.is_configured())
        self.assertEqual(provider.host, "smtp.example.com")
        self.assertEqual(provider.port, 587)
        self.assertEqual(provider.from_email, "notifications@ejarabd.com")
        self.assertEqual(provider.from_name, "EjaraBD Alerts")
        self.assertEqual(provider.timeout, 15)

    def test_environment_variable_loading(self):
        """Verify environment variables are appropriately recognized."""
        env_vars = {
            "SMTP_HOST": "mail.customserver.net",
            "SMTP_PORT": "465",
            "SMTP_USERNAME": "testuser",
            "SMTP_PASSWORD": "testpassword",
            "SMTP_FROM_EMAIL": "test@customserver.net",
            "SMTP_FROM_NAME": "EjaraBD Mailer",
            "SMTP_USE_TLS": "false",
            "SMTP_TIMEOUT": "20"
        }
        with patch.dict(os.environ, env_vars, clear=False):
            provider = SMTPEmailProvider()
            self.assertTrue(provider.is_configured())
            self.assertEqual(provider.host, "mail.customserver.net")
            self.assertEqual(provider.port, 465)
            self.assertEqual(provider.from_email, "test@customserver.net")
            self.assertEqual(provider.from_name, "EjaraBD Mailer")
            self.assertFalse(provider.use_tls)
            self.assertEqual(provider.timeout, 20)

    def test_missing_config_fails_gracefully(self):
        """Verify unconfigured provider returns structured failure without crashing."""
        provider = SMTPEmailProvider(host="", from_email="")
        res = provider.send_email(
            to_email="contractor@example.com",
            subject="Test",
            html_body="<p>Test</p>"
        )
        self.assertFalse(res.success)
        self.assertEqual(res.error_category, "config_error")
        self.assertIn("কনফিগার", res.message)


class TestEmailTemplates(unittest.TestCase):
    """Test 2: Bengali email template rendering & zero-hallucination rules."""

    def test_complete_tender_rendering(self):
        """Verify complete tender renders all fields in proper Bengali format."""
        mock_tender = {
            "title": "দিনাজপুর বীরগঞ্জ সড়কের উন্নয়ন ও পুনর্বাসন কাজ",
            "tender_id": "1045231",
            "agency": "LGED",
            "procuring_entity_office": "নির্বাহী প্রকৌশলীর কার্যালয়, দিনাজপুর",
            "project_location_district": "Dinajpur",
            "project_location_details": "বীরগঞ্জ",
            "publication_date": datetime(2026, 10, 1, 10, 0),
            "closing_date": datetime(2026, 11, 15, 14, 0),
            "tender_security_bdt": 350000.0,
            "source_url": "https://www.eprocure.gov.bd/resources/sample/1045231"
        }
        mock_contractor = {
            "business_name": "মেসার্স হক ট্রেডার্স"
        }
        mock_assessment = {
            "overall_fit_explanation_bn": "দিনাজপুর জেলায় সড়ক সংস্কারের পূর্ব অভিজ্ঞতার সাথে এটি শতভাগ মিলে যায়।",
            "unknown_items_to_verify": ["শিডিউল ক্রয় করে টার্নওভার শর্ত যাচাই করতে হবে।"],
            "known_mismatches": []
        }

        subject, html_body, text_body = render_tender_notification_email(
            tender=mock_tender,
            contractor=mock_contractor,
            assessment=mock_assessment
        )

        # Subject check
        self.assertEqual(subject, "নতুন টেন্ডার — দিনাজপুর বীরগঞ্জ সড়কের উন্নয়ন ও পুনর্বাসন কাজ")

        # Core facts in HTML and Plain Text
        for body in (html_body, text_body):
            self.assertIn("1045231", body)
            self.assertIn("LGED", body)
            self.assertIn("Dinajpur", body)
            self.assertIn("15-11-2026", body)
            self.assertIn("350,000", body)
            self.assertIn("https://www.eprocure.gov.bd/resources/sample/1045231", body)
            self.assertIn("দিনাজপুর জেলায় সড়ক সংস্কারের", body)
            self.assertIn("টার্নওভার শর্ত যাচাই করতে হবে", body)

        # Anti-hallucination: Ensure tender security is NOT claimed as project value
        self.assertNotIn("প্রকল্পের প্রাক্কলিত মূল্য: ৳ 350,000", html_body)
        self.assertIn("টেন্ডার সিকিউরিটি", html_body)
        self.assertIn("টেন্ডার সিকিউরিটি", text_body)

    def test_missing_fields_fallback_to_unknown(self):
        """Verify that any missing attribute falls back strictly to 'অজ্ঞাত / যাচাই প্রয়োজন'."""
        minimal_tender = {
            "title": None,
            "tender_id": "",
            "agency": None,
            "procuring_entity_office": None,
            "project_location_district": None,
            "project_location_details": None,
            "publication_date": None,
            "closing_date": None,
            "tender_security_bdt": None,
            "source_url": None
        }

        subject, html_body, text_body = render_tender_notification_email(
            tender=minimal_tender,
            contractor=None,
            assessment=None
        )

        self.assertEqual(subject, f"নতুন টেন্ডার — {FALLBACK_VALUE}")
        self.assertIn(FALLBACK_VALUE, html_body)
        self.assertIn(FALLBACK_VALUE, text_body)

        # Ensure no arbitrary values were fabricated
        self.assertNotIn("undefined", html_body)
        self.assertNotIn("None", html_body)
        self.assertNotIn("null", html_body)

    def test_zero_hallucination_security_not_project_value(self):
        """Explicitly verify that security money is never treated as project value."""
        tender = {
            "title": "কালভার্ট নির্মাণ",
            "tender_id": "999888",
            "tender_security_bdt": 50000.0,
            "estimated_value_bdt": None  # Unknown estimated value
        }

        _, html_body, text_body = render_tender_notification_email(tender=tender)

        # Security must be displayed under security label
        self.assertIn("50,000", html_body)
        # Never invent 50,000 * 20 or project value = 50,000
        self.assertNotIn("প্রাক্কলিত মূল্য: ৳ 50,000", html_body)
        self.assertNotIn("প্রাক্কলিত বাজেট: ৳ 50,000", text_body)

    def test_procurement_nature_rendering(self):
        """Verify procurement nature/category is cleanly mapped to Bengali in email."""
        tender = {
            "title": "রাস্তা সংস্কার",
            "tender_id": "888777",
            "category": "Works",
            "procurement_method": "OTM",
            "closing_date": "2026-12-01 14:00:00"
        }
        _, html_body, text_body = render_tender_notification_email(tender=tender)
        self.assertIn("নির্মাণ কাজ (Works)", html_body)
        self.assertIn("OTM", html_body)
        self.assertIn("নির্মাণ কাজ (Works)", text_body)
        self.assertIn("OTM", text_body)

    def test_real_tender_from_db_rendering(self):
        """Verify rendering a real tender from the database produces complete email without errors."""
        db = SessionLocal()
        try:
            real_tender = db.query(Tender).filter(Tender.is_synthetic == False).first()
            if not real_tender:
                real_tender = db.query(Tender).first()
            self.assertIsNotNone(real_tender)

            subject, html_body, text_body = render_tender_notification_email(tender=real_tender)
            self.assertIn("নতুন টেন্ডার", subject)
            self.assertIn(str(real_tender.tender_id), html_body)
            self.assertIn(str(real_tender.tender_id), text_body)
            self.assertIn("ইজারাবিডি", html_body)
            self.assertIn("e-GP", html_body)
        finally:
            db.close()


class TestSMTPEmailProvider(unittest.TestCase):
    """Test 3: SMTPEmailProvider with mocked smtplib (No real emails sent)."""

    def setUp(self):
        self.provider = SMTPEmailProvider(
            host="smtp.testserver.com",
            port=587,
            username="testuser",
            password="secretpassword",
            from_email="noreply@ejarabd.com",
            from_name="EjaraBD",
            use_tls=True,
            timeout=5
        )

    @patch("smtplib.SMTP")
    def test_successful_smtp_send(self, mock_smtp_cls):
        """Verify successful TLS email delivery workflow."""
        mock_server = MagicMock()
        mock_smtp_cls.return_value = mock_server

        result = self.provider.send_email(
            to_email="contractor@test.com",
            subject="টেস্ট বিষয় — নতুন টেন্ডার",
            html_body="<p>বাংলা কন্টেন্ট</p>",
            text_body="বাংলা কন্টেন্ট"
        )

        self.assertTrue(result.success)
        self.assertEqual(result.provider, "smtp")
        self.assertEqual(result.recipient, "contractor@test.com")

        # Verify SMTP interaction sequence
        mock_smtp_cls.assert_called_once_with("smtp.testserver.com", 587, timeout=5)
        self.assertTrue(mock_server.starttls.called)
        mock_server.login.assert_called_once_with("testuser", "secretpassword")
        self.assertTrue(mock_server.sendmail.called)
        self.assertTrue(mock_server.quit.called)

        # Verify sent message content contains UTF-8 Bengali text
        send_args = mock_server.sendmail.call_args[0]
        from_arg = send_args[0]
        to_arg = send_args[1]
        msg_str = send_args[2]

        self.assertEqual(from_arg, "noreply@ejarabd.com")
        self.assertEqual(to_arg, ["contractor@test.com"])
        self.assertIn("contractor@test.com", msg_str)

    @patch("smtplib.SMTP")
    def test_authentication_failure_handling(self, mock_smtp_cls):
        """Verify SMTPAuthenticationError is caught safely without leaking credentials."""
        mock_server = MagicMock()
        mock_smtp_cls.return_value = mock_server
        mock_server.login.side_effect = smtplib.SMTPAuthenticationError(535, b"Invalid credentials")

        result = self.provider.send_email(
            to_email="contractor@test.com",
            subject="Test",
            html_body="<p>Test</p>"
        )

        self.assertFalse(result.success)
        self.assertEqual(result.error_category, "auth_error")
        self.assertIn("প্রমাণীকরণ", result.message)
        # Ensure password is not present in result error message
        self.assertNotIn("secretpassword", str(result.error))

    @patch("smtplib.SMTP")
    def test_connection_failure_handling(self, mock_smtp_cls):
        """Verify connection error / timeout is classified appropriately."""
        mock_smtp_cls.side_effect = socket.timeout("Connection timed out")

        result = self.provider.send_email(
            to_email="contractor@test.com",
            subject="Test",
            html_body="<p>Test</p>"
        )

        self.assertFalse(result.success)
        self.assertEqual(result.error_category, "connection_error")
        self.assertIn("সংযোগ", result.message)

    def test_mock_email_provider(self):
        """Verify MockEmailProvider records emails accurately for test assertions."""
        mock_prov = MockEmailProvider()
        self.assertTrue(mock_prov.is_configured())

        res = mock_prov.send_email(
            to_email="pilot@ejarabd.com",
            subject="মক টেস্ট বিষয়",
            html_body="<h1>মক বডি</h1>",
            text_body="মক বডি"
        )
        self.assertTrue(res.success)
        self.assertEqual(len(mock_prov.sent_emails), 1)
        self.assertEqual(mock_prov.last_email["to_email"], "pilot@ejarabd.com")
        self.assertEqual(mock_prov.last_email["subject"], "মক টেস্ট বিষয়")


class TestEmailAPIEndpoints(unittest.TestCase):
    """Test 4: FastAPI endpoints (POST /api/email/test, POST /api/tenders/{tender_id}/email-test)."""

    def setUp(self):
        self.client = TestClient(app)
        self.db = SessionLocal()
        # Ensure tests use an isolated mock provider
        self.mock_provider = MockEmailProvider(configured=True)
        set_email_provider(self.mock_provider)

    def tearDown(self):
        self.client.close()
        self.db.close()
        set_email_provider(None)

    def test_post_email_test_success(self):
        """Verify POST /api/email/test dispatches test email successfully."""
        res = self.client.post("/api/email/test", json={"to_email": "contractor@example.com"})
        self.assertEqual(res.status_code, 200, f"Expected 200, got: {res.text}")
        data = res.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["recipient"], "contractor@example.com")
        self.assertEqual(data["provider"], "mock")
        self.assertEqual(len(self.mock_provider.sent_emails), 1)

    def test_post_email_test_invalid_email(self):
        """Verify POST /api/email/test validates malformed email addresses."""
        res = self.client.post("/api/email/test", json={"to_email": "not-an-email"})
        self.assertEqual(res.status_code, 400)
        self.assertIn("অবৈধ বা ত্রুটিপূর্ণ", res.json()["detail"])

    def test_post_email_test_unconfigured_provider(self):
        """Verify POST /api/email/test returns 503 when provider is unconfigured."""
        unconfigured_provider = MockEmailProvider(configured=False)
        set_email_provider(unconfigured_provider)

        res = self.client.post("/api/email/test", json={"to_email": "contractor@example.com"})
        self.assertEqual(res.status_code, 503)
        self.assertIn("কনফিগার করা হয়নি", res.json()["detail"])

    def test_post_tender_email_test_valid_tender(self):
        """Verify POST /api/tenders/{tender_id}/email-test sends Bengali tender email."""
        tender = self.db.query(Tender).first()
        self.assertIsNotNone(tender, "Database must contain at least one seeded tender")

        res = self.client.post(
            f"/api/tenders/{tender.tender_id}/email-test",
            json={"to_email": "contractor@example.com"}
        )
        self.assertEqual(res.status_code, 200, f"Expected 200, got: {res.text}")
        data = res.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["tender_id"], tender.tender_id)
        self.assertEqual(data["recipient"], "contractor@example.com")

        # Verify sent email content
        self.assertEqual(len(self.mock_provider.sent_emails), 1)
        sent = self.mock_provider.last_email
        self.assertIn(tender.title[:20], sent["subject"])
        self.assertIn("ইজারাবিডি", sent["html_body"])
        self.assertIn("টেন্ডার ID", sent["text_body"])

    def test_post_tender_email_test_content_verification(self):
        """Verify all required tender fields are present in email and zero-hallucination guarantees hold."""
        tender = self.db.query(Tender).first()
        self.assertIsNotNone(tender)

        res = self.client.post(
            f"/api/tenders/{tender.tender_id}/email-test",
            json={"to_email": "contractor@example.com"}
        )
        self.assertEqual(res.status_code, 200)
        sent = self.mock_provider.last_email
        html = sent["html_body"]
        text = sent["text_body"]

        # 1. Tender Title
        self.assertIn(tender.title[:20], html)
        self.assertIn(tender.title[:20], text)

        # 2. Tender ID
        self.assertIn(str(tender.tender_id), html)
        self.assertIn(str(tender.tender_id), text)

        # 3. Procuring Entity / Organization
        self.assertIn(tender.agency, html)
        self.assertIn(tender.agency, text)

        # 4. Procurement Type / Nature / Method
        self.assertIn("কাজের ধরণ / প্রকৃতি", html)
        self.assertIn("কাজের প্রকৃতি / ধরণ", text)

        # 5. District / Project Location
        self.assertIn(tender.project_location_district, html)
        self.assertIn(tender.project_location_district, text)

        # 6. Tender Security (never confused with project value)
        self.assertIn("টেন্ডার সিকিউরিটি", html)
        self.assertIn("টেন্ডার সিকিউরিটি", text)
        self.assertIn("টেন্ডার সিকিউরিটি কখনোই প্রকল্পের প্রাক্কলিত বাজেট নয়", html)
        self.assertIn("টেন্ডার সিকিউরিটি কখনোই মোট প্রকল্পের প্রাক্কলিত বাজেট নয়", text)

        # 7. Closing / Submission Deadline
        self.assertIn("জমাদানের শেষ সময়", html)
        self.assertIn("জমাদানের শেষ সময়", text)

        # 8. Official e-GP Source URL
        self.assertIn(tender.source_url, html)
        self.assertIn(tender.source_url, text)

        # 9. Anti-hallucination: Ensure security amount is never claimed as project value
        if tender.tender_security_bdt:
            sec_str = f"{tender.tender_security_bdt:,.0f}"
            self.assertNotIn(f"প্রাক্কলিত মূল্য: ৳ {sec_str}", html)
            self.assertNotIn(f"প্রাক্কলিত বাজেট: ৳ {sec_str}", text)

    def test_post_tender_email_test_invalid_email(self):
        """Verify POST /api/tenders/{tender_id}/email-test rejects malformed email addresses with 400."""
        tender = self.db.query(Tender).first()
        self.assertIsNotNone(tender)

        res = self.client.post(
            f"/api/tenders/{tender.tender_id}/email-test",
            json={"to_email": "invalid-email-address"}
        )
        self.assertEqual(res.status_code, 400)
        self.assertIn("অবৈধ বা ত্রুটিপূর্ণ", res.json()["detail"])

    def test_post_tender_email_test_numeric_id_lookup(self):
        """Verify endpoint also retrieves tender using numeric primary key if tender_id doesn't match."""
        tender = self.db.query(Tender).first()
        self.assertIsNotNone(tender)

        res = self.client.post(
            f"/api/tenders/{tender.id}/email-test",
            json={"to_email": "contractor@example.com"}
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["tender_id"], tender.tender_id)

    def test_post_tender_email_test_nonexistent_tender(self):
        """Verify POST /api/tenders/{invalid}/email-test returns 404 without crashing."""
        res = self.client.post(
            "/api/tenders/NON_EXISTENT_ID_99999/email-test",
            json={"to_email": "contractor@example.com"}
        )
        self.assertEqual(res.status_code, 404)
        self.assertIn("পাওয়া যায়নি", res.json()["detail"])


if __name__ == "__main__":
    unittest.main()
