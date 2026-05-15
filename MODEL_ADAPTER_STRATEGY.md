# Model Adapter Strategy

## Goals

- Keep model providers swappable.
- Require structured JSON output.
- Retry invalid JSON.
- Use mock output only in explicit demo/deploy mode.
- Keep prompts outside route handlers.

## Interface

All adapters implement `ModelAdapter.analyze_document(text, chunks)` and return an `AnalysisResult`.

## Adapters

### MockModelAdapter

Demo/deployment adapter. Produces deterministic output from bundled sample content for UI testing without a local model. It should not be used for real local analysis.

### OllamaAdapter

HTTP scaffold for local Ollama-compatible models. It builds a structured prompt, asks for JSON, validates with Pydantic, retries invalid JSON, and falls back to mock output.

### MLXAdapter

Apple Silicon local runtime scaffold for MLX-converted Gemma 4 text models. It loads `MLX_MODEL_PATH`, asks for strict JSON, validates with Pydantic, and returns explicit errors when the model fails. Current local presets use bf16 Gemma 4 E2B and E4B models.

### Runtime Policy

- Local development: use MLX or Ollama.
- Demo deployment: use mock only with `APP_DEMO_MODE=true`.
- Real model failure must not silently return mock learning content.

### Edge Runtime Direction

Gemma 4 is intended for edge devices, so the adapter layer must avoid desktop-only assumptions. PC/Mac local runtime is the prototype path, but the architecture should support:

- local desktop inference through MLX or Ollama;
- Android on-device inference through a mobile runtime when practical;
- web-hosted app shell with downloadable local model assets;
- cloud fallback only as an optional convenience, not the core product thesis.

The product should treat model runtime as a capability selected by device, not a fixed deployment target.

### Future Gemma Adapter

Gemma support can run through MLX, Ollama, a mobile runtime, or another compatible local server. Every runtime must reuse the same structured output contract.
