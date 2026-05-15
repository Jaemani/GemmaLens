# GemmaLens Technical Report

## 1. Project Summary

GemmaLens is a local-first language-learning assistant for academic, technical, and video-based reading. The target user is a non-native reader who wants to learn from papers, reports, tutorials, videos, and short passages without repeatedly copy-pasting individual sentences into a translator.

The core thesis is:

```text
document or transcript -> extracted text -> structured learning objects -> dictionary/review tools
```

The project is not a PDF chatbot and not a general summarizer. The intended product value is personalized language acquisition while reading real material.

## 2. Competition Fit

The project aligns with the Gemma 4 Good Hackathon themes in these areas:

- Future of Education: personalized reading support, quiz generation, user-level settings, and learning-object extraction.
- Digital Equity and Inclusivity: multilingual support, local-first architecture, and support for users with limited cloud access.
- Safety and Trust: local document processing, explicit model-runtime status, and no silent mock fallback for real analysis.
- Special Technology Track potential: local Gemma runtime through MLX now, with Ollama/LiteRT/llama.cpp as planned runtime targets.

Rule-compliance notes from the Kaggle rules provided by the user:

- One Kaggle account and one team should be used.
- Team size must stay within the stated five-person maximum.
- Hackathon submission should be submitted once by the team.
- External tools and models should be publicly available, reasonably accessible, and documented.
- If submitted as a winning project, source code and reproduction instructions must be deliverable.
- Winning submission license is CC-BY 4.0 according to the pasted rules.
- No competition data is provided, so this prototype uses user-provided documents and public model/tool dependencies.

This is not legal advice; it is an engineering compliance checklist based on the pasted rules.

## 3. Architecture

### Frontend

- Next.js App Router
- TypeScript
- Tailwind CSS
- Material-inspired layout
- Same-origin `/api/backend/*` proxy for local backend access from phones and non-Chrome browsers
- Main routes:
  - `/documents`: upload or paste text
  - `/analysis/[documentId]`: structured result
  - `/video`: YouTube transcript/subtitle learning
  - `/dictionary`: saved terms and expressions
  - `/settings`: learner profile
  - `/tools`: focused translation UI
  - `/quiz`: quiz generation from analyzed docs/videos
  - `/guide`: user-level guide

### Backend

- FastAPI
- Pydantic schemas
- SQLAlchemy + SQLite
- Uvicorn
- Repository/service separation
- Main endpoints:
  - `GET /health`
  - `POST /documents`
  - `POST /documents/upload`
  - `GET /documents`
  - `GET /documents/{id}`
  - `DELETE /documents/{id}`
  - `POST /documents/{id}/analyze`
  - `GET /documents/{id}/analysis`
  - dictionary endpoints
  - profile endpoints
  - model preset endpoints
  - video transcript endpoints
  - translation endpoint

### Model Layer

The model layer is provider-neutral:

- `MockModelAdapter`: demo/deploy-only UI testing mode.
- `MLXAdapter`: Apple Silicon local Gemma runtime.
- `OllamaAdapter`: local Ollama-compatible runtime scaffold.

Important current policy:

- Local development should use real local model runtime.
- Mock is only for deployed UI/demo mode.
- Real MLX failures must not silently return mock content.
- MLX prompts use atomic JSON-only tasks with thinking disabled to reduce invalid structured output.
- The loaded MLX model is cached in process and can be warmed up through `POST /models/warmup`.

## 4. Implemented Changes

### Document Input

- Removed prefilled sample text.
- Added separate upload and paste modes.
- Added PDF/text/markdown upload.
- Added upload progress and phase-specific status.
- Added delete buttons for document/video history.
- Added backend `DELETE /documents/{id}` with analysis cleanup.

### Analysis Result

- Structured result includes domain, difficulty, terms, phrases, sentence decomposition, summaries, and warnings.
- Added A/B controls for save behavior, labels, layout, item detail, review state, and user-fit mode.
- Added user-facing section-level status when analysis is section-limited.
- Hid internal validator warnings from the result UI because they are debugging signals, not learning content.
- Prevented silent mock fallback on MLX failure.

### Video Learning

- Added YouTube transcript extraction.
- Added `yt-dlp` fallback for generated captions.
- Added synced transcript/player layout.
- Added transcript analysis and current-scene analysis.
- Fixed transcript source type support.
- Collapsed manual subtitle fallback behind a button.

### Translate

- Added independent Translate route.
- Added searchable source/target language selectors.
- Added character limit, Clear, Translate, and Copy controls.
- Added backend `POST /translate` endpoint for real MLX translation.
- Removed fake echo output; the UI now shows real model output or an explicit runtime error.

### Quiz

