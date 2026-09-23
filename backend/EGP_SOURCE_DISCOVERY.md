# Bangladesh National e-GP Portal (eprocure.gov.bd) — Source Discovery & Technical Inspection Report

**Inspection Date:** September 21, 2026 (BST)  
**Target System:** National Electronic Government Procurement (e-GP) Portal  
**Authority:** Bangladesh Public Procurement Authority (BPPA) / IMED, Ministry of Planning  
**Primary URL:** `https://www.eprocure.gov.bd`  
**Status:** Successfully Inspected & Live-Verified  

---

## ১. ভূমিকা ও পরিদর্শনের উদ্দেশ্য (Executive Summary)

EjaraBD প্রকল্পের মাইলস্টোন ৫-এর অংশ হিসেবে বাংলাদেশ সরকারের কেন্দ্রীয় e-GP পোর্টাল (`eprocure.gov.bd`) সরাসরি এবং স্বয়ংক্রিয়ভাবে পরিদর্শন করা হয়েছে। 

উদ্দেশ্য ছিল:
1. লাইভ e-GP সিস্টেমে কোনো কাল্পনিক সিলেক্টর বা মনগড়া API অনুমান না করে প্রকৃত আর্কিটেকচার উন্মোচন করা।
2. পাবলিক টেন্ডার তালিকা ও নোটিশের তথ্য অনুসন্ধানের জন্য লগইন বা অনুমোদনের প্রয়োজনীয়তা যাচাই করা।
3. ডেটা কি স্ট্যাটিক HTML, সার্ভার-রেন্ডারড JSP, নাকি ব্যাকএন্ড XHR/AJAX থেকে আসে তা নির্ধারণ করা।
4. টেন্ডারের কোন কোন ফিল্ড উন্মুক্ত এবং কোন কোন ফিল্ড অনুপস্থিত তা চিহ্নিত করা।
5. EjaraBD-এর বিদ্যমান `backend/ingestion.py` পাইপলাইনের সাথে ফিল্ডের সামঞ্জস্য নিরূপণ করা।

---

## ২. প্রকৃত আর্কিটেকচার ও এন্ডপয়েন্টসমূহ (Discovered Architecture & Endpoints)

e-GP পোর্টালটি Java Enterprise (J2EE / Apache Tomcat / Servlets / JSP) প্রযুক্তির উপর নির্মিত।

### ক. সেশন ও অ্যাক্সেস কন্ট্রোল (Session Management)
* **প্রয়োজনীয়তা:** সকল রিকোয়েস্টে একটি বৈধ `JSESSIONID` কুকি বাধ্যতামূলক।
* **আচরণ:** কোনো পূর্ব-প্রতিষ্ঠিত সেশন ছাড়া সরাসরি কোনো সাব-পেজে রিকোয়েস্ট পাঠালে সার্ভার `HTTP 302` রিডাইরেক্ট করে `SessionTimedOut.jsp`-তে পাঠিয়ে দেয়।
* **সমাধান:** একটি স্ট্যান্ডার্ড HTTP ক্লায়েন্ট দিয়ে প্রথমে `GET https://www.eprocure.gov.bd/Index.jsp` লোড করলে সার্ভার বৈধ `JSESSIONID` কুকি প্রদান করে। এরপর পরবর্তী সকল রিকোয়েস্ট সফলভাবে সম্পাদিত হয়।
* **লগইন:** পাবলিক টেন্ডার সার্চ এবং বিস্তারিত নোটিশ (`ViewTender.jsp`) দেখার জন্য **কোনো লগইন বা পাসওয়ার্ডের প্রয়োজন নেই**।
* **ক্যাপচা (CAPTCHA):** শুধুমাত্র ইউজার লগইন ফর্মে (`LoginSrBean`) ক্যাপচা রয়েছে; **পাবলিক টেন্ডার সার্চ ও নোটিশ ভিউতে কোনো ক্যাপচা নেই**।

### খ. উন্মোচিত এন্ডপয়েন্ট তালিকা

