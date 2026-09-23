import sys
from datetime import datetime

# Windows কনসোলে বাংলা আউটপুটের জন্য UTF-8 নিশ্চিত করা
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from backend.database import engine, Base, SessionLocal
from backend.models import ContractorProfile, Tender

def seed():
    """বাস্তবসম্মত স্যাম্পল ডেটা সিড করা"""
    print("ডাটাবেজ টেবিল চেক ও প্রস্তুত করা হচ্ছে...")
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    try:
        # ১. পাইলট কন্ট্রাক্টর প্রোফাইল (দিনাজপুর কেন্দ্রিক, অভিজ্ঞ ঠিকাদার)
        existing_contractor = db.query(ContractorProfile).first()
        if not existing_contractor:
            contractor = ContractorProfile(
                business_name="মেসার্স দিনাজপুর কন্সট্রাকশন (পাইলট প্রোফাইল)",
                contact_person="আলহাজ্ব মোঃ ঠিকাদার সাহেব",
                preferred_language="bn",
                whatsapp_number="+8801711000000",
                preferred_districts=["Dinajpur"],
                work_categories=["Civil Works", "Road Construction", "Culvert & Bridge Maintenance"],
                preferred_agencies=["LGED", "RHD", "PWD"],
                min_project_value_bdt=1000000.0,   # ১০ লাখ টাকা
                max_project_value_bdt=15000000.0,  # ১ কোটি ৫০ লাখ টাকা
                experience_notes="দিনাজপুর ও পার্শ্ববর্তী অঞ্চলে প্রায় ৪০ বছরের বাস্তব কাজের অভিজ্ঞতা। এলজিইডি ও আরএইচডি-তে একাধিক গ্রামীণ সড়ক ও কালভার্ট সফলভাবে সম্পন্ন করেছেন।",
                known_constraints="দিনাজপুর জেলার বাইরে বা পাহাড়ি/নদীভাঙন এলাকায় কাজ করতে অনিচ্ছুক। ইলেকট্রিক্যাল বা ড্রেনেজ কাজের চেয়ে সড়ক ও সিভিল কাজে অগ্রাধিকার বেশি।",
                message_frequency="daily_digest",
                messaging_consent=True
            )
            db.add(contractor)
            db.commit()
            db.refresh(contractor)
            print(f"✓ পাইলট ঠিকাদার প্রোফাইল তৈরি হয়েছে: {contractor.business_name} (ID: {contractor.id})")
        else:
            contractor = existing_contractor
            print(f"• ঠিকাদার প্রোফাইল ইতিমধ্যে বিদ্যমান: {contractor.business_name}")

        # ২. স্যাম্পল টেন্ডার ডেটা সংকলন (বাস্তবসম্মত ৩টি ভিন্ন কেস)
        sample_tenders = [
            {
                "tender_id": "eGP-1092341",
                "title": "দিনাজপুর সদর ও বীরগঞ্জ উপজেলায় গ্রামীণ সংযোগ সড়ক এইচবিবি ও কার্পেটিং দ্বারা উন্নয়ন কাজ",
                "agency": "Local Government Engineering Department (LGED)",
                "procuring_entity_office": "নির্বাহী প্রকৌশলীর কার্যালয়, এলজিইডি, দিনাজপুর",
                "project_location_district": "Dinajpur",
                "project_location_details": "দিনাজপুর সদর ও বীরগঞ্জ উপজেলা",
                "category": "Road Construction",
                "estimated_value_bdt": 5500000.0,  # ৫৫ লাখ টাকা (স্পষ্ট প্রাক্কলিত মূল্য)
                "tender_security_bdt": 140000.0,   # ১ লাখ ৪০ হাজার টাকা
                "document_price_bdt": 2000.0,
                "publication_date": datetime(2026, 9, 18, 10, 0, 0),
                "document_last_selling_date": datetime(2026, 10, 12, 17, 0, 0),
                "closing_date": datetime(2026, 10, 13, 14, 0, 0), # BST
                "opening_date": datetime(2026, 10, 13, 14, 30, 0),
                "source_url": "https://eprocure.gov.bd/resources/sample-tenders/1092341",
                "source_type": "e-GP Sample Fixture",
                "raw_eligibility_text": "১. যে কোনো সরকারি/আধা-সরকারি প্রতিষ্ঠান হতে বিগত ৫ বছরে একক চুক্তিতে ন্যূনতম ৩৫ লাখ টাকার সড়ক কাজের সফল সমাপ্তির সনদ। ২. নূন্যতম তরল সম্পদের (Liquid Asset) পরিমাণ ২৫ লাখ টাকা হতে হবে।",
                "is_amendment": False,
                "amendment_details": None,
                "status": "active"
            },
            {
                "tender_id": "eGP-1095582",
                "title": "রংপুর-দিনাজপুর জাতীয় মহাসড়কের (এন-৫১০) নির্দিষ্ট অংশে প্যাচওয়ার্ক ও সিলকোট দ্বারা সড়ক রক্ষণাবেক্ষণ",
                "agency": "Roads and Highways Department (RHD)",
                "procuring_entity_office": "নির্বাহী প্রকৌশলীর কার্যালয়, সড়ক বিভাগ, দিনাজপুর",
                "project_location_district": "Dinajpur",
                "project_location_details": "দশমাইল মোড় হতে দিনাজপুর শহর সংযোগ সড়ক",
                "category": "Road Maintenance",
                "estimated_value_bdt": None,       # নিয়ম: প্রাক্কলিত মূল্য অজানা, সিকিউরিটি থেকে কখনো অনুমান করা যাবে না
                "tender_security_bdt": 180000.0,   # ১ লাখ ৮০ হাজার টাকা
                "document_price_bdt": 2500.0,
                "publication_date": datetime(2026, 9, 19, 11, 0, 0),
                "document_last_selling_date": datetime(2026, 10, 18, 16, 0, 0),
                "closing_date": datetime(2026, 10, 19, 13, 0, 0), # BST
                "opening_date": datetime(2026, 10, 19, 13, 30, 0),
                "source_url": "https://eprocure.gov.bd/resources/sample-tenders/1095582",
                "source_type": "e-GP Sample Fixture",
                "raw_eligibility_text": "সড়ক ও জনপথ অধিদপ্তরের অনুরূপ বিটুমিনাস কাজের পূর্ব অভিজ্ঞতা এবং হালনাগাদ ঠিকাদারি ও ট্যাক্স ক্লিয়ারেন্স সার্টিফিকেট প্রয়োজন।",
                "is_amendment": False,
                "amendment_details": None,
                "status": "active"
            },
            {
                "tender_id": "eGP-1088920",
                "title": "চট্টগ্রাম জেলার পটিয়া উপজেলায় গভীর নলকূপ ও পাইপড ওয়াটার সাপ্লাই স্কিম স্থাপন",
                "agency": "Department of Public Health Engineering (DPHE)",
                "procuring_entity_office": "নির্বাহী প্রকৌশলীর কার্যালয়, ডিপিএইচই, চট্টগ্রাম",
                "project_location_district": "Chattogram", # ভিন্ন জেলা (অমিল টেস্ট করার জন্য)
                "project_location_details": "পটিয়া উপজেলা",
                "category": "Water Supply & Tube-well",     # ভিন্ন ক্যাটাগরি (অমিল টেস্ট করার জন্য)
                "estimated_value_bdt": 8500000.0,  # ৮৫ লাখ টাকা
                "tender_security_bdt": 220000.0,
                "document_price_bdt": 2000.0,
                "publication_date": datetime(2026, 9, 10, 9, 30, 0),
                "document_last_selling_date": datetime(2026, 10, 8, 17, 0, 0),
                "closing_date": datetime(2026, 10, 9, 12, 0, 0), # পূর্বে ছিল ০১-১০-২০২৬, সংশোধনে পেছানো হয়েছে
                "opening_date": datetime(2026, 10, 9, 12, 30, 0),
                "source_url": "https://eprocure.gov.bd/resources/sample-tenders/1088920",
                "source_type": "e-GP Sample Fixture",
                "raw_eligibility_text": "ডিপিএইচই বা সমমানের সরকারি সংস্থায় ডিপ টিউবওয়েল স্থাপন কাজের ন্যূনতম ৩ বছরের বাস্তব অভিজ্ঞতা সনদ আবশ্যক।",
                "is_amendment": True,
                "amendment_details": "সংশোধনী ১ (তারিখ: ১৭-০৯-২০২৬): দরপত্র দাখিলের শেষ তারিখ ০১-১০-২০২৬ হতে বৃদ্ধি করে ০৯-১০-২০২৬ দুপুর ১২:০০ ঘটিকা পর্যন্ত পুনঃনির্ধারণ করা হলো।",
                "status": "amended"
            }
        ]

        for tender_data in sample_tenders:
            existing = db.query(Tender).filter_by(tender_id=tender_data["tender_id"]).first()
            if not existing:
                tender = Tender(**tender_data)
                db.add(tender)
                db.commit()
                db.refresh(tender)
                print(f"✓ নতুন স্যাম্পল টেন্ডার সংরক্ষিত: [{tender.tender_id}] {tender.title[:45]}...")
            else:
                print(f"• টেন্ডার ইতিমধ্যে বিদ্যমান: [{existing.tender_id}] {existing.title[:45]}...")

        print("\nসকল স্যাম্পল ফিক্সচার সফলভাবে সিড সম্পন্ন হয়েছে!")

    finally:
        db.close()


