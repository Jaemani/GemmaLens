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

## Fixed From Direct Use

- The app no longer pretends one short section is a whole-paper guide. The paper map shows coverage such as `1 / 27 sections analyzed`.
- The PDF source is rendered in-app with PDF.js canvas instead of a fragile embedded iframe.
- The main paper-reading action is now visible beside the PDF: previous/next extracted section plus `Analyze this section`.
- The section reader now gets backend-cleaned sections from `GET /documents/{id}/sections`; it no longer duplicates splitting logic in the browser.
- `Analyze this section` uses the same zero-based backend section index that the UI displays.
- Backend section responses now include `analyzed`, and the reader shows analyzed count, section status chips, and a `Next unstudied` action.
- New PDF uploads preserve internal page markers during extraction, allowing section responses to include labels such as `PDF page 2`. Older existing demo records may not have these markers.
- The PDF viewer now follows section selection when source labels are available. In the BatchNorm smoke check, selecting section 4 moved the left preview to `PDF page 2 / 11`.
- A completed section lesson now includes `Analyze next unstudied`, keeping the reading loop moving after the user finishes a section.
- The cumulative paper map refreshes after section analysis.
- Old bad base-analysis fragments such as `Training Deep Neural Networks` and `inputs changes during training` are normalized out of cumulative paper-map terms/concepts.
- Added real-paper normalization fixtures for BatchNorm and BERT snippets so generic fragments and PDF split artifacts are rejected in tests.
- The per-result concept block is called `Concept anchors`, while the cumulative cross-section block is called `Paper map`.
- The section reader shows a short preview of the current backend-cleaned text before opening the full source text.

## Still Weak

- PDF page navigation and extracted section navigation are partially aligned. Section-to-PDF movement works when source labels are available; PDF-to-section reverse navigation is not implemented yet.
- Full-paper staged analysis is not automated yet. The user still has to trigger section analysis manually, though the UI now helps move to the next unstudied section.
- The lower analysis page still contains large report-style blocks. It is usable, but it is not yet a polished reading companion.
- Some source extraction remains lossy for multi-column papers and equations.
- Concept quality is improved by guardrails, but still needs broader real model-output contract tests across more papers and sections.
- Paper map is cumulative from analyzed sections only; it does not yet perform a final whole-paper merge after all major sections are complete.

## Next Product Fixes

1. Add a background staged-analysis mode that processes sections sequentially and updates paper-map coverage.
2. Add a final merge step that deduplicates concepts, terms, expressions, references, and summaries after enough sections are analyzed.
3. Improve PDF page-to-text-section alignment. If exact alignment is not possible, make the mismatch explicit and avoid implying they are the same unit.
4. Add real-paper quality fixtures for BERT, BatchNorm, and Transformer papers that reject generic fragments and verify expected concept/term separation.

## Current Verdict

The app is closer to a real paper-reading workspace than before because source, extracted section, analysis action, and cumulative map are now visible in one flow. It is still not finished as a full-paper language-learning product because staged analysis, section status, and final merge are missing.
