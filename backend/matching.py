import sys
from datetime import datetime
from typing import Dict, Any, List, Optional

# Windows কনসোলে বাংলা অক্ষরের জন্য সেফটি
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from sqlalchemy.orm import Session
from backend.models import ContractorProfile, Tender, MatchAssessment, NotificationDraft

# সংখ্যা বাংলায় রূপান্তর করার সহায়ক ফাংশন
EN_TO_BN_NUM = str.maketrans("0123456789", "০১২৩৪৫৬৭৮৯")

def to_bn_number(number_str: str) -> str:
    """ইংরেজি সংখ্যাকে বাংলায় রূপান্তর"""
    return str(number_str).translate(EN_TO_BN_NUM)

def format_bdt_lakh_crore(amount: Optional[float]) -> str:
    """টাকার পরিমাণকে স্পষ্ট লাখ বা কোটিতে প্রকাশ করা"""
    if amount is None:
        return "অফিসিয়াল নোটিশে প্রাক্কলিত মূল্য উল্লেখ নেই (দলিল দেখতে হবে)"
    
    if amount >= 10_000_000: # ১ কোটি বা তদূর্ধ্ব
        crore_val = amount / 10_000_000
        formatted = f"{crore_val:.2f}".rstrip('0').rstrip('.')
        return f"৳ {to_bn_number(formatted)} কোটি"
    elif amount >= 100_000: # ১ লাখ বা তদূর্ধ্ব
        lakh_val = amount / 100_000
        formatted = f"{lakh_val:.2f}".rstrip('0').rstrip('.')
        return f"৳ {to_bn_number(formatted)} লাখ"
    else:
        return f"৳ {to_bn_number(f'{amount:,.0f}')}"

def format_bst_datetime(dt: Optional[datetime]) -> str:
    """তারিখ ও সময়কে বাংলাদেশ সময় (BST) ফরম্যাটে বাংলায় দেখানো"""
    if not dt:
        return "তারিখ ও সময় নোটিশে উল্লেখ নেই"
    
    months_bn = [
        "", "জানুয়ারি", "ফেব্রুয়ারি", "মার্চ", "এপ্রিল", "মে", "জুন",
        "জুলাই", "আগস্ট", "সেপ্টেম্বর", "অক্টোবর", "নভেম্বর", "ডিসেম্বর"
    ]
    
    day_bn = to_bn_number(str(dt.day))
    month_bn = months_bn[dt.month]
    year_bn = to_bn_number(str(dt.year))
    
    hour = dt.hour
    minute = dt.minute
    period = "সকাল" if hour < 12 else ("দুপুর" if hour < 15 else ("বিকাল" if hour < 18 else "সন্ধ্যা"))
    display_hour = hour if hour <= 12 else hour - 12
    if display_hour == 0:
        display_hour = 12
    
    time_str = f"{period} {to_bn_number(f'{display_hour:02d}')}:{to_bn_number(f'{minute:02d}')} মিনিট"
    return f"{day_bn} {month_bn} {year_bn}, {time_str} (BST)"


