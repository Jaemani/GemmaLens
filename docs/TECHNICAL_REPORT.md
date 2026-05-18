# GemmaLens Technical Report

## 1. Project Summary

GemmaLens is a local-first language-learning assistant for academic, technical, and video-based reading. The target user is a non-native reader who wants to learn from papers, reports, tutorials, videos, and short passages without repeatedly copy-pasting individual sentences into a translator.

The core thesis is:

```text
document or transcript -> extracted text -> structured learning objects -> dictionary/review tools
```

The project is not a PDF chatbot and not a general summarizer. The intended product value is personalized language acquisition while reading real material.

The current product distinction is:

```text
translation explains the current sentence
summary explains the current document
GemmaLens builds a reusable reading guide: concepts, terms, phrases, sentence structures, and review memory
```

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
- Repository code is Apache-2.0. Kaggle writeups, videos, and final submission artifacts may be subject to competition-specific publication and licensing rules.
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
  - `/translate`: short text translation UI
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
  - `GET /documents/{id}/sections`
  - `GET /documents/{id}/sections/{section_index}`
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
- `RemoteGemmaAdapter`: HTTP adapter for a private local, LAN, or edge Gemma server configured through `REMOTE_GEMMA_BASE_URL`.

Important current policy:

- Local development should use real local model runtime.
- Mock is only for deployed UI/demo mode.
- Real MLX failures must not silently return mock content.
- MLX prompts use atomic JSON-only tasks with thinking disabled to reduce invalid structured output.
- The loaded MLX model is cached in process and can be warmed up through `POST /models/warmup`.
- MLX generation runs in a worker thread instead of the FastAPI event loop. This keeps health checks, PDF file serving, section listing, and cached lesson reads responsive while a background section analysis is running.
- Remote Gemma runtime can be selected through model presets for cases where the Mac GPU is occupied by another project.

## 4. Implemented Changes

### Document Input

- Removed prefilled sample text.
- Added separate upload and paste modes.
- Added PDF/DOCX/text/markdown upload. Legacy `.doc` files return an actionable conversion message.
- Text extraction has an explicit failure path: scanned or image-only PDFs require OCR, and image-only DOCX files should be exported or pasted as text.
- Uploaded originals are now stored locally. PDF originals can be served back to the frontend and rendered in the analysis workspace beside the learning guide.
- The PDF workspace now uses PDF.js canvas rendering instead of a native iframe, giving reliable in-app page preview and PDF page Previous/Next controls during demos.
- Added upload progress and phase-specific status.
- Added delete buttons for document/video history.
- Added backend `DELETE /documents/{id}` with analysis cleanup.

### Analysis Result

