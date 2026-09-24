"""
EjaraBD (ইজারাবিডি) Email Templates.

Generates beautiful, high-clarity Bengali HTML and plain-text email templates
for tender notifications, adhering strictly to zero-hallucination principles.
"""

import html
from typing import Tuple, Optional, List, Union, Any
from datetime import datetime

FALLBACK_VALUE = "অজ্ঞাত / যাচাই প্রয়োজন"


def _format_bengali_digits(num_str: str) -> str:
    """Convert western numerals to Bengali numerals for natural reading."""
    bengali_digits = {"0": "০", "1": "১", "2": "২", "3": "৩", "4": "৪", "5": "৫", "6": "৬", "7": "৭", "8": "৮", "9": "৯"}
    return "".join(bengali_digits.get(char, char) for char in num_str)


def _format_currency_bdt(amount: Optional[Union[float, int]]) -> str:
    """
    Format BDT currency safely.
    Returns FALLBACK_VALUE if amount is missing, None, or non-positive.
    """
    if amount is None:
        return FALLBACK_VALUE
    try:
        val = float(amount)
        if val <= 0:
            return FALLBACK_VALUE
        # Format with thousand separators
        formatted = f"৳ {val:,.0f}"
        return formatted
    except (ValueError, TypeError):
        return FALLBACK_VALUE


def _format_datetime(dt: Optional[Union[datetime, str]]) -> str:
    """
    Format publication or closing datetime.
    Returns FALLBACK_VALUE if unavailable.
    """
    if not dt:
        return FALLBACK_VALUE
    if isinstance(dt, datetime):
        return dt.strftime("%d-%m-%Y %I:%M %p BST")
    if isinstance(dt, str):
        cleaned = dt.strip()
        if not cleaned:
            return FALLBACK_VALUE
        try:
            # Attempt to parse ISO string
            parsed = datetime.fromisoformat(cleaned.replace("Z", "+00:00"))
            return parsed.strftime("%d-%m-%Y %I:%M %p BST")
        except Exception:
            return cleaned
    return FALLBACK_VALUE