def evaluate_tender_for_contractor(contractor: ContractorProfile, tender: Tender) -> Dict[str, Any]:
    """
    ঠিকাদারের পছন্দের সাথে টেন্ডারের শর্তভিত্তিক স্বচ্ছ মূল্যায়ন
    (কোনো কাল্পনিক শতকরা স্কোর নয়)
    """
    preference_reasons: List[str] = []
    known_mismatches: List[str] = []
    unknown_items: List[str] = []

    # ০. বাদ দেওয়ার এলাকা বা ক্যাটাগরি (Exclusions Check)
    excluded = contractor.excluded_areas_or_categories or []
    if isinstance(excluded, str):
        excluded = [e.strip() for e in excluded.split(",") if e.strip()]

    is_excluded = False
    for exc in excluded:
        exc_lower = str(exc).lower().strip()
        if not exc_lower:
            continue
        if (
            exc_lower in tender.project_location_district.lower()
            or (tender.project_location_details and exc_lower in tender.project_location_details.lower())
            or exc_lower in tender.category.lower()
            or exc_lower in tender.title.lower()
        ):
            is_excluded = True
            known_mismatches.append(f"আপনার বাদ দেওয়ার তালিকাভুক্ত শর্তের মধ্যে পড়েছে ({exc})।")
            break
    
    # ১. জেলা ও অবস্থান যাচাই (প্রকৃত কাজের অবস্থান)
    district_match = False
    if contractor.preferred_districts:
        for pref_dist in contractor.preferred_districts:
            if pref_dist.lower() in tender.project_location_district.lower():
                district_match = True
                break
    
    # উপজেলা যাচাই
    upazila_match = False
    preferred_upazilas = contractor.preferred_upazilas or []
    if isinstance(preferred_upazilas, str):
        preferred_upazilas = [u.strip() for u in preferred_upazilas.split(",") if u.strip()]

    if preferred_upazilas:
        tender_loc_text = f"{tender.project_location_details or ''} {tender.title}".lower()
        for u in preferred_upazilas:
            if u.lower() in tender_loc_text:
                upazila_match = True
                break

    if district_match:
        loc_details = f" ({tender.project_location_details})" if tender.project_location_details else ""
        upz_text = " (পছন্দের উপজেলার সাথে মিল)" if upazila_match else ""
        preference_reasons.append(f"কাজের এলাকা আপনার পছন্দের জেলা {tender.project_location_district}{loc_details}{upz_text}-এর মধ্যে।")
    else:
        known_mismatches.append(f"কাজের এলাকা ({tender.project_location_district}) আপনার পছন্দের এলাকার বাইরে।")

    # ২. কাজের ক্যাটাগরি ও ধরনের মিল যাচাই
    category_match = False
    if contractor.work_categories:
        for cat in contractor.work_categories:
            if cat.lower() in tender.category.lower() or any(w.lower() in tender.title.lower() for w in cat.split()):
                category_match = True
                break
                
    if category_match:
        preference_reasons.append(f"কাজের ধরন ({tender.category}) আপনার অভিজ্ঞতার ক্ষেত্রের সাথে সামঞ্জস্যপূর্ণ।")
    else:
        known_mismatches.append(f"কাজের ধরন ({tender.category}) আপনার নির্বাচিত কাজের তালিকার বাইরে।")

    # ২.১ পছন্দের সংস্থা (Agencies)
    agency_match = False
    preferred_agencies = contractor.preferred_agencies or []
    if isinstance(preferred_agencies, str):
        preferred_agencies = [a.strip() for a in preferred_agencies.split(",") if a.strip()]

    if preferred_agencies:
        tender_agency_text = f"{tender.agency} {tender.procuring_entity_office}".lower()
        for ag in preferred_agencies:
            if ag.lower() in tender_agency_text:
                agency_match = True
                preference_reasons.append(f"দরপত্র আহবানকারী সংস্থা ({tender.agency}) আপনার পছন্দের সংস্থার মধ্যে রয়েছে।")
                break

    # ৩. বাজেট ও আর্থিক পরিসীমা যাচাই (নিয়ম: অজানা থাকলে অজানা থাকবে)
    if tender.estimated_value_bdt is not None:
        val = tender.estimated_value_bdt
        min_v = contractor.min_project_value_bdt or 0
        max_v = contractor.max_project_value_bdt or float('inf')
        
        if min_v <= val <= max_v:
            preference_reasons.append(f"আনুমানিক বাজেট ({format_bdt_lakh_crore(val)}) আপনার নির্ধারিত পরিসীমার ভেতর রয়েছে।")
        else:
            known_mismatches.append(f"আনুমানিক বাজেট ({format_bdt_lakh_crore(val)}) আপনার নিয়মিত কাজের সীমার বাইরে।")
    else:
        unknown_items.append("নোটিশে প্রাক্কলিত কাজের মূল্য উল্লেখ নেই; টেন্ডার শিডিউল কিনে সঠিক প্রাক্কলন নিশ্চিত করতে হবে।")

    # ৪. টেন্ডার নোটিশের বিশেষ শর্তাবলি ও ঘাটতি যাচাই
    if tender.raw_eligibility_text:
        raw = tender.raw_eligibility_text
        if "একক চুক্তি" in raw or "সমাপ্তির সনদ" in raw:
            unknown_items.append("বিগত ৫ বছরের নির্দিষ্ট অংকের অনুরূপ কাজের সফল সমাপ্তি সনদপত্র আপনার হালনাগাদ আছে কিনা যাচাই করুন।")
        if "তরল সম্পদ" in raw or "Liquid Asset" in raw or "ক্রেডিট লাইন" in raw:
            unknown_items.append("ব্যাংক থেকে প্রয়োজনীয় তরল সম্পদ (Liquid Asset) বা ক্রেডিট সুবিধার সার্টিফিকেট সংগ্রহ করা যাবে কিনা নিশ্চিত করুন।")
        if "লাইসেন্স" in raw or "ট্যাক্স" in raw:
            unknown_items.append("হালনাগাদ ঠিকাদারি লাইসেন্স ও ট্যাক্স ক্লিয়ারেন্স সার্টিফিকেট প্রস্তুত আছে কিনা দেখুন।")
    else:
        unknown_items.append("নোটিশে বিস্তারিত যোগ্যতা উল্লেখ নেই; শিডিউলের ITT বা TDS অংশ দেখে শর্ত নিশ্চিত হতে হবে।")

    # সামগ্রিক ফিট স্ট্যাটাস নির্ধারণ
    if is_excluded:
        preference_fit_status = "outside"
        qualification_status = "does_not_meet"
        fit_summary_bn = "দরপত্রটি আপনার বাদ দেওয়ার তালিকাভুক্ত শর্তে পড়েছে।"
    elif district_match and category_match:
        preference_fit_status = "fits"
        qualification_status = "unknown_needs_verification"
        fit_summary_bn = "আপনার কাজের জেলা ও ধরনের সাথে ভালো মিল রয়েছে। প্রয়োজনীয় কাগজপত্র ও শর্তগুলো মিলিয়ে দেখার মতো।"
    elif district_match or category_match:
        preference_fit_status = "partial"
        qualification_status = "unknown_needs_verification"
        fit_summary_bn = "কিছু বিষয়ে মিল থাকলেও কিছু শর্ত বা তথ্যের অমিল রয়েছে; ভেবেচিন্তে সিদ্ধান্ত নিন।"
    else:
        preference_fit_status = "outside"
        qualification_status = "does_not_meet"
        fit_summary_bn = "জেলা ও কাজের ধরন আপনার নিয়মিত প্রোফাইলের সাথে মেলে না।"

    return {
        "preference_fit_status": preference_fit_status,
        "preference_reasons": preference_reasons,
        "qualification_status": qualification_status,
        "known_mismatches": known_mismatches,
        "unknown_items_to_verify": unknown_items,
        "overall_fit_explanation_bn": fit_summary_bn
    }


