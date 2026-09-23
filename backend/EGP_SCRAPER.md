# EjaraBD — Live e-GP Tender Scraper & Client Documentation

## ১. পরিচিতি ও আর্কিটেকচার (Architecture Overview)

বাংলাদেশ জাতীয় ই-প্রকিউরমেন্ট পোর্টাল (`https://www.eprocure.gov.bd`) থেকে পাবলিক দরপত্র তালিকা ও বিস্তারিত নোটিশ সংগ্রহের জন্য EjaraBD-এ একটি ডিটারমিনিস্টিক, প্রোডাকশন-গ্রেড ক্লায়েন্ট ও ইনজেশন সার্ভিস তৈরি করা হয়েছে।

### পাইপলাইন প্রবাহ (Pipeline Flow)

```text
[1. HTTP Session Initialization] 
      (/Index.jsp -> JSESSIONID)
                ↓
[2. Listing Search via POST]
      (/TenderDetailsServlet -> <tr>...</tr> HTML)
                ↓
[3. Pure HTML Parsing & Normalization]
      (Extract IDs, reference, dates, agency, status)
                ↓
[4. Deterministic Pre-filtering]
      (Skip distant/irrelevant tenders before detail fetch)
                ↓
[5. Detail Retrieval for Candidates]
      (/resources/common/ViewTender.jsp?id={id}&h=t)
                ↓
[6. Detail Parsing & Validation]
      (Extract lot security, location, raw eligibility; budget strictly None)
                ↓
[7. Authoritative Ingestion & Deduplication]
      (backend/ingestion.py -> SQLite Database)
                ↓
[8. Deterministic Matching & WhatsApp Drafting]
      (backend/matching.py)
```

---

## ২. মডিউল পরিচিতি (Modules)

1. **`backend/egp_client.py` (`EGPClient`)**:
   - HTTP সেশন হ্যান্ডলিং (`JSESSIONID` কুকি নিশ্চিতকরণ)।
   - সেশন মেয়াদোত্তীর্ণ হলে (`SessionTimedOut.jsp` / HTTP 302) স্বয়ংক্রিয় রিকভারি।
   - `search_page` ও `search_tenders`: ফিল্টার প্যারামিটার সহ অনুসন্ধান ও ডুপ্লিকেট-মুক্ত পেজিনেশন।
   - `parse_listing_html`: সার্চ রেজাল্টের টেবিল থেকে ডেটা নিষ্কাশন।
   - `get_tender_details` ও `parse_tender_details_html`: নোটিশ ভিউ থেকে যোগ্যতা শর্ত ও লট সিকিউরিটি নিষ্কাশন।
   - নম্র ক্রলিং ও এক্সপোনেনশিয়াল ব্যাকঅফ রিট্রাই।

2. **`backend/egp_ingestion_service.py` (`run_egp_sync`)**:
   - ব্যাচ সমন্বয়কারী সার্ভিস।
   - ডিটারমিনিস্টিক প্রি-ফিল্টারিং (`is_candidate_relevant_prefilter`)।
   - ব্যর্থ টেন্ডার আইসোলেশন (একক কোনো টেন্ডার ব্যর্থ হলে সম্পূর্ণ ব্যাচ থামবে না)।
   - `backend/ingestion.py` এর মাধ্যমে ডাটাবেজে সংরক্ষণ ও ডিডুপ্লিকেশন।
   - পরিসংখ্যান ও মেট্রিক্স তৈরি।

3. **`backend/main.py` (`POST /api/tenders/egp-sync`)**:
   - ফ্রন্টএন্ড বা শিডিউলার থেকে ট্রিগার করার জন্য পাবলিক API এন্ডপয়েন্ট।

---

## ৩. কনফিগারেশন (Configuration)

| প্যারামিটার / এনভায়রনমেন্ট | ডিফল্ট মান | বিবরণ |
| :--- | :--- | :--- |
| `EGP_BASE_URL` | `https://www.eprocure.gov.bd` | বাংলাদেশ e-GP পোর্টাল রুট URL |
| `EGP_REQUEST_DELAY_MIN` | `1.0` সেকেন্ড | রিকোয়েস্টের মধ্যবর্তী সর্বনিম্ন বিলম্ব |
| `EGP_REQUEST_DELAY_MAX` | `2.0` সেকেন্ড | রিকোয়েস্টের মধ্যবর্তী সর্বোচ্চ এলোমেলো বিলম্ব |
| `DEFAULT_TIMEOUT` | `25.0` সেকেন্ড | কানেকশন ও রিড টাইমআউট |
| `DEFAULT_MAX_RETRIES` | `3` বার | সাময়িক ব্যর্থতা বা নেটওয়ার্ক ড্রপে সর্বোচ্চ রিট্রাই |

---

## ৪. সমর্থিত সার্চ ফিল্টারসমূহ (Supported Search Filters)

