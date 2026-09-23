import logging
from typing import Dict, Any, List, Optional, Tuple, Set
from sqlalchemy.orm import Session

from backend.models import ContractorProfile
from backend.ingestion import ingest_single_tender
from backend.matching import run_matching_pipeline
from backend.egp_client import EGPClient

logger = logging.getLogger("ejarabd.egp_ingestion_service")


def is_candidate_relevant_prefilter(
    listing: Dict[str, Any],
    contractor: Optional[ContractorProfile] = None
) -> Tuple[bool, str]:
    """
    ডিটারমিনিস্টিক প্রি-ফিল্টারিং:
    দামি নোটিশ ভিউ (ViewTender.jsp) রিকোয়েস্ট পাঠানোর পূর্বেই স্পষ্ট অপ্রাসঙ্গিক টেন্ডার বাদ দেওয়া।
    
    নিয়ম:
    - ঠিকাদারের পছন্দের জেলা ও কাজের ধরন বিবেচনা করা হয়।
    - কোনো সন্দেহ বা সাধারণ দরপত্র হলে সেটিকে ক্যান্ডিডেট হিসেবে রাখা হয় ("When in doubt, fetch").
    - শুধুমাত্র স্পষ্ট অমিল থাকলে বাদ দেওয়া হয় (যেমন: দিনাজপুর কেন্দ্রিক ঠিকাদারের জন্য চট্টগ্রাম বা কক্সবাজারের কাজ)।
    """
    if not contractor:
        return True, "ঠিকাদার প্রোফাইল নির্দিষ্ট নেই; বিস্তারিত নোটিশ সংগ্রহ করা হবে"

    title = listing.get("title", "").lower()
    office = listing.get("procuring_entity_office", "").lower()
    agency = listing.get("agency", "").lower()
    nature = listing.get("procurement_nature", "").lower()

    # ১. কাজের ধরণ যাচাই
    if contractor.work_categories:
        # ঠিকাদার যদি শুধুমাত্র Civil / Road কাজ করেন এবং টেন্ডারটি যদি স্পষ্ট Goods (চিকিৎসা সামগ্রী, খাদ্য) হয়
        if "goods" in nature and not any(w in title for w in ["pipe", "culvert", "stone", "bitumen", "rod", "cement"]):
            # কিন্তু হেড অফিসের সাধারণ সাপ্লাই হলে বাদ দেওয়া যেতে পারে
            if any(med in title for med in ["soyabean", "lentil", "sugar", "medicine", "surgical", "doppler"]):
                return False, f"কাজের প্রকৃতি ({nature}: ভোগ্যপণ্য/চিকিৎসা সরঞ্জাম) ঠিকাদারের অভিজ্ঞতার সাথে মিলে না"

    # ২. জেলা ও অবস্থান যাচাই (পাইলট ঠিকাদার: দিনাজপুর)
    preferred_districts = [d.lower() for d in (contractor.preferred_districts or [])]
    if preferred_districts:
        text_corpus = f"{title} {office} {agency}"

        # যদি পছন্দের কোনো জেলার নাম উল্লেখ থাকে -> সরাসরি ক্যান্ডিডেট
        if any(pd in text_corpus for pd in preferred_districts) or any(w in text_corpus for w in ["দিনাজপুর", "dinajpur"]):
            return True, "পছন্দের জেলা (দিনাজপুর) সরাসরি নোটিশ বিবরণে পাওয়া গেছে"

        # প্রধান কার্যালয়ের দরপত্র (হেড অফিস) হলে সারা দেশের উপজেলা থাকতে পারে, তাই বাদ দেওয়া যাবে না
        if any(h in office for h in ["head office", "head quarter", "প্রধান কার্যালয়", "সদর দপ্তর", "chief engineer"]):
            return True, "প্রধান কার্যালয়ের দরপত্র; বিস্তারিত নোটিশে স্থানীয় প্যাকেজ থাকতে পারে"

        # কিন্তু স্থানীয় কার্যালয় যদি সম্পূর্ণ ভিন্ন ও দূরবর্তী জেলার হয়
        distant_districts = [
            "chattogram", "chittagong", "cox's bazar", "sylhet", "barishal",
            "khulna", "satkhira", "patuakhali", "noakhali", "cumilla"
        ]
        if any(dist in text_corpus for dist in distant_districts):
            return False, "কাজের এলাকা ও নির্বাহী প্রকৌশলীর অফিস আপনার নির্ধারিত অঞ্চলের সম্পূর্ণ বাইরে"

    return True, "প্রাথমিক শর্তাবলির সাথে সামঞ্জস্যপূর্ণ"


