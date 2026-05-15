# GemmaLens

GemmaLens: Multimodal Language Learning from Any Content.

Local-first learning harness for turning documents, transcripts, and short passages into personalized language-learning objects with Gemma.

## Stack

- Backend: FastAPI, Pydantic, SQLAlchemy, SQLite, Uvicorn
- Frontend: Next.js, TypeScript, Tailwind CSS
- Model layer: provider-neutral adapter with MLX local runtime, Ollama scaffold, and demo-only mock mode

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

## Run Local Demo Stack

For phone/team testing on the local network, use the fixed demo ports:

```bash
./scripts/run_local_stack.sh
```

This starts:

- Backend: `http://127.0.0.1:8012`
- Frontend: `http://localhost:3003`

The frontend uses a same-origin `/api/backend/*` proxy for private/local backend URLs. This avoids browser CORS and changed-IP failures when testing from Samsung Internet or another device on the same network.

## Smoke Test

```bash
curl http://127.0.0.1:8000/health
curl -X POST http://127.0.0.1:8000/documents \
  -H "Content-Type: application/json" \
  -d '{"title":"Demo","content":"Although previous studies have suggested a correlation between sleep deprivation and reduced cognitive performance, the extent to which these findings generalize across real-world learning environments remains unclear. To address this gap, we analyze longitudinal study logs collected from undergraduate students over a six-week period.","source_type":"text"}'
```

## Test

```bash
cd backend
pip install -r requirements-dev.txt
ruff check app tests
pytest
```

Uploads support `.txt`, `.md`, `.markdown`, and basic text-extractable `.pdf` files through `POST /documents/upload`.

## Prototype Scope

This slice supports pasted text or uploaded text/markdown/PDF files, local structured document analysis, transcript learning, dictionary saving, short model-backed translation, and quiz draft generation. Mock/demo content is only shown when `NEXT_PUBLIC_DEMO_MODE=true`. Full-paper staged analysis, model-backed quiz generation, auth, sync, and multi-document RAG are roadmap items.

## Optional Gemma 4 MLX Runtime

For Apple Silicon, use the MLX path. The recommended small local model is:

```txt
mlx-community/gemma-4-e4b-it-bf16
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

Local MLX failures return explicit errors. Mock output is reserved for demo/deployment UI testing via `APP_DEMO_MODE=true`.

The default E4B preset uses the full-precision MLX bf16 conversion at `~/Models/mlx/gemma-4-e4b-it-bf16`.

Run one local model smoke test and save normalized JSON:

```bash
backend/.venv-mlx/bin/python scripts/local_model_smoke.py --provider mlx --preset gemma4-e4b-mlx
```

Output is written to `tmp/local_model_smoke.json`.

Run a local E2B/E4B benchmark over fixed samples:

```bash
backend/.venv-mlx/bin/python scripts/model_benchmark.py
```

Benchmark summaries are written to `tmp/model_benchmark/summary.json` and `tmp/model_benchmark/summary.csv`.

## Technical Report

See `docs/TECHNICAL_REPORT.md` for architecture, competition-rule checklist, current limitations, and recommended learning-method design.