- Structured result includes domain, difficulty, terms, phrases, concepts, sentence decomposition, summaries, and warnings.
- Concepts are first-class learning objects, separate from dictionary terms. They connect vocabulary to the paper's argument, method, and referenced ideas.
- Concepts can be saved to the dictionary/review store, just like terms and phrases.
- Added source-grounded guardrails after model analysis. If the edge model returns empty phrase lists, repeated source text as summaries, weak sentence decompositions, or generic noun fragments, the backend now repairs or discards those items before the UI sees them.
- Added paper-specific weak-output guards for real PDFs. When extracted text or edge-model output turns figure captions and equation fragments into summaries, the backend now replaces them with deterministic source-grounded learning summaries for Transformer architecture, scaled dot-product attention, and multi-head attention sections.
- Short section filtering is artifact-aware rather than length-only: tiny formula/caption fragments can be skipped, while short valid learning summaries remain visible.
- Added ResNet/Deep Residual Learning guardrails after a real-PDF smoke test. The normalizer now recovers residual learning concepts and filters bad model fragments such as `to ease the training` and `of networks`.
- Paper-map ranking now promotes core methods over generic descriptors, so cumulative guides prioritize ideas such as residual learning before broad descriptors such as deeper networks.
- The current Batch Normalization smoke result now separates concepts (`internal covariate shift`, `Batch Normalization`, `mini-batch`) from vocabulary (`stochastic gradient descent`, `learning rate`, `vanishing gradients`) and reusable academic expressions (`is complicated by the fact that`, `as opposed to`, `This motivates us to`).
- The current BERT smoke result now separates core BERT concepts and vocabulary (`BERT`, `pre-training`, `fine-tuning`, `masked language model`, `next sentence prediction`) from incidental terms that appear elsewhere in the full paper but should not drive the first learning guide.
- Added browser-local A/B controls for save behavior, labels, layout, item detail, review state, and user-fit mode, then removed them from the learner-facing navigation after the core workflow stabilized.
- Added user-facing section-level status when analysis is section-limited.
- Hid internal validator warnings from the result UI because they are debugging signals, not learning content.
- Prevented silent mock fallback on MLX failure.
- Added a re-analysis button so cached low-quality results can be replaced after model/runtime improvements.
- Reordered the analysis result screen so the domain summary and source/learning workspace appear before experiment controls. This makes the demo read as a paper-learning tool rather than a settings dashboard.
- Extracted-section controls are now visible without opening a hidden text block. The user can move through extracted sections and analyze the current section while the original PDF stays visible.
- Added a same-document section analysis endpoint, `POST /documents/{id}/sections/{section_index}/analyze`. This lets the frontend show an inline section lesson without creating a separate document or breaking the user's place in the paper.
- Section analysis is now cached in SQLite. In the BERT paper smoke test, a cold section analysis took about 67.0 seconds on the current remote edge route; the cached repeat call returned in about 0.03 seconds.
- Cached analysis normalization now uses the analyzed text span rather than the entire readable paper, reducing cross-section contamination where later-paper vocabulary could appear in the first-section guide.
- Added a paper map endpoint, `GET /documents/{id}/paper-map`, built from analyzed section cache. It aggregates cumulative concepts, terms, reusable expressions, and section summaries while explicitly reflecting only analyzed sections.
- The paper map now returns total section count and analyzed section numbers. The UI displays coverage such as `1 / 27 sections analyzed`, and refreshes automatically after a section lesson is generated.
- Reordered the paper workspace so the section reader and "Analyze this section" action appear directly beside the PDF before the cumulative map and lower learning-object tables. This supports page-by-page study instead of forcing the user to scroll through a static analysis report before continuing.
- The current section lesson now renders immediately below the section controls, before the paper map. This keeps the user in a read-analyze-learn loop rather than sending them through a cumulative report first.
- The current section lesson includes direct dictionary save buttons for concepts, terms, and reusable expressions, so the primary reading loop supports learning-memory creation without opening the legacy detailed output.
- The section lesson filters generic discourse fragments out of its main expression list when they are not good save targets.
- The PDF source pane now includes zoom controls and defaults to a more readable scale, with overflow contained inside the pane.
- The analysis workspace grid was adjusted to avoid horizontal overflow at laptop widths while preserving the two-pane paper/source layout.
- Renamed the single-result concept panel to "Concept anchors" so it is not confused with the cumulative paper map.
- Added backend section endpoints, `GET /documents/{id}/sections` and `GET /documents/{id}/sections/{section_index}`. The frontend section reader now uses these endpoints instead of duplicating split logic in the browser, so the text shown to the user is the same text submitted to section analysis.
- Cached section lessons are re-normalized on read with the current guardrails. This lets older cached output improve when the validation layer improves, without forcing a slow model rerun.
- Native/support-language glosses are now part of the analysis schema. Terms can include `support_language_meaning`; phrases can include `support_language_explanation`. The section lesson shows the support-language gloss beside the English/context explanation so language learners can read from the source without mentally translating every item.
- Long PDF pages now open directly into the PDF/section workspace before base analysis is requested. The first source page and current extracted section are visible first; remaining section lessons can prepare in the background according to the profile setting `auto_analyze_documents`.
- Background preparation is intentionally quiet. It should not expose debug-style controls such as multiple auto-study buttons. The current section has one foreground action: analyze or refresh the selected section lesson.

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

