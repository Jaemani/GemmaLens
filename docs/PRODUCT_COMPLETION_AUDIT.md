# GemmaLens Product Completion Audit

Date: 2026-05-16

## Objective Restated

Evaluate GemmaLens as a real user reading famous academic PDFs end to end. The app should feel like a useful offline-first academic language-learning workspace, not a chaotic PDF chatbot, generic translator, or thin vocabulary extractor.

## Success Criteria

1. A user can upload/open full famous PDFs and read the original source beside learning output.
2. The app distinguishes PDF pages from backend-cleaned text sections.
3. The section lesson helps language learning: concepts, terms, expressions, sentence patterns, and source evidence are separated.
4. A complete paper guide emerges after all sections are analyzed.
5. Lists and dashboards do not expose extraction trash, duplicate partial uploads, or internal implementation language.
6. Translate, Video, Dictionary, Settings, and Guide feel consistent with the document-learning product, not separate unfinished demos.
7. Desktop and mobile layouts avoid console errors and horizontal overflow.
8. Current limitations are honest and visible.

## Prompt-To-Artifact Checklist

| Requirement | Evidence inspected | Current status |
| --- | --- | --- |
| Famous full PDFs tested | Live documents for Transformer, BERT, ResNet, BatchNorm; complete paper-map API audit recorded in `docs/REAL_PAPER_USABILITY_AUDIT.md` | Mostly met for four demo papers |
| Whole PDF source visible | `PdfSourcePane` renders original PDF beside section study on analysis pages | Met for PDFs with stored original file |
| Page vs section distinction | `DocumentPageReader` groups sections under PDF page headers and shows document section plus page-local section | Met |
| Useful complete paper guide | `PaperMapProgressPanel` shows whole-paper guide, collapsed argument flow, priority concepts, terms, expressions; completed paper maps now return `complete section guide` | Partly met; synthesis is deterministic and light |
| Concepts vs words separated | `SectionLessonCard` separates concept anchors, terms, reusable expressions, hard sentence pattern | Met in UI; quality still depends on profiles/normalizer |
| Extraction trash hidden | Dashboard/Documents previews and lesson snippets strip PDF markers and raw clutter; paper-map synthesis filters references-boundary summaries, bibliography venue markers, and low-value expression fragments from priority study lists | Met for inspected pages |
| Duplicate partial uploads reduced | `displayableDocuments` chooses the most complete display item per title/source type | Met for display; raw duplicate records still exist |
| Translate is not blank/opaque | Translate page empty/loading/copy states verified by Playwright | Met |
| Video has usable empty/progress state | Video page empty/fetch/parse states verified by screenshot and build | Met for empty state; full transcript interaction still lightly tested |
| Dictionary is a review queue | Dictionary shows type counts and review-focus filters; Quiz can now use saved dictionary items as a review source | Partly met; no spaced repetition scheduler yet |
| Guide matches current product | Guide rewritten around PDF source, section study, paper map, current limits | Met |
| Internal experiment tooling hidden | Sidebar nav no longer links experiments, real analysis pages hide A/B panels, and the standalone `/experiments` route has been removed from the build | Met |
| Responsive layout | Latest Playwright desktop/mobile audit on Dashboard, Documents, Translate, Video, Dictionary, Settings, Guide, Quiz, and Analysis showed no console errors, no horizontal overflow, no visible PDF markers, and no Experiments nav leakage | Met for inspected routes |
| Build/test health | `npm --prefix frontend run build`, `pytest backend/tests`, `ruff check backend` passed | Met |

## Remaining Weak Points

- The final whole-paper guide is still a structured draft, not a model-backed synthesis pass over all section summaries.
- Staged analysis is still request/response style and lacks a durable background job queue, but the UI now supports both small batches and a `Study remaining` action for moving a paper toward complete coverage.
- Duplicate document records are hidden in lists but not merged or cleaned in the database.
- PDF extraction still loses equations, columns, and some mathematical layout; the UI is honest about this but does not solve OCR/layout recovery.
- Dictionary review now shows lightweight review states (`New`, `Review soon`, `Familiar`) from encounter and view counts, and saved items can be reviewed directly from Quiz. It is still not a full spaced-repetition scheduler.
- Video transcript analysis is aligned visually, but the full video-result flow needs the same depth of famous-paper auditing.
- Quiz now builds prompts from saved dictionary items and from complete paper-map priority concepts, terms, and expressions when available, then falls back to base analysis items. It is still lightweight and not a full spaced-repetition scheduler.

## Current Verdict

GemmaLens is now usable as a paper-reading prototype for the four audited PDFs. It is not yet complete as a polished hackathon product because final synthesis, durable jobs, database cleanup, and deeper review mechanics remain incomplete.
