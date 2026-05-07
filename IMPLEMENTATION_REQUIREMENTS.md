# Implementation Requirements

## Required First Prototype

- Plain text input.
- Text and markdown upload.
- Basic PDF extraction through parser abstraction when `pypdf` is installed.
- FastAPI backend with SQLite persistence.
- Next.js frontend with four screens.
- Mock analysis output matching product schema.
- Dictionary create/list/delete.
- Provider-neutral model adapter.
- Ollama scaffold with fallback to mock.

## Not In First Prototype

- Auth and cloud accounts.
- Payments.
- Chat-first interface.
- Vector database.
- Multi-document RAG.
- Mobile app.
- Audio/video.
- Perfect LLM output quality.

## API Endpoints

- `GET /health`
- `POST /documents`
- `GET /documents`
- `GET /documents/{document_id}`
- `POST /documents/{document_id}/analyze`
- `GET /documents/{document_id}/analysis`
- `POST /dictionary/items`
- `GET /dictionary/items`
- `DELETE /dictionary/items/{item_id}`

## Quality Bar

Routes must delegate to services. Prompts must live outside route handlers. Raw model output must be parsed into structured Pydantic models before storage.