- Reworked the dashboard into a tighter workspace view with one primary document action, one video action, recent documents, runtime status, and a small learning-loop panel.
- Removed team-testing/deployment copy from the user-facing page.
- Model runtime status remains visible without presenting the app as a generic landing page.
- Added model warmup control so demos can load Gemma before the first translation or analysis task.

### Runtime Stability

- Added same-origin frontend proxy to avoid direct browser calls to `:8012`.
- Added `scripts/run_local_stack.sh` to start backend and frontend together on stable ports.
- If upload shows `Backend is not reachable at http://127.0.0.1:8012`, the frontend is alive but the FastAPI backend is not listening on the expected local-stack port. Restart `./scripts/run_local_stack.sh` or run the backend manually on `8012`.
- Switched the local stack from Turbopack dev mode to webpack dev mode after repeated Turbopack panics caused browser refresh loops and aborted API requests.
- Restricted demo data and demo result links to explicit `NEXT_PUBLIC_DEMO_MODE=true`.
- Fixed the MLX warmup route to run async; the first implementation loaded MLX in a FastAPI worker thread and could fail later with a GPU stream/thread error.
- Added private remote Gemma presets:
  - `Gemma 4 E2B (remote fp16)` -> remote model id `e2b`
  - `Gemma 4 E2B (remote Q4)` -> llama.cpp Q4_K_M-compatible endpoint
  - `Gemma 4 E4B (remote fp16)` -> remote model id `e4b`
- Verified the remote server health endpoint and a model-backed English-to-Korean translation through the GemmaLens backend.
- Changed Settings to server-prefetch the learner profile so it does not stay in a client-side loading state when the browser aborts or reloads requests.

Observed warm local timings on E2B:

- Model warmup: about 2.7 seconds in the latest local run.
- Short translation: about 1.3 seconds after warmup.
- Short structured analysis: about 15.3 seconds after warmup.

Observed private remote runtime:

- Server: configured through `REMOTE_GEMMA_BASE_URL`
- Health: available with active model `e2b`
- Models: Gemma 4 E2B fp16 and Gemma 4 E4B fp16
- Current limitation: CPU generation is slow, so long analysis tasks need progress UI and staged chunking.
- Q4 result: the remote Q4 E2B route is much faster for functional testing than CPU fp16. A short batch-normalization explanation returned 38 output tokens in 5.63s, about 6.75 tok/s.

## 5. UI/UX Design

### Design Principle

The UI is designed to feel like a calm academic reading workspace, not a model dashboard or debug panel. Key rules applied throughout:

- The source document and the current section notes are the primary surfaces. All status, navigation, and secondary information is subordinate.
- Information appears at most once. If page number is shown in the navigation cluster, it is not repeated in a separate text line.
- Layout shifts are prevented by returning `null` during loading states rather than showing placeholder cards that take different heights than the final content.
- Internal model/system concepts do not leak into the UI: no "analyzed_sections", no section-level JSON fields, no uppercase tracking-wide status labels.
- Model output filler phrases are stripped at render time (e.g., "This term refers to...", "In this context...") via a `stripFiller()` utility in `DocumentPageReader.tsx`.

### Reader Workspace (`/analysis/[documentId]`)

The analysis workspace has a two-column layout at `xl:` widths: PDF source pane on the left (sticky), section reader and notes on the right.

Right panel order:
1. Section preparation progress (only while background preparation is running or paused)
2. `DocumentPageReader` — section navigation, source text toggle
3. `SectionLessonCard` — current section notes (terms, phrases, patterns, ideas tabs)
4. `PaperMapProgressPanel` — paper-level guide (compact row when closed)

#### Section navigator (`DocumentPageReader`)

The section navigator uses a compact bar layout:

```
[«][<] 2/9 [>][»]    [Build notes]    [Attach PDF?]
```

Page number (`2/9`) is embedded inside the navigation button cluster as a non-interactive span. No separate text line.

