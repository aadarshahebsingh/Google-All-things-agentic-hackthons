# Setup

## Prerequisites
- Python 3.11+
- Node 18+
- A Google Cloud project (Vertex AI, Firestore, Pub/Sub, Calendar API enabled) — optional for demo mode.

## Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt   # Windows
copy ..\.env.example .env                        # fill in what you have; demo mode works with none
.venv\Scripts\python -m pytest tests -q          # run tests
.venv\Scripts\uvicorn app.main:app --port 8080 --reload
```

## Frontend

```bash
cd frontend
npm install
npm run dev    # http://localhost:3000, proxies /api to :8080
```

## Google Cloud enablement

```bash
gcloud services enable aiplatform.googleapis.com firestore.googleapis.com \
  pubsub.googleapis.com calendar-json.googleapis.com run.googleapis.com
gcloud pubsub topics create founder-shortcut-jobs
```

For the real ADK/Gemini path set `GOOGLE_GENAI_USE_VERTEXAI=TRUE` with Application Default Credentials (`gcloud auth application-default login`). Without credentials the system runs in demo mode: deterministic parsing + cached sources + simulated voice, all labeled in the UI and event log.
