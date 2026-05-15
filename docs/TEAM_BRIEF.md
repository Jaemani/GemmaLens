# GemmaLens Team Brief

## One-Sentence Summary

GemmaLens turns academic or technical documents into personalized language-learning objects: terms, phrases, sentence structures, summaries, and saved review items.

## Current Prototype

- Frontend: Next.js, TypeScript, Tailwind, Google-like Material-inspired UI.
- Backend: FastAPI, SQLite, SQLAlchemy, Pydantic.
- Model runtime: Mock, Ollama scaffold, MLX Gemma 4 presets, and ThinkPad remote Gemma 4 presets over Tailscale.
- Local models installed: Gemma 4 E2B bf16 and Gemma 4 E4B bf16 under `~/Models/mlx`.
- Input: pasted text, text/markdown upload, basic PDF text extraction.
- Output: domain, difficulty, concepts, terms, phrases, sentence decomposition, layered summaries.
- Dictionary: save/list/delete concepts, terms, phrases, and sentences.

## Current Learning Signals

- `overall_level`: B1, B2, C1, C2, domain-heavy, unknown.
- `lexical_difficulty`: vocabulary and expression load, 0-10.
- `syntax_difficulty`: sentence structure load, 0-10.
- `domain_difficulty`: background knowledge load, 0-10.

These are learning-priority estimates, not official CEFR certification.

## Language Direction

Current default is English academic reading with Korean support in sentence explanations. The product direction is selectable:

- Support/user language: English, Korean, Spanish, French, Japanese.
- Learning/target language: English, Korean, Spanish, French, Japanese.

The model layer should drive multilingual behavior through prompts and schemas. The app should not hard-code one language pair into data models.

The prototype now includes local profile settings for support language, learning language, target level, and onboarding completion.

## Learning Memory Direction

- Concepts are now separate from words. A concept is an idea the reader must understand to follow the paper, such as a method, hypothesis, phenomenon, or theoretical claim.
- Terms are vocabulary items. Phrases are reusable academic expressions. Concepts are argument anchors.
- Future concept memory should connect repeated concepts across pages, related terms, and citation markers.
- Dictionary items track how many times they were saved or encountered.
- Dictionary items now also track view count and last viewed time.
- This is the first step toward knowing what the user is learning now.
- Future memory should combine saved terms, viewed items, document domains, and repeated sentence structures.

## Demo Notes

- First MLX analysis after backend start loads model into memory and is slower.
- Repeated analysis with same selected MLX model reuses cached model.
- Switching E2B/E4B loads a different model once.
- Mock preset is best for fast UI demos.
- ThinkPad remote presets are useful when the Mac GPU is already occupied. They keep the same GemmaLens backend/API path while routing generation to `http://PRIVATE-GEMMA-SERVER:11444`.
- ThinkPad Q4 preset is preferred for fast functional testing. It uses a separate llama.cpp server on `http://PRIVATE-GEMMA-SERVER:11445`, leaving the fp16 server on `:11444` untouched.
- Vercel deployment is currently for team UI feedback only. It can open `/analysis/demo` without a backend, but real Gemma analysis still needs a reachable FastAPI backend connected to local MLX/Ollama.
- Do not expose a personal Mac LLM server directly for team testing. Use local demos now, then decide on a controlled backend/runtime path later.
- Next deployment step: deploy the backend in mock mode first. This makes the full product flow testable without model hosting, while preserving the same adapter layer for local Mac and future Android runtimes.

## Edge Device Direction

Gemma 4 is an edge-device model family, so GemmaLens should not become a desktop-only product. The current PC/Mac prototype is a practical first runtime, but future packaging should consider:

- desktop local inference for students with laptops;
- Android on-device inference when a stable mobile runtime is available;
- a hosted web app shell that can guide users through downloading compatible local model assets;
- optional remote fallback for users whose device cannot run the model.

Near-term product stance: keep the document pipeline and schemas device-agnostic, then choose runtime by device capability.

## Near Product Decisions

- Whether language settings are global user preferences or per-document settings.
- Whether dictionary items should store both original text and support-language explanation.
- How much Korean explanation remains in first public demo.
- Whether to expose model runtime settings to users or keep them in developer settings.
- Whether Android runs full analysis on-device or uses a companion/local network runtime first.

## Latest Engineering Notes

- Dashboard copy now uses `GemmaLens: Multimodal Language Learning from Any Content` as the product description.
- Local dev stack uses webpack for Next.js dev mode because Turbopack was repeatedly panicking and forcing browser refresh loops.
- Settings now loads the learner profile from the server-rendered page first, avoiding the previous endless loading state.
- Model selector is still available from the dashboard runtime card under `Change model`, but it is collapsed by default so the dashboard stays cleaner.
- Current active test runtime can be switched to `Gemma 4 E2B (ThinkPad fp16)` or `Gemma 4 E4B (ThinkPad fp16)` for remote CPU testing.
- Q4 remote analysis now uses atomic tasks. The system asks Gemma for small term/phrase/sentence jobs, then code parses, validates, discards ungrounded items, and fills sparse outputs with source-grounded fallback candidates.
- This is the intended edge-device principle: Gemma handles language judgment; deterministic code handles reliability.
- Concept extraction has been added as a first-class step. For Q4 edge testing, concepts can be generated from source-grounded terms without another slow model call; larger/faster runtimes can use a dedicated concept extraction task.
- The result page now includes a paper-map concept panel before the vocabulary table, because paper reading needs idea structure before word memorization.
- Cached old analyses can be replaced with the re-analysis button after changing model/runtime logic.
- The result page includes a page-slice reader with previous/next controls and "Analyze this page" so long papers are not trapped at the first analyzed section.
- PDF hyphenation cleanup now repairs common extraction artifacts before term/concept selection.

## Paper Reading Direction

The target experience should not be "upload a PDF and get a short summary." The useful learning structure is:

```text
whole-paper map
-> page/section guide
-> concept anchors
-> must-know terms
-> reusable academic phrases
-> hard sentence decomposition
-> save/review memory
```

For long papers, the MVP should analyze page-by-page or section-by-section. A global summary alone is too shallow for language learning; a full-paper prompt is too fragile for edge devices. Sequential page lessons plus a merged paper map fit the product and the Gemma edge-device story better.

## Active Team Discussion Docs

- `docs/AB_TEST_CANDIDATES.md`: cleanup-time A/B tests for term, expression, highlight, and dictionary UX.
- `docs/LEARNING_RESEARCH_NOTES.md`: short learning-research notes translated into product decisions.
- `docs/MODEL_BENCHMARK_RESULTS.md`: current local E2B/E4B MLX benchmark results.
- `docs/VIDEO_LEARNING_STRATEGY.md`: transcript-first video learning plan and first technical slice.
- `docs/VIDEO_PERSONA_TEST_PLAN.md`: persona-based video testing scenarios.
- Frontend `/experiments`: visible controller for all six documented A/B candidates.
