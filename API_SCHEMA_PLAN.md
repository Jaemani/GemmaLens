# Backend API Schema Plan

## Document

- `id`: string UUID
- `title`: string
- `source_type`: `text | markdown | pdf | unknown`
- `content`: normalized text
- `created_at`: ISO timestamp

## Analysis

Stored as structured JSON linked to one document. Shape matches `AnalysisResult` schema:

- domain
- difficulty
- terms
- phrases
- sentences
- summaries

## Dictionary Item

- `id`: string UUID
- `item_type`: `term | phrase | sentence`
- `text`: saved learning item
- `meaning`: optional explanation
- `source_sentence`: optional source sentence
- `document_id`: optional source document
- `notes`: optional user notes
- `encounter_count`: integer
- `created_at`: ISO timestamp
