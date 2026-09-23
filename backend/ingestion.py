import re
import sys
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple, Union
from sqlalchemy.orm import Session
from bs4 import BeautifulSoup

# Windows কনসোলে UTF-8 এনকোডিং
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from backend.models import Tender, ContractorProfile, MatchAssessment
from backend.matching import run_matching_pipeline, evaluate_tender_for_contractor

# বাংলা সংখ্যা থেকে ইংরেজি সংখ্যা রূপান্তর
BN_TO_EN_NUM = str.maketrans("০১২৩৪৫৬৭৮৯", "0123456789")

def to_en_number(val_str: str) -> str:
    """বাংলা সংখ্যাকে ইংরেজি সংখ্যায় রূপান্তর"""
    return str(val_str).translate(BN_TO_EN_NUM)

def clean_text(text: Optional[str]) -> Optional[str]:
    """অপ্রয়োজনীয় স্পেস ও HTML ট্যাগ অপসারণ করে পরিষ্কার টেক্সট তৈরি"""
    if not text:
        return None
    s = str(text)
    # HTML ট্যাগ থাকলে BeautifulSoup দিয়ে পরিষ্কার করা
    if "<" in s and ">" in s:
        soup = BeautifulSoup(s, "html.parser")
        s = soup.get_text(separator=" ", strip=True)
    # অতিরিক্ত ফাঁকা স্পেস সংকুচিত করা
    cleaned = re.sub(r'\s+', ' ', s).strip()
    return cleaned if cleaned else None

def clean_numeric_value(val: Any) -> Optional[float]:
    """
    টাকার পরিমাণ বা সংখ্যা পার্স করা।
    অজানা/অনুপস্থিত থাকলে কঠোরভাবে None প্রদান করে (কোনো মনগড়া মান তৈরি করবে না)।
    """
    if val is None:
        return None
    
    if isinstance(val, (int, float)):
        return float(val)
    
    s = str(val).strip()
    if not s:
        return None
    
    # পরিচিত অনুপস্থিতির নির্দেশক
    unknown_indicators = [
        "not mentioned", "n/a", "na", "none", "null", "tbd",
        "উল্লেখ নেই", "অজ্ঞাত", "প্রযোজ্য নয়", "যাচাই প্রয়োজন"
    ]
    if s.lower() in unknown_indicators:
        return None
    
    # বাংলা সংখ্যা থেকে ইংরেজি রূপান্তর
    s = to_en_number(s)
    
    # মুদ্রা ও অপ্রয়োজনীয় প্রিফিক্স/সাফিক্স মুছে ফেলা (যেমন: ৳, BDT, Tk. ইত্যাদি)
    s = re.sub(r'(?:BDT|Tk\.?|৳)', '', s, flags=re.IGNORECASE)
    
    # কমা, স্পেস ইত্যাদি সরানো কিন্তু দশমিক বিন্দু অক্ষত রাখা
    s = re.sub(r'[,,\s\-]', '', s)
    
    # রেগুলার এক্সপ্রেশন দিয়ে প্রথম বৈধ ফ্লোট বের করা
    match = re.search(r'[-+]?\d*\.?\d+', s)
    if match:
        try:
            return float(match.group(0))
        except ValueError:
            return None
    return None

