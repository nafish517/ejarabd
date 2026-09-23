"""
EjaraBD (ইজারাবিডি) Email Service Infrastructure.

Provides clean provider abstraction, SMTP implementation with UTF-8 & Bengali
support, mock provider for zero-cost hermetic testing, and safe logging.
"""

import os
import sys
import smtplib
import socket
import logging
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.header import Header
from email.utils import formataddr, formatdate
from dataclasses import dataclass, field
from pathlib import Path
from dotenv import load_dotenv

# Load .env from backend or root directory if present
BASE_DIR = Path(__file__).resolve().parent
ROOT_DIR = BASE_DIR.parent

if (BASE_DIR / ".env").exists():
    load_dotenv(BASE_DIR / ".env")
elif (ROOT_DIR / ".env").exists():
    load_dotenv(ROOT_DIR / ".env")
else:
    load_dotenv()

# Logger setup
logger = logging.getLogger("ejarabd.email")


@dataclass
class EmailSendResult:
    """Structured result of an email send operation."""
    success: bool
    message: str
    provider: str
    recipient: str
    error: Optional[str] = None
    error_category: Optional[str] = None  # config_error, auth_error, connection_error, send_error
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "message": self.message,
            "provider": self.provider,
            "recipient": self.recipient,
            "error": self.error,
            "error_category": self.error_category,
            "timestamp": self.timestamp,
        }