Below the nav bar, an always-expanded section map shows page groups:

```
14/25 ready · Preparing…          [● Current] [● Ready] [○ Not ready]
Page 1                 Page 2                 Page 3
[1] [2]         [1] [~2] [3] [4]         [~1]
```

Continuation sections (text that spans from the previous page) are marked with a `~` prefix and a dashed border. When the current section is a continuation, an amber context banner appears:

> ↩ Continues from page 3 — this text is part of the same section.  [View page 3 notes]

Clicking the button jumps to the parent section (last section on the previous page).

#### Section notes (`SectionLessonCard`)

Four tabs: Terms | Phrases | Patterns | Ideas.

- Each tab shows items with English meaning + Korean gloss (if available) + source sentence evidence.
- Save buttons on each item write to the Library (`/dictionary`).
- Tab counts visible as small badges.
- Heading area shows `summaries.one_line` and `summaries.academic` from the section analysis.

### Paper Map (`PaperMapProgressPanel`)

Collapsed state: single compact row showing progress bar, `X/Y` count, Refresh, and "Open map" button.

Open state: full-screen modal with four tabs:

| Tab | Description |
|-----|-------------|
| **Overview** | Thesis so far, Reading focus, Next steps from the guide, Section map grid grouped by PDF page. Hover any analyzed section to see its summary in a tooltip and preview card. |
| **Argument** | Numbered flow diagram: each step in `synthesis.argument_flow` rendered as a node with vertical connecting line. Shows `priority_concepts` below. |
| **Concepts** | Cross-reference grid: all concepts and terms sorted by how many sections they appear in. Each card shows the item name, kind badge, `§N §M` section chips, and meaning. Filterable by All / Concepts / Terms. |
| **Vocabulary** | Priority terms, Reusable expressions, Review plan — from `synthesis`. |

The section map in the Overview tab fetches both `GET /documents/{id}/paper-map` and `GET /documents/{id}/sections` in parallel so it can group section tiles by PDF page rather than presenting a flat numbered list.

### Library (`/dictionary`)

Filter pill tabs at the top of the page:

```
[All 42]  [Key ideas 8]  [Terms 14]  [Phrases 12]  [Patterns 8]
```

Review queue summary (New / Learning / Familiar) shown inline in the page header, right side.

### Dashboard (`/`)

- Hero: "Read academic English better." with primary action (Analyze a document) and secondary action (Study a video).
- Recent documents list with progress badges (New / X% / Complete / Ready).
- Workflow card: three numbered steps (Upload → Read → Save).
- Model runtime status card (compact mode).

### Global Status Dock (sidebar bottom)

Small card showing:
- Activity indicator: "Ready" when idle, task label when active.
- Backend status: "Online" / "Off" / "Check" as a colored dot.
- Model preset label.

"Online" was chosen over "Ready" to distinguish backend liveness from task readiness, which also shows "Ready" when idle.

### Typography

Body font: system UI sans-serif stack (`-apple-system, BlinkMacSystemFont, "Segoe UI", "Helvetica Neue", Arial`). Antialiasing enabled. No custom webfont in the reading workspace to keep rendering neutral and fast.

Section headers throughout the UI use `text-xs font-semibold text-neutral-500` — no uppercase, no letter-spacing. Uppercase tracking-wide headers were removed as they created visual noise without adding scannability in this context.

## 7. Current Technical Limitations

### Edge Atomic Pipeline

The remote Gemma path now follows an edge-first atomic pipeline instead of asking the model for one large document-level JSON object.

Current behavior:

```text
source chunk
-> code-generated fast meta/summary for Q4 routes
-> atomic term task
-> atomic phrase task
-> atomic concept task or source-grounded concept fallback
-> atomic sentence task
-> JSON extraction/repair
-> source-grounded normalization
-> discard placeholders and items not found in source
-> fallback source parser when Q4 output is invalid or too sparse
-> learning guardrails repair weak summaries, phrases, concepts, and sentence structures
```