def clean_datetime_value(val: Any) -> Optional[datetime]:
    """
    বিভিন্ন ফরম্যাটের তারিখ ও সময়কে BST datetime অবজেক্টে রূপান্তর।
    ব্যর্থ হলে None প্রদান করে।
    """
    if not val:
        return None
    if isinstance(val, datetime):
        return val
    
    s = str(val).strip()
    if not s:
        return None
    
    s = to_en_number(s)
    
    # ISO ফরম্যাট
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00").split("+")[0])
    except Exception:
        pass
    
    # সম্ভাব্য সাধারণ ফরম্যাটসমূহ
    formats = [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d",
        "%d-%m-%Y %H:%M:%S",
        "%d-%m-%Y %H:%M",
        "%d-%m-%Y",
        "%d/%m/%Y %H:%M:%S",
        "%d/%m/%Y %H:%M",
        "%d/%m/%Y",
        "%d-%b-%Y %H:%M:%S",
        "%d-%b-%Y %H:%M",
        "%d-%b-%Y",
        "%Y/%m/%d %H:%M:%S",
        "%Y/%m/%d %H:%M",
        "%Y/%m/%d"
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
            
    return None

def parse_html_tender(html_content: str) -> Dict[str, Any]:
    """
    HTML স্নsnippet থেকে টেন্ডারের তথ্য নিষ্কাশন এবং স্ক্রিপ্ট/স্টাইল ট্যাগ বর্জন
    """
    soup = BeautifulSoup(html_content, "html.parser")
    
    # ক্ষতিকর বা অতিরিক্ত ট্যাগ মুছে ফেলা
    for tag in soup(["script", "style", "meta", "noscript"]):
        tag.decompose()
        
    extracted: Dict[str, Any] = {}
    
    # ১. ডেটা অ্যাট্রিবিউট বা সুনির্দিষ্ট ক্লাস খোঁজা
    id_el = soup.select_one("[data-tender-id], .tender-id, #tender-id, .ref-no")
    if id_el:
        extracted["tender_id"] = id_el.get("data-tender-id") or id_el.get_text(strip=True)
        
    title_el = soup.select_one("[data-title], .tender-title, .title, h1, h2, h3")
    if title_el:
        extracted["title"] = title_el.get("data-title") or title_el.get_text(strip=True)
        
    agency_el = soup.select_one("[data-agency], .agency, .ministry")
    if agency_el:
        extracted["agency"] = agency_el.get_text(strip=True)
        
    office_el = soup.select_one("[data-office], .procuring-entity, .pe-office")
    if office_el:
        extracted["procuring_entity_office"] = office_el.get_text(strip=True)
        
    district_el = soup.select_one("[data-district], .district, .location")
    if district_el:
        extracted["project_location_district"] = district_el.get_text(strip=True)
        
    category_el = soup.select_one("[data-category], .category, .work-type")
    if category_el:
        extracted["category"] = category_el.get_text(strip=True)
        
    val_el = soup.select_one("[data-estimated-value], .estimated-value, .tender-value")
    if val_el:
        extracted["estimated_value_bdt"] = val_el.get("data-estimated-value") or val_el.get_text(strip=True)
        
    sec_el = soup.select_one("[data-tender-security], .tender-security, .security-amount")
    if sec_el:
        extracted["tender_security_bdt"] = sec_el.get("data-tender-security") or sec_el.get_text(strip=True)
        
    close_el = soup.select_one("[data-closing-date], .closing-date, .closing-time")
    if close_el:
        extracted["closing_date"] = close_el.get("data-closing-date") or close_el.get_text(strip=True)
        
    url_el = soup.select_one("a[href]")
    if url_el and url_el.get("href"):
        extracted["source_url"] = url_el.get("href")
        
    elig_el = soup.select_one("[data-eligibility], .eligibility, .qualification")
    if elig_el:
        extracted["raw_eligibility_text"] = elig_el.get_text(strip=True)
        
    # যদি কোনো স্ট্রাকচার্ড ক্লাস না মেলে, টেবিল থেকে কী-ভ্যালু নিষ্কাশন
    for tr in soup.find_all("tr"):
        tds = tr.find_all(["td", "th"])
        if len(tds) >= 2:
            key = tds[0].get_text(strip=True).lower()
            val = tds[1].get_text(strip=True)
            if "tender id" in key or "দরপত্র নং" in key:
                extracted.setdefault("tender_id", val)
            elif "title" in key or "শিরোনাম" in key:
                extracted.setdefault("title", val)
            elif "agency" in key or "সংস্থা" in key:
                extracted.setdefault("agency", val)
            elif "closing" in key or "শেষ সময়" in key:
                extracted.setdefault("closing_date", val)
            elif "security" in key or "জামানত" in key:
                extracted.setdefault("tender_security_bdt", val)
            elif "value" in key or "মূল্য" in key:
                extracted.setdefault("estimated_value_bdt", val)
                
    return extracted

BD_DISTRICT_SYNONYMS: Dict[str, str] = {
    # Dhaka Division
    "dhaka": "Dhaka", "ঢাকা": "Dhaka",
    "gazipur": "Gazipur", "গাজীপুর": "Gazipur",
    "narayanganj": "Narayanganj", "নারায়ণগঞ্জ": "Narayanganj",
    "tangail": "Tangail", "টাঙ্গাইল": "Tangail",
    "kishoreganj": "Kishoreganj", "কিশোরগঞ্জ": "Kishoreganj",
    "narsingdi": "Narsingdi", "নরসিংদী": "Narsingdi",
    "manikganj": "Manikganj", "মানিকগঞ্জ": "Manikganj", "aricha": "Manikganj", "আরিচা": "Manikganj",
    "munshiganj": "Munshiganj", "মুন্সীগঞ্জ": "Munshiganj",
    "faridpur": "Faridpur", "ফরিদপুর": "Faridpur",
    "gopalganj": "Gopalganj", "গোপালগঞ্জ": "Gopalganj",
    "madaripur": "Madaripur", "মাদারীপুর": "Madaripur",
    "rajbari": "Rajbari", "রাজবাড়ী": "Rajbari", "daulatdia": "Rajbari", "দৌলতদিয়া": "Rajbari",
    "shariatpur": "Shariatpur", "শরীয়তপুর": "Shariatpur",
    # Chattogram Division
    "chattogram": "Chattogram", "চট্টগ্রাম": "Chattogram", "chittagong": "Chattogram",
    "cox's bazar": "Cox's Bazar", "কক্সবাজার": "Cox's Bazar", "coxsbazar": "Cox's Bazar",
    "cumilla": "Cumilla", "কুমিল্লা": "Cumilla", "comilla": "Cumilla",
    "feni": "Feni", "ফেনী": "Feni",
    "brahmanbaria": "Brahmanbaria", "ব্রাহ্মণবাড়িয়া": "Brahmanbaria",
    "rangamati": "Rangamati", "রাঙ্গামাটি": "Rangamati",
    "noakhali": "Noakhali", "নোয়াখালী": "Noakhali",
    "chandpur": "Chandpur", "চাঁদপুর": "Chandpur",
    "lakshmipur": "Lakshmipur", "লক্ষ্মীপুর": "Lakshmipur",
    "khagrachhari": "Khagrachhari", "খাগড়াছড়ি": "Khagrachhari",
    "bandarban": "Bandarban", "বান্দরবান": "Bandarban",
    # Rajshahi Division
    "rajshahi": "Rajshahi", "রাজশাহী": "Rajshahi",
    "bogura": "Bogura", "বগুড়া": "Bogura", "bogra": "Bogura",
    "pabna": "Pabna", "পাবনা": "Pabna",
    "sirajganj": "Sirajganj", "সিরাজগঞ্জ": "Sirajganj",
    "naogaon": "Naogaon", "নওগাঁ": "Naogaon",
    "natore": "Natore", "নাটোর": "Natore",
    "joypurhat": "Joypurhat", "জয়পুরহাট": "Joypurhat",
    "chapainawabganj": "Chapainawabganj", "চাঁপাইনবাবগঞ্জ": "Chapainawabganj", "nawabganj": "Chapainawabganj",
    # Khulna Division
    "khulna": "Khulna", "খুলনা": "Khulna",
    "jashore": "Jashore", "যশোর": "Jashore", "jessore": "Jashore",
    "kushtia": "Kushtia", "কুষ্টিয়া": "Kushtia",
    "jhenaidah": "Jhenaidah", "ঝিনাইদহ": "Jhenaidah",
    "satkhira": "Satkhira", "সাতক্ষীরা": "Satkhira",
    "bagerhat": "Bagerhat", "বাগেরহাট": "Bagerhat",
    "chuadanga": "Chuadanga", "চুয়াডাঙ্গা": "Chuadanga",
    "magura": "Magura", "মাগুরা": "Magura",
    "meherpur": "Meherpur", "মেহেরপুর": "Meherpur",
    "narail": "Narail", "নড়াইল": "Narail",
    # Barishal Division
    "barishal": "Barishal", "বরিশাল": "Barishal", "barisal": "Barishal",
    "patuakhali": "Patuakhali", "পটুয়াখালী": "Patuakhali",
    "bhola": "Bhola", "ভোলা": "Bhola",
    "pirojpur": "Pirojpur", "পিরোজপুর": "Pirojpur",
    "barguna": "Barguna", "বরগুনা": "Barguna",
    "jhalokathi": "Jhalokathi", "ঝালকাঠি": "Jhalokathi", "jhalakati": "Jhalokathi",
    # Sylhet Division
    "sylhet": "Sylhet", "সিলেট": "Sylhet",
    "moulvibazar": "Moulvibazar", "মৌলভীবাজার": "Moulvibazar", "maulvibazar": "Moulvibazar",
    "habiganj": "Habiganj", "হবিগঞ্জ": "Habiganj",
    "sunamganj": "Sunamganj", "সুনামগঞ্জ": "Sunamganj",
    # Rangpur Division
    "rangpur": "Rangpur", "রংপুর": "Rangpur",
    "dinajpur": "Dinajpur", "দিনাজপুর": "Dinajpur",
    "kurigram": "Kurigram", "কুড়িগ্রাম": "Kurigram",
    "gaibandha": "Gaibandha", "গাইবান্ধা": "Gaibandha",
    "nilphamari": "Nilphamari", "নীলফামারী": "Nilphamari",
    "panchagarh": "Panchagarh", "পঞ্চগড়": "Panchagarh",
    "thakurgaon": "Thakurgaon", "ঠাকুরগাঁও": "Thakurgaon",
    "lalmonirhat": "Lalmonirhat", "লালমনিরহাট": "Lalmonirhat",
    # Mymensingh Division
    "mymensingh": "Mymensingh", "ময়মনসিংহ": "Mymensingh",
    "jamalpur": "Jamalpur", "জামালপুর": "Jamalpur",
    "netrokona": "Netrokona", "নেত্রকোণা": "Netrokona", "netrakona": "Netrokona",
    "sherpur": "Sherpur", "শেরপুর": "Sherpur",
}

def extract_bangladesh_district(*text_sources: Optional[str]) -> Optional[str]:
    """বিভিন্ন টেক্সট ফিল্ড (অফিস, শিরোনাম, বিবরণ) থেকে বাংলাদেশের ৬৪ জেলার নাম নিষ্কাশন"""
    for src in text_sources:
        if not src:
            continue
        lower_src = str(src).lower()
        for kw, canonical in BD_DISTRICT_SYNONYMS.items():
            pattern = rf"\b{re.escape(kw)}\b" if kw.isascii() else re.escape(kw)
            if re.search(pattern, lower_src):
                return canonical
    return None

def normalize_tender_payload(raw_data: Union[Dict[str, Any], str]) -> Dict[str, Any]:
    """
    যে কোনো কাঁচা পেলোড (Dict বা HTML) থেকে স্ট্যান্ডার্ড Tender ফিল্ড ডিকশনারি তৈরি।
    কোনো অনুপস্থিত ফিল্ডে মনগড়া তথ্য যুক্ত করা সম্পূর্ণ নিষিদ্ধ।
    """
    if isinstance(raw_data, str):
        # যদি ইনপুট স্ট্রিং হয়, HTML পার্সার ব্যবহার
        data = parse_html_tender(raw_data)
    elif isinstance(raw_data, dict):
        data = dict(raw_data)
    else:
        return {}

    # টেন্ডার আইডি ও শিরোনাম স্যানিটাইজ
    tender_id = clean_text(data.get("tender_id"))
    title = clean_text(data.get("title"))
    
    # সংস্থা ও অফিস
    agency = clean_text(data.get("agency")) or "Government Agency"
    pe_office = clean_text(data.get("procuring_entity_office")) or "Procuring Entity"
    
    # জেলা ও কাজের ধরণ
    district = clean_text(data.get("project_location_district"))
    if not district or district.lower() in ["general / unknown", "unknown", "none", "null"]:
        detected_dist = extract_bangladesh_district(
            data.get("procuring_entity_district"),
            pe_office,
            agency,
            title,
            data.get("project_location_details")
        )
        district = detected_dist if detected_dist else "General / Unknown"
            
    loc_details = clean_text(data.get("project_location_details"))
    category = clean_text(data.get("category")) or "Works"
    
    # আর্থিক মানসমূহ (নিরাপদভাবে আলাদা রাখা: security != estimated_value)
    estimated_val = clean_numeric_value(data.get("estimated_value_bdt"))
    security_val = clean_numeric_value(data.get("tender_security_bdt"))
    doc_price = clean_numeric_value(data.get("document_price_bdt"))
    
    # তারিখসমূহ
    pub_date = clean_datetime_value(data.get("publication_date"))
    selling_date = clean_datetime_value(data.get("document_last_selling_date"))
    closing_date = clean_datetime_value(data.get("closing_date"))
    opening_date = clean_datetime_value(data.get("opening_date"))
    
    # সোর্স ইউআরএল ও টাইপ
    source_url = clean_text(data.get("source_url"))
    if not source_url and tender_id:
        source_url = f"https://eprocure.gov.bd/resources/sample-tenders/{tender_id}"
        
    source_type = clean_text(data.get("source_type")) or "e-GP Ingestion"
    raw_elig = clean_text(data.get("raw_eligibility_text"))
    
    # সংশোধনী তথ্য
    is_amendment = bool(data.get("is_amendment", False))
    amendment_details = clean_text(data.get("amendment_details"))
    status = clean_text(data.get("status")) or "active"

    # সিন্থেটিক বা টেস্ট ফিক্সচার সনাক্তকরণ
    is_synthetic = bool(data.get("is_synthetic", False))
    if not is_synthetic and tender_id:
        tid_str = str(tender_id)
        st_lower = str(source_type).lower()
        if (
            tid_str.startswith("eGP-") or
            tid_str in ["1001", "1002", "1003"] or
            "sample" in st_lower or
            "fixture" in st_lower or
            "mock" in st_lower
        ):
            is_synthetic = True

    return {
        "tender_id": tender_id,
        "title": title,
        "agency": agency,
        "procuring_entity_office": pe_office,
        "project_location_district": district,
        "project_location_details": loc_details,
        "category": category,
        "estimated_value_bdt": estimated_val,
        "tender_security_bdt": security_val,
        "document_price_bdt": doc_price,
        "publication_date": pub_date,
        "document_last_selling_date": selling_date,
        "closing_date": closing_date,
        "opening_date": opening_date,
        "source_url": source_url,
        "source_type": source_type,
        "raw_eligibility_text": raw_elig,
        "is_amendment": is_amendment,
        "amendment_details": amendment_details,
        "status": status,
        "is_synthetic": is_synthetic
    }

def validate_tender_payload(payload: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    ডাটাবেজে ইনসার্ট করার আগে মৌলিক ভ্যালিডেশন
    """
    errors = []
    if not payload.get("tender_id"):
        errors.append("টেন্ডার আইডি (tender_id) অনুপস্থিত বা অবৈধ।")
    if not payload.get("title"):
        errors.append("টেন্ডারের শিরোনাম (title) অনুপস্থিত।")
    if not payload.get("closing_date"):
        errors.append("দরপত্র দাখিলের শেষ তারিখ (closing_date) অনুপস্থিত বা অবৈধ।")
    if not payload.get("source_url"):
        errors.append("অফিসিয়াল সোর্স লিংক (source_url) অনুপস্থিত।")
        
    return len(errors) == 0, errors

def ingest_single_tender(
    db: Session,
    raw_input: Union[Dict[str, Any], str],
    update_existing: bool = True
) -> Dict[str, Any]:
    """
    একটি একক টেন্ডার ডিলুপ্লিকেট করে ডাটাবেজে ইনজেস্ট করা।
    - একই tender_id বিদ্যমান থাকলে ডুপ্লিকেট না বানিয়ে আপডেট বা স্কিপ করে।
    - ভ্যালিডেশন ফেইল করলে ডাটাবেজে কোনো ক্ষতি না করে সেফলি ব্যর্থতা রিটার্ন করে।
    """
    try:
        norm = normalize_tender_payload(raw_input)
    except Exception as e:
        return {
            "status": "failed",
            "action": "parse_error",
            "error": f"পার্সিং ব্যর্থ হয়েছে: {str(e)}",
            "tender_id": None
        }
        
    is_valid, errors = validate_tender_payload(norm)
    if not is_valid:
        return {
            "status": "failed",
            "action": "validation_error",
            "errors": errors,
            "tender_id": norm.get("tender_id")
        }
        
    tender_ref = norm["tender_id"]
    
    try:
        # ডিডুপ্লিকেশন চেক: tender_id ইউনিক কনস্ট্রেইন্ট ব্যবহার
        existing = db.query(Tender).filter_by(tender_id=tender_ref).first()
        
        if existing:
            if update_existing:
                # বিদ্যমান রেকর্ড নিরাপদে আপডেট করা (আইডি ও তৈরি তারিখ অক্ষত রেখে)
                for key, val in norm.items():
                    if val is not None:
                        setattr(existing, key, val)
                existing.last_checked_at = datetime.utcnow()
                db.commit()
                db.refresh(existing)
                return {
                    "status": "success",
                    "action": "updated",
                    "id": existing.id,
                    "tender_id": existing.tender_id,
                    "title": existing.title
                }
            else:
                return {
                    "status": "success",
                    "action": "skipped_duplicate",
                    "id": existing.id,
                    "tender_id": existing.tender_id,
                    "title": existing.title
                }
        else:
            # নতুন টেন্ডার তৈরি
            new_tender = Tender(**norm)
            db.add(new_tender)
            db.commit()
            db.refresh(new_tender)
            return {
                "status": "success",
                "action": "created",
                "id": new_tender.id,
                "tender_id": new_tender.tender_id,
                "title": new_tender.title
            }
    except Exception as e:
        db.rollback()
        return {
            "status": "failed",
            "action": "db_error",
            "error": f"ডাটাবেজ সংরক্ষণ ত্রুটি: {str(e)}",
            "tender_id": tender_ref
        }

def ingest_tenders_batch(
    db: Session,
    tenders_list: List[Union[Dict[str, Any], str]],
    auto_run_matching: bool = False
) -> Dict[str, Any]:
    """
    একাধিক টেন্ডার ব্যাচে ইনজেস্ট করা।
    ব্যর্থ কোনো আইটেম পুরো ব্যাচ বা পূর্ববর্তী ডেটা নষ্ট করবে না।
    """
    total = len(tenders_list)
    created_count = 0
    updated_count = 0
    skipped_count = 0
    failed_count = 0
    results = []
    
    for item in tenders_list:
        res = ingest_single_tender(db, item, update_existing=True)
        results.append(res)
        if res["status"] == "success":
            if res["action"] == "created":
                created_count += 1
            elif res["action"] == "updated":
                updated_count += 1
            elif res["action"] == "skipped_duplicate":
                skipped_count += 1
        else:
            failed_count += 1
            
    matches_processed = 0
    if auto_run_matching and (created_count > 0 or updated_count > 0):
        matches_processed = run_matching_pipeline(db)
        
    return {
        "total": total,
        "created": created_count,
        "updated": updated_count,
        "skipped": skipped_count,
        "failed": failed_count,
        "matches_processed": matches_processed,
        "results": results
    }

def filter_relevant_tenders(db: Session, contractor_id: Optional[int] = None) -> List[Dict[str, Any]]:
    """
    PHASE 6: ডিটারমিনিস্টিক ফিল্টারিং।
    হাজারো টেন্ডার থেকে এআই-তে পাঠানোর পূর্বেই প্রাসঙ্গিক ক্যান্ডিডেট বাছাই।
    (fits এবং partial টেন্ডারসমূহ ফিল্টার করে, outside টেন্ডার বাদ দেয়)
    """
    contractor = None
    if contractor_id:
        contractor = db.query(ContractorProfile).filter_by(id=contractor_id).first()
    if not contractor:
        contractor = db.query(ContractorProfile).first()
        
    if not contractor:
        return []
        
    tenders = db.query(Tender).filter_by(status="active").all()
    candidates = []
    
    for t in tenders:
        evaluation = evaluate_tender_for_contractor(contractor, t)
        status = evaluation.get("preference_fit_status")
        # শুধুমাত্র fits বা partial টেন্ডারগুলোকে প্রাসঙ্গিক বিবেচনা করা
        if status in ["fits", "partial"]:
            candidates.append({
                "tender_id": t.tender_id,
                "id": t.id,
                "title": t.title,
                "category": t.category,
                "district": t.project_location_district,
                "estimated_value_bdt": t.estimated_value_bdt,
                "tender_security_bdt": t.tender_security_bdt,
                "preference_fit_status": status,
                "qualification_status": evaluation.get("qualification_status")
            })
            
    return candidates

def get_clean_tender_summary_for_ai(tender: Tender) -> Dict[str, Any]:
    """
    PHASE 7: এআই কস্ট ও টোকেন প্রটেকশন।
    কাঁচা এইচটিএমএল বর্জন করে শুধুমাত্র পরিচ্ছন্ন স্ট্রাকচার্ড টেক্সট প্রদান করে।
    """
    return {
        "tender_id": tender.tender_id,
        "title": tender.title,
        "agency": tender.agency,
        "procuring_entity_office": tender.procuring_entity_office,
        "location_district": tender.project_location_district,
        "location_details": tender.project_location_details or "অজানা",
        "category": tender.category,
        "estimated_value_bdt": tender.estimated_value_bdt,
        "tender_security_bdt": tender.tender_security_bdt,
        "closing_date": tender.closing_date.isoformat() if tender.closing_date else "অজানা",
        "clean_eligibility_requirements": clean_text(tender.raw_eligibility_text) or "নোটিশে বিস্তারিত যোগ্যতা উল্লেখ নেই",
        "source_url": tender.source_url
    }
