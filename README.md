<p align="center">
  <img src="./frontend/public/gemmalens_icon.png" alt="GemmaLens icon" width="96" height="96" />
</p>

<h1 align="center">GemmaLens</h1>

<p align="center">
  A local-first academic reading coach powered by Gemma.
</p>

<p align="center">
  <strong>Translation helps with this sentence. GemmaLens helps you read the next one.</strong>
</p>

---

## What It Does

GemmaLens turns real learning sources into source-grounded study material:

- academic PDFs and papers
- technical documents and reports
- local videos with SRT/VTT subtitles
- public videos with available transcripts

Instead of replacing reading with a summary, GemmaLens keeps the source visible and builds learning objects beside it:

- key ideas
- technical vocabulary
- reusable academic phrases
- difficult sentence patterns
- paper maps
- saved review items

The first user is a non-native English-speaking student or researcher who needs to read papers, lectures, documentation, and technical material with more durable support than one-off translation.

## Why Gemma

GemmaLens is designed around small, local, incremental jobs:

```txt
source -> sections or subtitle windows -> Gemma analysis -> learning objects -> saved review
```

That shape fits Gemma well:

- E2B can provide fast glosses and live subtitle cues.
- E4B gives stronger local phrase and sentence analysis.
- Larger Gemma routes can be used for deeper paper maps and recaps.
- The same workflow can run locally, on a private edge backend, or in a low-connectivity setting.

The product goal is not a chatbot. It is a reading workspace where Gemma prepares the next useful lesson while the learner keeps reading.

## Core Workflows

### Paper Reading

1. Upload a PDF, DOCX, Markdown, or text file.
2. GemmaLens opens the first readable page or section quickly.
3. Remaining sections prepare in the background.
4. The learner reads the original source beside structured notes.
5. Paper map, key ideas, vocabulary, phrases, and sentence patterns grow from analyzed sections.

### Video Study

1. Load a local video or a public video transcript.
2. Attach or fetch English subtitles.
3. The subtitle timeline follows playback.
4. GemmaLens surfaces live cues, scene lessons, and watched-part recaps.
5. The learner can save terms, concepts, and spoken expressions to the library.

### Review

Saved terms, phrases, concepts, and sentence patterns become reviewable items. Quiz prompts are generated from current saved sources and local drafts, not from a permanent backend quiz table.

## Architecture

```txt
frontend/
  Next.js + TypeScript + Tailwind
  document reader, video workspace, library, settings, guide

backend/
  FastAPI + Pydantic + SQLAlchemy + SQLite
  ingestion, sectioning, model adapters, normalization, dictionary

model layer/
  provider-neutral adapter
  MLX local Gemma route
  optional MLX 4-bit larger Gemma routes
  optional GGUF/llama.cpp bridge
  Ollama scaffold
  remote/private Gemma route
  mock mode for UI and CI smoke tests
```

Important design constraints:

- Prompts do not live in route handlers.
- Model output is normalized into structured objects.
- Source sentences remain attached to learning objects.
- Local/private routes are preferred for sensitive documents.
- Demo mode is explicit and separate from real model behavior.

## Quick Start

### 1. Backend

```bash
cd backend
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8012
```

Backend health check:

```bash
curl http://localhost:8012/health
```

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

Open:

```txt
http://localhost:3000
```

If the backend is not on `localhost:8012`, set one of:

```bash
BACKEND_INTERNAL_URL=http://localhost:8012
NEXT_PUBLIC_API_BASE_URL=http://localhost:8012
```

### 3. Local Demo Stack

For the fixed local demo ports:

```bash
./scripts/run_local_stack.sh
```

Default local demo ports:

- backend: `http://localhost:8012`
- frontend: `http://localhost:3003`

The frontend proxies browser requests through `/api/backend/*`, so a Vercel or local frontend can call a private backend without exposing backend keys to the browser.

## Optional Gemma MLX Runtime

For Apple Silicon:

