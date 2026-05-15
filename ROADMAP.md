# Roadmap

## Near Term

- Implement staged full-document analysis: page/section analysis, stored section results, merged paper map, and whole-paper summary.
- Add backend model-backed translation endpoint.
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