- Added independent Quiz route.
- Loads analyzed documents and video transcripts.
- Builds quiz drafts from terms, phrases, and sentence structures.
- Caches quiz drafts in browser localStorage.

### Language Settings

- Replaced fixed five-language buttons with searchable language selection.
- Added broad language catalog for Gemma-family multilingual coverage.
- Collapsed the language list until the user opens it, with the current selection duplicated at the top for fast confirmation.
- Backend profile schema now accepts arbitrary language strings.

### Dashboard

- Reworked the dashboard into a compact workspace view.
- Removed duplicated action buttons and team-testing/deployment copy from the user-facing page.
- Model runtime status remains visible without presenting the app as a generic landing page.
- Added model warmup control so demos can load Gemma before the first translation or analysis task.

### Runtime Stability

- Added same-origin frontend proxy to avoid direct browser calls to `:8012`.
- Added `scripts/run_local_stack.sh` to start backend and frontend together on stable ports.
- Restricted demo data and demo result links to explicit `NEXT_PUBLIC_DEMO_MODE=true`.
- Fixed the MLX warmup route to run async; the first implementation loaded MLX in a FastAPI worker thread and could fail later with a GPU stream/thread error.

Observed warm local timings on E2B:

- Model warmup: about 2.7 seconds in the latest local run.
- Short translation: about 1.3 seconds after warmup.
- Short structured analysis: about 15.3 seconds after warmup.

## 5. Current Technical Limitations

### Full-Paper Analysis

Current real-model analysis is section-limited to avoid Metal out-of-memory crashes on the shared GPU. This prevents truthful full-paper output.

Observed failure:

```text
[METAL] Command buffer execution failed: Insufficient Memory
```

Current mitigation:

- Reduced MLX prompt/input budget.
- Reduced generation token budget.
- No silent mock fallback.
- Result warns when analysis is section-level.

Required next step:

```text
extract full text
-> split by page/section
-> analyze section 1..N sequentially
-> store each section result
-> merge into whole-paper summary/map
-> generate per-section vocab/sentence drills
```

This staged approach is better for edge devices than sending a full paper in one prompt.

### Translation

Translation is implemented as a short atomic model task. It is intentionally character-limited so it can run on an edge device without competing with full-document analysis. The next quality step is streaming progress plus optional dictionary extraction from the translated result.

### Quiz

Quiz generation currently uses structured analysis objects. It should later use the model to create distractors, cloze items, and level-aware question types.

## 6. Learning Method Rationale

The current product direction should combine several well-supported learning principles:

- Meaning-focused input: users read real target material, not isolated textbook examples.
- Glossing: terms and phrases are explained in context, with support-language meaning where useful.
- Noticing/input enhancement: important phrases and structures are highlighted in source sentences.
- Retrieval practice: quiz and dictionary review should require recall, not only rereading.
- Spaced review: saved terms/phrases should be scheduled by user state such as new, viewed, familiar, mastered, ignored.
- Section-based reading: long papers should be learned in chunks, then merged into a global map.
- User-fit filtering: the app should suppress known terms and emphasize new but context-important expressions.

Useful references:

- Google AI for Developers Gemma docs: https://ai.google.dev/gemma/docs
- Gemma 3 model overview: https://ai.google.dev/gemma/docs/core
- Gemma 3 technical report: https://storage.googleapis.com/deepmind-media/gemma/Gemma3Report.pdf
- Retrieval practice systematic review: https://link.springer.com/article/10.1007/s10648-021-09595-9
- Digital reading and vocabulary learning meta-analysis: https://link.springer.com/article/10.1007/s10639-023-11969-1
- L1/L2 glosses meta-analysis: https://journals.sagepub.com/doi/full/10.1177/1362168820981394
- Visual input enhancement meta-analysis: https://www.cambridge.org/core/product/identifier/S0272263108080479/type/journal_article
- AI-based language learning tools review: https://arxiv.org/abs/2111.04455

## 7. Recommended Next Engineering Tasks

1. Implement staged full-document analysis.
2. Add section result storage schema.
3. Add backend quiz generation endpoint.
4. Add model output contract tests with real Gemma samples.
5. Add streaming progress events for long jobs.
6. Add model runtime health and memory status.
7. Add exportable hackathon report and demo script.
8. Add reproducible setup instructions for MLX and Ollama.
9. Decide mobile edge target: LiteRT, llama.cpp, or companion-server mode.

## 8. Demo Script

1. Open dashboard and show selected local model.
2. Upload a short PDF/text excerpt.
3. Show section-level language analysis.
4. Save terms to dictionary.
5. Fetch a YouTube transcript.
6. Analyze current scene or full transcript.
7. Generate quiz from analyzed source.
8. Show translation panel.
9. Explain full-paper staged analysis roadmap.