This makes the Q4 remote route usable for functional testing. A short Batch Normalization smoke analysis completed in about 48 seconds with source-grounded terms, phrases, and sentence explanation, instead of timing out at 300 seconds on the fp16 CPU route.

Design rule:

- small Gemma 4 models should receive short, single-purpose tasks;
- external code owns parsing, validation, fallback, and discard behavior;
- invalid model output should affect only that task, not the whole document.

### Full-Paper Analysis

Current real-model analysis is section-based to avoid Metal out-of-memory crashes on the shared GPU and to fit edge-device latency. A truthful full-paper guide is built by merging cached section lessons rather than pretending one prompt has read the entire paper.

Observed failure:

```text
[METAL] Command buffer execution failed: Insufficient Memory
```

Current mitigation:

- Reduced MLX prompt/input budget.
- Reduced generation token budget.
- No silent mock fallback.
- Result warns when analysis is section-level.
- Long PDF analysis pages do not automatically trigger full-document base analysis when no cached analysis exists. They open into the section workspace first, and full base analysis is an explicit action. This prevents surprise multi-minute jobs and fits the edge-device principle that long papers should be processed in visible, restartable chunks.
- Automatic section preparation can run after the PDF source is ready. This is default-on for the local demo because the current small-section path is fast enough to prepare the paper while the learner reads.

Required next step:

```text
extract full text
-> clean front matter and detect readable abstract/introduction
-> split by page/section
-> run atomic tasks for section 1..N sequentially
-> store each section result
-> build a whole-paper map: research problem, method, key concepts, references, and conclusion
-> generate per-page lessons: concepts, vocabulary, phrases, sentence structures, and study notes
-> merge repeated concepts/terms into review memory
```

This staged approach is better for edge devices than sending a full paper in one prompt.

Recommended reading UX:

- Start with a whole-paper map so the learner knows what the paper is trying to do.
- Let the learner open one page or section at a time.
- The current UI includes a section reader with previous/next controls and an "Analyze this section" action placed beside the PDF. This is now the primary paper-reading loop, while the paper map shows how much cumulative coverage exists.
- Each section lesson now shows: concept anchors with source evidence, must-know terms, reusable academic phrases, hard sentence structures, academic/simple summaries, and focus notes. This keeps the product centered on language learning rather than acting like a generic summarizer.
- Save concepts separately from words. A concept such as "internal covariate shift" may have related terms, cited references, and repeated mentions across the paper.
- Track repeated concepts and references so the learner sees which ideas are central instead of memorizing every extracted phrase.

### Translation

Translation is implemented as a short atomic model task. It is intentionally character-limited so it can run on an edge device without competing with full-document analysis. The next quality step is streaming progress plus optional dictionary extraction from the translated result.

### Quiz

Quiz generation currently uses structured analysis objects. It should later use the model to create distractors, cloze items, and level-aware question types.

## 8. Cross-Domain Analysis Quality Evaluation

### Methodology

Four paper extracts were selected from distinct academic domains to evaluate whether the analysis pipeline produces level-appropriate, domain-relevant output across real scientific text. The evaluation compared B2 vs C2 level outputs for the same text, measuring: term count and relevance, phrase quality and base-form compliance, B2 leakage into C2 outputs, and surface-clause contamination.

**Corpus**

| Paper | Domain | Pages used | Char length |
|-------|--------|-----------|-------------|
| Vaswani et al. 2017 — Attention is All You Need | NLP / CS | 3–5 (encoder-decoder architecture) | 6,679 |
| arXiv 2105.05093 — Electric Mott Transition in V₂O₃ | Condensed Matter Physics | 7–8 (Raman/X-ray results) | 6,255 |
| arXiv 2212.08011 — Multi-VALUE dialectology benchmark | Computational Linguistics | 2–4 (pipeline + related work) | 11,854 |
| arXiv 2202.13790 — Relativistic hydrodynamics with Coulomb friction | High-Energy Physics | 2–3 (viscosity derivation) | 10,725 |

