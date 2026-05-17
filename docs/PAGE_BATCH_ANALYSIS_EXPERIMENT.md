# Page-Batch Analysis Experiment

Last checked: 2026-05-17

## Executive Summary

GemmaLens should move long-document preparation from section-by-section requests to page-batch requests.

The current section-level pipeline is useful because it keeps lessons source-grounded, but it is too slow for real PDFs because it repeats HTTP, model generation, JSON parsing, normalization, and DB writes for every extracted section. A page-batch pipeline keeps the user-facing reading model page-based while still returning section-level lessons.

Measured on three real PDF papers, page-batch preparation would reduce:

- frontend/backend analysis requests from `105` to `38` (`63.8%` fewer)
- local MLX/Ollama model generations from `105` to `38` (`63.8%` fewer)
- ThinkPad remote Q4 model generations from an estimated `315` to `38` (`87.9%` fewer)
- full remote atomic model generations from an estimated `525` to `38` (`92.8%` fewer)

This is not only a performance optimization. It also matches the product better: learners read PDFs by page, but study lessons by logical section.

## User Problem

The current automatic preparation flow can feel slow and over-fragmented:

- the app sends one analysis request per extracted section
- long documents can show hundreds of pending sections
- section boundaries sometimes inherit PDF extraction artifacts
- users care about the current page first, not the entire internal section queue
- progress messages become noisy because they report low-level preparation mechanics

The user should experience:

```txt
Upload PDF -> prepare first page -> open PDF viewer with first lesson ready -> prepare remaining pages in background
```

Internally, each page batch can still produce multiple page-local section lessons such as `S1`, `S2`, and `S3`.

## Current Pipeline

Current flow:

```txt
PDF extraction
-> page markers
-> backend section splitter
-> frontend loops over sections
-> POST /documents/{id}/sections/{index}/analyze
-> model analysis for one section
-> normalize
-> save section cache
```

This works, but the expensive path repeats once per section.

Runtime implication:

- MLX/Ollama adapter: usually one generation per section
- remote Q4 adapter: three atomic generations per section (`terms`, `phrases`, `sentences`)
- full remote adapter: five atomic generations per section (`meta`, `terms`, `phrases`, `concepts`, `sentences`)

The remote path is especially sensitive because each section can multiply into several model-server round trips.

## Proposed Pipeline

Proposed flow:

```txt
PDF extraction
-> page markers
-> page text selection
-> POST /documents/{id}/pages/{page}/analyze
-> model returns page-local section boundaries and lessons
-> backend stores each returned lesson as section-level cache
-> UI shows PDF page + page-local S1/S2/S3 lessons
```

The model task should ask for:

- page-local sections
- section title if obvious
- continuation marker if the page starts mid-section
- concepts, terms, expressions, sentence pattern, summary per section
- source-grounded evidence for each learning object

The UI should remain simple:

- page navigation is primary
- `S1`, `S2`, `S3` are page-local section buttons
- first page is prepared before the workspace opens
- remaining pages prepare in the background
- paper map updates from completed page/section caches

## Experiment Method

Script:

```bash
rtk backend/.venv-mlx/bin/python scripts/page_batch_experiment.py
```

Inputs:

- `tmp/eval_papers/attention_is_all_you_need.pdf`
- `tmp/eval_papers/batch_norm.pdf`
- `tmp/eval_papers/bert.pdf`

The script uses the real PDF extraction and section splitting code:

- `DocumentIngestionService._extract_pdf`
- `DocumentIngestionService.normalize_text`
- `DocumentSectionService.split_with_labels`

It measures actual extracted pages and logical sections, then estimates request/model-call pressure for the current and proposed designs.

Generated artifacts:

- `tmp/page_batch_experiment/summary.md`
- `tmp/page_batch_experiment/summary.json`

## Results

