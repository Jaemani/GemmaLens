# Model Adapter Strategy

## Goals

- Keep model providers swappable.
- Require structured JSON output.
- Retry invalid JSON.
- Fall back to mock output.
- Keep prompts outside route handlers.

## Interface

All adapters implement `ModelAdapter.analyze_document(text, chunks)` and return an `AnalysisResult`.

## Adapters

### MockModelAdapter

Default adapter. Produces deterministic output from bundled sample content and general fallback text. It lets the app run with no external dependencies.

### OllamaAdapter

HTTP scaffold for local Ollama-compatible models. It builds a structured prompt, asks for JSON, validates with Pydantic, retries invalid JSON, and falls back to mock output.

### MLXAdapter

Apple Silicon local runtime scaffold for MLX-converted Gemma 4 text models. It loads `MLX_MODEL_PATH`, asks for strict JSON, validates with Pydantic, and falls back to mock output if the model or `mlx-lm` runtime is unavailable. The default target is `mlx-community/gemma-4-e4b-it-OptiQ-4bit` because it is text-compatible with standard `mlx-lm`.

### Future Gemma Adapter

Gemma support can run through MLX, Ollama, or another compatible HTTP server. Every runtime must reuse the same structured output contract.
