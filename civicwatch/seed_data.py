#!/usr/bin/env python3
"""
Seed CivicWatch with sample complaints for demo/testing.
Run: python seed_data.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
os.chdir(os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

from backend.database import init_db, SessionLocal, Complaint
from ai.engine import analyze_text, compute_priority, index_complaint
import json
from datetime import datetime, timedelta
import random

SAMPLE_COMPLAINTS = [
    {"title": "Large pothole causing accidents near sector 14", "description": "There is a massive pothole on the main road near sector 14 market. Several bikes have already fallen. It is extremely dangerous and urgent action needed.", "location_text": "Sector 14 Market, Gurugram", "latitude": 28.4595, "longitude": 77.0266, "citizen_name": "Rahul Sharma", "days_ago": 1},
    {"title": "Garbage not collected for 5 days in our colony", "description": "Garbage has been accumulating for 5 days in C-block colony. The smell is terrible and creating health hazards. Flies and mosquitoes breeding everywhere.", "location_text": "C-Block DLF Phase 1, Gurugram", "latitude": 28.4724, "longitude": 77.0927, "citizen_name": "Priya Verma", "days_ago": 2},
    {"title": "Water pipe burst flooding entire street", "description": "Emergency! Water pipe has burst near the school crossing. Entire street is flooded and children cannot go to school safely. Immediate repair needed.", "location_text": "Near Government School, Sector 5", "latitude": 28.4651, "longitude": 77.0184, "citizen_name": "Amit Kumar", "days_ago": 0},
    {"title": "Street light not working for 2 weeks", "description": "The street light on the main road has been not working for 2 weeks. The area is very dark at night and people are afraid to walk. Two incidents of snatching have happened.", "location_text": "MG Road near Metro Station", "latitude": 28.4808, "longitude": 77.0873, "citizen_name": "Sunita Devi", "days_ago": 3},
    {"title": "Footpath broken and dangerous for pedestrians", "description": "The footpath tiles are broken and cracked. An elderly person fell and got injured last week. The infrastructure damage is severe and needs immediate repair.", "location_text": "Sector 29 Huda Market", "latitude": 28.4535, "longitude": 77.0706, "citizen_name": "Mohan Singh", "days_ago": 5},
    {"title": "Sewage overflow near residential area", "description": "Sewage water is overflowing from the drain and entering houses. The smell is unbearable. Water leakage from broken underground pipe is making the situation worse.", "location_text": "Sheetla Colony, Gurugram", "latitude": 28.4389, "longitude": 77.0060, "citizen_name": "Deepa Nair", "days_ago": 1},
    {"title": "Minor crack in boundary wall of park", "description": "Small crack has appeared in the boundary wall of sector 21 park. It is a minor issue but should be fixed before it gets worse.", "location_text": "Sector 21 Park", "latitude": 28.4701, "longitude": 77.0388, "citizen_name": "Rajesh Gupta", "days_ago": 7},
    {"title": "Illegal encroachment blocking footpath", "description": "A vendor has set up an illegal stall on the footpath completely blocking it. Pedestrians are forced to walk on the road which is dangerous.", "location_text": "Cyber City Gate 3", "latitude": 28.4943, "longitude": 77.0880, "citizen_name": "Anita Mehra", "days_ago": 4},
]

def seed():
    init_db()
    db = SessionLocal()

    existing = db.query(Complaint).count()
    if existing > 0:
        print(f"✅ Database already has {existing} complaints. Skipping seed.")
        db.close()
        return

    print("🌱 Seeding sample complaints...")
    statuses = ["Open", "Open", "Open", "In Progress", "Resolved"]

    for i, s in enumerate(SAMPLE_COMPLAINTS):
        nlp = analyze_text(s["title"], s["description"])
        score, label = compute_priority(nlp["category"], nlp["sentiment"], False, True)
        status = random.choice(statuses)

        c = Complaint(
            title=s["title"],
            description=s["description"],
            location_text=s["location_text"],
            latitude=s.get("latitude"),
            longitude=s.get("longitude"),
            citizen_name=s.get("citizen_name"),
            category=nlp["category"],
            nlp_category=nlp["category"],
            nlp_sentiment=nlp["sentiment"],
            nlp_keywords=json.dumps(nlp["keywords"]),
            priority_score=score,
            priority_label=label,
            ai_summary=f"Category: {nlp['category']} | Severity: {nlp['sentiment'].capitalize()} | Priority: {label} ({score}/10). Keywords: {', '.join(nlp['keywords'][:4])}.",
            status=status,
            created_at=datetime.utcnow() - timedelta(days=s["days_ago"]),
            resolved_at=datetime.utcnow() if status == "Resolved" else None
        )
        db.add(c)
        db.commit()
        db.refresh(c)

        index_complaint(c.id, f"{c.title} {c.description} {c.location_text}", {
            "category": c.category, "priority": c.priority_label,
            "status": c.status, "location": c.location_text
        })
        print(f"  #{c.id} — {c.title[:50]}... [{c.priority_label}]")

    print(f"\n✅ Seeded {len(SAMPLE_COMPLAINTS)} sample complaints!")
    print("🌐 Open http://127.0.0.1:8000/admin to see them")
    db.close()

if __name__ == '__main__':
    seed()