| Paper | PDF pages | Learning pages | Sections | Current requests | Page-batch requests | Request reduction | Current Q4 calls | Page-batch calls | Q4 call reduction |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `attention_is_all_you_need.pdf` | 15 | 12 | 26 | 26 | 12 | 53.8% | 78 | 12 | 84.6% |
| `batch_norm.pdf` | 11 | 11 | 34 | 34 | 11 | 67.6% | 102 | 11 | 89.2% |
| `bert.pdf` | 16 | 15 | 45 | 45 | 15 | 66.7% | 135 | 15 | 88.9% |
| **Total** | **42** | **38** | **105** | **105** | **38** | **63.8%** | **315** | **38** | **87.9%** |

## Boundary Findings

| Paper | Pages with multiple sections | Max sections on one page | Continued sections |
| --- | ---: | ---: | ---: |
| `attention_is_all_you_need.pdf` | 7 | 4 | 9 |
| `batch_norm.pdf` | 8 | 6 | 22 |
| `bert.pdf` | 14 | 5 | 26 |

These numbers matter because they show why pure page analysis is not enough. Many pages contain multiple learning sections, and many sections continue across pages. The right product shape is therefore not "page summary" and not "one section request at a time"; it is page-batch section lessons.

## Quality Interpretation

Section-by-section is strong for grounding because the model sees a focused unit. Page-batch should preserve that strength by requiring the model to return several small section lessons inside the page result.

Expected benefits:

- fewer model calls
- fewer progress state transitions
- better first-page readiness
- better page/section alignment in the UI
- fewer accidental splits caused by isolated line fragments
- clearer demo story for local and edge runtimes

Risks:

- large equation/table-heavy pages can produce oversized JSON
- page-end continuation sections need explicit handling
- references and appendices should be skim/navigation lessons, not normal vocabulary lessons
- a bad page-batch result can affect several section lessons at once

Mitigation:

- keep the current section endpoint as a fallback
- cap page-batch output to page-local sections only
- store each returned section lesson independently
- allow retry for one page
- mark continued sections visibly
- run the existing source-grounding normalizer on every returned lesson

## Client-Side UX Findings

From a learner's perspective, these are the remaining weak points to fix while moving to page-batch:

- The first screen should not show an empty PDF workspace. It should prepare the first page lesson first, then open the viewer.
- Progress should be page-oriented: `Preparing page 3 of 15`, not low-level wording like `one-by-one`.
- The global status dock should say what is being processed and where clicking takes the user.
- Page navigation should be the main mental model; section buttons should be local to the page.
- The section lesson should start with the current section summary, then words/expressions, then concepts and sentence patterns.
- Paper map should not dominate incomplete documents. It should become more prominent when enough pages are ready.
- Very long books need a different policy: prepare current page, next page, and a small lookahead window instead of all pages immediately.
- Native-language gloss quality is a product requirement, not a fallback detail. Missing glosses should be treated as weak output.

## Submission Positioning

For Gemma 4 Good, this experiment supports the key claim:

> GemmaLens uses local Gemma models to turn academic reading into a progressive learning workflow. It prepares the first page quickly, builds section-level language lessons from real source text, and continues preparing the rest of the document in the background.

The page-batch design makes the demo more credible because it explains why local inference can feel responsive even when complete-document analysis is expensive:

- first-page lesson gives immediate value
- page-batch preparation reduces model-call overhead
- source-grounded section lessons remain durable review material
- background preparation turns the full paper into a study map over time

## Implemented Experimental Path

The experimental path is now implemented:

1. `POST /documents/{id}/pages/{page_number}/analyze` prepares one PDF page and stores every page-local section lesson in `SectionAnalysisRepository`.
2. `POST /documents/{id}/page-batches` prepares the next unready page batches instead of looping section-by-section from the client.
3. The frontend automatic preparation path now calls page analysis, not section analysis.
4. The first page lesson is prepared before the PDF viewer is shown, so users do not land in an empty workspace.
5. Manual retry of the currently selected section remains available through the existing section endpoint.
6. Playwright coverage verifies first-page readiness, delayed PDF viewer display, page navigation, and current-page highlighting.

This should still be treated as experimental because page-batch quality needs more real-model output audits on equation-heavy pages, textbooks, references, and appendices. The current fallback section endpoint is intentionally kept for manual repair.
