# Edge Runtime Strategy

## Principle

GemmaLens should stay local-first and edge-friendly. Gemma 4 is intended for edge devices, so the product should not assume a permanent cloud backend or desktop-only runtime.

## Current Runtime

- Mac/PC prototype with FastAPI backend.
- MLX Gemma 4 bf16 models on Apple Silicon.
- Ollama-compatible scaffold for local HTTP runtimes.
- Mock adapter for demos and development.

## Candidate Deployment Paths

### Desktop Local

Best for the current prototype. Users run the app and model on a laptop or desktop. This gives the easiest path to PDF parsing, local SQLite, model caching, and debugging.

### Hosted Web Shell + Local Runtime

The web app can be hosted, but the model still runs locally through a small local server or browser/device runtime. This keeps privacy and avoids cloud model cost while making distribution easier.

### Android On-Device

Target direction for real edge use. The app should eventually run analysis locally on Android when a stable Gemma-compatible runtime and acceptable memory/performance profile are available.

### Remote Fallback

Useful for low-end devices, but should remain optional. The product thesis is local-first learning, not cloud-only document analysis.

## Design Constraints

- Model adapter interface must stay provider-neutral.
- Analysis schema must not depend on one runtime.
- Language settings should be prompt/schema inputs, not hard-coded UI text.
- Model assets should be selectable/downloadable by device capability.
- First model load should be explicit or visibly progressive because cold start can be slow.

## Open Questions

- Which Android runtime should be the first supported target?
- Should mobile store full dictionary data locally or sync with desktop?
- Should the hosted web shell manage local model download, or should a native wrapper handle it?
- Should E2B be the default mobile model and E4B the default desktop model?