def generate_whatsapp_message(contractor: ContractorProfile, tender: Tender, assessment_data: Dict[str, Any]) -> str:
    """
    ঠিকাদারের জন্য মার্জিত, সম্মানজনক ও সহজ বাংলায় বার্তার ড্রাফট
    """
    greeting = f"আসসালামু আলাইকুম {contractor.contact_person},"
    budget_line = format_bdt_lakh_crore(tender.estimated_value_bdt)
    security_line = format_bdt_lakh_crore(tender.tender_security_bdt) if tender.tender_security_bdt else "নোটিশে উল্লেখ নেই"
    
    # কেন মিলল
    reasons_text = ""
    for r in assessment_data["preference_reasons"]:
        reasons_text += f"• {r}\n"
    if not reasons_text:
        reasons_text = "• এই টেন্ডারটি পর্যালোচনার জন্য পাঠানো হলো।\n"

    # কী যাচাই করতে হবে
    verify_text = ""
    for u in assessment_data["unknown_items_to_verify"]:
        verify_text += f"• {u}\n"
    if not verify_text:
        verify_text = "• শিডিউল দেখে বিস্তারিত শর্ত যাচাই করুন।\n"

    # সংশোধনী থাকলে বিশেষ সতর্কতা
    amendment_notice = ""
    if tender.is_amendment and tender.amendment_details:
        amendment_notice = f"\n📢 *সংশোধনী সতর্কতা:*\n{tender.amendment_details}\n"

    closing_time_str = format_bst_datetime(tender.closing_date)
    selling_time_str = format_bst_datetime(tender.document_last_selling_date) if tender.document_last_selling_date else "নোটিশে উল্লিখিত সময় অনুযায়ী"

    draft = f"""{greeting}
আপনার কাজের সাথে সামঞ্জস্যপূর্ণ একটি টেন্ডার সংক্ষেপ নিচে দেওয়া হলো:

📌 *কাজের শিরোনাম:* {tender.title}
🏢 *সংস্থা:* {tender.agency}
📍 *কাজের এলাকা:* {tender.project_location_district} {f'({tender.project_location_details})' if tender.project_location_details else ''}
💰 *আনুমানিক বাজেট:* {budget_line}
🔒 *টেন্ডার সিকিউরিটি:* {security_line}
{amendment_notice}
✅ *কেন আপনার কাজের সাথে মেলে:*
{reasons_text.strip()}

⚠️ *জমা দেওয়ার আগে যা যাচাই করতে হবে:*
{verify_text.strip()}

⏰ *জরুরি সময়সীমা (বাংলাদেশ সময়):*
• শিডিউল ক্রয়ের শেষ তারিখ: {selling_time_str}
• দরপত্র জমা দেওয়ার শেষ সময়: *{closing_time_str}*

🔗 *অফিসিয়াল দরপত্র লিংক:*
{tender.source_url}

_এটি ইজারাবিডি (EjaraBD) সিস্টেমের মাধ্যমে আপনার জন্য সংক্ষেপিত। সিদ্ধান্ত নেওয়ার পূর্বে মূল দরপত্র দলিল ভালোভাবে পড়ে নিন।_"""

    return draft


