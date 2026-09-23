#!/usr/bin/env python3
"""
EjaraBD (ইজারাবিডি) Manual Email Smoke Test Script.

This script is exclusively intended for manual live testing of SMTP delivery.
It is NOT executed during automated unittest discover runs.

Usage:
    python backend/test_email_smoke.py --help
    python backend/test_email_smoke.py --to recipient@example.com
"""

import sys
import os
import argparse
from pathlib import Path

# Ensure UTF-8 output on Windows consoles
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Ensure parent directory is in sys.path for backend imports
CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CURRENT_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.email_service import SMTPEmailProvider, EmailSendResult


def run_smoke_test(to_email: str) -> int:
    """
    Execute manual SMTP smoke test to verify live email delivery.
    Never prints passwords or sensitive credentials.
    """
    # Instantiate SMTP provider directly from .env
    provider = SMTPEmailProvider()

    from_addr = provider.from_email or "<not configured>"
    recipient = to_email.strip() if to_email else "<not specified>"

    print("EjaraBD Email Smoke Test")
    print(f"Provider: {provider.provider_name.upper()}")
    print(f"From: {from_addr}")
    print(f"To: {recipient}")

    if not provider.is_configured():
        print("Status: FAILED (Configuration missing in .env: SMTP_HOST and SMTP_FROM_EMAIL required)")
        print("\nNote: Please create or update .env with valid SMTP credentials to perform live delivery.")
        return 1

    if not to_email or "@" not in to_email:
        print("Status: FAILED (Invalid or missing recipient email. Specify with --to user@example.com)")
        return 1

    subject = "ইজারাবিডি — লাইভ ইমেইল ডেলিভারি স্মোক টেস্ট"
    text_body = (
        "ইজারাবিডি (EjaraBD) ইমেইল ডেলিভারি স্মোক টেস্ট সফল হয়েছে।\n\n"
        "এই ইমেইলটি প্রমাণ করে যে কনফিগারকৃত SMTP ক্রেডেনশিয়াল ও সার্ভার সংযোগ সঠিকভাবে কাজ করছে।"
    )
    html_body = f"""<!DOCTYPE html>
<html lang="bn">
<head><meta charset="UTF-8"></head>
<body style="font-family: sans-serif; background-color: #f8fafc; padding: 20px; color: #1e293b;">
  <div style="max-width: 500px; margin: 0 auto; background: white; border-radius: 8px; padding: 24px; border: 1px solid #e2e8f0;">
    <h2 style="color: #1e3a8a; margin-top: 0;">ইজারাবিডি (EjaraBD)</h2>
    <div style="background-color: #ecfdf5; border-left: 4px solid #10b981; padding: 12px; margin-bottom: 16px;">
      <strong style="color: #065f46;">স্মোক টেস্ট সফল:</strong> লাইভ SMTP সংযোগ প্রতিষ্ঠিত হয়েছে।
    </div>
    <p style="font-size: 14px; color: #475569;">
      আপনার ইজারাবিডি সিস্টেম এখন ঠিকাদারদের কাছে বাংলা টেন্ডার নোটিফিকেশন পাঠানোর জন্য সম্পূর্ণ প্রস্তুত।
    </p>
  </div>
</body>
</html>"""

    result: EmailSendResult = provider.send_email(
        to_email=to_email,
        subject=subject,
        html_body=html_body,
        text_body=text_body
    )

    if result.success:
        print("Status: SUCCESS")
        return 0
    else:
        # Print error details safely without passwords
        err_detail = result.error or result.message
        print(f"Status: FAILED: {err_detail}")
        return 1


def main():
    parser = argparse.ArgumentParser(
        description="EjaraBD Manual SMTP Email Smoke Test Utility",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Example:\n  python backend/test_email_smoke.py --to operator@example.com"
    )
    parser.add_argument(
        "--to", "-t",
        dest="to_email",
        type=str,
        default=os.getenv("SMTP_FROM_EMAIL", ""),
        help="Recipient email address for smoke test (defaults to SMTP_FROM_EMAIL if set)"
    )

    args = parser.parse_args()
    exit_code = run_smoke_test(args.to_email)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
