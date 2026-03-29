# ⚡ CivicWatch — AI-Powered Civic Issue Monitoring System

An end-to-end AI civic complaint system with NLP analysis, computer vision, priority scoring, admin dashboard, map view, and RAG chatbot.

---

## 🚀 Quick Start (5 minutes)

### Prerequisites
- Python 3.10 or higher
- VS Code (recommended)

### Step 1 — Clone / Open the folder in VS Code
```
Open the civicwatch/ folder in VS Code
Open a terminal: Terminal → New Terminal
```

### Step 2 — Create virtual environment
```bash
python -m venv venv

# Windows:
venv\Scripts\activate

# Mac/Linux:
source venv/bin/activate
```

### Step 3 — Install dependencies
```bash
# Fast install (recommended to start):
pip install -r requirements-minimal.txt

# OR full install (includes HuggingFace models — slower):
pip install -r requirements.txt
```

### Step 4 — Configure API keys (optional but recommended)
```bash
# Copy the template:
cp .env.example .env

# Edit .env and add your keys:
# ANTHROPIC_API_KEY=sk-ant-...  ← for AI chatbot (free at console.anthropic.com)
# GEMINI_API_KEY=...            ← for image analysis (free at aistudio.google.com)
```

### Step 5 — Run the app
```bash
python run.py
```

### Step 6 — Add sample data (optional)
Open a second terminal (with venv activated):
```bash
python seed_data.py
```

### Step 7 — Open in browser
- 🌐 **Citizen Portal**: http://127.0.0.1:8000
- 📊 **Admin Dashboard**: http://127.0.0.1:8000/admin
- 📚 **API Docs**: http://127.0.0.1:8000/docs

---

## 📁 Project Structure

```
civicwatch/
├── backend/
│   ├── main.py          # FastAPI app — all routes
│   └── database.py      # SQLAlchemy models + DB setup
├── ai/
│   └── engine.py        # NLP + CV + Priority + RAG
├── frontend/
│   ├── citizen.html     # Complaint submission portal
│   └── admin.html       # Admin dashboard
├── data/
│   ├── uploads/         # Uploaded images
│   └── civicwatch.db    # SQLite database (auto-created)
├── run.py               # One-command launcher
├── seed_data.py         # Sample data seeder
├── requirements.txt     # Full dependencies
├── requirements-minimal.txt  # Minimal (fast install)
└── .env.example         # API key template
```

---

## ✨ Features

| Feature | Status | Notes |
|---|---|---|
| Complaint submission (text + image + GPS) | ✅ | Works without any API key |
| NLP category classification | ✅ | Rule-based, no API needed |
| Sentiment / severity detection | ✅ | Rule-based, no API needed |
| Priority scoring (1-10) | ✅ | Weighted formula |
| Image analysis (Computer Vision) | ✅ | Needs GEMINI_API_KEY (free) |
| Admin dashboard with charts | ✅ | Chart.js, no API needed |
| Interactive map view | ✅ | Leaflet.js, needs GPS in complaints |
| Complaint tracking by ID | ✅ | Works for citizens |
| Status management | ✅ | Open → In Progress → Resolved |
| CSV export | ✅ | One click in admin |
| RAG AI chatbot | ✅ | Needs ANTHROPIC_API_KEY |
| Vector search (ChromaDB) | ✅ | Auto-used for RAG |

---

## 🔑 API Keys (Where to Get Them Free)

### Anthropic API Key (for AI chatbot)
1. Go to https://console.anthropic.com
2. Sign up → API Keys → Create key
3. Add to `.env` as `ANTHROPIC_API_KEY=sk-ant-...`

### Gemini API Key (for image analysis)
1. Go to https://aistudio.google.com
2. Sign in → Get API key → Create API key
3. Add to `.env` as `GEMINI_API_KEY=AIza...`

**The app works perfectly without any API keys** — only the AI chatbot and image AI analysis need keys. All NLP, priority scoring, and the dashboard work out of the box.

---

## 🧪 Testing the API

With the app running, open http://127.0.0.1:8000/docs for the interactive Swagger UI.

Or use curl:
```bash
# Submit a complaint
curl -X POST http://127.0.0.1:8000/api/complaints \
  -F "title=Pothole on main road" \
  -F "description=Large dangerous pothole causing accidents near market"

# Get all complaints
curl http://127.0.0.1:8000/api/complaints

# Get stats
curl http://127.0.0.1:8000/api/stats

# Chat with AI
curl -X POST http://127.0.0.1:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"question": "What are the most critical issues?"}'
```

---

## 🛠️ VS Code Tips

1. Install the **Python extension** in VS Code
2. Select the venv interpreter: `Ctrl+Shift+P` → "Python: Select Interpreter" → choose `venv`
3. Use the integrated terminal (`Ctrl+\``) to run commands
4. The app auto-reloads when you edit files (thanks to `--reload`)

---

## 📈 For Your Resume / Project Report

**Tech Stack:**
- Backend: FastAPI (Python), SQLAlchemy, SQLite
- AI/NLP: Rule-based classifier, sentiment analysis, keyword extraction
- Computer Vision: Google Gemini Vision API
- RAG Chatbot: ChromaDB (vector store) + Claude API
- Frontend: Vanilla HTML/CSS/JS, Chart.js, Leaflet.js
- Architecture: REST API, MVC pattern

**Key AI Features:**
- Automatic issue categorization (8 categories)
- Severity detection from text
- Priority score computation (weighted multi-factor)
- Image content analysis
- Vector similarity search for RAG
- AI-generated complaint summaries