`EGPClient.search_tenders(...)` এবং `POST /api/tenders/egp-sync` এ সমর্থিত ফিল্টারসমূহ:

- `procurement_nature`: কাজের প্রকৃতি (`1`=Goods, `2`=Works, `3`=Services, `4`=Physical Services)।
- `procurement_type`: সংগ্রহের ধরন (NCT / ICT)।
- `procurement_method`: দরপত্র পদ্ধতি (OTM, LTM, RFQ, ইত্যাদি; ডিফল্ট `0`=All)।
- `tender_id`: সুনির্দিষ্ট টেন্ডার আইডি (যেমন: `1336788`)।
- `reference_no`: সুনির্দিষ্ট টেন্ডার রেফারেন্স নম্বর।
- `keyword`: শিরোনাম বা নোটিশের কি-ওয়ার্ড সার্চ।
- `publication_date_from` / `publication_date_to`: প্রকাশের সময়সীমা (`DD-Mon-YYYY`)।
- `closing_date_from` / `closing_date_to`: দাখিলের শেষ সময়সীমা (`DD-Mon-YYYY`)।
- `page_size`: প্রতি পৃষ্ঠার টেন্ডার সংখ্যা (১০, ২০, ৫০, ১০০)।
- `max_pages`: সর্বোচ্চ কয়টি পৃষ্ঠা স্ক্যান করা হবে।
- `prefilter`: ডিটারমিনিস্টিক প্রি-ফিল্টারিং চালু/বন্ধ (ডিফল্ট `True`)।

---

## ৫. নিরাপদ পেজিনেশন ও লুপ প্রতিরোধ (Safe Pagination)

- প্রতিটি পৃষ্ঠার টেন্ডার আইডি একটি `seen_ids` সেটে ট্র্যাক করা হয়।
- যখন কোনো পৃষ্ঠায় কোনো নতুন টেন্ডার আইডি আসে না (0 new unique tenders) অথবা কোনো রো রিটার্ন হয় না, তখনই পেজিনেশন থেমে যায়।
- এর ফলে অসীম লুপ (Infinite Loop) হওয়া সম্পূর্ণ অসম্ভব।

---

## ৬. রেট লিমিটিং ও ভদ্র ক্রলিং (Polite Rate Limiting)

- সরকারি সার্ভারে একযোগে অতিরিক্ত রিকোয়েস্ট বা DDoS সদৃশ চাপ না দেওয়ার জন্য ক্লায়েন্টে সিকোয়েনশিয়াল রিকোয়েস্ট ব্যবহার করা হয়।
- প্রতিটি রিকোয়েস্ট পাঠানোর পূর্বে `delay_min` থেকে `delay_max` এর মাঝে র্যান্ডম বিলম্ব নিশ্চিত করা হয় (`self._sleep_polite()`)।
- কোনো সমান্তরাল বন্যা (Parallel Flooding) করা হয় না।

---

## ৭. ব্যর্থতা ও রিট্রাই হ্যান্ডলিং (Retry & Failure Isolation)

1. **সেশন টাইমআউট রিকভারি**: e-GP পোর্টাল ৩ মিনিট নিষ্ক্রিয় থাকলে বা কোনো রিকোয়েস্টে `SessionTimedOut.jsp` দিলে ক্লায়েন্ট সাথে সাথে স্বয়ংক্রিয়ভাবে নতুন সেশন ইনিশিয়ালাইজ করে এবং ড্রপ হওয়া রিকোয়েস্টটি রিট্রাই করে।
2. **নেটওয়ার্ক ফেইলিউর ও এক্সপোনেনশিয়াল ব্যাকঅফ**: `httpx.TimeoutException` বা `NetworkError` হলে সূচকীয় বিলম্ব (`(2 ** retries) * 0.5s`) সহ সর্বোচ্চ ৩ বার চেষ্টা করা হয়।
3. **ব্যর্থ নোটিশ আইসোলেশন**: যদি কোনো সুনির্দিষ্ট টেন্ডারের `ViewTender.jsp` ফেচ করতে ব্যর্থ হয়, তবে সেই নির্দিষ্ট আইডিটি `failed_details` তালিকায় সংরক্ষিত হয় এবং অন্য টেন্ডারগুলোর প্রসেসিং স্বাভাবিকভাবে চলতে থাকে। ব্যাচ ক্র্যাশ করে না।

---

## ৮. সংগৃহীত ও ইচ্ছাকৃতভাবে অপ্রকাশিত ফিল্ডসমূহ (Fields Collected vs Omitted)

