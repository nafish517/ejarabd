import os
import sys
import logging
from typing import List, Optional, Any, Dict, Union
from datetime import datetime, timezone

# Add backend and root to sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(BASE_DIR)
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

# Windows UTF-8 console output safety
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.database import get_db, engine, init_db_schema
from backend.models import (
    ContractorProfile,
    Tender,
    MatchAssessment,
    EmailNotificationRecord,
    ActivityEvent,
)
from backend.matching import run_matching_pipeline, evaluate_tender_for_contractor
from backend.email_service import send_email
from backend.email_templates import render_tender_notification_email
from backend.egp_client import EGPClient
from backend.egp_ingestion_service import run_egp_sync
from backend.ingestion import ingest_tenders_batch

logger = logging.getLogger("ejarabd.api")
logging.basicConfig(level=logging.INFO)

# Initialize database schema safely (preserves existing 1,727 live tenders and clients)
init_db_schema(engine)

app = FastAPI(
    title="EjaraBD API (ইজারাবিডি)",
    description="অভিজ্ঞ বাংলাদেশি ঠিকাদারদের জন্য দরপত্র যাচাই ও ক্লায়েন্ট অনবোর্ডিং ব্যাকএন্ড এপিআই",
    version="1.0.0"
)

# CORS configuration for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==============================================================================
# Pydantic Schemas (19-Field Onboarding Spec)
# ==============================================================================

class ClientCreate(BaseModel):
    # Core Identity
    business_name: str
    contact_person: str
    email: str
    phone: Optional[str] = None
    preferred_language: Optional[str] = "bn"

    # Location & Agency
    district: Optional[str] = None
    preferred_districts: Optional[List[str]] = ["Dinajpur"]
    preferred_upazilas: Optional[List[str]] = []
    preferred_agencies: Optional[List[str]] = ["LGED", "RHD"]

    # Category & Value
    work_categories: Optional[List[str]] = ["Civil Works", "Road Construction"]
    min_project_value_bdt: Optional[float] = None
    max_project_value_bdt: Optional[float] = None

    # Experience & Capacity
    years_of_experience: Optional[int] = None
    previous_project_types: Optional[List[str]] = []
    similar_work_experience: Optional[str] = None
    approx_annual_turnover_bdt: Optional[float] = None
    available_equipment: Optional[List[str]] = []
    available_manpower: Optional[List[str]] = []
    licenses_certifications: Optional[List[str]] = []
    excluded_areas_or_categories: Optional[List[str]] = []

    # Notification & Lifecycle
    notification_preference: Optional[str] = "daily_email"
    notification_schedules: Optional[List[str]] = ["12:00", "19:00"]
    client_status: Optional[str] = "active" # draft, active, paused
    is_demo: Optional[bool] = False
    experience_notes: Optional[str] = None
    known_constraints: Optional[str] = None


class ClientUpdate(BaseModel):
    business_name: Optional[str] = None
    contact_person: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    preferred_language: Optional[str] = None
    district: Optional[str] = None
    preferred_districts: Optional[List[str]] = None
    preferred_upazilas: Optional[List[str]] = None
    preferred_agencies: Optional[List[str]] = None
    work_categories: Optional[List[str]] = None
    min_project_value_bdt: Optional[float] = None
    max_project_value_bdt: Optional[float] = None
    years_of_experience: Optional[int] = None
    previous_project_types: Optional[List[str]] = None
    similar_work_experience: Optional[str] = None
    approx_annual_turnover_bdt: Optional[float] = None
    available_equipment: Optional[List[str]] = None
    available_manpower: Optional[List[str]] = None
    licenses_certifications: Optional[List[str]] = None
    excluded_areas_or_categories: Optional[List[str]] = None
    notification_preference: Optional[str] = None
    notification_schedules: Optional[List[str]] = None
    client_status: Optional[str] = None # draft, active, paused
    is_demo: Optional[bool] = None
    experience_notes: Optional[str] = None
    known_constraints: Optional[str] = None


class ClientStatusUpdate(BaseModel):
    client_status: str # active, paused, draft


class TestEmailRequest(BaseModel):
    recipient_email: Optional[str] = None
    tender_id: Optional[int] = None


# ==============================================================================
# Helper Serializer
# ==============================================================================

