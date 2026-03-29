"""
CivicWatch AI Engine
- NLP: category classification + keyword extraction (rule-based + optional HuggingFace)
- CV: image analysis via Gemini API (with fallback)
- Priority scoring: weighted formula
- RAG chatbot: ChromaDB + Claude API
"""

import os
import json
import re
import base64
from pathlib import Path
from typing import Optional
import httpx

# ── Category rules (no model needed for basic operation) ──────────────────────
CATEGORY_RULES = {
    "Pothole": ["pothole", "road damage", "road crack", "broken road", "crater", "road hole"],
    "Garbage": ["garbage", "trash", "waste", "litter", "dump", "rubbish", "filth", "dirty", "smell"],
    "Water Leakage": ["water leak", "leakage", "pipe burst", "broken pipe", "flooding", "waterlogging", "sewage", "drain"],
    "Street Light": ["street light", "light out", "dark road", "lamp post", "no light", "power"],
    "Infrastructure": ["bridge", "footpath", "pavement", "building crack", "wall collapse", "structure"],
    "Noise Pollution": ["noise", "loud", "sound", "disturbance", "music", "horn"],
    "Encroachment": ["encroachment", "illegal", "blocked", "obstruct", "hawker", "vendor"],
    "Other": []
}

SEVERITY_WORDS = {
    "critical": ["dangerous", "urgent", "emergency", "accident", "death", "injury", "collapsed", "burst", "flood"],
    "high": ["severe", "bad", "major", "serious", "broken", "damaged", "hazard", "risk"],
    "medium": ["issue", "problem", "concern", "moderate", "need attention"],
    "low": ["minor", "small", "little", "slight", "suggestion"]
}

CATEGORY_BASE_SCORES = {
    "Water Leakage": 8.0,
    "Infrastructure": 7.5,
    "Pothole": 7.0,
    "Street Light": 6.5,
    "Garbage": 5.5,
    "Noise Pollution": 4.5,
    "Encroachment": 4.0,
    "Other": 5.0
}


def classify_category(text: str) -> str:
    text_lower = text.lower()
    for category, keywords in CATEGORY_RULES.items():
        for kw in keywords:
            if kw in text_lower:
                return category
    return "Other"


def extract_keywords(text: str) -> list[str]:
    stop_words = {"the", "a", "an", "is", "are", "was", "were", "in", "on", "at", "to",
                  "of", "and", "or", "but", "it", "this", "that", "my", "our", "your"}
    words = re.findall(r'\b[a-zA-Z]{4,}\b', text.lower())
    keywords = [w for w in words if w not in stop_words]
    # Return top unique keywords by frequency
    freq = {}
    for w in keywords:
        freq[w] = freq.get(w, 0) + 1
    sorted_kw = sorted(freq, key=freq.get, reverse=True)
    return sorted_kw[:8]


def detect_sentiment(text: str) -> str:
    text_lower = text.lower()
    for severity, words in SEVERITY_WORDS.items():
        for w in words:
            if w in text_lower:
                return severity
    return "medium"


def compute_priority(category: str, sentiment: str, has_image: bool, location: bool) -> tuple[float, str]:
    base = CATEGORY_BASE_SCORES.get(category, 5.0)
    
    sentiment_bonus = {"critical": 2.5, "high": 1.5, "medium": 0.0, "low": -1.0}.get(sentiment, 0.0)
    image_bonus = 0.5 if has_image else 0.0
    location_bonus = 0.3 if location else 0.0
    
    score = min(10.0, max(1.0, base + sentiment_bonus + image_bonus + location_bonus))
    
    if score >= 8.5:
        label = "Critical"
    elif score >= 6.5:
        label = "High"
    elif score >= 4.5:
        label = "Medium"
    else:
        label = "Low"
    
    return round(score, 1), label


