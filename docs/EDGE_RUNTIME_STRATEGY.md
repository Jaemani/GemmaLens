# Edge Runtime Strategy

## Principle

GemmaLens should stay local-first and edge-friendly. Gemma 4 is intended for edge devices, so the product should not assume a permanent cloud backend or desktop-only runtime.

## Current Runtime

- Mac/PC prototype with FastAPI backend.
- MLX Gemma 4 bf16 models on Apple Silicon.
- Ollama-compatible scaffold for local HTTP runtimes.
- Mock adapter for demos and development.
- Remote Gemma/llama.cpp route for ThinkPad-class LAN/Tailscale testing.

## Candidate Deployment Paths

### Desktop Local

Best for the current prototype. Users run the app and model on a laptop or desktop. This gives the easiest path to PDF parsing, local SQLite, model caching, and debugging.

Mac M1 Max demo path: run the PDF workspace locally, show the first page immediately, then let section lessons prepare in the background. MLX generation is executed off the FastAPI event loop so lightweight document/file/section requests can continue while a section is being analyzed.

### Hosted Web Shell + Local Runtime

The web app can be hosted, but the model still runs locally through a small local server or browser/device runtime. This keeps privacy and avoids cloud model cost while making distribution easier.

### Android On-Device

Target direction for real edge use. The app should eventually run analysis locally on Android when a stable Gemma-compatible runtime and acceptable memory/performance profile are available.

Mobile demo story: the product is already shaped for constrained devices because paper work is split into page-section jobs. The mobile runtime does not need to hold a whole paper prompt in memory before the learner sees value.

### Remote Fallback

Useful for low-end devices, but should remain optional. The product thesis is local-first learning, not cloud-only document analysis.

ThinkPad demo path: use the E2B/Q4 remote preset to show that the same section pipeline works outside the Mac. The UI should emphasize source-first reading and quiet background preparation, not raw benchmark speed.

## Design Constraints

- Model adapter interface must stay provider-neutral.
- Analysis schema must not depend on one runtime.
- Language settings should be prompt/schema inputs, not hard-coded UI text.
- Model assets should be selectable/downloadable by device capability.
- First model load should be explicit or visibly progressive because cold start can be slow.
- Long documents should be prepared as small section jobs. The first visible page/section must not wait for a whole-paper model call.
- Blocking model calls must not run on the web server event loop. The backend should keep health, file, document, and section-cache routes responsive while inference runs.

## Open Questions

- Which Android runtime should be the first supported target?
- Should mobile store full dictionary data locally or sync with desktop?
- Should the hosted web shell manage local model download, or should a native wrapper handle it?
- Should E2B be the default mobile model and E4B the default desktop model?