```bash
./scripts/download_gemma4_mlx.sh
./scripts/setup_backend_mlx.sh
./scripts/run_backend_mlx.sh
```

The model adapter can be switched through the app model card or the backend model config endpoint.

Default validated local presets:

```txt
gemma4-e2b-mlx -> ~/Models/mlx/gemma-4-e2b-it-bf16
gemma4-e4b-mlx -> ~/Models/mlx/gemma-4-e4b-it-bf16
```

Optional larger MLX 4-bit presets are exposed only as local paths. They show as
`missing` until the model folder exists:

```bash
./scripts/download_gemma4_mlx.sh \
  mlx-community/gemma-4-26B-A4B-it-OptiQ-4bit \
  ~/Models/mlx/gemma-4-26B-A4B-it-OptiQ-4bit

./scripts/download_gemma4_mlx.sh \
  mlx-community/gemma-4-31b-4bit \
  ~/Models/mlx/gemma-4-31b-4bit
```

GGUF is also supported as an optional bridge through llama.cpp. It is not the
default demo path because it requires a separate local `llama-server` process
and a valid GGUF file:

```bash
./scripts/run_gguf_server.sh
```

Then point the backend remote route at the wrapper:

```bash
MODEL_PROVIDER=remote \
REMOTE_GEMMA_BASE_URL=http://localhost:11445 \
REMOTE_GEMMA_MODEL=gemma4-26b-gguf \
./scripts/run_funnel_backend.sh
```

For judging, the stable path is the validated MLX E2B/E4B route.

For quick local model validation:

```bash
backend/.venv-mlx/bin/python scripts/local_model_smoke.py --provider mlx --preset gemma4-e4b-mlx
```

For a small fixed benchmark:

```bash
backend/.venv-mlx/bin/python scripts/model_benchmark.py
```

## Public Demo Deployment

Recommended deployment shape:

```txt
Vercel frontend
  -> /api/backend proxy
  -> private/local FastAPI backend
  -> local or edge Gemma runtime
```

Use a server-side backend URL and API key:

```txt
BACKEND_INTERNAL_URL=https://your-backend.example
GEMMALENS_API_KEY=...
```

The browser should not receive private backend keys. See `docs/DEPLOYMENT.md` for setup notes.

Current public judging demo note: the Vercel frontend uses a private Gemma 4
runtime on the developer's Mac through a protected backend proxy. This temporary
model host is for judging only and will be shut down after judging ends.

## Testing

Backend:

```bash
cd backend
pip install -r requirements-dev.txt
ruff check app tests
pytest
```

Frontend:

```bash
cd frontend
npm run build
```

## Demo Sources

For a clean public demo, use sources with clear redistribution or public-access terms:

- public academic papers
- open course lecture videos
- local SRT/VTT subtitle files
- short excerpts where rights are clear

Do not commit downloaded copyrighted movies, private PDFs, transcripts with unclear redistribution rights, local databases, model weights, or user-specific runtime files.

## Repository Notes

This repository intentionally does not include:

- Gemma model weights
- local SQLite databases
- private PDFs or videos
- generated local runtime config
- browser-local quiz drafts
- agent workspace files

Submission planning docs may appear under `docs/` when they are public-safe.
Final video files, downloaded demo media, private transcripts, and bulk
screenshots should stay outside the repository unless the rights are clear and
the file is intentionally part of the public project presentation.

Useful docs:

- `docs/DEPLOYMENT.md`
- `docs/TECHNICAL_REPORT.md`
- `docs/VIDEO_LEARNING_STRATEGY.md`
- `docs/RECENT_PRODUCT_CHANGELOG.md`

## License

Code in this repository is released under the Apache License 2.0. See
`LICENSE`.

Gemma model weights are not included in this repository and remain under their
own license and usage terms. Demo sources, videos, papers, subtitles, local
databases, and model outputs are not redistributed here unless their rights are
clear. Kaggle writeups, videos, and final submission artifacts may also be
subject to the competition-specific publication and licensing rules.