| এন্ডপয়েন্ট | মেথড | রেসপন্স ফরম্যাট | ভূমিকা ও বিবরণ |
| :--- | :--- | :--- | :--- |
| `https://www.eprocure.gov.bd/Index.jsp` | GET | HTML | হোমপেজ; ব্রাউজার সেশন ও `JSESSIONID` প্রতিষ্ঠা করার জন্য প্রথম ধাপ। |
| `https://www.eprocure.gov.bd/resources/common/AllTenders.jsp?h=t` | GET | HTML | অ্যাডভান্সড সার্চ পেজ; সার্চ ফর্ম ও ফিল্টারিং অপশন ধারণ করে। |
| `https://www.eprocure.gov.bd/resources/common/StdTenderSearch.jsp?h=t` | GET / POST | HTML | স্ট্যান্ডার্ড সার্চ পেজ; কি-ওয়ার্ড সার্চ অপশন ধারণ করে। |
| `https://www.eprocure.gov.bd/TenderDetailsServlet` | **POST** | **HTML Fragment (`<tr>...</tr>`)** | **মূল ডেটা এন্ডপয়েন্ট (AJAX/XHR)**। সার্চ ক্রাইটেরিয়া ও পেজিনেশন অনুযায়ী টেবিল রো রিটার্ন করে। |
| `https://www.eprocure.gov.bd/resources/common/ViewTender.jsp` | **POST / GET** | **HTML Document** | **পূর্ণাঙ্গ নোটিশ ও শর্তাবলি ভিউ** (`id={tender_id}&h=t`)। যোগ্যতা ও সিকিউরিটির পূর্ণ বিবরণ থাকে। |
| `https://www.eprocure.gov.bd/ComboServlet` | POST | HTML/Options | বিভিন্ন ড্রপডাউনের ক্যাস্কেডিং অপশন (মন্ত্রণালয়, অফিস)। |
| `https://citizen.bppa.gov.bd/` (Legacy: `citizen.cptu.gov.bd`) | GET | JSON | **HTTP 401 Unauthorized** (ওপেন পাবলিক অ্যাক্সেস বন্ধ; অনুমোদিত টোকেন প্রয়োজন)। |

---

## ৩. সার্চ ও পেজিনেশন মেকানিজম (Search & Pagination Details)

e-GP পোর্টালের লাইভ টেন্ডার সার্চ মূলত `POST https://www.eprocure.gov.bd/TenderDetailsServlet`-এর মাধ্যমে কাজ করে।

### ক. রিকোয়েস্ট প্যারামিটারসমূহ (Form Payload)
```text
funName: "AllTenders"
viewType: "Live"             (বিকল্প: "Archive", "Cancelled", "All")
departmentId: ""             (নির্দিষ্ট মন্ত্রণালয় বা অধিদপ্তর আইডি)
office: ""                   (নির্দিষ্ট সার্কেল বা নির্বাহী প্রকৌশলীর অফিস)
procNature: "2"              (১ = Goods, ২ = Works, ৩ = Service, ৪ = Physical Services)
procType: ""                 ("NCT" = জাতীয়, "ICT" = আন্তর্জাতিক)
procMethod: "0"              ("0" = All, ২ = OTM, ৩ = LTM, ১ = RFQ ইত্যাদি)
tenderId: ""                 (নির্দিষ্ট ৬/৭ ডিজিটের টেন্ডার আইডি)
refNo: ""                    (অফিসিয়াল রেফারেন্স বা স্মারক নং)
pubDtFrm: ""                 (পাবলিশিং শুরু তারিখ, ফরম্যাট: dd/MM/yyyy)
pubDtTo: ""                  (পাবলিশিং শেষ তারিখ, ফরম্যাট: dd/MM/yyyy)
closeDtFrm: ""               (দাখিলের শেষ শুরুর তারিখ, ফরম্যাট: dd/MM/yyyy)
closeDtTo: ""                (দাখিলের শেষ শেষের তারিখ, ফরম্যাট: dd/MM/yyyy)
cpvCategory: ""              (CPV শ্রেণিবিভাগ)
isFrame: "0"                 ("0" = All, ১ = Yes, ২ = No)
pageNo: "1"                  (পেজ নম্বর: ১, ২, ৩...)
size: "10"                   (প্রতি পেজে টেন্ডার সংখ্যা: ১০, ২০, ৫০ সমর্থিত)
keyword: ""                  (কি-ওয়ার্ড সার্চের জন্য, যেমন: "Dinajpur")
homeWSearch: "homeWSearch"   (কি-ওয়ার্ড সার্চে ব্যবহৃত ফ্ল্যাগ)
h: "t"                       (পাবলিক নোটিশ ভ্যালিডেশন প্যারামিটার)
```

