"""
CivicWatch — FastAPI Backend
Run with: uvicorn backend.main:app --reload --port 8000
"""

import os
import sys
import json
import shutil
from pathlib import Path
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse
from sqlalchemy.orm import Session
from sqlalchemy import func

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from backend.database import get_db, init_db, Complaint
from ai.engine import full_analysis, chat_with_rag, index_complaint

app = FastAPI(title="CivicWatch API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files & templates
app.mount("/static", StaticFiles(directory="frontend/static"), name="static")
app.mount("/uploads", StaticFiles(directory="data/uploads"), name="uploads")
templates = Jinja2Templates(directory="frontend")

UPLOAD_DIR = Path("data/uploads")
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}


# ── Pages ─────────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def citizen_portal(request: Request):
    return templates.TemplateResponse(request, "citizen.html")


@app.get("/admin", response_class=HTMLResponse)
async def admin_dashboard(request: Request):
    return templates.TemplateResponse(request, "admin.html")


# ── Complaints API ─────────────────────────────────────────────────────────────

@app.post("/api/complaints")
async def submit_complaint(
    title: str = Form(...),
    description: str = Form(...),
    location_text: str = Form(""),
    latitude: Optional[float] = Form(None),
    longitude: Optional[float] = Form(None),
    citizen_name: str = Form(""),
    citizen_email: str = Form(""),
    citizen_phone: str = Form(""),
    image: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db)
):
    image_path = None
    if image and image.filename:
        ext = Path(image.filename).suffix.lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(400, "Image must be JPG, PNG, or WEBP")
        
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}_{image.filename}"
        save_path = UPLOAD_DIR / filename
        with save_path.open("wb") as f:
            shutil.copyfileobj(image.file, f)
        image_path = str(save_path)
    
    # Run AI analysis
    analysis = await full_analysis(title, description, image_path, latitude, longitude)
    
    complaint = Complaint(
        title=title,
        description=description,
        location_text=location_text,
        latitude=latitude,
        longitude=longitude,
        citizen_name=citizen_name,
        citizen_email=citizen_email,
        citizen_phone=citizen_phone,
        image_path=image_path,
        category=analysis["final_category"],
        nlp_category=analysis["nlp_category"],
        nlp_sentiment=analysis["nlp_sentiment"],
        nlp_keywords=analysis["nlp_keywords"],
        cv_analysis=analysis["cv_analysis"],
        priority_score=analysis["priority_score"],
        priority_label=analysis["priority_label"],
        ai_summary=analysis["ai_summary"],
        status="Open"
    )
    db.add(complaint)
    db.commit()
    db.refresh(complaint)
    
    # Index in vector DB for RAG
    index_text = f"{title} {description} {location_text} Category:{complaint.category}"
    index_complaint(complaint.id, index_text, {
        "category": complaint.category,
        "priority": complaint.priority_label,
        "status": complaint.status,
        "location": location_text
    })
    
    return {
        "success": True,
        "complaint_id": complaint.id,
        "category": complaint.category,
        "priority_score": complaint.priority_score,
        "priority_label": complaint.priority_label,
        "ai_summary": complaint.ai_summary,
        "message": f"Complaint #{complaint.id} submitted successfully!"
    }


