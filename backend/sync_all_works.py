import os
import sys
import time
import logging
from typing import Dict, Any, List, Set
from datetime import datetime

# Windows কনসোলে UTF-8 এনকোডিং
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.database import SessionLocal
from backend.models import Tender, ContractorProfile
from backend.egp_client import EGPClient
from backend.ingestion import ingest_single_tender
from backend.matching import run_matching_pipeline

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("ejarabd.sync_all_works")


def fetch_and_ingest_all_live_works() -> Dict[str, Any]:
    """
    Fetch all currently live Works tenders from e-GP,
    paginate through every available page,
    collect them, deduplicate them, ingest them into EjaraBD,
    and report the exact number found/processed/failed.
    """
    start_time = time.time()
    db = SessionLocal()
    client = EGPClient(delay_min=0.8, delay_max=1.5)

    print("=" * 70)
    print("  EjaraBD — e-GP Live Works Tender Sync & Ingestion Pipeline")
    print("=" * 70)
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S BST')}")
    print("Filter: Category='Works' (procNature='2'), ViewType='Live'")
    print("Page size: 100 tenders per page (maximum polite bulk)")
    print("-" * 70)

    all_raw_listings: List[Dict[str, Any]] = []
    seen_ids: Set[str] = set()
    page_boundary_duplicates: int = 0
    pages_scanned = 0
    total_pages_available = 1

    try:
        # Step 1: Ensure session
        client.ensure_session()

        # Step 2: Paginate through all pages
        curr_page = 1
        while True:
            logger.info(f"Requesting e-GP page {curr_page} (size=100)...")
            res = client.search_page(
                page_no=curr_page,
                size=100,
                proc_nature="2",
                view_type="Live"
            )

            pages_scanned += 1
            total_pages_available = res.get("total_pages", 1)
            tenders_on_page = res.get("tenders", [])

            if not tenders_on_page:
                logger.info(f"Page {curr_page} returned 0 tenders. Pagination completed.")
                break

            new_on_this_page = 0
            for t in tenders_on_page:
                all_raw_listings.append(t)
                tid = t.get("tender_id")
                if tid:
                    if tid in seen_ids:
                        page_boundary_duplicates += 1
                    else:
                        seen_ids.add(tid)
                        new_on_this_page += 1

            print(f"  [Page {curr_page:2d}/{total_pages_available:2d}] Fetched {len(tenders_on_page):3d} rows | New unique: {new_on_this_page:3d} | Total unique so far: {len(seen_ids):4d}")

            if curr_page >= total_pages_available:
                logger.info(f"Reached last page ({total_pages_available}). Pagination completed.")
                break

            curr_page += 1

        print("-" * 70)
        print(f"Pagination Finished: {pages_scanned} pages scanned.")
        print(f"Total Rows Discovered: {len(all_raw_listings)}")
        print(f"Unique Tenders Collected: {len(seen_ids)}")
        print(f"Duplicates across Page Boundaries: {page_boundary_duplicates}")
        print("-" * 70)

        # Step 3: Ingest and deduplicate into EjaraBD Database
        print("Starting Database Ingestion & Deduplication into EjaraBD...")
        created_count = 0
        updated_count = 0
        failed_count = 0
        failed_details: List[Dict[str, Any]] = []

        # Deduplicate collection in memory first
        unique_tenders_dict: Dict[str, Dict[str, Any]] = {}
        for t in all_raw_listings:
            tid = t.get("tender_id")
            if tid and tid not in unique_tenders_dict:
                unique_tenders_dict[tid] = t

        for i, (tid, tender_payload) in enumerate(unique_tenders_dict.items(), 1):
            try:
                ingest_res = ingest_single_tender(db, tender_payload, update_existing=True)
                if ingest_res.get("status") == "success":
                    act = ingest_res.get("action")
                    if act == "created":
                        created_count += 1
                    elif act in ["updated", "skipped_duplicate"]:
                        updated_count += 1
                else:
                    failed_count += 1
                    err_msg = ingest_res.get("error") or str(ingest_res.get("errors", "Ingestion failed"))
                    failed_details.append({"tender_id": tid, "error": err_msg})
            except Exception as e:
                failed_count += 1
                failed_details.append({"tender_id": tid, "error": str(e)})

            if i % 250 == 0 or i == len(unique_tenders_dict):
                print(f"  Processed {i:4d}/{len(unique_tenders_dict):4d} tenders (Created: {created_count}, Updated: {updated_count}, Failed: {failed_count})")

        # Step 4: Run auto-matching pipeline for contractor profiles
        print("Running Deterministic Matching Pipeline for Profiles...")
        matches_evaluated = 0
        try:
            matches_evaluated = run_matching_pipeline(db)
            print(f"Evaluated matches across all contractors. New/updated assessments: {matches_evaluated}")
        except Exception as e:
            logger.warning(f"Matching pipeline evaluation warning: {e}")

        # Total tenders currently in DB
        db_total_tenders = db.query(Tender).count()
        works_in_db = db.query(Tender).filter(Tender.category == "Works").count()

        elapsed_time = time.time() - start_time

        stats = {
            "status": "success",
            "pages_scanned": pages_scanned,
            "total_pages_available": total_pages_available,
            "total_found": len(all_raw_listings),
            "unique_collected": len(unique_tenders_dict),
            "page_boundary_duplicates": page_boundary_duplicates,
            "processed_successfully": created_count + updated_count,
            "created": created_count,
            "updated": updated_count,
            "failed": failed_count,
            "failed_details": failed_details,
            "db_total_tenders": db_total_tenders,
            "db_works_tenders": works_in_db,
            "matches_evaluated": matches_evaluated,
            "elapsed_seconds": round(elapsed_time, 2)
        }

        print("=" * 70)
        print("  FINAL INGESTION SUMMARY REPORT")
        print("=" * 70)
        print(f"  • Pages Scanned:               {pages_scanned} / {total_pages_available}")
        print(f"  • Total Live Works Found:       {stats['total_found']}")
        print(f"  • Unique Tenders Collected:    {stats['unique_collected']}")
        print(f"  • Duplicates Filtered:         {stats['page_boundary_duplicates']}")
        print(f"  • Successfully Processed:      {stats['processed_successfully']}")
        print(f"      - Newly Created:           {stats['created']}")
        print(f"      - Updated Existing:        {stats['updated']}")
        print(f"  • Failed Ingestion:            {stats['failed']}")
        print(f"  • Total Tenders Now in DB:     {db_total_tenders} (Works: {works_in_db})")
        print(f"  • Contractor Matches Evaluated:{matches_evaluated}")
        print(f"  • Total Time Elapsed:          {stats['elapsed_seconds']}s")
        print("=" * 70)

        return stats

    finally:
        client.close()
        db.close()


if __name__ == "__main__":
    fetch_and_ingest_all_live_works()
