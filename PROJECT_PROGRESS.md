# EjaraBD - Project Milestones & Changelog

## 1. Project Overview
- **Name:** EjaraBD (ইজারাবিডি)
- **Purpose:** Intelligent e-GP (Bangladesh National e-Government Procurement) tender discovery, deterministic matching, and automated bilingual notification pipeline tailored for Bangladeshi contractors.
- **Core Value Proposition:** Filters through thousands of complex e-GP notices, matches works tenders strictly against contractor capabilities (district, work categories, capacity), and delivers structured notifications without hallucinating missing data.
- **Architecture:** Human-in-the-loop operator console with FastAPI (Python 3.11) backend, SQLite persistence, deterministic rule-based matching engine, and React 19 + TypeScript frontend.

---

## 2. Core Architecture & Engineering Principles
1. **Zero-Hallucination Tender Intelligence:** If estimated budget or eligibility requirements are not publicly disclosed in the e-GP notice, they remain strictly marked as `UNKNOWN / Verification Required`. Tender security amounts are never confused with estimated project value.
2. **Deterministic Matching Engine:** Multi-factor scoring evaluating district, upazila, procuring agency, work nature, and explicit negative/exclusion keywords with clear, human-auditable reasons.
3. **Bilingual Notifications:** Structured Bengali and English notification generators tailored for multi-channel operator dispatch.
4. **Resilient Ingestion:** Session-aware scraping with polite rate limiting, retry logic, automatic deduplication, and failure isolation.

---

## 3. Milestone Changelog

### Phase 1: Core Architecture & Verification
- Established database models (`ContractorProfile`, `Tender`, `MatchAssessment`, `NotificationDraft`) with SQLAlchemy.
- Implemented robust deterministic matching pipeline with explicit match and mismatch reasoning.
- Built 19-field contractor onboarding endpoints with full validation and duplicate email prevention.
- Added comprehensive automated test suite verifying CRUD operations, client pause/resume toggling, and data integrity.

### Phase 2: e-GP Scraper & Ingestion Pipeline
- Developed polite, session-aware crawler (`backend/egp_client.py`) with automatic `JSESSIONID` refresh and exponential backoff.
- Built bulk tender ingestion engine (`backend/ingestion.py`) with database deduplication by official `tender_id`.
- Designed fallback isolation ensuring individual tender fetch failures do not crash batch ingestion runs.

### Phase 3: Bilingual Notification Engine & Operator Console
- Implemented responsive Bengali and English notification templates (`backend/email_templates.py`).
- Added developer mode email safeguards preventing accidental delivery to external recipients during testing.
- Created modern React + TypeScript dashboard with live client management, tender exploration, and match inspection.

---

## 4. Verification & Testing
- Automated test suites verify 100% of core business logic:
  - Database schema & constraints (`test_client_endpoints.py`, `verify_db.py`)
  - e-GP client parsing & session handling (`test_egp_client.py`, `test_egp_source_discovery.py`)
  - Ingestion & deduplication (`test_ingestion.py`)
  - Deterministic matching engine (`test_matching.py`)
  - Bilingual notification service (`test_email_service.py`)
  - Unified system verification (`test_phase1_verification.py`)
