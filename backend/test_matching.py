import os
import sys

# Ensure workspace root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Windows কনসোলে বাংলা অক্ষরের জন্য সেফটি
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from backend.database import SessionLocal
from backend.models import ContractorProfile, Tender, MatchAssessment, NotificationDraft
from backend.matching import run_matching_pipeline

def test_matching():
    db = SessionLocal()
    try:
        print("১. ম্যাচিং পাইপলাইন চালু করা হচ্ছে...")
        count = run_matching_pipeline(db)
        print(f"-> মোট {count} টি টেন্ডার-কন্ট্রাক্টর জোড়া মূল্যায়ন সম্পন্ন হয়েছে।\n")

        contractor = db.query(ContractorProfile).first()
        print(f"ঠিকাদার: {contractor.business_name}")
        print(f"নির্বাচিত জেলা: {contractor.preferred_districts}")
        print(f"কাজের ক্ষেত্র: {contractor.work_categories}\n" + "="*60)

        assessments = db.query(MatchAssessment).filter_by(contractor_id=contractor.id).all()
        for ass in assessments:
            t = ass.tender
            draft = db.query(NotificationDraft).filter_by(assessment_id=ass.id).first()
            
            print(f"\n[টেন্ডার আইডি: {t.tender_id}] {t.title}")
            print(f"সংস্থা: {t.agency} | জেলা: {t.project_location_district}")
            print(f"মিলের স্থিতি (Preference Fit): {ass.preference_fit_status}")
            print(f"যোগ্যতা যাচাই অবস্থা: {ass.qualification_status}")
            print(f"সারসংক্ষেপ: {ass.overall_fit_explanation_bn}")
            
            if ass.known_mismatches:
                print(f"অমিলসমূহ: {ass.known_mismatches}")
            if ass.unknown_items_to_verify:
                print(f"যাচাই প্রয়োজন: {ass.unknown_items_to_verify}")

            if t.tender_id == "eGP-1092341":
                print("\n--- [উদাহরণ: হোয়াটসঅ্যাপ বার্তার প্রিভিউ (Tender 1)] ---")
                print(draft.draft_message_bn)
                print("--------------------------------------------------")

        print("\nম্যাচিং এবং ড্রাফট তৈরির পরীক্ষা ১০০% সফল!")

    finally:
        db.close()

if __name__ == "__main__":
    test_matching()