### সংগৃহীত ফিল্ডসমূহ:
- `tender_id`: e-GP টেন্ডার/প্রস্তাব আইডি।
- `reference_no`: অফিসিয়াল রেফারেন্স নম্বর।
- `title`: কাজের পূর্ণাঙ্গ বিবরণ বা প্যাকেজের নাম।
- `procurement_nature`: কাজের প্রকৃতি (Works, Goods, ইত্যাদি)।
- `procurement_type`: NCT / ICT।
- `procurement_method`: OTM, LTM, ইত্যাদি।
- `ministry`, `division`, `agency`, `procuring_entity_office`: ক্রয়কারী কর্তৃপক্ষ।
- `project_location_district`: কাজের নির্দিষ্ট জেলা।
- `project_location_details`: লট টেবিল থেকে প্রাপ্ত কাজের সুনির্দিষ্ট স্থান (উপজেলা/ঘাট/রাস্তা)।
- `raw_eligibility_text`: মূল নোটিশের হুবহু যোগ্যতা শর্তাবলি (অক্ষত রূপ)।
- `tender_security_bdt`: লট টেবিল থেকে নির্দিষ্ট টেন্ডার জামানতের পরিমাণ (BDT)।
- `document_price_bdt`: দরপত্র শিডিউল ক্রয় মূল্য (BDT)।
- `publication_date`: বিজ্ঞপ্তি প্রকাশের তারিখ ও সময় (BST)।
- `document_last_selling_date`: শিডিউল বিক্রির শেষ তারিখ ও সময় (BST)।
- `closing_date`: দরপত্র দাখিলের শেষ তারিখ ও সময় (BST)।
- `opening_date`: দরপত্র উন্মুক্তকরণের তারিখ ও সময় (BST)।
- `source_url`: মূল দরপত্র দেখার লিংক (`ViewTender.jsp?id={id}&h=t`)।
- `status`: দরপত্রের বর্তমান স্থিতি (active, amended, cancelled)।

### ⚠️ ইচ্ছাকৃতভাবে অপ্রকাশিত/অগৃহীত ফিল্ড:
- **`estimated_value_bdt = None`**:
  - বাংলাদেশ পাবলিক প্রকিউরমেন্ট বিধিমালা (PPR 2008) মোতাবেক উন্মুক্ত দরপত্রের প্রাক্কলিত সরকারি মূল্য (Official Estimated Cost) পাবলিক নোটিশে কখনো প্রকাশ করা হয় না।
  - টেন্ডার সিকিউরিটি (Tender Security) থেকে কখনোই প্রাক্কলিত মূল্য অনুমান করা হয় না।
  - এটি কঠোরভাবে `None` রাখা হয়।

---

## ৯. কীভাবে সিঙ্ক চালাতে হবে (How to Run Sync)

### ক. ছোট স্মোক টেস্ট / টেস্ট রান (Small Sync):
```python
from backend.database import SessionLocal
from backend.egp_ingestion_service import run_egp_sync

db = SessionLocal()
stats = run_egp_sync(
    db=db,
    proc_nature="2", # Works
    page_size=5,
    max_pages=1,
    prefilter=True,
    auto_match=True
)
print("Sync Stats:", stats)
db.close()
```

অথবা API এর মাধ্যমে:
```bash
curl -X POST http://127.0.0.1:8000/api/tenders/egp-sync \
  -H "Content-Type: application/json" \
  -d '{"procurement_nature": "2", "page_size": 5, "max_pages": 1, "prefilter": true}'
```

### খ. বড় বা নিয়মিত শিডিউলড সিঙ্ক (Scheduled Production Sync):
```bash
curl -X POST http://127.0.0.1:8000/api/tenders/egp-sync \
  -H "Content-Type: application/json" \
  -d '{
    "procurement_nature": "2",
    "page_size": 50,
    "max_pages": 5,
    "prefilter": true,
    "auto_match": true
  }'
```

---

## ১০. সীমাবদ্ধতা (Limitations)

1. **পাবলিক নোটিশ সীমা**: এই ক্লায়েন্ট শুধুমাত্র পাবলিক নোটিশে উন্মুক্ত তথ্য সংগ্রহ করে। লগইন-প্রয়োজনীয় বা ফি দিয়ে ক্রয়যোগ্য বিস্তারিত শিডিউল (BoQ) ডাউনলোড করে না।
2. **ক্যাপচা পরিহার**: পাবলিক অনুসন্ধানে কোনো ক্যাপচা থাকে না। যদি ভবিষ্যতে কোনো সার্ভলেট বা অ্যান্ডপয়েন্টে ক্যাপচা আসে, সিস্টেম তা বাইপাস না করে নিরাপদ নোটিফিকেশন দেবে।
3. **সার্ভার রক্ষণাবেক্ষণ সময়**: বাংলাদেশ সরকারের e-GP সার্ভারে প্রতি রাতে ও ছুটির দিনে নির্ধারিত রক্ষণাবেক্ষণ থাকে। সেই সময়ে কানেকশন টাইমআউট হতে পারে, যা ক্লায়েন্টের রিট্রাই ও লগিং সিস্টেমে ধরা পড়ে।