class EmailProvider(ABC):
    """Abstract base interface for all email delivery providers."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        pass

    @abstractmethod
    def is_configured(self) -> bool:
        """Check if provider has all required configuration parameters."""
        pass

    @abstractmethod
    def send_email(
        self,
        to_email: str,
        subject: str,
        html_body: str,
        text_body: Optional[str] = None
    ) -> EmailSendResult:
        """Send an email using this provider."""
        pass


class SMTPEmailProvider(EmailProvider):
    """
    Standard SMTP implementation with TLS, UTF-8, Bengali language support,
    multipart/alternative MIME, and strict credential isolation in logs.
    """

    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        from_email: Optional[str] = None,
        from_name: Optional[str] = None,
        use_tls: Optional[bool] = None,
        timeout: Optional[int] = None
    ):
        self.host = host if host is not None else os.getenv("SMTP_HOST", "").strip()
        port_raw = port if port is not None else os.getenv("SMTP_PORT", "587")
        try:
            self.port = int(port_raw) if port_raw else 587
        except (ValueError, TypeError):
            self.port = 587

        self.username = username if username is not None else os.getenv("SMTP_USERNAME", "").strip()
        self._password = password if password is not None else os.getenv("SMTP_PASSWORD", "").strip()
        self.from_email = from_email if from_email is not None else os.getenv("SMTP_FROM_EMAIL", "").strip()
        self.from_name = from_name if from_name is not None else os.getenv("SMTP_FROM_NAME", "EjaraBD").strip()

        tls_raw = use_tls if use_tls is not None else os.getenv("SMTP_USE_TLS", "true")
        if isinstance(tls_raw, bool):
            self.use_tls = tls_raw
        else:
            self.use_tls = str(tls_raw).lower() in ("true", "1", "yes")

        timeout_raw = timeout if timeout is not None else os.getenv("SMTP_TIMEOUT", "10")
        try:
            self.timeout = int(timeout_raw) if timeout_raw else 10
        except (ValueError, TypeError):
            self.timeout = 10

    @property
    def provider_name(self) -> str:
        return "smtp"

    def is_configured(self) -> bool:
        """Verify minimum required configuration for SMTP delivery."""
        return bool(self.host and self.from_email)

    def _create_message(
        self,
        to_email: str,
        subject: str,
        html_body: str,
        text_body: Optional[str] = None
    ) -> MIMEMultipart:
        """
        Construct a robust UTF-8 multipart/alternative email message
        preserving Bengali script and headers.
        """
        msg = MIMEMultipart("alternative")
        msg["Subject"] = Header(subject, "utf-8")
        msg["From"] = formataddr((self.from_name, self.from_email), charset="utf-8")
        msg["To"] = to_email
        msg["Date"] = formatdate(localtime=True)

        # Fallback text representation if text_body is omitted
        plain_text = text_body or "অনুগ্রহ করে HTML সমর্থিত ইমেইল ক্লায়েন্ট ব্যবহার করুন।"

        # First attach plain text, then HTML (so clients prefer HTML if capable)
        part_text = MIMEText(plain_text, "plain", "utf-8")
        msg.attach(part_text)

        part_html = MIMEText(html_body, "html", "utf-8")
        msg.attach(part_html)

        return msg

    def send_email(
        self,
        to_email: str,
        subject: str,
        html_body: str,
        text_body: Optional[str] = None
    ) -> EmailSendResult:
        """Deliver email via SMTP connection with structured error categorization."""
        to_email = (to_email or "").strip()
        if not to_email:
            return EmailSendResult(
                success=False,
                message="গ্রহীতার ইমেইল ঠিকানা প্রদান করা হয়নি",
                provider=self.provider_name,
                recipient="",
                error="Recipient email is required",
                error_category="config_error"
            )

        if not self.is_configured():
            msg = "SMTP সার্ভার বা প্রেরক ঠিকানা কনফিগার করা হয়নি"
            logger.warning(
                "SMTP send attempt aborted: Missing configuration. Host=%s, From=%s",
                bool(self.host),
                bool(self.from_email)
            )
            return EmailSendResult(
                success=False,
                message=msg,
                provider=self.provider_name,
                recipient=to_email,
                error="Missing required SMTP configuration (host or from_email)",
                error_category="config_error"
            )

        # Check Development Safety Mode (disabled in unit test execution so mocks work)
        is_unit_test = "unittest" in sys.modules or "pytest" in sys.modules or os.getenv("TESTING") == "1"
        dev_mode_raw = os.getenv("EMAIL_DEV_MODE", "true").strip().lower()
        is_dev_mode = (dev_mode_raw in ("true", "1", "yes")) and not is_unit_test
        safe_test_email = os.getenv("SAFE_TEST_EMAIL", "").strip().lower()

        if is_dev_mode:
            # Allow sending only if recipient matches SAFE_TEST_EMAIL or sender
            if safe_test_email and to_email.lower() != safe_test_email and to_email.lower() != self.from_email.lower():
                logger.info(
                    "[DEV MODE SAFETY] Suppressed real client email to '%s'. Set EMAIL_DEV_MODE=false or use safe test recipient.",
                    to_email
                )
                return EmailSendResult(
                    success=True,
                    message=f"[DEV MODE SAFETY] ইমেইল প্রেরণ স্থগিত রাখা হয়েছে: '{to_email}'। বাস্তব ইমেইল পাঠাতে EMAIL_DEV_MODE=false সেট করুন।",
                    provider="smtp_dev_mode_suppressed",
                    recipient=to_email
                )

        logger.info(
            "Attempting to send email via SMTP. Provider: %s, To: %s, Host: %s:%d, TLS: %s, DevMode: %s",
            self.provider_name,
            to_email,
            self.host,
            self.port,
            self.use_tls,
            is_dev_mode
        )

        server = None
        try:
            # Build message
            message = self._create_message(to_email, subject, html_body, text_body)

            # Connect (Port 465 uses SSL directly; others use standard SMTP + optional STARTTLS)
            if self.port == 465:
                server = smtplib.SMTP_SSL(self.host, self.port, timeout=self.timeout)
            else:
                server = smtplib.SMTP(self.host, self.port, timeout=self.timeout)
                server.ehlo()
                if self.use_tls:
                    server.starttls()
                    server.ehlo()

            # Authenticate if credentials are provided
            if self.username and self._password:
                server.login(self.username, self._password)

            # Send email
            server.sendmail(self.from_email, [to_email], message.as_string())

            logger.info("Email delivered successfully via SMTP to %s", to_email)
            return EmailSendResult(
                success=True,
                message="ইমেইল সফলভাবে পাঠানো হয়েছে",
                provider=self.provider_name,
                recipient=to_email
            )

        except smtplib.SMTPAuthenticationError as e:
            err_msg = f"SMTP প্রমাণীকরণ ব্যর্থ: {e.smtp_error.decode('utf-8', 'ignore') if isinstance(e.smtp_error, bytes) else str(e)}"
            logger.error(
                "SMTP Authentication Error sending to %s. Error: %s (Password omitted)",
                to_email,
                err_msg
            )
            return EmailSendResult(
                success=False,
                message="SMTP প্রমাণীকরণ ব্যর্থ হয়েছে। ইউজারনেম বা অ্যাপ পাসওয়ার্ড সঠিক কিনা পরীক্ষা করুন।",
                provider=self.provider_name,
                recipient=to_email,
                error=err_msg,
                error_category="auth_error"
            )

        except (smtplib.SMTPConnectError, socket.timeout, TimeoutError, ConnectionRefusedError, socket.gaierror) as e:
            err_msg = f"SMTP সংযোগ ব্যর্থ: {str(e)}"
            logger.error("SMTP Connection Error sending to %s: %s", to_email, err_msg)
            return EmailSendResult(
                success=False,
                message="SMTP সার্ভারের সাথে সংযোগ স্থাপন করা যায়নি। হোস্ট ও পোর্ট যাচাই করুন।",
                provider=self.provider_name,
                recipient=to_email,
                error=err_msg,
                error_category="connection_error"
            )

        except smtplib.SMTPException as e:
            err_msg = f"SMTP প্রোটোকল এরর: {str(e)}"
            logger.error("SMTP Protocol Exception sending to %s: %s", to_email, err_msg)
            return EmailSendResult(
                success=False,
                message=f"ইমেইল প্রেরণে ত্রুটি ঘটেছে: {str(e)}",
                provider=self.provider_name,
                recipient=to_email,
                error=err_msg,
                error_category="send_error"
            )

        except Exception as e:
            err_msg = f"অপ্রত্যাশিত ত্রুটি: {str(e)}"
            logger.error("Unexpected error sending email to %s: %s", to_email, err_msg, exc_info=True)
            return EmailSendResult(
                success=False,
                message="ইমেইল প্রেরণের সময় অপ্রত্যাশিত ত্রুটি ঘটেছে।",
                provider=self.provider_name,
                recipient=to_email,
                error=err_msg,
                error_category="send_error"
            )

        finally:
            if server is not None:
                try:
                    server.quit()
                except Exception:
                    pass


class MockEmailProvider(EmailProvider):
    """
    In-memory Mock Email Provider for testing and offline development.
    Captures all sent emails without initiating network connections.
    """

    def __init__(
        self,
        configured: bool = True,
        simulate_failure: bool = False,
        failure_category: str = "send_error",
        failure_message: str = "Mock simulated failure"
    ):
        self._configured = configured
        self.simulate_failure = simulate_failure
        self.failure_category = failure_category
        self.failure_message = failure_message
        self.sent_emails: List[Dict[str, Any]] = []

    @property
    def provider_name(self) -> str:
        return "mock"

    def is_configured(self) -> bool:
        return self._configured

    def send_email(
        self,
        to_email: str,
        subject: str,
        html_body: str,
        text_body: Optional[str] = None
    ) -> EmailSendResult:
        to_email = (to_email or "").strip()
        if not to_email:
            return EmailSendResult(
                success=False,
                message="গ্রহীতার ইমেইল ঠিকানা প্রদান করা হয়নি",
                provider=self.provider_name,
                recipient="",
                error="Recipient email is required",
                error_category="config_error"
            )

        if not self.is_configured():
            return EmailSendResult(
                success=False,
                message="মক ইমেইল প্রোভাইডার আনকনফিগারড অবস্থায় আছে",
                provider=self.provider_name,
                recipient=to_email,
                error="MockEmailProvider is not configured",
                error_category="config_error"
            )

        if self.simulate_failure:
            return EmailSendResult(
                success=False,
                message=self.failure_message,
                provider=self.provider_name,
                recipient=to_email,
                error=self.failure_message,
                error_category=self.failure_category
            )

        record = {
            "to_email": to_email,
            "subject": subject,
            "html_body": html_body,
            "text_body": text_body,
            "timestamp": datetime.utcnow().isoformat()
        }
        self.sent_emails.append(record)
        logger.info("MockEmailProvider recorded email to: %s with subject: %s", to_email, subject)

        return EmailSendResult(
            success=True,
            message="মক ইমেইল সফলভাবে রেকর্ড করা হয়েছে",
            provider=self.provider_name,
            recipient=to_email
        )

    def clear(self) -> None:
        """Clear recorded emails."""
        self.sent_emails.clear()

    @property
    def last_email(self) -> Optional[Dict[str, Any]]:
        """Return the most recently sent email record if any."""
        return self.sent_emails[-1] if self.sent_emails else None


# Module-level provider singleton
_active_provider: Optional[EmailProvider] = None


def get_email_provider(force_reload: bool = False) -> EmailProvider:
    """
    Factory function to retrieve the configured EmailProvider.
    Uses lazy initialization. Supports runtime injection for testing.
    """
    global _active_provider
    if _active_provider is not None and not force_reload:
        return _active_provider

    provider_type = os.getenv("EMAIL_PROVIDER", "smtp").strip().lower()

    if provider_type == "mock" or os.getenv("TESTING") == "1":
        _active_provider = MockEmailProvider()
    elif provider_type == "smtp":
        _active_provider = SMTPEmailProvider()
    else:
        logger.warning(
            "Unknown EMAIL_PROVIDER '%s'. Falling back to SMTP provider.",
            provider_type
        )
        _active_provider = SMTPEmailProvider()

    return _active_provider


def set_email_provider(provider: Optional[EmailProvider]) -> None:
    """Set or override the active email provider (useful for unit tests)."""
    global _active_provider
    _active_provider = provider


def send_email(
    to_email: str,
    subject: str,
    html_body: str,
    text_body: Optional[str] = None
) -> EmailSendResult:
    """Convenience facade to dispatch an email via the active provider."""
    provider = get_email_provider()
    return provider.send_email(
        to_email=to_email,
        subject=subject,
        html_body=html_body,
        text_body=text_body
    )
