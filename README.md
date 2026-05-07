# PaperLens Core Prototype

Local-first academic language learning harness for turning documents into structured learning objects.

## Stack

- Backend: FastAPI, Pydantic, SQLAlchemy, SQLite, Uvicorn
- Frontend: Next.js, TypeScript, Tailwind CSS
- Model layer: provider-neutral adapter with mock default and Ollama scaffold

## Run Backend

```bash
cd backend
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Backend API: `http://localhost:8000`

## Run Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend app: `http://localhost:3000`

Set `NEXT_PUBLIC_API_BASE_URL=http://localhost:8000` if the backend runs elsewhere.

## Prototype Scope

This first slice supports pasted text or uploaded text/markdown/PDF files, mock structured document analysis, and dictionary saving. Real model quality, auth, quizzes, sync, and multi-document RAG are roadmap items.