async def analyze_image_gemini(image_path: str) -> dict:
    """Analyze image using Gemini Vision API (free tier)."""
    api_key = os.getenv("GEMINI_API_KEY", "")
    if not api_key or api_key == "your_gemini_api_key_here":
        return _fallback_image_analysis(image_path)
    
    try:
        img_data = Path(image_path).read_bytes()
        b64 = base64.b64encode(img_data).decode()
        ext = Path(image_path).suffix.lower().replace(".", "")
        mime = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png", "webp": "image/webp"}.get(ext, "image/jpeg")
        
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
        payload = {
            "contents": [{
                "parts": [
                    {"inline_data": {"mime_type": mime, "data": b64}},
                    {"text": (
                        "You are a civic issue inspector. Analyze this image and respond ONLY with JSON:\n"
                        "{\n"
                        "  \"issue_detected\": \"short description of what you see\",\n"
                        "  \"category\": \"one of: Pothole/Garbage/Water Leakage/Street Light/Infrastructure/Other\",\n"
                        "  \"severity\": \"one of: critical/high/medium/low\",\n"
                        "  \"confidence\": 0.0-1.0,\n"
                        "  \"visible_details\": \"key visual observations\"\n"
                        "}"
                    )}
                ]
            }]
        }
        
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.post(url, json=payload)
            data = resp.json()
        
        raw_text = data["candidates"][0]["content"]["parts"][0]["text"]
        json_match = re.search(r'\{.*\}', raw_text, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
        return _fallback_image_analysis(image_path)
    
    except Exception as e:
        print(f"⚠️  Gemini API error: {e}")
        return _fallback_image_analysis(image_path)


def _fallback_image_analysis(image_path: str) -> dict:
    return {
        "issue_detected": "Image uploaded (manual review needed — add GEMINI_API_KEY for AI vision)",
        "category": "Other",
        "severity": "medium",
        "confidence": 0.5,
        "visible_details": "No API key configured for automated image analysis"
    }


def analyze_text(title: str, description: str) -> dict:
    full_text = f"{title} {description}"
    category = classify_category(full_text)
    sentiment = detect_sentiment(full_text)
    keywords = extract_keywords(full_text)
    return {
        "category": category,
        "sentiment": sentiment,
        "keywords": keywords
    }


async def full_analysis(title: str, description: str, image_path: Optional[str], latitude: Optional[float], longitude: Optional[float]) -> dict:
    """Run complete AI analysis pipeline."""
    # NLP
    nlp = analyze_text(title, description)
    
    # CV
    cv = {}
    if image_path and Path(image_path).exists():
        cv = await analyze_image_gemini(image_path)
    
    # Merge category (prefer CV if confident)
    final_category = nlp["category"]
    if cv.get("confidence", 0) > 0.7 and cv.get("category", "Other") != "Other":
        final_category = cv["category"]
    
    # Merge severity
    cv_severity = cv.get("severity", "medium")
    nlp_severity = nlp["sentiment"]
    severity_rank = {"critical": 4, "high": 3, "medium": 2, "low": 1}
    final_severity = cv_severity if severity_rank.get(cv_severity, 2) >= severity_rank.get(nlp_severity, 2) else nlp_severity
    
    # Priority
    score, label = compute_priority(
        final_category,
        final_severity,
        has_image=bool(image_path),
        location=bool(latitude and longitude)
    )
    
    ai_summary = (
        f"Category: {final_category} | Severity: {final_severity.capitalize()} | "
        f"Priority: {label} ({score}/10). "
        f"Keywords: {', '.join(nlp['keywords'][:4])}."
    )
    if cv.get("visible_details"):
        ai_summary += f" Visual: {cv['visible_details']}"
    
    return {
        "nlp_category": nlp["category"],
        "nlp_sentiment": nlp["sentiment"],
        "nlp_keywords": json.dumps(nlp["keywords"]),
        "cv_analysis": json.dumps(cv) if cv else None,
        "final_category": final_category,
        "priority_score": score,
        "priority_label": label,
        "ai_summary": ai_summary
    }


# ── RAG Chatbot ───────────────────────────────────────────────────────────────

_chroma_collection = None

def get_chroma_collection():
    global _chroma_collection
    if _chroma_collection is None:
        try:
            import chromadb
            client = chromadb.PersistentClient(path="./data/chroma")
            _chroma_collection = client.get_or_create_collection("complaints")
        except Exception as e:
            print(f"⚠️  ChromaDB not available: {e}")
    return _chroma_collection


def index_complaint(complaint_id: int, text: str, metadata: dict):
    """Add a complaint to the vector store."""
    col = get_chroma_collection()
    if col is None:
        return
    try:
        col.upsert(
            documents=[text],
            ids=[str(complaint_id)],
            metadatas=[metadata]
        )
    except Exception as e:
        print(f"⚠️  ChromaDB index error: {e}")


def retrieve_context(query: str, n: int = 5) -> list[dict]:
    """Retrieve relevant complaints for a query."""
    col = get_chroma_collection()
    if col is None:
        return []
    try:
        results = col.query(query_texts=[query], n_results=min(n, col.count() or 1))
        docs = results.get("documents", [[]])[0]
        metas = results.get("metadatas", [[]])[0]
        return [{"text": d, "meta": m} for d, m in zip(docs, metas)]
    except Exception:
        return []


async def chat_with_rag(user_question: str, db_summary: str) -> str:
    """RAG chatbot using Claude API."""
    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key or api_key == "your_anthropic_api_key_here":
        return "⚠️ Please add your ANTHROPIC_API_KEY to the .env file to enable the AI assistant."
    
    # Retrieve context
    context_items = retrieve_context(user_question)
    context_text = "\n".join([f"- {item['text']}" for item in context_items]) or "No specific complaints found."
    
    system_prompt = (
        "You are CivicWatch AI Assistant — an intelligent assistant for municipal administrators. "
        "You help analyze civic complaint data and provide actionable insights. "
        "Be concise, data-driven, and helpful. Use bullet points for lists."
    )
    
    user_prompt = (
        f"Database Summary:\n{db_summary}\n\n"
        f"Relevant Complaints:\n{context_text}\n\n"
        f"Admin Question: {user_question}"
    )
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json"
                },
                json={
                    "model": "claude-sonnet-4-20250514",
                    "max_tokens": 800,
                    "system": system_prompt,
                    "messages": [{"role": "user", "content": user_prompt}]
                }
            )
            data = resp.json()
            return data["content"][0]["text"]
    except Exception as e:
        return f"Error contacting Claude API: {str(e)}"