### খ. পেজিনেশন প্রতিক্রিয়া (Pagination Response)
সার্ভার রেসপন্সের একদম শেষে দুটি হিডেন ইনপুট থাকে:
- `<input type="hidden" id="cntTenBrief" value="10">` (বর্তমান পেজে প্রাপ্ত টেন্ডার সংখ্যা)
- `<input type="hidden" id="totalPages" value="383">` (মোট পেজ সংখ্যা; লাইভ টেস্টে ৩,৮৩০টি সক্রিয় টেন্ডার পাওয়া গেছে!)

---

## ৪. প্রাপ্ত ফিল্ড ও ইজারাবিডি মডেলের ম্যাপিং (Field Mapping to Tender Model)

| e-GP সোর্স ফিল্ড (Source Field) | উৎস অবস্থান | EjaraBD ফিল্ড (`Tender`) | রূপান্তর ও স্যানিটাইজেশন (Transformation) | প্রাপ্যতা স্ট্যাটাস |
| :--- | :--- | :--- | :--- | :--- |
| **Tender/Proposal ID** | কলাম ২ বা ViewTender | `tender_id` | স্ট্রিং হিসেবে রূপান্তর (যেমন: `"1336788"` বা `"eGP-1336788"`), ইউনিক কী। | **VERIFIED LIVE** |
| **Title / Package Description** | কলাম ৩ (`span[id^=tenderBrief] p`) | `title` | HTML ট্যাগ ও অতিরিক্ত স্পেস পরিষ্কার করা। | **VERIFIED LIVE** |
| **Ministry, Division, Organization** | কলাম ৪ (লাইন ১-৩) | `agency` | মূল সংস্থার নাম আলাদা করা (যেমন: LGED, RHD, BIWTA)। | **VERIFIED LIVE** |
| **Procuring Entity (PE) Office** | কলাম ৪ (লাইন ৪) / ViewTender | `procuring_entity_office` | অফিসের নাম (যেমন: নির্বাহী প্রকৌশলীর কার্যালয়...)। | **VERIFIED LIVE** |
| **PE District / Location** | ViewTender (`District :`) | `project_location_district` | প্রমিত ইংরেজি জেলার নাম (যেমন: `"Dinajpur"`, `"Manikganj"`)। | **VERIFIED LIVE** |
| **Lot Location Details** | ViewTender (Lot টেবিল) | `project_location_details` | কাজের সুনির্দিষ্ট স্থান/উপজেলা/ঘাট/রাস্তার বিবরণ। | **VERIFIED LIVE** |
| **Procurement Nature** | কলাম ৩ (হেডার) | `category` | `"Works"`, `"Road Construction"`, `"Goods"` ইত্যাদি। | **VERIFIED LIVE** |
| **Estimated Value (BDT)** | কোথাও নেই | `estimated_value_bdt` | **অনুপস্থিত। কঠোরভাবে `None` (SQL NULL) থাকবে।** | **UNAVAILABLE (By Law)** |
| **Tender Security (BDT)** | ViewTender (Lot টেবিল) | `tender_security_bdt` | সংখ্যায় রূপান্তর (যেমন: `"350000"` -> `350000.0`)। | **VERIFIED LIVE** |
| **Document Price (BDT)** | ViewTender (`Document Price :`) | `document_price_bdt` | সংখ্যায় রূপান্তর (যেমন: `"2500"` -> `2500.0`)। | **VERIFIED LIVE** |
| **Publishing Date & Time** | কলাম ৬ / ViewTender | `publication_date` | `21-Sep-2026 20:30` -> BST `datetime` অবজেক্ট। | **VERIFIED LIVE** |
| **Document Last Selling Date** | ViewTender (`Selling Date :`) | `document_last_selling_date`| `06-Oct-2026 12:30` -> BST `datetime` অবজেক্ট। | **VERIFIED LIVE** |
| **Closing Date & Time** | কলাম ৬ / ViewTender | `closing_date` | `06-Oct-2026 13:30` -> BST `datetime` অবজেক্ট। | **VERIFIED LIVE** |
| **Opening Date & Time** | ViewTender (`Opening Date :`) | `opening_date` | `06-Oct-2026 13:30` -> BST `datetime` অবজেক্ট। | **VERIFIED LIVE** |
| **Official Notice URL** | ক্যালকুলেটেড লিঙ্ক | `source_url` | `https://www.eprocure.gov.bd/resources/common/ViewTender.jsp?id={id}&h=t` | **VERIFIED LIVE** |
| **Source Type** | ফিক্সড স্ট্রিং | `source_type` | `"e-GP National Portal"` | **VERIFIED LIVE** |
| **Eligibility of Tenderer** | ViewTender (`Eligibility :`) | `raw_eligibility_text` | নোটিশে উল্লিখিত অভিজ্ঞতা, টার্নওভার, ক্রেডিট লাইন শর্তাবলি। | **VERIFIED LIVE** |
| **Status / Amendment** | কলাম ২ লেবেল / ViewTender | `status`, `is_amendment` | `"Live"` -> `active`, `"Corrigendum"` -> `amended` (`True`)। | **VERIFIED LIVE** |

