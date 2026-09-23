import os
import sys
from datetime import datetime

# Add root directory to sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(BASE_DIR)
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

# Windows কনসোলে বাংলা টেক্সট প্রিন্ট করার জন্য UTF-8 সেট করা
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from backend.database import engine, Base, SessionLocal
from backend.models import ContractorProfile, Tender, MatchAssessment, NotificationDraft, Feedback

def test_database():
    print("১. SQLite ডাটাবেজ টেবিল তৈরি পরীক্ষা করা হচ্ছে...")
    Base.metadata.create_all(bind=engine)
    print("-> টেবিলসমূহ সফলভাবে তৈরি হয়েছে!")

    db = SessionLocal()
    try:
        print("২. একটি টেস্ট কন্ট্রাক্টর প্রোফাইল ডাটাবেজে সংরক্ষণ করা হচ্ছে...")
        test_contractor = ContractorProfile(
            business_name="মেসার্স উদাহরণ কনস্ট্রাকশন",
            contact_person="মোঃ ঠিকাদার সাহেব",
            preferred_districts=["Dinajpur"],
            work_categories=["Civil Works", "Road Construction"],
            experience_notes="৪০ বছরের বাস্তব কাজের অভিজ্ঞতা, দিনাজপুর অঞ্চলে রাস্তা ও ভবন নির্মাণ।"
        )
        db.add(test_contractor)
        db.commit()
        db.refresh(test_contractor)
        print(f"-> কন্ট্রাক্টর প্রোফাইল সংরক্ষিত! ID: {test_contractor.id}, নাম: {test_contractor.business_name}")

        print("৩. একটি টেস্ট টেন্ডার রেকর্ড ডাটাবেজে সংরক্ষণ করা হচ্ছে...")
        test_tender = Tender(
            tender_id="TEST-1045231",
            title="দিনাজপুর জেলার বীরগঞ্জ উপজেলায় গ্রামীণ সড়ক সংস্কার কাজ",
            agency="Local Government Engineering Department (LGED)",
            procuring_entity_office="নির্বাহী প্রকৌশলীর কার্যালয়, এলজিইডি, দিনাজপুর",
            project_location_district="Dinajpur",
            project_location_details="বীরগঞ্জ উপজেলা",
            category="Road Maintenance",
            estimated_value_bdt=4500000.0, # ৪৫ লাখ টাকা
            tender_security_bdt=120000.0,  # ১ লাখ ২০ হাজার টাকা
            document_price_bdt=2000.0,
            closing_date=datetime(2026, 10, 15, 14, 0, 0),
            source_url="https://eprocure.gov.bd/sample/1045231",
            raw_eligibility_text="ন্যূনতম ৫ বছরের সিভিল কাজের অভিজ্ঞতা এবং অনুরূপ কাজের প্রমাণপত্র আবশ্যক।"
        )
        db.add(test_tender)
        db.commit()
        db.refresh(test_tender)
        print(f"-> টেন্ডার সংরক্ষিত! ID: {test_tender.id}, টেন্ডার আইডি: {test_tender.tender_id}")

        # রিড যাচাই
        contractor_from_db = db.query(ContractorProfile).filter_by(id=test_contractor.id).first()
        tender_from_db = db.query(Tender).filter_by(id=test_tender.id).first()

        assert contractor_from_db is not None, "কন্ট্রাক্টর ডাটাবেজে পাওয়া যায়নি!"
        assert tender_from_db is not None, "টেন্ডার ডাটাবেজে পাওয়া যায়নি!"
        assert tender_from_db.tender_security_bdt != tender_from_db.estimated_value_bdt, "সিকিউরিটি ও প্রজেক্ট ভ্যালু আলাদা থাকতে হবে!"

        print("৪. ডেটাবেজ রিড এবং অ্যাসর্শন যাচাই সফল!")

        # টেস্ট ডাটা ক্লিনআপ (যাতে অপ্রয়োজনীয় টেস্ট ডাটা না থাকে)
        db.delete(test_contractor)
        db.delete(test_tender)
        db.commit()
        print("৫. পরীক্ষামূলক টেস্ট ডাটা সফলভাবে মুছে ক্লিনআপ সম্পন্ন হয়েছে।")
        print("\nডাটাবেজ ও মডেল আর্কিটেকচার ১০০% প্রস্তুত ও সফলভাবে কার্যকর!")
    finally:
        db.close()

if __name__ == "__main__":
    test_database()
