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
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8012
```

Backend API: `http://127.0.0.1:8012`

## Run Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend app: `http://localhost:3000`

Set `BACKEND_INTERNAL_URL=http://127.0.0.1:8012` or `NEXT_PUBLIC_API_BASE_URL` if the backend runs elsewhere.

## Run Local Demo Stack

For phone/team testing on the local network, use the fixed demo ports:

```bash
./scripts/run_local_stack.sh
```

This starts:

- Backend: `http://127.0.0.1:8012`
- Frontend: `http://localhost:3003`

The frontend uses a same-origin `/api/backend/*` proxy for private/local backend URLs. This avoids browser CORS and changed-IP failures when testing from Samsung Internet or another device on the same network.

The local stack uses Next.js webpack dev mode for stability. Turbopack previously caused repeated dev-server panics and browser refresh loops in this project.

If the frontend is running but upload shows `Backend is not reachable at http://127.0.0.1:8012`, the backend process is down while the Next.js app is still alive. Restart the stack with `./scripts/run_local_stack.sh`, or start the backend on port `8012` before uploading.

## Smoke Test

```bash
curl http://127.0.0.1:8012/health
curl -X POST http://127.0.0.1:8012/documents \
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

Uploads support `.txt`, `.md`, `.markdown`, `.docx`, and basic text-extractable `.pdf` files through `POST /documents/upload`. Legacy `.doc` files should be exported to `.docx`, `.pdf`, or `.txt` first. Scanned/image-only PDFs need OCR before GemmaLens can analyze them.
Uploaded originals are stored locally so PDF uploads can be opened through `GET /documents/{id}/file` and rendered in the analysis workspace. Existing documents created before this storage change will not have an original file attached.
For existing demo documents, attach the original source later with `POST /documents/{id}/file`; the document id and existing analysis can remain in place.

## Prototype Scope

This slice supports pasted text or uploaded text/markdown/DOCX/PDF files, local structured document analysis, transcript learning, learning-library saves, short model-backed translation, and quiz draft generation. Mock/demo content is only shown when `NEXT_PUBLIC_DEMO_MODE=true`. Long PDFs open directly into a source-aware section workspace; GemmaLens shows the first page/section first, then prepares remaining section lessons in the background when the setting is enabled.

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

## Optional Remote Gemma Runtime

GemmaLens can also route model calls to a LAN/Tailscale Gemma server when the local GPU is busy. The current tested server is:

```txt
http://PRIVATE-GEMMA-SERVER:11444
```

Available presets:

- `Gemma 4 E2B (ThinkPad fp16)`
- `Gemma 4 E2B (ThinkPad Q4)`
- `Gemma 4 E4B (ThinkPad fp16)`

Select the preset from the dashboard model card under `Change model`, or call:

```bash
curl -X POST http://127.0.0.1:8012/models/config \
  -H "Content-Type: application/json" \
  -d '{"preset_id":"gemma4-e2b-thinkpad"}'
```

The backend reads the remote server from `REMOTE_GEMMA_BASE_URL`. `scripts/run_local_stack.sh` defaults that variable to the current ThinkPad Tailscale server for local testing.

For fast functional testing, prefer the Q4 preset. It uses the ThinkPad llama.cpp server on `http://PRIVATE-GEMMA-SERVER:11445` and leaves the fp16 server on `:11444` untouched.

The Q4 route uses an atomic analysis path: separate small calls for learning terms, phrases, and sentence explanation, followed by parser/validator cleanup and source-grounded fallback. This is the recommended path for CPU or mobile-class edge testing.

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