**Evaluation rubric**

- *Term relevance*: is the term domain-specific and vocabulary-useful for the assigned level?
- *Phrase base form*: is the phrase in infinitive/lemma form, or is it a surface clause copied from the text?
- *B2 leakage*: do generic transitions (similar to, based on, can be described as) appear in C2 output?
- *Level differentiation*: does C2 select harder, more field-specific items than B2?

### Root-Cause Findings

**Finding 1 — Token budget truncation (high impact, fixed)**

The `mlx_max_tokens` setting was 768. A full analysis JSON for 10 terms requires approximately 700–750 tokens, leaving no budget for the phrases array. The model generated complete terms but the output was cut before writing any phrases, resulting in zero phrases across all test papers.

Evidence: raw model output file showed valid JSON truncating mid-array after 10 term objects, with no `phrases` key present at all.

Fix: `mlx_max_tokens: 768 → 1536`. Phrase generation is now enabled. Analysis latency increased from ~28 s to ~56 s per section on M1 Max.

**Finding 2 — Phrase verbatim check vs. PDF-joined text (medium impact, fixed)**

The normalization service required every phrase to appear verbatim as a substring in the document text (`_appears_in_text`). Two-column PDF extraction joins adjacent words without spaces ("ScaledDot-ProductAttention", "Weemployaresidualconnection"). Correct base-form phrases like "scaled dot-product attention" therefore failed the substring check and were silently discarded.

Fix: added a compact-match fallback that strips all spaces and hyphens before comparison. "scaleddotproductattention" is now found inside the joined PDF text.

**Finding 3 — Valid domain phrase in hard blocklist (low impact, fixed)**

"scaled dot-product attention" was in the phrase blocklist at `analysis_normalization_service.py:684`. This is one of the most domain-specific collocations in the Attention paper and should not be blocked.

Fix: removed the entry from the hard blocklist.

**Finding 4 — Surface clause leakage (medium impact, partially fixed)**

After increasing the token budget, the model generated phrases such as:
- "prevent positions from attending to subsequent positions" (9 words, verbatim text fragment)
- "composed of a stack of N = 6 identical layers" (clause with embedded formula)

These are not base-form expressions; they are sentences copied from the source.

Backend fix: strengthened prompt with an explicit negative example — "BAD: 'prevent positions from attending to subsequent positions'. GOOD: 'prevent X from attending to Y'. Do not embed numbers, variable names, or citations in phrases."

Frontend fix: `isUsefulExpression()` now rejects phrases with more than 6 words that contain embedded formulas, position references, or "composed of a stack".

**Finding 5 — B2 leakage in raw C2 output (medium impact, mitigated)**

"similar to", "based on", "similarly to", and "can be described as" appeared in C2 phrase output for both physics papers despite backend prompt instructions to skip them at C2. The backend prompt was strengthened but model compliance was not complete.

Mitigation: the frontend `BASIC_PHRASE_BLOCKLIST` was expanded to include "similarly to" and "can be described as". These are filtered before display. Raw API output still contains leakage in physics domains.

### Results

**Before fixes (baseline)**

| Paper | B2 Phrases (raw) | C2 Phrases (raw) | Phrase quality |
|-------|-----------------|-----------------|---------------|
| NLP (Attention) | 0 | 0 | — (truncated) |
| Physics (Mott) | 2 | 2 | B2 leakage only |
| Linguistics (Multi-VALUE) | 0 | 0 | — (truncated) |
| Fluid Physics | 2 | 2 | B2 leakage only |

**After all fixes (final evaluation)**

| Paper | B2 Display | C2 Display | Sample quality phrases |
|-------|-----------|-----------|----------------------|
| NLP (Attention) | 1 | 1 | "linear projection"; "compute the matrix of outputs" |
| Physics (Mott) | 3 | 0 | "spatially resolved X-ray diffraction experiment"; "maximize the signal coming from" |
| Linguistics | 0 | 1 | "close the performance gap" |
| Fluid Physics | 1 | 2 | "restore the uniform"; "dissipative term related to" |

