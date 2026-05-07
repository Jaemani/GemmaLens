# Product Design

## Thesis

Every academic or technical document can become a personalized language lesson. PaperLens builds reading ability by extracting vocabulary, phrase patterns, sentence structures, and summaries from difficult source text.

## User

Initial user is a non-native English-speaking undergraduate or graduate student reading papers, reports, documentation, and research material.

## Core Flow

1. User pastes or uploads document text.
2. Backend extracts normalized plain text.
3. Text is chunked for analysis.
4. Pipeline detects domain and difficulty.
5. Pipeline extracts terms, academic phrases, difficult sentences, and layered summaries.
6. User saves useful items into dictionary.
7. Dictionary tracks repeated terms and structures.

## Product Boundaries

PaperLens is not a PDF chatbot, generic translator, or summarizer. The UI centers on document-to-learning-object analysis, not chat.

## UI Principles

- Four screens only: Dashboard, Document Input, Analysis Result, Dictionary.
- Serious academic tool tone.
- Material Design 3-inspired surfaces, spacing, typography, and contrast.
- Progressive disclosure over dense raw output.
- Cards only for meaningful grouped information.

## Success Criteria

- Runs locally without model setup.
- Analysis result uses stable structured schema.
- Model adapter can be swapped.
- Dictionary saving works.
- Architecture supports future quiz/review and local model expansion.
