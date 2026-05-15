# GemmaLens Team Brief

## One-Sentence Summary

GemmaLens turns academic or technical documents into personalized language-learning objects: terms, phrases, sentence structures, summaries, and saved review items.

## Current Prototype

- Frontend: Next.js, TypeScript, Tailwind, Google-like Material-inspired UI.
- Backend: FastAPI, SQLite, SQLAlchemy, Pydantic.
- Model runtime: Mock, Ollama scaffold, MLX Gemma 4 presets.
- Local models installed: Gemma 4 E2B bf16 and Gemma 4 E4B bf16 under `~/Models/mlx`.
- Input: pasted text, text/markdown upload, basic PDF text extraction.
- Output: domain, difficulty, terms, phrases, sentence decomposition, layered summaries.
- Dictionary: save/list/delete terms, phrases, and sentences.

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

- Dictionary items track how many times they were saved or encountered.
- Dictionary items now also track view count and last viewed time.
- This is the first step toward knowing what the user is learning now.
- Future memory should combine saved terms, viewed items, document domains, and repeated sentence structures.

## Demo Notes

- First MLX analysis after backend start loads model into memory and is slower.
- Repeated analysis with same selected MLX model reuses cached model.
- Switching E2B/E4B loads a different model once.
- Mock preset is best for fast UI demos.
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

## Active Team Discussion Docs

- `docs/AB_TEST_CANDIDATES.md`: cleanup-time A/B tests for term, expression, highlight, and dictionary UX.
- `docs/LEARNING_RESEARCH_NOTES.md`: short learning-research notes translated into product decisions.
- `docs/MODEL_BENCHMARK_RESULTS.md`: current local E2B/E4B MLX benchmark results.
- `docs/VIDEO_LEARNING_STRATEGY.md`: transcript-first video learning plan and first technical slice.
- `docs/VIDEO_PERSONA_TEST_PLAN.md`: persona-based video testing scenarios.
- Frontend `/experiments`: visible controller for all six documented A/B candidates.
