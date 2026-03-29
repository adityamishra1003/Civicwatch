from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data/civicwatch.db")

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class Complaint(Base):
    __tablename__ = "complaints"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    category = Column(String(100), default="Uncategorized")
    location_text = Column(String(300))
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    image_path = Column(String(500), nullable=True)
    
    # AI Analysis
    nlp_category = Column(String(100), nullable=True)
    nlp_sentiment = Column(String(50), nullable=True)
    nlp_keywords = Column(Text, nullable=True)          # JSON string
    cv_analysis = Column(Text, nullable=True)            # JSON string
    priority_score = Column(Float, default=5.0)
    priority_label = Column(String(20), default="Medium")
    ai_summary = Column(Text, nullable=True)
    
    # Status
    status = Column(String(50), default="Open")          # Open, In Progress, Resolved
    citizen_name = Column(String(150), nullable=True)
    citizen_email = Column(String(200), nullable=True)
    citizen_phone = Column(String(30), nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    resolved_at = Column(DateTime, nullable=True)
    admin_notes = Column(Text, nullable=True)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    os.makedirs("data", exist_ok=True)
    os.makedirs("data/uploads", exist_ok=True)
    Base.metadata.create_all(bind=engine)
    print("✅ Database initialised")