@app.get("/api/complaints")
def list_complaints(
    status: Optional[str] = None,
    category: Optional[str] = None,
    priority: Optional[str] = None,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    q = db.query(Complaint)
    if status:
        q = q.filter(Complaint.status == status)
    if category:
        q = q.filter(Complaint.category == category)
    if priority:
        q = q.filter(Complaint.priority_label == priority)
    complaints = q.order_by(Complaint.priority_score.desc(), Complaint.created_at.desc()).limit(limit).all()
    return [_serialize(c) for c in complaints]


@app.get("/api/complaints/{complaint_id}")
def get_complaint(complaint_id: int, db: Session = Depends(get_db)):
    c = db.query(Complaint).filter(Complaint.id == complaint_id).first()
    if not c:
        raise HTTPException(404, "Complaint not found")
    return _serialize(c)


@app.patch("/api/complaints/{complaint_id}/status")
def update_status(complaint_id: int, payload: dict, db: Session = Depends(get_db)):
    c = db.query(Complaint).filter(Complaint.id == complaint_id).first()
    if not c:
        raise HTTPException(404, "Complaint not found")
    
    new_status = payload.get("status")
    admin_notes = payload.get("admin_notes")
    
    if new_status:
        c.status = new_status
        if new_status == "Resolved":
            c.resolved_at = datetime.utcnow()
    if admin_notes is not None:
        c.admin_notes = admin_notes
    
    c.updated_at = datetime.utcnow()
    db.commit()
    return {"success": True, "status": c.status}


# ── Stats API ─────────────────────────────────────────────────────────────────

@app.get("/api/stats")
def get_stats(db: Session = Depends(get_db)):
    total = db.query(func.count(Complaint.id)).scalar()
    open_count = db.query(func.count(Complaint.id)).filter(Complaint.status == "Open").scalar()
    resolved = db.query(func.count(Complaint.id)).filter(Complaint.status == "Resolved").scalar()
    critical = db.query(func.count(Complaint.id)).filter(Complaint.priority_label == "Critical").scalar()
    
    by_category = (
        db.query(Complaint.category, func.count(Complaint.id).label("count"))
        .group_by(Complaint.category).all()
    )
    by_status = (
        db.query(Complaint.status, func.count(Complaint.id).label("count"))
        .group_by(Complaint.status).all()
    )
    by_priority = (
        db.query(Complaint.priority_label, func.count(Complaint.id).label("count"))
        .group_by(Complaint.priority_label).all()
    )
    
    recent = (
        db.query(Complaint)
        .order_by(Complaint.created_at.desc())
        .limit(5).all()
    )
    
    map_points = (
        db.query(Complaint)
        .filter(Complaint.latitude.isnot(None), Complaint.longitude.isnot(None))
        .all()
    )
    
    return {
        "total": total,
        "open": open_count,
        "resolved": resolved,
        "critical": critical,
        "by_category": [{"category": r[0], "count": r[1]} for r in by_category],
        "by_status": [{"status": r[0], "count": r[1]} for r in by_status],
        "by_priority": [{"priority": r[0], "count": r[1]} for r in by_priority],
        "recent": [_serialize(c) for c in recent],
        "map_points": [
            {
                "id": c.id, "lat": c.latitude, "lng": c.longitude,
                "title": c.title, "category": c.category,
                "priority": c.priority_label, "status": c.status
            }
            for c in map_points
        ]
    }


# ── RAG Chatbot API ───────────────────────────────────────────────────────────

@app.post("/api/chat")
async def chat(payload: dict, db: Session = Depends(get_db)):
    question = payload.get("question", "").strip()
    if not question:
        raise HTTPException(400, "Question is required")
    
    # Build DB summary for context
    total = db.query(func.count(Complaint.id)).scalar()
    open_c = db.query(func.count(Complaint.id)).filter(Complaint.status == "Open").scalar()
    critical = db.query(func.count(Complaint.id)).filter(Complaint.priority_label == "Critical").scalar()
    
    by_cat = db.query(Complaint.category, func.count(Complaint.id)).group_by(Complaint.category).all()
    cat_summary = ", ".join([f"{cat}: {cnt}" for cat, cnt in by_cat])
    
    db_summary = (
        f"Total complaints: {total}. Open: {open_c}. Critical: {critical}. "
        f"By category: {cat_summary}."
    )
    
    answer = await chat_with_rag(question, db_summary)
    return {"answer": answer}


# ── Helpers ────────────────────────────────────────────────────────────────────

def _serialize(c: Complaint) -> dict:
    cv = {}
    if c.cv_analysis:
        try:
            cv = json.loads(c.cv_analysis)
        except Exception:
            pass
    keywords = []
    if c.nlp_keywords:
        try:
            keywords = json.loads(c.nlp_keywords)
        except Exception:
            pass
    
    image_url = None
    if c.image_path:
        fname = Path(c.image_path).name
        image_url = f"/uploads/{fname}"
    
    return {
        "id": c.id,
        "title": c.title,
        "description": c.description,
        "category": c.category,
        "location_text": c.location_text,
        "latitude": c.latitude,
        "longitude": c.longitude,
        "image_url": image_url,
        "nlp_category": c.nlp_category,
        "nlp_sentiment": c.nlp_sentiment,
        "nlp_keywords": keywords,
        "cv_analysis": cv,
        "priority_score": c.priority_score,
        "priority_label": c.priority_label,
        "ai_summary": c.ai_summary,
        "status": c.status,
        "citizen_name": c.citizen_name,
        "citizen_email": c.citizen_email,
        "admin_notes": c.admin_notes,
        "created_at": c.created_at.isoformat() if c.created_at else None,
        "updated_at": c.updated_at.isoformat() if c.updated_at else None,
        "resolved_at": c.resolved_at.isoformat() if c.resolved_at else None,
    }


# ── Startup ────────────────────────────────────────────────────────────────────

@app.on_event("startup")
async def startup():
    init_db()
    print("🚀 CivicWatch running at http://127.0.0.1:8000")
    print("📊 Admin dashboard: http://127.0.0.1:8000/admin")
