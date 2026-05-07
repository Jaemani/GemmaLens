# Frontend Component Plan

## Layout

- `AppShell`: page frame with sidebar and top bar.
- `Sidebar`: navigation for Dashboard, Documents, Dictionary.
- `TopBar`: app title and local-first status.

## Document

- `DocumentInputPanel`: paste text, title, submit, analyze action.
- `DocumentUploadCard`: file input for text, markdown, PDF.
- `DocumentPreview`: recent document list and content preview.

## Analysis

- `DomainOverviewCard`: domain, document type, confidence, difficulty.
- `TermTable`: extracted terms with save action.
- `SentenceDecompositionCard`: sentence structure learning cards.
- `LayeredSummaryPanel`: one-line, simple, academic, and study notes.
- `DifficultyBadge`: compact level display.

## Dictionary

- `DictionaryTable`: saved item list with delete.
- `SavedTermCard`: compact repeated-item card for future review mode.

## Common

- `EmptyState`, `LoadingState`, `ErrorState`.