def seed_demo_clients_if_needed(db: SessionLocal):
    """
    ডেমো ক্লায়েন্ট সিডিং (স্পষ্টভাবে is_demo=True চিহ্নিত):
    প্রোডাকশন ক্লায়েন্টদের কোনো তথ্য পরিবর্তন না করে শুধুমাত্র টেস্ট ও ডেমো পর্যালোচনার জন্য
    ৩টি ভিন্ন অঞ্চলের স্পষ্ট ডেমো ক্লায়েন্ট প্রস্তুত করা হয়।
    """
    from backend.models import PaymentRecord, ActivityEvent

    demo_exists = db.query(ContractorProfile).filter_by(is_demo=True).first()
    if demo_exists:
        return

    demos = [
        {
            "business_name": "[DEMO] রহমান বিল্ডার্স অ্যান্ড ট্রেডার্স",
            "contact_person": "মোঃ রফিকুল ইসলাম",
            "email": "demo.contractor.a@example.com",
            "phone": "+8801700000001",
            "district": "Dhaka",
            "is_demo": True,
            "account_status": "active",
            "payment_status": "confirmed",
            "subscription_status": "active",
            "onboarding_status": "complete",
            "notification_schedules": ["10:00", "16:00"],
            "preferred_districts": ["Dhaka", "Gazipur"],
            "work_categories": ["Civil Works", "Building Construction"],
            "preferred_agencies": ["PWD", "EED"],
            "min_project_value_bdt": 2000000.0,
            "max_project_value_bdt": 20000000.0,
            "experience_notes": "ভবন নির্মাণ ও সিভিল কাজের দীর্ঘ অভিজ্ঞতা রয়েছে।",
            "payment_info": {
                "payment_id": "PAY-DEMO-001",
                "amount": 3500.0,
                "method": "bKash",
                "trx": "BKASH987DEMO1",
                "status": "confirmed"
            }
        },
        {
            "business_name": "[DEMO] উত্তরবঙ্গ ইনফ্রাস্ট্রাকচার লিমিটেড",
            "contact_person": "ইঞ্জিনিয়ার কামরুল হাসান",
            "email": "demo.contractor.b@example.com",
            "phone": "+8801700000002",
            "district": "Rangpur",
            "is_demo": True,
            "account_status": "onboarding",
            "payment_status": "confirmed",
            "subscription_status": "active",
            "onboarding_status": "started",
            "notification_schedules": ["12:00"],
            "preferred_districts": ["Rangpur", "Dinajpur"],
            "work_categories": ["Road Construction", "Culvert & Bridge Maintenance"],
            "preferred_agencies": ["RHD", "LGED"],
            "min_project_value_bdt": 1500000.0,
            "max_project_value_bdt": 12000000.0,
            "experience_notes": "সড়ক ও কালভার্ট নির্মাণে বিশেষ পারদর্শী।",
            "payment_info": {
                "payment_id": "PAY-DEMO-002",
                "amount": 2500.0,
                "method": "bKash",
                "trx": "BKASH654DEMO2",
                "status": "confirmed"
            }
        },
        {
            "business_name": "[DEMO] সুরমা কনস্ট্রাকশন অ্যান্ড সাপ্লাইয়ার্স",
            "contact_person": "শফিকুল আলম",
            "email": "demo.contractor.c@example.com",
            "phone": "+8801700000003",
            "district": "Sylhet",
            "is_demo": True,
            "account_status": "lead_payment_pending",
            "payment_status": "none",
            "subscription_status": "inactive",
            "onboarding_status": "not_started",
            "notification_schedules": ["12:00", "19:00"],
            "preferred_districts": ["Sylhet"],
            "work_categories": ["Water Supply & Tube-well", "Civil Works"],
            "preferred_agencies": ["BWDB", "DPHE"],
            "min_project_value_bdt": 500000.0,
            "max_project_value_bdt": 8000000.0,
            "experience_notes": "পানি সরবরাহ ও পাইপলাইন কাজ।",
            "payment_info": None
        }
    ]

    for d in demos:
        pay_info = d.pop("payment_info", None)
        c = ContractorProfile(**d)
        db.add(c)
        db.commit()
        db.refresh(c)

        if pay_info:
            pay = PaymentRecord(
                contractor_id=c.id,
                payment_id=pay_info["payment_id"],
                amount=pay_info["amount"],
                currency="BDT",
                payment_method=pay_info["method"],
                transaction_reference=pay_info["trx"],
                payment_status=pay_info["status"],
                confirmed_at=datetime.utcnow(),
                confirmation_source="Operator Manual (Demo Seed)",
                notes="Demo verified payment"
            )
            db.add(pay)

            act = ActivityEvent(
                timestamp=datetime.utcnow(),
                event_type="payment_confirmed",
                contractor_id=c.id,
                title=f"Payment confirmed: ৳{pay_info['amount']}",
                description=f"Client: {c.business_name} | Method: {pay_info['method']} | Trx: {pay_info['trx']}"
            )
            db.add(act)
            db.commit()


if __name__ == "__main__":
    seed()