---

## ৫. অনুপস্থিত ফিল্ড এবং আইনি তাৎপর্য (Missing Fields Analysis)

### `estimated_value_bdt` (কাজের প্রাক্কলিত সরকারি মূল্য):
* **বাস্তব পর্যবেক্ষণ:** উন্মুক্ত e-GP নোটিশে বা সার্চ তালিকায় কাজের অফিশিয়াল প্রাক্কলিত মূল্য (Official Estimated Cost) উল্লেখ থাকে না।
* **আইনি কারণ:** গণক্রয় আইন (PPA 2006) এবং বিধিমালা (PPR 2008) অনুসারে সাধারণ ওটিএম (OTM) দরপত্রে দরপত্রদাতাদের মধ্যে সিন্ডিকেট বা যোগসাজশ রোধ করতে নোটিশে প্রাক্কলিত মূল্য গোপন রাখা হয়। শুধুমাত্র শিডিউলের দরপত্র অংশে বা অনুমোদিত বিওকিউ (BoQ)-তে নির্দিষ্ট রেট থাকে।
* **ইজারাবিডির সিদ্ধান্ত:** EjaraBD-এর **Rule 1 (No Invented Facts)** এবং **Rule 2 (Security ≠ Project Value)** শতভাগ সঠিক প্রমাণিত হয়েছে। টেন্ডার সিকিউরিটি দেখে কখনো কাজের মূল্য অনুমান করা যাবে না এবং ডেটাবেজে এটি সর্বদা `None` থাকবে।

---

## ৬. বিদ্যমান `backend/ingestion.py`-এর সাথে তুলনা ও অভিযোজন

