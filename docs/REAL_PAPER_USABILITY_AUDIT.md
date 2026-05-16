# Real Paper Usability Audit

This document tracks whether GemmaLens feels useful when used on real academic PDFs, not toy paragraphs.

## Audit Standard

GemmaLens is acceptable only if a user can answer these questions while reading:

- What part of the original paper am I looking at?
- What text was actually sent to the model?
- How much of the paper has been analyzed?
- Which items are concepts, which are vocabulary, and which are reusable academic expressions?
- Can I continue section by section without losing my place?
- Are extracted learning objects worth saving, or are they generic fragments?

Passing tests or producing JSON is not enough. The screen must support reading behavior.

## Current Real Inputs

- `Attention Is All You Need`
- `BERT: Pre-training of Deep Bidirectional Transformers for Language Understanding`
- `Batch Normalization: Accelerating Deep Network Training by Reducing Internal Covariate Shift`

Local demo records currently include:

- `batch_norm.pdf`: `126750e9-d96a-43b0-84ad-1c9d7bd6d04a`
- `bert.pdf`: `95a095cf-71fb-42ec-9b76-934c32ce86ca`
- `attention_is_all_you_need.pdf`: `e5795f9e-8ca4-438d-a083-08bac1a1caae`

## Fixed From Direct Use

- The app no longer pretends one short section is a whole-paper guide. The paper map shows coverage such as `1 / 27 sections analyzed`.
- The PDF source is rendered in-app with PDF.js canvas instead of a fragile embedded iframe.
- The main paper-reading action is now visible beside the PDF: previous/next extracted section plus `Analyze this section`.
- The section reader now gets backend-cleaned sections from `GET /documents/{id}/sections`; it no longer duplicates splitting logic in the browser.
- `Analyze this section` uses the same zero-based backend section index that the UI displays.
- Backend section responses now include `analyzed`, and the reader shows analyzed count, section status chips, and a `Next unstudied` action.
- New PDF uploads preserve internal page markers during extraction, allowing section responses to include labels such as `PDF page 2`. Older existing demo records may not have these markers.
- The PDF viewer now follows section selection when source labels are available. In the BatchNorm smoke check, selecting section 4 moved the left preview to `PDF page 2 / 11`.
- Reverse sync also works for labeled PDFs. In the BatchNorm smoke check, clicking the PDF preview `Next` button moved the reader to `Section 4 / 31`, labeled `PDF page 2`.
- Added `Auto-study next 3` as a lightweight staged-analysis loop. It uses the same section-analysis endpoint repeatedly and updates section status/paper-map state after each section.
- `Auto-study next 3` now delegates the sequence to `POST /documents/{id}/staged-analysis`, so backend state, cache keys, and section ordering stay aligned while the browser shows progress and refreshes afterward.
- Auto-study progress is persisted per document in browser localStorage. A reload can restore the last status message and keep the continuation path visible.
- A completed section lesson now includes `Analyze next unstudied`, keeping the reading loop moving after the user finishes a section.
- The cumulative paper map refreshes after section analysis.
- The cumulative paper map now starts with a reading guide: thesis so far, honest coverage note, reading focus, and next steps. This makes it behave more like a reading companion than three isolated lists.
- The paper map now includes a deterministic whole-paper learning draft assembled from analyzed section caches: argument flow, priority concepts, priority terms, reusable expressions, and review plan. This is not model-backed final synthesis yet, but it gives users a study plan instead of raw lists only.
- The whole-paper learning draft appears before raw concept/term/expression lists, so the user sees a study plan before lower-level signals.
- Raw source-grounded signal lists are collapsed by default. This reduces the long report-like page and lets the user inspect raw concepts/terms/expressions only when needed.
- Whole-paper draft priority lists show only the top three compact items by default, so the paper-level study plan remains scannable.
- The old full generated-output report is collapsed by default. The main reading workspace now prioritizes PDF/source, section study, paper map, whole-paper draft, and current section lesson.
- Paper-map coverage now includes the base first-section analysis even when later section caches exist. This fixes a real BERT smoke-test mismatch where the reader showed section 1 analyzed but the paper map only summarized section 3.
- Attention Is All You Need smoke test now produces useful first-section anchors: Transformer, self-attention, attention mechanism, sequence transduction, recurrent/convolutional baselines, and BLEU. Raw signal lists remain collapsed by default.
- Updated stale scope copy so the analysis page explains the current staged section-analysis and paper-map draft behavior instead of implying full-paper staged analysis is still absent.
- Already analyzed sections now load their cached lesson when selected, so the green analyzed state leads back to usable learning content rather than only acting as a status marker.
- Analysis-column learning cards now stay single-column in the PDF workspace. The previous multi-column layout made concept and term cards too narrow on normal desktop widths.
- Old bad base-analysis fragments such as `Training Deep Neural Networks` and `inputs changes during training` are normalized out of cumulative paper-map terms/concepts.
- Added real-paper normalization fixtures for BatchNorm and BERT snippets so generic fragments and PDF split artifacts are rejected in tests.
- Added an Attention/Transformer fixture so `the best performing models` is handled as a discourse signal rather than a saveable term/concept, while Transformer, self-attention, sequence transduction, and parallelization remain learnable.
- The per-result concept block is called `Concept anchors`, while the cumulative cross-section block is called `Paper map`.
- The section reader shows a short preview of the current backend-cleaned text before opening the full source text.

## Still Weak

- PDF page navigation and extracted section navigation are partially aligned for new uploads. Section-to-PDF and PDF-to-section movement both work when source labels are available.
- Full-paper staged analysis is partly automated. The user can trigger `Auto-study next 3`, and the backend analyzes the next unstudied sections sequentially, but there is no durable background job queue or full-paper final merge.
- The lower analysis page still contains large report-style blocks. It is usable, but it is not yet a polished reading companion.
- The paper-map guide and whole-paper learning draft are deterministic and source-grounded, but still light synthesis. They do not yet perform model-backed final argument reconstruction across all analyzed sections.
- Some source extraction remains lossy for multi-column papers and equations.
- Concept quality is improved by guardrails, but still needs broader real model-output contract tests across more papers and sections.
- Paper map is cumulative from analyzed sections only; it does not yet perform a final whole-paper merge after all major sections are complete.

## Next Product Fixes

1. Promote staged analysis from a request/response endpoint to a durable backend job queue with pause/resume and status recovery after refresh.
2. Add a final merge step that deduplicates concepts, terms, expressions, references, and summaries after enough sections are analyzed.
3. Improve PDF page-to-text-section alignment. If exact alignment is not possible, make the mismatch explicit and avoid implying they are the same unit.
4. Add real-paper quality fixtures for BERT, BatchNorm, and Transformer papers that reject generic fragments and verify expected concept/term separation.

## Current Verdict

The app is closer to a real paper-reading workspace than before because source, extracted section, analysis action, staged section analysis, and cumulative map are now visible in one flow. It is still not finished as a full-paper language-learning product because the final whole-paper merge and durable job control are missing.