def run_matching_pipeline(db: Session, target_contractor_id: Optional[int] = None) -> int:
    """
    সকল সক্রিয় ঠিকাদারের বিপরীতে টেন্ডার ম্যাচিং সম্পন্ন করে ডাটাবেজে সংরক্ষণ করা।
    উন্নত ব্যাচ কমিট ব্যবহার করা হয়েছে যাতে দ্রুততম সময়ে সম্পন্ন হয়।
    """
    query = db.query(ContractorProfile)
    if target_contractor_id:
        query = query.filter(ContractorProfile.id == target_contractor_id)
    else:
        # শুধুমাত্র সক্রিয় ঠিকাদার (ড্রাফট বা পজড নয়)
        query = query.filter(
            ContractorProfile.client_status.in_(["active", "complete"]),
            ContractorProfile.account_status.in_(["active", "complete", "onboarding"])
        )

    contractors = query.all()
    if not contractors:
        # ফলব্যাক: অন্তত একজন ক্লায়েন্ট থাকলে তা আনা
        contractors = db.query(ContractorProfile).all()

    tenders = db.query(Tender).all()
    processed_count = 0
    batch_counter = 0

    for contractor in contractors:
        # এই ঠিকাদারের বিদ্যমান অ্যাসেসমেন্টগুলো মেমোরিতে লোড করে দ্রুত লুকআপ নিশ্চিত করা
        existing_map = {
            a.tender_id: a for a in db.query(MatchAssessment).filter_by(contractor_id=contractor.id).all()
        }

        for tender in tenders:
            existing_assessment = existing_map.get(tender.id)
            assessment_result = evaluate_tender_for_contractor(contractor, tender)

            if not existing_assessment:
                assessment = MatchAssessment(
                    contractor_id=contractor.id,
                    tender_id=tender.id,
                    preference_fit_status=assessment_result["preference_fit_status"],
                    preference_reasons=assessment_result["preference_reasons"],
                    qualification_status=assessment_result["qualification_status"],
                    known_mismatches=assessment_result["known_mismatches"],
                    unknown_items_to_verify=assessment_result["unknown_items_to_verify"],
                    overall_fit_explanation_bn=assessment_result["overall_fit_explanation_bn"],
                    operator_review_status="pending"
                )
                db.add(assessment)
            else:
                existing_assessment.preference_fit_status = assessment_result["preference_fit_status"]
                existing_assessment.preference_reasons = assessment_result["preference_reasons"]
                existing_assessment.qualification_status = assessment_result["qualification_status"]
                existing_assessment.known_mismatches = assessment_result["known_mismatches"]
                existing_assessment.unknown_items_to_verify = assessment_result["unknown_items_to_verify"]
                existing_assessment.overall_fit_explanation_bn = assessment_result["overall_fit_explanation_bn"]

            processed_count += 1
            batch_counter += 1

            if batch_counter >= 300:
                db.commit()
                batch_counter = 0

        db.commit()

    return processed_count

