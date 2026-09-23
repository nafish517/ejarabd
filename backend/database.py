import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# লোকাল ফোল্ডারে SQLite ডাটাবেজ ফাইল পাথ নির্ধারণ
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

import sys

def get_db_path(db_name: str = None) -> str:
    name = db_name or os.getenv("EJARABD_DB_NAME") or os.getenv("TENDERWISE_DB_NAME")
    if not name:
        if "unittest" in sys.modules or os.getenv("TESTING") == "1" or "pytest" in sys.modules:
            name = "test_ejarabd.db"
        else:
            name = "ejarabd.db"
    return os.path.join(BASE_DIR, name)

DB_PATH = get_db_path()
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DB_PATH}")

# SQLite-এর জন্য মাল্টিথ্রেড সেফটি হ্যান্ডলিং
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=False
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def init_db_schema(target_engine=None):
    """
    নিরাপদ ও অক্ষত স্কিমা মাইগ্রেশন:
    বিদ্যমান ১৭০০+ টেন্ডার ও পাইলট রেকর্ড সম্পূর্ণ অক্ষত রেখে
    নতুন কলাম ও নতুন টেবিলসমূহ নিরাপদে যুক্ত করা হয়।
    """
    curr_engine = target_engine or engine
    
    # 1. Base.metadata.create_all দিয়ে নতুন টেবিল (payment_records, email_notification_records, activity_events) তৈরি
    Base.metadata.create_all(bind=curr_engine)

    # 2. SQLite ALTER TABLE দিয়ে contractor_profiles-এ নতুন ফিল্ড যুক্ত করা
    with curr_engine.connect() as conn:
        try:
            res = conn.exec_driver_sql("PRAGMA table_info(contractor_profiles)")
            existing_cols = {row[1] for row in res.fetchall()}
            
            if existing_cols:
                new_columns = [
                    ("email", "VARCHAR(255)"),
                    ("phone", "VARCHAR(50)"),
                    ("district", "VARCHAR(100)"),
                    ("client_status", "VARCHAR(50) DEFAULT 'active'"),
                    ("account_status", "VARCHAR(50) DEFAULT 'active'"),
                    ("payment_status", "VARCHAR(50) DEFAULT 'confirmed'"),
                    ("subscription_status", "VARCHAR(50) DEFAULT 'active'"),
                    ("subscription_expires_at", "DATETIME"),
                    ("onboarding_status", "VARCHAR(50) DEFAULT 'complete'"),
                    ("onboarding_data", "JSON"),
                    ("is_demo", "BOOLEAN DEFAULT 0"),
                    ("notification_schedules", "JSON DEFAULT '[\"12:00\", \"19:00\"]'"),
                    ("notification_preference", "VARCHAR(50) DEFAULT 'daily_email'"),
                    ("preferred_upazilas", "JSON DEFAULT '[]'"),
                    ("years_of_experience", "INTEGER"),
                    ("previous_project_types", "JSON DEFAULT '[]'"),
                    ("similar_work_experience", "TEXT"),
                    ("approx_annual_turnover_bdt", "FLOAT"),
                    ("available_equipment", "JSON DEFAULT '[]'"),
                    ("available_manpower", "JSON DEFAULT '[]'"),
                    ("licenses_certifications", "JSON DEFAULT '[]'"),
                    ("excluded_areas_or_categories", "JSON DEFAULT '[]'"),
                ]
                
                for col_name, col_type in new_columns:
                    if col_name not in existing_cols:
                        conn.exec_driver_sql(f"ALTER TABLE contractor_profiles ADD COLUMN {col_name} {col_type}")
                
                # পাইলট ক্লায়েন্ট #1 (পিতার প্রোফাইল) ও বিদ্যমান ক্লায়েন্ট রেকর্ড সক্রিয় রাখা
                conn.exec_driver_sql("""
                    UPDATE contractor_profiles 
                    SET client_status = 'active',
                        account_status = 'active', 
                        payment_status = 'confirmed', 
                        subscription_status = 'active', 
                        onboarding_status = 'complete'
                    WHERE (client_status IS NULL OR client_status = 'lead_payment_pending' OR client_status = '')
                """)
                conn.commit()
        except Exception:
            pass


def set_database(db_name: str):
    """টেস্ট বা ভিন্ন ডাটাবেজে রূপান্তর করার ইউটিলিটি"""
    global engine, DATABASE_URL, DB_PATH
    DB_PATH = get_db_path(db_name)
    DATABASE_URL = f"sqlite:///{DB_PATH}"
    engine.dispose()
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
        echo=False
    )
    SessionLocal.configure(bind=engine)
    init_db_schema(engine)

def get_db():
    """ডাটাবেজ সেশন ডিপেনডেন্সি"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

