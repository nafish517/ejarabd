# EjaraBD (ইজারাবিডি) — Intelligent e-GP Tender Discovery & Client Onboarding Platform

> **Portfolio MVP**: Rule-based e-GP tender discovery, multi-client onboarding, deterministic evaluation, and localized email notification system for Bangladeshi contractors.

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat&logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688?style=flat&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18.0+-61DAFB?style=flat&logo=react&logoColor=black)](https://react.dev/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.0+-3178C6?style=flat&logo=typescript&logoColor=white)](https://www.typescriptlang.org/)
[![Vite](https://img.shields.io/badge/Vite-5.0+-646CFF?style=flat&logo=vite&logoColor=white)](https://vitejs.dev/)
[![SQLite](https://img.shields.io/badge/Database-SQLite-003B57?style=flat&logo=sqlite&logoColor=white)](https://www.sqlite.org/)
[![Tests](https://img.shields.io/badge/Tests-11%20Suites%20Passed-10b981?style=flat)]()

---

## 📌 Professional Project Summary (Suitable for CV)

**EjaraBD (ইজারাবিডি)** is an end-to-end tender intelligence platform built to eliminate information asymmetry for Bangladeshi government contractors participating in the national e-GP portal (*eprocure.gov.bd*). It features an automated procurement scraper, a 19-field contractor onboarding system, a zero-hallucination deterministic matching engine, and a bilingual (Bengali/English) email dispatch engine with built-in safety controls.

- **Frontend**: Responsive React 18 SPA with TypeScript, modern CSS design tokens, dual-view navigation (Clients Dashboard & Stored Tenders Explorer), and real-time validation.
- **Backend**: FastAPI with SQLAlchemy ORM, SQLite database, resilient HTML/JSON scrapers, and pluggable SMTP providers with UTF-8 Bengali MIME support.
- **Data Integrity**: 1,727+ live Works tenders preserved, client isolation, slot-level duplicate notification prevention, and hermetic unit/integration test suites.

---

## 🎯 Key Features

### 1. Minimal Client Onboarding & Lifecycle Management
- **19-Field Specification**: Captures company identity, contact details, district/upazila preferences, agency preferences (LGED, RHD, PWD, BWDB), experience years, turnover, equipment, manpower, and excluded domains.
- **Lifecycle Status Control**: One-click toggling between **Active** and **Paused** states with immediate effect.
- **Strict Validation**: Real-time required field enforcement and duplicate email rejection (HTTP 400 with Bengali explanatory messages).

### 2. e-GP Tender System & Data Preservation
- **Preserved Ingestion Pipeline**: Ingests, normalizes, and deduplicates government tenders from national procurement sources.
- **1,727+ Stored Tenders**: Live database populated with active works tenders, preserved with zero data corruption.
- **Stored Tenders Explorer**: Fast searchable/filterable UI table with pagination, district filters, budget indicators, BST closing countdowns, and direct official e-GP links.

### 3. Rule-Based Deterministic Matching Engine
- **Zero-Hallucination Design**: Eliminates AI hallucination by evaluating strict rules against verified fields (District, Upazila, Agency, Work Category, Excluded Categories, Budget Limits).
- **Match Status Categorization**: Classifies tenders into **Fits (পূর্ণ মিল)**, **Partial (আংশিক মিল)**, or **Outside (তালিকার বাইরে)**.
- **Transparent Reasoning**: Explicitly displays positive fit reasons, known mismatches, and **unverified items** (e.g. ITT turnover certificates or liquid asset requirements) rather than inventing eligibility.

### 4. Bilingual Email Notification Engine
- **Language Localization**: Dynamically renders either professional **Bengali** or **English** templates according to contractor preference.
- **Development Safety Guard (`EMAIL_DEV_MODE=true`)**: Redirects all outgoing notifications to a verified test address during development to protect real contractors.
- **Duplicate Prevention**: Tracks `(contractor_id, tender_id)` dispatch history to prevent redundant notifications.
- **Audit Logging**: Persists send timestamp, provider, error messages, and HTML preview in `email_notification_records`.

---

## 🏗️ System Architecture

```mermaid
graph TD
    subgraph National Source
        EGP["National e-GP Portal (eprocure.gov.bd)"]
    end

    subgraph Backend [FastAPI Backend Service]
        Scraper["e-GP Scraper & Ingestion (egp_client.py)"]
        DB[(SQLite DB: ejarabd.db)]
        Engine["Rule-Based Matching Engine (matching.py)"]
        Mailer["SMTP Delivery Service (email_service.py)"]
        Scheduler["Slot Deduplication Scheduler (schedule_service.py)"]
    end

    subgraph Frontend [React + TypeScript SPA]
        ClientsUI["Client Management & Onboarding Modal"]
        TendersUI["Stored Tenders Explorer (1,727+ Tenders)"]
        MatchesUI["Matches & Reasons Drawer"]
    end

    EGP -->|Scrape & Parse| Scraper
    Scraper -->|Upsert Tenders| DB
    ClientsUI -->|CRUD & Status| DB
    DB -->|Read Tenders & Profiles| Engine
    Engine -->|Assessments & Reasons| MatchesUI
    Engine -->|Candidate Drafts| Scheduler
    Scheduler -->|Dispatch (Safe Mode)| Mailer
    Mailer -->|Encrypted TLS| Gmail[Gmail SMTP Gateway]
    TendersUI -->|Browse & Search| DB
```

---

## 📂 Project Directory Structure

```text
ejarabd/
├── backend/
│   ├── .env.example              # Environment variables template
│   ├── main.py                   # FastAPI REST API endpoints
│   ├── database.py               # SQLite connection & session factory
│   ├── models.py                 # SQLAlchemy DB schema models
│   ├── matching.py               # Deterministic rule-based matching engine
│   ├── email_service.py          # SMTP provider with UTF-8 Bengali support
│   ├── email_templates.py        # Bilingual (Bengali/English) HTML/Text templates
│   ├── schedule_service.py       # Notification scheduling & slot deduplication
│   ├── egp_client.py             # e-GP portal scraper client
│   ├── egp_ingestion_service.py  # Tender sync & ingestion coordinator
│   ├── run_all_tests.py          # Master workflow test runner (11 suites)
│   └── ejarabd.db                # SQLite database (1,727 live tenders)
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── ClientFormModal.tsx # 19-field onboarding modal
│   │   │   └── MatchesDrawer.tsx   # Match details & reasons drawer
│   │   ├── services/
│   │   │   └── api.ts            # Typed REST API client
│   │   ├── types/
│   │   │   └── index.ts          # TypeScript interfaces (Client, Tender, Matches)
│   │   ├── utils/
│   │   │   └── formatters.ts     # Bengali numerals, currency & date formatting
│   │   ├── App.tsx               # Dual-view dashboard (Clients + Tenders Explorer)
│   │   └── index.css             # High-contrast CSS design tokens
│   ├── package.json
│   └── vite.config.ts
├── .gitignore                    # Strict secret shielding rules
└── README.md
```

---

## ⚙️ Environment Variables

Create a `backend/.env` file based on `.env.example`:

```ini
# Environment
ENV=development

# Development Safety Guard:
# When true, emails are NOT delivered to real clients. All dispatches route to SAFE_TEST_EMAIL.
EMAIL_DEV_MODE=true
SAFE_TEST_EMAIL=your-safe-test-email@gmail.com

# SMTP Server Settings (Gmail App Password)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-16-char-gmail-app-password

# Sender Identity
SMTP_FROM_EMAIL=your-email@gmail.com
SMTP_FROM_NAME=EjaraBD

# SMTP Connection Options
SMTP_USE_TLS=true
SMTP_TIMEOUT=10
```

> **Security Rule**: `backend/.env` is strictly ignored by Git. Never commit or hardcode credentials into any source files.

---

## 🚀 Setup & Execution Guide

### 1. Prerequisites
- **Python**: 3.11 or higher
- **Node.js**: v18 or higher (with npm)
- **Git**

### 2. Backend Setup
```bash
# Navigate to backend directory
cd backend

# Create and activate virtual environment
python -m venv venv
# On Windows:
venv\Scripts\activate
# On Linux/macOS:
# source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run the backend API server
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```
*API Swagger Documentation is available at: `http://127.0.0.1:8000/docs`*

### 3. Frontend Setup
```bash
# Navigate to frontend directory in another terminal
cd frontend

# Install packages
npm install

# Run the frontend development server
npm run dev
```
*Frontend interface is accessible at: `http://localhost:5173`*

---

## 🧪 Testing

The platform includes an automated master test runner covering all 11 system workflows:

```bash
# Run all 11 test suites
python backend/run_all_tests.py
```

### Verified Test Suites:
1. `test_phase1_verification.py`: Core acceptance & architectural integrity.
2. `test_client_endpoints.py`: 19-field client onboarding, duplicate email check, status updates.
3. `verify_db.py`: Database schema and table integrity.
4. `test_egp_source_discovery.py`: e-GP portal discovery and mapping.
5. `test_egp_client.py`: Scraper crawling resilience and parsing.
6. `test_ingestion.py`: Batch tender ingestion and deduplication.
7. `test_matching.py`: Deterministic rule-based matching engine.
8. `test_email_service.py`: Email provider abstraction & bilingual templates.
9. `test_email_smoke.py`: Real SMTP TLS handshake and safe dev mode verification.
10. `test_operations_platform.py`: Slot deduplication, multi-customer isolation, lifecycle transitions.
11. `test_api.py`: FastAPI route contracts and payload validation.

---

## 🎬 2-Minute Demonstration Flow

1. **Client Management (30 seconds)**:
   - Open the web interface at `http://localhost:5173`.
   - Click **"+ নতুন ক্লায়েন্ট যোগ করুন (Add Client)"** to demonstrate the 19-field onboarding modal.
   - Show required field validation and duplicate email prevention.
   - Toggle an existing client between **Active** and **Paused**.
2. **e-GP Stored Tenders Explorer (30 seconds)**:
   - Switch to the **"সংরক্ষিত ই-জিপি দরপত্র ভান্ডার (e-GP Tenders)"** tab.
   - Show the 1,727+ stored tenders, search by keyword (e.g. `LGED` or `Dinajpur`), and demonstrate official e-GP links.
3. **Deterministic Matching (30 seconds)**:
   - Click **"Run Matching"** to evaluate all active clients against the tender database.
   - Click **"Eye (ম্যাচিং টেন্ডার)"** on Client #1 to open the Matches Drawer.
   - Highlight the **transparent reasoning**: positive match criteria, known mismatches, and checklist of items needing verification.
4. **Safe Email Delivery (30 seconds)**:
   - Click **"Send Test Email"** on a matched tender.
   - Point out the `Email Dev Mode (Safe)` indicator showing safe redirection to the test mailbox.
   - Demonstrate the duplicate send prevention preventing redundant notices.

---

## ⚠️ Known Limitations (Portfolio MVP Scope)

- **Heuristic-Driven Categorization**: Detailed tender work items are classified based on e-GP summary tables; full Bill of Quantities (BOQ) parsing and scanned image OCR are deferred to Phase 2.
- **Local SQLite Store**: Designed for local execution and portfolio demonstration; transition to PostgreSQL recommended for multi-worker production concurrency.
- **Synchronous Scraping Runs**: The scraper runs in-process or via scheduled cron batches rather than distributed Celery worker pools.

---

## 🗺️ Future Roadmap

- [ ] **OCR & Document Extraction**: Automated parsing of PDF/ZIP tender schedules, ITT requirements, and BOQ work breakdowns.
- [ ] **AI-Assisted Feasibility Scoring**: Optional Gemini-powered semantic analysis for nuanced past-experience matching.
- [ ] **SMS / WhatsApp Gateway**: Multi-channel alert distribution via Twilio or local Bangladeshi SMS gateways.
- [ ] **Contractor Document Repository**: Secure upload and expiration tracking of trade licenses, tax certificates, and completion records.

---

## 📄 License & Attribution

Developed by **Nafish Rahim** ([nafishrahim@gmail.com](mailto:nafishrahim@gmail.com)) as a portfolio MVP showcasing full-stack engineering, robust backend scraping, deterministic rule engines, and reliable client workflows.