def serialize_client(c: ContractorProfile, db: Session) -> Dict[str, Any]:
    """Client model to complete 19-field dictionary with match counts."""
    # Count matches
    matches_count = db.query(MatchAssessment).filter(
        MatchAssessment.contractor_id == c.id,
        MatchAssessment.preference_fit_status.in_(["fits", "partial"])
    ).count()

    # Determine display status (normalized to draft, active, paused)
    raw_status = (c.client_status or c.account_status or "active").lower()
    if raw_status in ["active", "complete", "payment_confirmed"]:
        status = "active"
    elif raw_status in ["paused", "inactive"]:
        status = "paused"
    else:
        status = "draft"

    return {
        "id": c.id,
        "business_name": c.business_name,
        "contact_person": c.contact_person,
        "email": c.email,
        "phone": c.phone or c.whatsapp_number,
        "preferred_language": c.preferred_language or "bn",
        "district": c.district or (c.preferred_districts[0] if c.preferred_districts else None),
        "preferred_districts": c.preferred_districts or [],
        "preferred_upazilas": c.preferred_upazilas or [],
        "work_categories": c.work_categories or [],
        "preferred_agencies": c.preferred_agencies or [],
        "min_project_value_bdt": c.min_project_value_bdt,
        "max_project_value_bdt": c.max_project_value_bdt,
        "years_of_experience": c.years_of_experience,
        "previous_project_types": c.previous_project_types or [],
        "similar_work_experience": c.similar_work_experience,
        "approx_annual_turnover_bdt": c.approx_annual_turnover_bdt,
        "available_equipment": c.available_equipment or [],
        "available_manpower": c.available_manpower or [],
        "licenses_certifications": c.licenses_certifications or [],
        "excluded_areas_or_categories": c.excluded_areas_or_categories or [],
        "notification_preference": c.notification_preference or "daily_email",
        "notification_schedules": c.notification_schedules or ["12:00", "19:00"],
        "client_status": status,
        "is_demo": bool(c.is_demo),
        "experience_notes": c.experience_notes,
        "known_constraints": c.known_constraints,
        "total_matches": matches_count,
        "created_at": c.created_at.isoformat() if c.created_at else None,
        "updated_at": c.updated_at.isoformat() if c.updated_at else None,
    }


# ==============================================================================
# API Endpoints
# ==============================================================================

@app.get("/api/health")
def health_check():
    """Health status and configuration telemetry."""
    dev_mode = os.getenv("EMAIL_DEV_MODE", "true").lower() in ("true", "1", "yes")
    return {
        "status": "healthy",
        "app": "EjaraBD Onboarding & Matching Core",
        "version": "1.0.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "email_dev_mode": dev_mode,
        "smtp_configured": bool(os.getenv("SMTP_HOST") and os.getenv("SMTP_FROM_EMAIL"))
    }


# ------------------------------------------------------------------------------
# Client Management Endpoints (CRUD)
# ------------------------------------------------------------------------------

