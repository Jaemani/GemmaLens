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

### Future Gemma Adapter

Reserved for a local Gemma runtime or compatible HTTP server. It should reuse the same structured output contract.
