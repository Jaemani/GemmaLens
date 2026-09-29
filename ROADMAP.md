# Roadmap

## Post-Judging Priority

- Continue migration preparation without deploying an always-on model service.
  The personal judging backend and automatic supervisor are shut down.
- [Linux development preparation (#2)](https://github.com/Jaemani/GemmaLens/issues/2):
  source changes reconciled, lint/browser/dependency checks passed, and a fresh
  GitHub clone rehearsed without a personal model server. Review PR #3 before
  merging; operational data cutover is not part of this preparation.
- [Accept API configuration when selecting a model (#1)](https://github.com/Jaemani/GemmaLens/issues/1):
  collect endpoint/provider, API key when needed, and model identifier; validate
  the connection and handle failures without silently starting local inference.
  Define credential lifetime and user/session isolation before implementation.
  This is follow-up work, not an already available feature.

## Near Term

- Implement staged full-document analysis: page/section analysis, stored section results, merged paper map, and whole-paper summary.
- Improve backend translation with streaming progress, dictionary extraction, and optional per-language style controls.
- Add backend quiz generation endpoint with distractors and level-aware question types.
- Improve PDF extraction quality and section detection.
- Add repeated-structure tracking.
- Add import history cleanup controls across documents, videos, and cached quizzes.
- Add richer Korean explanations.
- Add richer multilingual explanation quality checks.

## Model Expansion

- Complete Ollama adapter configuration UI.
- Harden Gemma 4 MLX structured output with schema-aware repair.
- Add streaming progress events.
- Add per-task prompts and provider selection.
- Define edge runtime matrix: desktop MLX/Ollama, Android on-device, web shell with local model download, optional remote fallback.

## Later

- Multi-document collections.
- Local embeddings for personal memory.
- Sync and account support.
- Browser extension.
- Android prototype for on-device or companion-device inference.