@app.get("/api/clients")
def list_clients(
    status: Optional[str] = None,
    is_demo: Optional[bool] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """List all clients with 19-field details and match counts."""
    query = db.query(ContractorProfile)

    if is_demo is not None:
        query = query.filter(ContractorProfile.is_demo == is_demo)

    if status:
        if status == "active":
            query = query.filter(ContractorProfile.client_status.in_(["active", "complete"]))
        elif status == "paused":
            query = query.filter(ContractorProfile.client_status.in_(["paused", "inactive"]))
        elif status == "draft":
            query = query.filter(ContractorProfile.client_status.in_(["draft", "lead_payment_pending", "not_started"]))

    if search:
        s = f"%{search.strip()}%"
        query = query.filter(
            (ContractorProfile.business_name.ilike(s)) |
            (ContractorProfile.contact_person.ilike(s)) |
            (ContractorProfile.email.ilike(s)) |
            (ContractorProfile.phone.ilike(s)) |
            (ContractorProfile.district.ilike(s))
        )

    clients = query.order_by(ContractorProfile.id.asc()).all()
    return [serialize_client(c, db) for c in clients]


@app.post("/api/clients")
def create_client(payload: ClientCreate, db: Session = Depends(get_db)):
    """
    Create a new client with complete 19 fields.
    Enforces duplicate email prevention.
    """
    clean_email = payload.email.strip().lower()

    # Prevent duplicate client emails
    existing_with_email = db.query(ContractorProfile).filter(
        func.lower(ContractorProfile.email) == clean_email
    ).first()
    if existing_with_email:
        raise HTTPException(
            status_code=400,
            detail=f"এই ইমেইল ঠিকানাটি ({payload.email}) ইতোমধ্যে ক্লায়েন্ট #{existing_with_email.id} ({existing_with_email.business_name})-এর ক্ষেত্রে নিবন্ধিত রয়েছে।"
        )

    # Determine status
    target_status = payload.client_status or "active"
    if target_status not in ["draft", "active", "paused"]:
        target_status = "active"

    new_client = ContractorProfile(
        business_name=payload.business_name.strip(),
        contact_person=payload.contact_person.strip(),
        email=clean_email,
        phone=payload.phone.strip() if payload.phone else None,
        preferred_language=payload.preferred_language or "bn",
        district=payload.district.strip() if payload.district else (payload.preferred_districts[0] if payload.preferred_districts else None),
        preferred_districts=payload.preferred_districts or ["Dinajpur"],
        preferred_upazilas=payload.preferred_upazilas or [],
        work_categories=payload.work_categories or ["Civil Works"],
        preferred_agencies=payload.preferred_agencies or ["LGED"],
        min_project_value_bdt=payload.min_project_value_bdt,
        max_project_value_bdt=payload.max_project_value_bdt,
        years_of_experience=payload.years_of_experience,
        previous_project_types=payload.previous_project_types or [],
        similar_work_experience=payload.similar_work_experience,
        approx_annual_turnover_bdt=payload.approx_annual_turnover_bdt,
        available_equipment=payload.available_equipment or [],
        available_manpower=payload.available_manpower or [],
        licenses_certifications=payload.licenses_certifications or [],
        excluded_areas_or_categories=payload.excluded_areas_or_categories or [],
        notification_preference=payload.notification_preference or "daily_email",
        notification_schedules=payload.notification_schedules or ["12:00", "19:00"],
        client_status=target_status,
        account_status=target_status,
        payment_status="confirmed",
        subscription_status="active",
        onboarding_status="complete",
        is_demo=bool(payload.is_demo),
        experience_notes=payload.experience_notes,
        known_constraints=payload.known_constraints,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )

    db.add(new_client)
    db.commit()
    db.refresh(new_client)

    logger.info("New client created: ID #%d (%s, %s)", new_client.id, new_client.business_name, new_client.email)
    return {
        "status": "success",
        "message": f"নতুন ক্লায়েন্ট সফলভাবে যুক্ত হয়েছে: {new_client.business_name}",
        "client": serialize_client(new_client, db)
    }


@app.get("/api/clients/{client_id}")
def get_client(client_id: int, db: Session = Depends(get_db)):
    """Get single client with full 19 attributes."""
    client = db.query(ContractorProfile).filter_by(id=client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="ক্লায়েন্ট পাওয়া যায়নি")
    return serialize_client(client, db)


@app.put("/api/clients/{client_id}")
def update_client(client_id: int, payload: ClientUpdate, db: Session = Depends(get_db)):
    """Update client profile and preferences with duplicate email check."""
    client = db.query(ContractorProfile).filter_by(id=client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="ক্লায়েন্ট পাওয়া যায়নি")

    # Email update & duplicate prevention
    if payload.email is not None:
        clean_email = payload.email.strip().lower()
        if clean_email and clean_email != (client.email or "").lower():
            conflict = db.query(ContractorProfile).filter(
                func.lower(ContractorProfile.email) == clean_email,
                ContractorProfile.id != client_id
            ).first()
            if conflict:
                raise HTTPException(
                    status_code=400,
                    detail=f"এই ইমেইল ঠিকানাটি ({payload.email}) ইতোমধ্যে অন্য ক্লায়েন্ট #{conflict.id} ({conflict.business_name})-এর ক্ষেত্রে নিবন্ধিত রয়েছে।"
                )
            client.email = clean_email

    if payload.business_name is not None:
        client.business_name = payload.business_name.strip()
    if payload.contact_person is not None:
        client.contact_person = payload.contact_person.strip()
    if payload.phone is not None:
        client.phone = payload.phone.strip()
    if payload.preferred_language is not None:
        client.preferred_language = payload.preferred_language
    if payload.district is not None:
        client.district = payload.district.strip()
    if payload.preferred_districts is not None:
        client.preferred_districts = payload.preferred_districts
    if payload.preferred_upazilas is not None:
        client.preferred_upazilas = payload.preferred_upazilas
    if payload.work_categories is not None:
        client.work_categories = payload.work_categories
    if payload.preferred_agencies is not None:
        client.preferred_agencies = payload.preferred_agencies
    if payload.min_project_value_bdt is not None:
        client.min_project_value_bdt = payload.min_project_value_bdt
    if payload.max_project_value_bdt is not None:
        client.max_project_value_bdt = payload.max_project_value_bdt
    if payload.years_of_experience is not None:
        client.years_of_experience = payload.years_of_experience
    if payload.previous_project_types is not None:
        client.previous_project_types = payload.previous_project_types
    if payload.similar_work_experience is not None:
        client.similar_work_experience = payload.similar_work_experience
    if payload.approx_annual_turnover_bdt is not None:
        client.approx_annual_turnover_bdt = payload.approx_annual_turnover_bdt
    if payload.available_equipment is not None:
        client.available_equipment = payload.available_equipment
    if payload.available_manpower is not None:
        client.available_manpower = payload.available_manpower
    if payload.licenses_certifications is not None:
        client.licenses_certifications = payload.licenses_certifications
    if payload.excluded_areas_or_categories is not None:
        client.excluded_areas_or_categories = payload.excluded_areas_or_categories
    if payload.notification_preference is not None:
        client.notification_preference = payload.notification_preference
    if payload.notification_schedules is not None:
        client.notification_schedules = payload.notification_schedules
    if payload.client_status is not None:
        client.client_status = payload.client_status
        client.account_status = payload.client_status
    if payload.is_demo is not None:
        client.is_demo = payload.is_demo
    if payload.experience_notes is not None:
        client.experience_notes = payload.experience_notes
    if payload.known_constraints is not None:
        client.known_constraints = payload.known_constraints

    client.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(client)

    return {
        "status": "success",
        "message": f"ক্লায়েন্ট প্রোফাইল সফলভাবে আপডেট হয়েছে: {client.business_name}",
        "client": serialize_client(client, db)
    }


@app.patch("/api/clients/{client_id}/status")
def update_client_status(client_id: int, payload: ClientStatusUpdate, db: Session = Depends(get_db)):
    """Pause, resume (activate), or draft client status."""
    client = db.query(ContractorProfile).filter_by(id=client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="ক্লায়েন্ট পাওয়া যায়নি")

    target_status = payload.client_status.strip().lower()
    if target_status not in ["active", "paused", "draft"]:
        raise HTTPException(status_code=400, detail="স্ট্যাটাস অবশ্যই 'active', 'paused', অথবা 'draft' হতে হবে")

    client.client_status = target_status
    client.account_status = target_status
    client.updated_at = datetime.utcnow()
    db.commit()

    label = "সক্রিয় (Active)" if target_status == "active" else ("স্থগিত (Paused)" if target_status == "paused" else "খসড়া (Draft)")
    return {
        "status": "success",
        "message": f"{client.business_name}-এর স্ট্যাটাস {label} করা হয়েছে।",
        "client_status": target_status
    }


# ------------------------------------------------------------------------------
# Matching Endpoints
# ------------------------------------------------------------------------------

@app.post("/api/match/run")
def trigger_matching(
    client_id: Optional[int] = Query(None, description="নির্দিষ্ট ক্লায়েন্টের জন্য ম্যাচিং চালাতে ID দিন"),
    db: Session = Depends(get_db)
):
    """
    ম্যানুয়াল ম্যাচিং ট্রিগার।
    যদি client_id দেওয়া থাকে, তবে শুধু সেই ক্লায়েন্টের জন্য ম্যাচ করবে; অন্যথায় সব সক্রিয় ক্লায়েন্টের জন্য করবে।
    """
    total_evaluated = run_matching_pipeline(db, target_contractor_id=client_id)
    target_text = f"ক্লায়েন্ট #{client_id}" if client_id else "সকল সক্রিয় ক্লায়েন্ট"
    return {
        "status": "success",
        "message": f"ম্যাচিং সম্পন্ন হয়েছে ({target_text})। মোট {total_evaluated}টি দরপত্র মূল্যায়ন সম্পন্ন।",
        "evaluated": total_evaluated
    }


@app.get("/api/clients/{client_id}/matches")
def get_client_matches(
    client_id: int,
    fit_status: Optional[str] = Query(None, description="fits, partial, outside"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """Retrieve matched tenders and explanations for a client."""
    client = db.query(ContractorProfile).filter_by(id=client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="ক্লায়েন্ট পাওয়া যায়নি")

    query = db.query(MatchAssessment, Tender).join(Tender, MatchAssessment.tender_id == Tender.id).filter(
        MatchAssessment.contractor_id == client_id
    )

    if fit_status:
        query = query.filter(MatchAssessment.preference_fit_status == fit_status)
    else:
        # Default prioritize fits and partial
        query = query.filter(MatchAssessment.preference_fit_status.in_(["fits", "partial"]))

    total_count = query.count()
    items = query.order_by(Tender.closing_date.asc()).offset(offset).limit(limit).all()

    results = []
    for assessment, tender in items:
        results.append({
            "assessment_id": assessment.id,
            "tender_id": tender.id,
            "official_tender_id": tender.tender_id,
            "title": tender.title,
            "agency": tender.agency,
            "office": tender.procuring_entity_office,
            "district": tender.project_location_district,
            "location_details": tender.project_location_details,
            "category": tender.category,
            "estimated_value_bdt": tender.estimated_value_bdt,
            "tender_security_bdt": tender.tender_security_bdt,
            "closing_date": tender.closing_date.isoformat() if tender.closing_date else None,
            "source_url": tender.source_url,
            "preference_fit_status": assessment.preference_fit_status,
            "preference_reasons": assessment.preference_reasons or [],
            "known_mismatches": assessment.known_mismatches or [],
            "unknown_items_to_verify": assessment.unknown_items_to_verify or [],
            "overall_fit_explanation_bn": assessment.overall_fit_explanation_bn
        })

    return {
        "client_id": client_id,
        "client_name": client.business_name,
        "total": total_count,
        "limit": limit,
        "offset": offset,
        "matches": results
    }


# ------------------------------------------------------------------------------
# Safe Email Test & Dispatch Endpoints
# ------------------------------------------------------------------------------

@app.post("/api/clients/{client_id}/test-email")
def send_test_email_for_client(
    client_id: int,
    payload: Optional[TestEmailRequest] = None,
    db: Session = Depends(get_db)
):
    """
    Send a safe test notification email for this client.
    Respects EMAIL_DEV_MODE: If enabled, only SAFE_TEST_EMAIL receives the message.
    Logs record into email_notification_records.
    """
    client = db.query(ContractorProfile).filter_by(id=client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="ক্লায়েন্ট পাওয়া যায়নি")

    # Select tender: specified or best match
    tender = None
    assessment = None
    if payload and payload.tender_id:
        tender = db.query(Tender).filter_by(id=payload.tender_id).first()
        if tender:
            assessment = db.query(MatchAssessment).filter_by(
                contractor_id=client.id, tender_id=tender.id
            ).first()

    if not tender:
        # Find best fit match
        best_match = db.query(MatchAssessment, Tender).join(
            Tender, MatchAssessment.tender_id == Tender.id
        ).filter(
            MatchAssessment.contractor_id == client.id,
            MatchAssessment.preference_fit_status == "fits"
        ).first()

        if best_match:
            assessment, tender = best_match
        else:
            # Fallback to any recent active tender
            tender = db.query(Tender).filter_by(status="active").first()
            if tender:
                assessment = db.query(MatchAssessment).filter_by(
                    contractor_id=client.id, tender_id=tender.id
                ).first()

    if not tender:
        raise HTTPException(status_code=404, detail="পরীক্ষার জন্য কোনো টেন্ডার ডাটাবেজে পাওয়া যায়নি")

    if not assessment:
        eval_res = evaluate_tender_for_contractor(client, tender)
        assessment = MatchAssessment(
            contractor_id=client.id,
            tender_id=tender.id,
            preference_fit_status=eval_res["preference_fit_status"],
            preference_reasons=eval_res["preference_reasons"],
            qualification_status=eval_res["qualification_status"],
            known_mismatches=eval_res["known_mismatches"],
            unknown_items_to_verify=eval_res["unknown_items_to_verify"],
            overall_fit_explanation_bn=eval_res["overall_fit_explanation_bn"]
        )

    # Determine recipient
    target_recipient = (payload.recipient_email if payload and payload.recipient_email else client.email) or ""
    target_recipient = target_recipient.strip()
    if not target_recipient:
        raise HTTPException(status_code=400, detail="ক্লায়েন্টের কোনো ইমেইল ঠিকানা নেই এবং কোনো টেস্ট ইমেইল প্রদান করা হয়নি")

    # Render email content
    subject, html_body, text_body = render_tender_notification_email(
        tender=tender,
        contractor=client,
        assessment=assessment
    )

    # Dispatch email safely
    result = send_email(
        to_email=target_recipient,
        subject=subject,
        html_body=html_body,
        text_body=text_body
    )

    # Log to email_notification_records
    rec_status = "sent" if result.success else "failed"
    email_rec = EmailNotificationRecord(
        contractor_id=client.id,
        tender_id=tender.id,
        recipient_email=target_recipient,
        subject=subject,
        status=rec_status,
        trigger_type="manual_test_send",
        sent_at=datetime.utcnow() if result.success else None,
        error_message=result.error or (None if result.success else result.message),
        provider=result.provider,
        html_preview=html_body[:2000],
        created_at=datetime.utcnow()
    )
    db.add(email_rec)
    db.commit()

    return {
        "status": "success" if result.success else "failed",
        "message": result.message,
        "recipient": target_recipient,
        "provider": result.provider,
        "tender_title": tender.title,
        "tender_id": tender.tender_id,
        "record_id": email_rec.id
    }


# ------------------------------------------------------------------------------
# Tenders & Scraper Endpoints
# ------------------------------------------------------------------------------

@app.get("/api/tenders")
def list_tenders(
    search: Optional[str] = None,
    district: Optional[str] = None,
    category: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """List tenders from live database with filters."""
    query = db.query(Tender)

    if search:
        s = f"%{search.strip()}%"
        query = query.filter((Tender.title.ilike(s)) | (Tender.tender_id.ilike(s)) | (Tender.agency.ilike(s)))
    if district:
        query = query.filter(Tender.project_location_district.ilike(f"%{district.strip()}%"))
    if category:
        query = query.filter(Tender.category.ilike(f"%{category.strip()}%"))

    total = query.count()
    tenders = query.order_by(Tender.closing_date.desc()).offset(offset).limit(limit).all()

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "items": [
            {
                "id": t.id,
                "tender_id": t.tender_id,
                "title": t.title,
                "agency": t.agency,
                "office": t.procuring_entity_office,
                "district": t.project_location_district,
                "location_details": t.project_location_details,
                "category": t.category,
                "estimated_value_bdt": t.estimated_value_bdt,
                "tender_security_bdt": t.tender_security_bdt,
                "closing_date": t.closing_date.isoformat() if t.closing_date else None,
                "source_url": t.source_url
            }
            for t in tenders
        ]
    }


@app.post("/api/tenders/egp-sync")
def sync_tenders_from_egp(
    pages: int = Query(1, ge=1, le=10),
    db: Session = Depends(get_db)
):
    """
    Sync live Works tenders from national e-GP portal (eprocure.gov.bd).
    Preserves existing tenders and adds newly published ones.
    """
    try:
        stats = run_egp_sync(
            db=db,
            proc_nature="2", # Works
            max_pages=pages,
            prefilter=False, # Don't limit to pilot contractor in multi-client era
            fetch_details=True,
            auto_match=True
        )
        return stats
    except Exception as e:
        logger.error("e-GP sync failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"e-GP সিঙ্ক ত্রুটি: {str(e)}")


@app.post("/api/tenders/ingest")
def api_ingest_tenders(
    payload: Dict[str, Any],
    db: Session = Depends(get_db)
):
    """Ingest batch of tenders with validation and deduplication."""
    tenders_data = payload.get("tenders", [])
    auto_match = payload.get("auto_match", False)
    res = ingest_tenders_batch(db, tenders_data, auto_run_matching=auto_match)
    return {"status": "success", "data": res}



@app.get("/api/communications/emails")
def list_email_logs(
    client_id: Optional[int] = None,
    limit: int = Query(30, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """View recent email dispatch history with delivery statuses and errors."""
    query = db.query(EmailNotificationRecord)
    if client_id:
        query = query.filter(EmailNotificationRecord.contractor_id == client_id)

    records = query.order_by(EmailNotificationRecord.created_at.desc()).limit(limit).all()

    return [
        {
            "id": r.id,
            "contractor_id": r.contractor_id,
            "tender_id": r.tender_id,
            "recipient_email": r.recipient_email,
            "subject": r.subject,
            "status": r.status,
            "trigger_type": r.trigger_type,
            "sent_at": r.sent_at.isoformat() if r.sent_at else None,
            "error_message": r.error_message,
            "provider": r.provider,
            "created_at": r.created_at.isoformat() if r.created_at else None
        }
        for r in records
    ]


@app.post("/api/email/test")
def test_raw_email(payload: Dict[str, Any], db: Session = Depends(get_db)):
    """Direct email configuration test endpoint."""
    to_email = payload.get("to_email", "").strip()
    if not to_email or "@" not in to_email or "." not in to_email:
        raise HTTPException(status_code=400, detail="অবৈধ বা ত্রুটিপূর্ণ ইমেইল ঠিকানা প্রদান করা হয়েছে।")

    from backend.email_service import get_email_provider
    provider = get_email_provider()
    if not provider.is_configured():
        raise HTTPException(status_code=503, detail="ইমেইল সার্ভিস কনফিগার করা হয়নি বা অফলাইন রয়েছে।")

    res = provider.send_email(
        to_email=to_email,
        subject="[EjaraBD] টেস্ট ইমেইল ভেরিফিকেশন",
        text_body="ইজারাবিডি ইমেইল সার্ভিস সফলভাবে সংযুক্ত আছে।",
        html_body="<h3>ইজারাবিডি ইমেইল সার্ভিস সফলভাবে সংযুক্ত আছে।</h3>"
    )
    if not res.success:
        raise HTTPException(status_code=500, detail=res.error or "ইমেইল পাঠাতে ব্যর্থ হয়েছে।")

    return {
        "success": True,
        "recipient": to_email,
        "provider": provider.provider_name
    }


@app.post("/api/tenders/{tender_id}/email-test")
def test_tender_email(tender_id: str, payload: Dict[str, Any], db: Session = Depends(get_db)):
    """Direct single tender email test endpoint."""
    to_email = payload.get("to_email", "").strip()
    if not to_email or "@" not in to_email or "." not in to_email:
        raise HTTPException(status_code=400, detail="অবৈধ বা ত্রুটিপূর্ণ ইমেইল ঠিকানা।")

    tender = db.query(Tender).filter(Tender.tender_id == tender_id).first()
    if not tender and tender_id.isdigit():
        tender = db.query(Tender).filter(Tender.id == int(tender_id)).first()

    if not tender:
        raise HTTPException(status_code=404, detail="অনুরোধকৃত টেন্ডারটি ডেটাবেজে পাওয়া যায়নি।")

    contractor = db.query(ContractorProfile).filter(ContractorProfile.id == 1).first()
    if not contractor:
        contractor = db.query(ContractorProfile).first()

    assessment = None
    if contractor:
        assessment = db.query(MatchAssessment).filter(
            MatchAssessment.tender_id == tender.id,
            MatchAssessment.contractor_id == contractor.id
        ).first()

    subject, html_body, text_body = render_tender_notification_email(
        tender=tender,
        contractor=contractor,
        assessment=assessment
    )

    from backend.email_service import send_email
    res = send_email(
        to_email=to_email,
        subject=subject,
        html_body=html_body,
        text_body=text_body
    )
    if not res.success:
        raise HTTPException(status_code=500, detail=res.error or "টেন্ডার ইমেইল পাঠাতে ব্যর্থ হয়েছে।")

    return {
        "success": True,
        "tender_id": tender.tender_id,
        "recipient": to_email
    }