* আমাদের বর্তমান `backend/ingestion.py` ইতোমধ্যে `normalize_tender_payload()`, `clean_numeric_value()`, `clean_datetime_value()`, `validate_tender_payload()`, `ingest_single_tender()` এবং ডিডুপ্লিকেশন লজিক সরবরাহ করে।
* `backend/ingestion.py`-এর মূল ইন্টারফেস অক্ষুণ্ণ থাকবে।
* মাইলস্টোন ৫ স্টেপ ২-এ শুধু একটি হালকা ক্লায়েন্ট অ্যাডাপ্টার (`backend/egp_client.py`) প্রয়োজন হবে, যা:
  1. e-GP সার্ভারের সাথে সেশন স্থাপন করবে।
  2. `/TenderDetailsServlet` থেকে টেবিল রো পার্স করে প্রাথমিক ডিকশনারি বানাবে।
  3. ফিল্টারকৃত টেন্ডারের জন্য `/resources/common/ViewTender.jsp` থেকে `raw_eligibility_text` ও `tender_security_bdt` এনে ডিকশনারি পূর্ণাঙ্গ করবে।
  4. প্রাপ্ত ডিকশনারিটি হুবহু `backend/ingestion.py`-এর `ingest_single_tender()` অথবা `ingest_tenders_batch()`-এ পাঠিয়ে দেবে।

---

## ৭. প্রযুক্তিগত ঝুঁকি ও সংগ্রহের সেরা কৌশল (Risks & Recommended Strategy)

### ক. প্রযুক্তিগত ঝুঁকি (Risks & Constraints)
1. **সেশন মেয়াদোত্তীর্ণ (Session Timeout):** e-GP সেশন ৩০ মিনিট নিষ্ক্রিয় থাকলে এক্সপায়ার হয়। সংগ্রাহককে সেশন ডিসকানেক্ট হলে পুনরায় `Index.jsp` হিট করে সেশন রিনিউ করতে হবে।
2. **রক্ষণাবেক্ষণ উইন্ডো (Maintenance Downtime):** নোটিশের মারকিতে দেখা গেছে মাঝে মাঝে সাইট মেইনটেন্যান্সে থাকে (যেমন ২৫ সেপ্টেম্বর ২০২৬)। স্ক্র্যাপার যেন নেটওয়ার্ক ত্রুটিতে ক্র্যাশ না করে এক্সপোনেনশিয়াল ব্যাকঅফ ব্যবহার করে।
3. **অনুরোধের গতি (Rate Limiting):** অতিরিক্ত দ্রুত রিকোয়েস্ট পাঠালে আইপি ব্লক বা অস্থায়ী থ্রটলিং হতে পারে। প্রতি রিকোয়েস্টের মাঝে **১.৫ থেকে ২.০ সেকেন্ডের ভদ্র বিরতি (Polite Delay)** রাখা আবশ্যক।

### খ. প্রস্তাবিত দুই-ধাপের কৌশল (Two-Stage Collection Pipeline)
```text
ধাপ ১: সার্চ ও লিস্টিং (Listing Fetch)
   POST /TenderDetailsServlet (procNature=2, pageNo=X, size=20)
   ↓
   HTML রো পার্সিং → [Tender ID, Title, Agency, PE Office, Dates]
   ↓
ধাপ ২: ডিটারমিনিস্টিক প্রি-ফিল্টারিং (Deterministic Pre-filter)
   দিনাজপুর / সিভিল কাজ / পছন্দের ক্যাটাগরি ম্যাচিং
   ↓
ধাপ ৩: বিস্তারিত নোটিশ আহরণ (Detailed Notice Fetch - Only for Matches)
   GET /resources/common/ViewTender.jsp?id={matched_id}&h=t
   ↓
   Extract [Eligibility Criteria, Tender Security BDT, Exact Location]
   ↓
ধাপ ৪: স্ট্যান্ডার্ড ইনজেশন ও ডিডুপ্লিকেশন (Ingestion Pipeline)
   ingest_single_tender() → SQLite Database
```

---

## ৮. পরবর্তী বাস্তবায়ন পদক্ষেপ (Milestone 5 Step 2 Planning)

1. `backend/egp_client.py` তৈরি করা (পাবলিক সোর্স থেকে পেজিনেশন ও ডিটেইল আনার নির্ভরযোগ্য ক্লায়েন্ট)।
2. রিয়েল-টাইম লাইভ টেস্টের পাশাপাশি ফিক্সচার টেস্ট সুইট সচল রাখা।
3. অপারেটর ড্যাশবোর্ডে `📥 e-GP থেকে নতুন টেন্ডার আনুন` বাটন যুক্ত করা।