def run_egp_sync(
    db: Session,
    proc_nature: str = "2",        # ২ = Works
    proc_method: str = "0",        # ০ = All
    proc_type: str = "",
    keyword: Optional[str] = None,
    tender_id: Optional[str] = None,
    page_size: int = 10,
    max_pages: Optional[int] = 1,
    prefilter: bool = True,
    auto_match: bool = True,
    fetch_details: bool = True,
    client: Optional[EGPClient] = None
) -> Dict[str, Any]:
    """
    e-GP পোর্টাল থেকে লাইভ টেন্ডার অনুসন্ধান, প্রি-ফিল্টারিং, বিস্তারিত নোটিশ সংগ্রহ ও ইনজেশন পাইপলাইন।
    
    রিটার্ন স্ট্যাটিসটিক্স:
    - pages_scanned
    - listings_discovered
    - unique_tenders
    - candidates_after_filtering
    - details_fetched
    - successfully_ingested
    - created
    - updated
    - failed_details
    - failed_ingestion
    - skipped_tenders
    - matches_evaluated
    """
    close_client = False
    if client is None:
        client = EGPClient()
        close_client = True

    pilot_contractor = db.query(ContractorProfile).first()

    pages_scanned = 0
    total_pages_available = 1
    listings_discovered = 0
    unique_tenders: Set[str] = set()
    candidates_after_filtering = 0
    details_fetched = 0
    successfully_ingested = 0
    created_count = 0
    updated_count = 0
    failed_details: List[Dict[str, str]] = []
    failed_ingestion: List[Dict[str, str]] = []
    skipped_tenders: List[Dict[str, str]] = []

    try:
        page_no = 1
        limit_pages = max_pages if max_pages is not None else 999999

        while page_no <= limit_pages:
            display_limit = str(limit_pages) if max_pages is not None else str(total_pages_available)
            logger.info(f"Scanning e-GP page {page_no}/{display_limit} (size: {page_size})...")
            search_res = client.search_tenders(
                page_no=page_no,
                size=page_size,
                proc_nature=proc_nature,
                proc_method=proc_method,
                proc_type=proc_type,
                keyword=keyword or "",
                tender_id=tender_id or ""
            )

            pages_scanned += 1
            if isinstance(search_res, dict):
                total_pages_available = search_res.get("total_pages", 1)
                page_tenders = search_res.get("tenders", [])
            elif isinstance(search_res, list):
                total_pages_available = 1
                page_tenders = search_res
            else:
                total_pages_available = 1
                page_tenders = []

            if not page_tenders:
                logger.info("No tenders returned on current page; stopping pagination.")
                break

            for listing in page_tenders:
                tid = listing.get("tender_id")
                if not tid:
                    continue

                listings_discovered += 1

                # পেজিনেশনের মাঝে ডুপ্লিকেট টেন্ডার আইডি প্রতিরোধ
                if tid in unique_tenders:
                    continue
                unique_tenders.add(tid)

                # ৩. ডিটারমিনিস্টিক প্রি-ফিল্টারিং
                if prefilter and pilot_contractor:
                    is_rel, reason = is_candidate_relevant_prefilter(listing, pilot_contractor)
                    if not is_rel:
                        skipped_tenders.append({"tender_id": tid, "title": listing.get("title", ""), "reason": reason})
                        continue

                candidates_after_filtering += 1

                # ৪. বিস্তারিত নোটিশ আহরণ (ViewTender.jsp)
                merged_payload = dict(listing)
                if fetch_details:
                    try:
                        logger.info(f"Fetching details for candidate tender: {tid}...")
                        details = client.get_tender_details(tid)
                        if details:
                            # ডিটেইল ডেটা লিস্টিং ডেটার উপর অগ্রাধিকার পাবে (যেমন: নির্দিষ্ট সিকিউরিটি ও যোগ্যতা শর্ত)
                            for k, v in details.items():
                                if v is not None:
                                    merged_payload[k] = v
                            details_fetched += 1
                    except Exception as e:
                        logger.warning(f"Could not fetch details for tender {tid}: {e}")
                        failed_details.append({"tender_id": tid, "error": str(e)})
                        # ডিটেইল ফেইল করলেও লিস্টিং ডেটা অক্ষত রেখে ইনজেশন চলবে

                # ৫. ইনজেশন ও ডিডুপ্লিকেশন (backend/ingestion.py)
                ingest_res = ingest_single_tender(db, merged_payload, update_existing=True)
                if ingest_res.get("status") == "success":
                    successfully_ingested += 1
                    act = ingest_res.get("action")
                    if act == "created":
                        created_count += 1
                    elif act in ["updated", "skipped_duplicate"]:
                        updated_count += 1
                else:
                    err_msg = ingest_res.get("error") or str(ingest_res.get("errors", "Ingestion failed"))
                    failed_ingestion.append({"tender_id": tid, "error": err_msg})

            # যদি বর্তমান পেজ শেষ পেজের সমান বা বেশি হয়, থামা
            if page_no >= total_pages_available:
                break
            page_no += 1

    finally:
        if close_client and client:
            client.close()

    # ৬. ম্যাচিং পাইপলাইন সমন্বয় (ঐচ্ছিক)
    matches_evaluated = 0
    if auto_match and (created_count > 0 or updated_count > 0):
        try:
            matches_evaluated = run_matching_pipeline(db)
        except Exception as e:
            logger.error(f"Error running matching pipeline after e-GP sync: {e}")

    stats = {
        "status": "success",
        "pages_scanned": pages_scanned,
        "total_pages_available": total_pages_available,
        "listings_discovered": listings_discovered,
        "unique_tenders": len(unique_tenders),
        "candidates_after_filtering": candidates_after_filtering,
        "details_fetched": details_fetched,
        "successfully_ingested": successfully_ingested,
        "created": created_count,
        "updated": updated_count,
        "failed_details_count": len(failed_details),
        "failed_details": failed_details,
        "failed_ingestion_count": len(failed_ingestion),
        "failed_ingestion": failed_ingestion,
        "skipped_tenders_count": len(skipped_tenders),
        "matches_evaluated": matches_evaluated
    }

    return stats