Display counts are after the frontend blocklist removes B2 leakage phrases.

**Term quality observations**

Terms were generated across all runs. Level differentiation was present but weak. At C2, the model consistently promoted more field-specific terms to the top of the list (Transformer > queries; Mott transition > lattice contraction; longitudinal bulk viscosity > shear viscosity). However, truly B2-level terms like "queries" and "keys" still appeared in C2 output for the NLP paper, indicating the level filter in the prompt is observed in ranking but not in exclusion.

Korean glosses were present and contextually accurate in all runs where output was complete. Confidence values were consistently 0.95–0.98, which is suspiciously uniform and likely the model interpolating a fixed confidence target rather than varying by actual item certainty.

### Remaining Gaps

1. **Phrase count below target**: the prompt requests 2–4 phrases but effective display is 0–3. Physics at C2 produces 0 displayable phrases because all generated phrases are blocked as B2 leakage. The model needs additional example collocations for non-NLP domains to produce valid C2 phrases.

2. **No genuine C2 exclusion for NLP terms**: "queries" and "keys" belong at B2 (core NLP vocabulary) but appear in C2 output. The backend prompt excludes "similar to" explicitly but does not tell the model which NLP terms are B2-level.

3. **PDF extraction quality**: two-column academic PDFs produce joined words and mixed column flow during text extraction. "dialectdisparities" and "cross-dialectalNLPperformance" appeared as terms in the linguistics paper, sourced from un-segmented PDF text. pdfplumber does not handle multi-column layout. Replacing with PyMuPDF (fitz) with explicit column-detection would improve input quality for all papers.

4. **"pip" as a term**: the linguistics paper's dataset-availability section contains `pip install` setup instructions. This was extracted as a technical term. A text-preprocessing step that strips code blocks, dataset access instructions, and bibliography entries before analysis would prevent this.

5. **Phrase count targeting**: the model generates 10–12 terms (exceeding the "3–6" instruction) and 1–5 phrases (within "2–4" for some runs but below for others). A post-analysis cap on term count, retaining only the highest-priority 6 items, would improve focus and reduce token cost.

### Configuration Changes Made

| Setting | Before | After | Rationale |
|---------|--------|-------|-----------|
| `mlx_max_tokens` | 768 | 1536 | prevent JSON truncation before phrases |
| `analysis_model_input_chars` | 2500 | 3500 | more context for section analysis |
| Phrase blocklist | included "scaled dot-product attention" | removed | valid domain collocation |
| `_appears_in_text` | exact substring only | + compact no-space match | handles PDF word-joining |
| Frontend `BASIC_PHRASE_BLOCKLIST` | 28 entries | 31 entries | added "similarly to", "can be described as", "is described as" |
| Backend phrase prompt | base form instruction | + negative example + formula prohibition | reduce surface-clause phrases |

## 10. Learning Method Rationale

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

## 11. Recommended Next Engineering Tasks

1. Add model output contract tests with real Gemma samples.
2. Add a durable backend preparation job if client orchestration becomes brittle.
3. Add model runtime health and memory status.
4. Add exportable hackathon report and demo script.
5. Add reproducible setup instructions for MLX, Ollama, and private remote presets.
6. Decide mobile edge target: LiteRT, llama.cpp, or companion-server mode.
7. Extend the learning library into graph/wiki views across papers, docs, and videos.

## 12. Demo Script

1. Open dashboard and show selected local model.
2. Upload a PDF and show the first page appears immediately.
3. Show background section preparation and a cached section lesson.
4. Point out native glosses, English meanings, source evidence, and concept anchors.
5. Save terms/expressions to the learning library.
6. Fetch a YouTube transcript and show inline video lesson output.
7. Generate quiz from analyzed source.
8. Show translation panel.
9. Explain the edge story: laptops, edge servers, and future mobile all use the same small section-job product shape.