def render_tender_notification_email(
    tender: Any,
    contractor: Optional[Any] = None,
    assessment: Optional[Any] = None,
    notification_draft: Optional[Any] = None
) -> Tuple[str, str, str]:
    """
    Render subject, HTML body, and plain-text fallback for a tender notification email.

    Args:
        tender: Tender DB model or dict-like object
        contractor: ContractorProfile DB model or dict-like object
        assessment: MatchAssessment DB model or dict-like object
        notification_draft: NotificationDraft DB model or dict-like object

    Returns:
        Tuple of (subject, html_body, text_body)
    """
    # Determine Language Preference
    lang = "bn"
    if contractor:
        pref = getattr(contractor, "preferred_language", None) or (contractor.get("preferred_language") if isinstance(contractor, dict) else None)
        if pref and str(pref).lower().strip() in ("en", "english"):
            lang = "en"

    fallback_val = "Unknown / Verification Required" if lang == "en" else FALLBACK_VALUE

    # 1. Tender Title & Subject
    title_raw = getattr(tender, "title", None) or (tender.get("title") if isinstance(tender, dict) else None)
    title = str(title_raw).strip() if title_raw else fallback_val
    subject = f"New Matched Tender — {title}" if lang == "en" else f"নতুন টেন্ডার — {title}"

    # 2. Tender ID
    tender_id_raw = getattr(tender, "tender_id", None) or (tender.get("tender_id") if isinstance(tender, dict) else None)
    tender_id = str(tender_id_raw).strip() if tender_id_raw else fallback_val

    # 3. Organization (Agency & Procuring Entity Office)
    agency = getattr(tender, "agency", None) or (tender.get("agency") if isinstance(tender, dict) else None)
    office = getattr(tender, "procuring_entity_office", None) or (tender.get("procuring_entity_office") if isinstance(tender, dict) else None)
    if agency and office and agency != office:
        organization = f"{agency} ({office})"
    elif agency:
        organization = str(agency).strip()
    elif office:
        organization = str(office).strip()
    else:
        organization = fallback_val

    # 4. Procurement Type / Nature / Method
    category_raw = getattr(tender, "category", None) or (tender.get("category") if isinstance(tender, dict) else None)
    proc_nature_raw = getattr(tender, "procurement_nature", None) or (tender.get("procurement_nature") if isinstance(tender, dict) else None)
    proc_method_raw = getattr(tender, "procurement_method", None) or (tender.get("procurement_method") if isinstance(tender, dict) else None)

    nature_parts = []
    if category_raw and str(category_raw).strip():
        cat_str = str(category_raw).strip()
        if lang == "en":
            nature_parts.append(cat_str)
        else:
            nature_mapping = {
                "Works": "নির্মাণ কাজ (Works)",
                "Goods": "পণ্য সরবরাহ (Goods)",
                "Services": "পরামর্শক / সেবা (Services)",
                "Physical Services": "ভৌত / কারিগরি সেবা (Physical Services)",
            }
            nature_parts.append(nature_mapping.get(cat_str, cat_str))
    elif proc_nature_raw and str(proc_nature_raw).strip():
        nature_parts.append(str(proc_nature_raw).strip())

    if proc_method_raw and str(proc_method_raw).strip():
        method_label = "Method: " if lang == "en" else "পদ্ধতি: "
        nature_parts.append(f"{method_label}{str(proc_method_raw).strip()}")

    procurement_nature = " | ".join(nature_parts) if nature_parts else fallback_val

    # 5. Location
    district = getattr(tender, "project_location_district", None) or (tender.get("project_location_district") if isinstance(tender, dict) else None)
    details = getattr(tender, "project_location_details", None) or (tender.get("project_location_details") if isinstance(tender, dict) else None)
    if district and details:
        location = f"{district} ({details})"
    elif district:
        location = str(district).strip()
    elif details:
        location = str(details).strip()
    else:
        location = fallback_val

    # 6. Dates
    pub_date_raw = getattr(tender, "publication_date", None) or (tender.get("publication_date") if isinstance(tender, dict) else None)
    publish_date = _format_datetime(pub_date_raw) if pub_date_raw else fallback_val

    closing_date_raw = getattr(tender, "closing_date", None) or (tender.get("closing_date") if isinstance(tender, dict) else None)
    closing_date = _format_datetime(closing_date_raw) if closing_date_raw else fallback_val

    # 7. Financials: Estimated Project Value & Tender Security
    est_val_raw = getattr(tender, "estimated_value_bdt", None) or (tender.get("estimated_value_bdt") if isinstance(tender, dict) else None)
    if est_val_raw is not None and float(est_val_raw) > 0:
        estimated_value = _format_currency_bdt(est_val_raw)
    else:
        estimated_value = "Undisclosed in notice / verify schedule" if lang == "en" else f"{FALLBACK_VALUE} (নোটিশে অপ্রকাশিত)"

    security_raw = getattr(tender, "tender_security_bdt", None) or (tender.get("tender_security_bdt") if isinstance(tender, dict) else None)
    tender_security = _format_currency_bdt(security_raw)

    # 8. Relevance Explanation
    relevance_raw = None
    if assessment:
        relevance_raw = getattr(assessment, "overall_fit_explanation_bn", None) or (assessment.get("overall_fit_explanation_bn") if isinstance(assessment, dict) else None)

    if relevance_raw and str(relevance_raw).strip():
        relevance_explanation = str(relevance_raw).strip()
    elif contractor:
        biz_name = getattr(contractor, "business_name", None) or (contractor.get("business_name") if isinstance(contractor, dict) else None)
        if biz_name:
            relevance_explanation = f"Matches profile and preferences of {biz_name}." if lang == "en" else f"{biz_name}-এর প্রোফাইল ও পছন্দের ক্ষেত্রের সাথে প্রাসঙ্গিক।"
        else:
            relevance_explanation = "Matches your work profile and selected criteria." if lang == "en" else "আপনার কাজের প্রোফাইলের সাথে সামঞ্জস্যপূর্ণ।"
    else:
        relevance_explanation = fallback_val

    # 9. Verification Items
    verify_list: List[str] = []
    if assessment:
        unknown_items = getattr(assessment, "unknown_items_to_verify", None) or (assessment.get("unknown_items_to_verify") if isinstance(assessment, dict) else None)
        if isinstance(unknown_items, list):
            verify_list.extend([str(item).strip() for item in unknown_items if str(item).strip()])

        mismatches = getattr(assessment, "known_mismatches", None) or (assessment.get("known_mismatches") if isinstance(assessment, dict) else None)
        if isinstance(mismatches, list):
            prefix = "Warning: " if lang == "en" else "সতর্কতা: "
            for m in mismatches:
                if str(m).strip() and str(m).strip() not in verify_list:
                    verify_list.append(f"{prefix}{str(m).strip()}")

    if not verify_list:
        default_verify = "Verify specific eligibility conditions in tender ITT/TDS documents." if lang == "en" else "নোটিশ বা শিডিউলের বিস্তারিত শর্তাবলি ITT/TDS দেখে যাচাই করতে হবে।"
        verify_list = [default_verify]

    verification_items_text = "\n".join(f"• {item}" for item in verify_list)
    verification_items_html = "".join(f"<li style='margin-bottom: 6px;'>{html.escape(item)}</li>" for item in verify_list)

    # 10. Official URL
    url_raw = getattr(tender, "source_url", None) or (tender.get("source_url") if isinstance(tender, dict) else None)
    official_url = str(url_raw).strip() if url_raw else fallback_val

    # Labels based on language
    if lang == "en":
        intro_text = "A new matching e-GP tender has been found for your business."
        lbl_tender = "Tender Title"
        lbl_id = "Tender ID"
        lbl_org = "Procuring Entity / Agency"
        lbl_nature = "Work Category / Nature"
        lbl_nature_html = "Work Category / Nature"
        lbl_loc = "Location"
        lbl_pub = "Publication Date"
        lbl_close = "Submission Deadline"
        lbl_est_val = "Estimated Budget"
        lbl_sec = "Tender Security"
        lbl_security_warn_html = "* Tender security is an earnest deposit, not the total project estimated value. Check the tender schedule for official budget details."
        lbl_security_warn_text = "*(Note: Tender security is never the total project estimated budget.)*"
        lbl_why = "🎯 Why this is relevant to you:"
        lbl_checklist = "🔍 Items to verify in tender schedule:"
        lbl_link = "🔗 Official e-GP Link:"
        lbl_footer_tagline = "EjaraBD — Intelligent Rule-Based Tender Discovery"
        lbl_footer_note = "This is an automated notification. For support or profile updates, contact your account manager."
    else:
        intro_text = "ইজারাবিডি থেকে আপনার জন্য একটি নতুন টেন্ডার পাওয়া গেছে।"
        lbl_tender = "টেন্ডার"
        lbl_id = "টেন্ডার ID"
        lbl_org = "সংস্থা"
        lbl_nature = "কাজের প্রকৃতি / ধরণ"
        lbl_nature_html = "কাজের ধরণ / প্রকৃতি"
        lbl_loc = "স্থান"
        lbl_pub = "প্রকাশের তারিখ"
        lbl_close = "জমাদানের শেষ সময়"
        lbl_est_val = "প্রাক্কলিত বাজেট"
        lbl_sec = "টেন্ডার সিকিউরিটি"
        lbl_security_warn_html = "* টেন্ডার সিকিউরিটি কখনোই প্রকল্পের প্রাক্কলিত বাজেট নয়। সঠিক প্রাক্কলিত মূল্য জানতে শিডিউল যাচাই করুন।"
        lbl_security_warn_text = "*(সতর্কবার্তা: টেন্ডার সিকিউরিটি কখনোই মোট প্রকল্পের প্রাক্কলিত বাজেট নয়।)*"
        lbl_why = "🎯 কেন আপনার জন্য প্রাসঙ্গিক:"
        lbl_checklist = "🔍 যা যাচাই করতে হবে:"
        lbl_link = "🔗 অফিসিয়াল e-GP লিংক:"
        lbl_footer_tagline = "ইজারাবিডি — আপনার কাজের সঙ্গে মেলে এমন টেন্ডার খুঁজে দিচ্ছে।"
        lbl_footer_note = "এটি একটি স্বয়ংক্রিয় নোটিফিকেশন সিস্টেম। কোনো ভুল বা সহায়তার জন্য অপারেটরের সাথে যোগাযোগ করুন।"

    # --- Construct Plain Text Body ---
    text_body = (
        f"{intro_text}\n"
        "━━━━━━━━━━━━━━━━━━\n"
        f"📋 {lbl_tender}\n{title}\n\n"
        f"🆔 {lbl_id}\n{tender_id}\n\n"
        f"🏢 {lbl_org}\n{organization}\n\n"
        f"🏷️ {lbl_nature}\n{procurement_nature}\n\n"
        f"📍 {lbl_loc}\n{location}\n\n"
        f"📅 {lbl_pub}\n{publish_date}\n\n"
        f"⏰ {lbl_close}\n{closing_date}\n\n"
        f"💵 {lbl_est_val}\n{estimated_value}\n\n"
        f"💰 {lbl_sec}\n{tender_security}\n"
        "━━━━━━━━━━━━━━━━━━\n"
        f"{lbl_why}\n"
        f"{relevance_explanation}\n\n"
        f"{lbl_checklist}\n"
        f"{verification_items_text}\n\n"
        f"{lbl_link}\n{official_url}\n\n"
        "━━━━━━━━━━━━━━━━━━\n"
        f"{lbl_footer_tagline}\n"
        f"{lbl_security_warn_text}"
    )

    # --- Construct HTML Body with Escaped Fields & Clean Styling ---
    e_title = html.escape(title)
    e_tender_id = html.escape(tender_id)
    e_org = html.escape(organization)
    e_nature = html.escape(procurement_nature)
    e_loc = html.escape(location)
    e_pub = html.escape(publish_date)
    e_close = html.escape(closing_date)
    e_est_val = html.escape(estimated_value)
    e_sec = html.escape(tender_security)
    e_relevance = html.escape(relevance_explanation)
    e_url = html.escape(official_url)

    url_link_html = (
        f'<a href="{e_url}" target="_blank" rel="noopener noreferrer" style="color: #0284c7; text-decoration: underline; word-break: break-all; font-weight: 600;">{e_url}</a>'
        if official_url != fallback_val
        else f'<span style="color: #64748b;">{fallback_val}</span>'
    )

    html_body = f"""<!DOCTYPE html>
<html lang="{lang}">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{html.escape(subject)}</title>
</head>
<body style="margin: 0; padding: 0; background-color: #f1f5f9; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, 'Kalpurush', 'SolaimanLipi', sans-serif; color: #1e293b; line-height: 1.6;">
  <div style="max-width: 620px; margin: 24px auto; background: #ffffff; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06); border: 1px solid #e2e8f0;">
    
    <!-- Header -->
    <div style="background: linear-gradient(135deg, #0f172a 0%, #1e3a8a 100%); padding: 24px 28px; color: #ffffff;">
      <div style="font-size: 22px; font-weight: 700; letter-spacing: -0.5px; margin-bottom: 6px;">ইজারাবিডি (EjaraBD)</div>
      <div style="font-size: 14px; color: #93c5fd;">{'A new matching tender recommendation' if lang == 'en' else 'আপনার জন্য একটি নতুন দরপত্র সুপারিশ'}</div>
    </div>

    <!-- Intro Greeting -->
    <div style="padding: 24px 28px 16px; border-bottom: 1px solid #f1f5f9;">
      <p style="margin: 0; font-size: 16px; font-weight: 600; color: #0f172a;">
        {intro_text}
      </p>
    </div>

    <!-- Main Tender Specs Card -->
    <div style="padding: 20px 28px; background-color: #f8fafc; border-bottom: 1px solid #e2e8f0;">
      
      <!-- Title -->
      <div style="margin-bottom: 16px;">
        <div style="font-size: 13px; font-weight: 600; color: #64748b; text-transform: uppercase; margin-bottom: 4px;">📋 {lbl_tender}</div>
        <div style="font-size: 17px; font-weight: 700; color: #0f172a; line-height: 1.4;">{e_title}</div>
      </div>

      <!-- Grid Details -->
      <table style="width: 100%; border-collapse: collapse; margin-top: 12px;">
        <tr>
          <td style="padding: 8px 0; font-size: 14px; color: #64748b; width: 38%; vertical-align: top;">🆔 {lbl_id}:</td>
          <td style="padding: 8px 0; font-size: 14px; font-weight: 700; color: #0f172a; vertical-align: top;">{e_tender_id}</td>
        </tr>
        <tr>
          <td style="padding: 8px 0; font-size: 14px; color: #64748b; vertical-align: top;">🏢 {lbl_org}:</td>
          <td style="padding: 8px 0; font-size: 14px; font-weight: 600; color: #1e293b; vertical-align: top;">{e_org}</td>
        </tr>
        <tr>
          <td style="padding: 8px 0; font-size: 14px; color: #64748b; vertical-align: top;">🏷️ {lbl_nature_html}:</td>
          <td style="padding: 8px 0; font-size: 14px; font-weight: 600; color: #1e293b; vertical-align: top;">{e_nature}</td>
        </tr>
        <tr>
          <td style="padding: 8px 0; font-size: 14px; color: #64748b; vertical-align: top;">📍 {lbl_loc}:</td>
          <td style="padding: 8px 0; font-size: 14px; font-weight: 600; color: #1e293b; vertical-align: top;">{e_loc}</td>
        </tr>
        <tr>
          <td style="padding: 8px 0; font-size: 14px; color: #64748b; vertical-align: top;">📅 {lbl_pub}:</td>
          <td style="padding: 8px 0; font-size: 14px; color: #334155; vertical-align: top;">{e_pub}</td>
        </tr>
        <tr>
          <td style="padding: 8px 0; font-size: 14px; color: #64748b; vertical-align: top;">⏰ {lbl_close}:</td>
          <td style="padding: 8px 0; font-size: 14px; font-weight: 700; color: #dc2626; vertical-align: top;">{e_close}</td>
        </tr>
        <tr>
          <td style="padding: 8px 0; font-size: 14px; color: #64748b; vertical-align: top;">💵 {lbl_est_val}:</td>
          <td style="padding: 8px 0; font-size: 14px; font-weight: 600; color: #0f172a; vertical-align: top;">{e_est_val}</td>
        </tr>
        <tr>
          <td style="padding: 8px 0; font-size: 14px; color: #64748b; vertical-align: top;">💰 {lbl_sec}:</td>
          <td style="padding: 8px 0; font-size: 15px; font-weight: 700; color: #15803d; vertical-align: top;">{e_sec}</td>
        </tr>
      </table>

      <div style="font-size: 11px; color: #94a3b8; margin-top: 8px; font-style: italic;">
        {lbl_security_warn_html}
      </div>
    </div>

    <!-- Relevance Analysis -->
    <div style="padding: 20px 28px; border-bottom: 1px solid #f1f5f9;">
      <div style="font-size: 15px; font-weight: 700; color: #1e3a8a; margin-bottom: 8px;">
        {lbl_why}
      </div>
      <div style="font-size: 14px; color: #334155; background-color: #eff6ff; padding: 12px 16px; border-radius: 8px; border-left: 4px solid #3b82f6;">
        {e_relevance}
      </div>
    </div>

    <!-- Verification Checklist -->
    <div style="padding: 20px 28px; border-bottom: 1px solid #f1f5f9;">
      <div style="font-size: 15px; font-weight: 700; color: #b45309; margin-bottom: 8px;">
        {lbl_checklist}
      </div>
      <ul style="margin: 0; padding-left: 20px; font-size: 14px; color: #475569; line-height: 1.7;">
        {verification_items_html}
      </ul>
    </div>

    <!-- Official URL Link -->
    <div style="padding: 20px 28px; background-color: #fafafa; border-bottom: 1px solid #e2e8f0;">
      <div style="font-size: 14px; font-weight: 700; color: #0f172a; margin-bottom: 6px;">
        {lbl_link}
      </div>
      <div style="font-size: 13px;">
        {url_link_html}
      </div>
    </div>

    <!-- Footer -->
    <div style="padding: 24px 28px; background-color: #f8fafc; text-align: center; color: #64748b; font-size: 13px;">
      <div style="font-weight: 600; color: #334155; margin-bottom: 4px;">ইজারাবিডি (EjaraBD)</div>
      <div>{lbl_footer_tagline}</div>
      <div style="font-size: 11px; color: #94a3b8; margin-top: 12px;">
        {lbl_footer_note}
      </div>
    </div>

  </div>
</body>
</html>"""

    return subject, html_body, text_body
