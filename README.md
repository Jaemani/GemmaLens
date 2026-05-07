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

## Smoke Test

```bash
curl http://127.0.0.1:8000/health
curl -X POST http://127.0.0.1:8000/documents \
  -H "Content-Type: application/json" \
  -d '{"title":"Demo","content":"Although previous studies have suggested a correlation between sleep deprivation and reduced cognitive performance, the extent to which these findings generalize across real-world learning environments remains unclear. To address this gap, we analyze longitudinal study logs collected from undergraduate students over a six-week period.","source_type":"text"}'
```

## Prototype Scope

This first slice supports pasted text or uploaded text/markdown/PDF files, mock structured document analysis, and dictionary saving. Real model quality, auth, quizzes, sync, and multi-document RAG are roadmap items.

## Optional Gemma 4 MLX Runtime

For Apple Silicon, use the MLX path. The recommended small local model is:

```txt
mlx-community/gemma-4-e4b-it-OptiQ-4bit
```

Download model weights:

```bash
./scripts/download_gemma4_mlx.sh
```

Install MLX backend env with Python 3.12:

```bash
./scripts/setup_backend_mlx.sh
```

Run backend with MLX provider:

```bash
./scripts/run_backend_mlx.sh
```

The app still falls back to mock output if MLX is missing, fails to load, or returns invalid JSON.

Note: `mlx-community/gemma-4-e4b-it-4bit` is a multimodal/VLM conversion and may not load in `mlx-lm` text-only mode. The OptiQ variant is the default because its model card documents standard `mlx-lm` usage.
