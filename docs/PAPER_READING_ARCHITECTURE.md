# Paper Reading Architecture

GemmaLens should make a paper learnable, not merely shorter.

## Product Rule

Generic AI tools already translate and summarize. GemmaLens should extract what a learner needs to keep reading independently:

- concepts: ideas, methods, phenomena, hypotheses, and claims;
- terms: domain vocabulary and technical words;
- phrases: reusable academic expressions;
- syntax: difficult sentence structures;
- references: citations or named works that connect ideas;
- review memory: saved, viewed, familiar, ignored, and mastered states.

The UI must stay source-aware. A PDF paper, pasted text, video transcript, and current video scene can share the same backend learning-object schema, but they should not share identical user-facing copy or navigation. Paper results need page/section reading controls. Video results need transcript/scene context and synchronized playback language.

## Recommended Flow

```text
PDF/text/transcript
-> extract text
-> clean front matter
-> split into pages/sections
-> analyze each unit with atomic Gemma tasks
-> validate every item against source text
-> store unit result
-> merge whole-paper map
-> let user save concepts, terms, phrases, and sentences
```

## Result Structure

### Whole-Paper Map

This should answer:

- What is the paper trying to solve?
- What method or evidence does it use?
- Which concepts repeat across sections?
- Which references or prior works are important?
- Which terms should the learner know before reading deeply?

### Page/Section Lesson

Each page or section should answer:

- What is the main idea here?
- Which concepts are necessary to understand this page?
- Which words or expressions should be saved?
- Which sentence is structurally difficult?
- What background knowledge would help the learner continue?

## Concept vs Term

A term is a word or phrase.

Example:

```text
Batch Normalization
```

A concept is an idea that may contain multiple terms and references.

Example:

```text
Batch Normalization as a method for stabilizing deep network training by normalizing mini-batch activations.
```

Concepts should be saveable because advanced reading depends on repeated idea recognition, not only vocabulary memorization.

Generic local context such as "the best performing models" should not become a saveable term or concept. If it is useful, it belongs in sentence/context explanation, not the learner dictionary. Saveable objects should pass a higher bar:

- term: reusable technical vocabulary or academic expression;
- concept: idea, method, phenomenon, task, claim, or model family;
- phrase: reusable academic wording or discourse function;
- sentence: structure worth practicing.

New PDF uploads preserve the original file locally. When available, the analysis workspace renders the original PDF with a PDF.js canvas preview and PDF page navigation on the left while the right panel shows learning guidance. Extracted text sections remain model-input units because OCR, equations, and multi-column layout can damage text extraction. They are useful for page/section analysis, but they should be labeled as extracted sections rather than faithful PDF pages.

## Ingestion Policy

Supported first-pass inputs:

- pasted text;
- `.txt`;
- `.md` / `.markdown`;
- `.docx`;
- selectable-text `.pdf`;
- video transcripts.

Unsupported or degraded inputs:

- legacy `.doc`: ask the user to export to `.docx`, `.pdf`, or `.txt`;
- scanned/image-only PDF: require OCR before analysis;
- image-only DOCX: ask the user to export or paste text;
- equation-heavy and multi-column PDFs: extracted text may be damaged, so do not present it as a faithful PDF reader.

## Edge Runtime Strategy

Small Gemma models should not receive a whole paper and be asked for one large JSON object. The stable pattern is:

```text
small source unit + one narrow task -> JSON -> validate -> merge
```

Atomic tasks:

- detect concepts;
- extract terms;
- extract academic phrases;
- decompose one or two difficult sentences;
- summarize the current page/section;
- extract citation markers near important concepts.

If a task returns invalid JSON, only that task should be retried or replaced with a source-grounded fallback. The whole document should not fail.

The backend must not pass model output directly to the learner. A separate normalization/guardrail layer should:

- prefer source-grounded known terms over low-confidence model guesses;
- discard generic fragments such as section titles, partial noun phrases, and vague local context;
- recover reusable academic phrases from source text when the model returns none;
- replace summaries that merely repeat the first sentence;
- replace missing sentence decomposition with explicit structure patterns and support-language explanation;
- keep concepts and vocabulary separate even when the surface string overlaps.

Section analysis should preserve the parent document context. Analyzing a section should not create a new top-level document or navigate away from the current paper workspace. The preferred interaction is:

```text
same PDF workspace
-> choose extracted section
-> analyze current section
-> render inline section lesson
-> cache section lesson by document and section index
-> update paper map from cached section lessons
-> keep PDF page navigation and section navigation available
```

Normalization must use the text span that was actually analyzed. Re-normalizing a first-section result against the whole paper can pull in later terms that are source-grounded somewhere in the document but irrelevant to the current reading moment.

The paper map should be honest about coverage. If only sections 2 and 3 are analyzed, it should say so and aggregate only those sections. It should not produce a whole-paper conclusion until all major sections have been analyzed or a separate whole-paper merge step has run.

Current implementation note: `GET /documents/{id}/paper-map` returns both `total_sections` and `analyzed_sections`. The frontend shows this as a coverage indicator and refreshes it after each section analysis, so the learner can tell whether the current map is only a first-section guide or a broader paper guide.

The frontend should not duplicate section-splitting logic. The reader requests backend-cleaned sections from `GET /documents/{id}/sections`, and `Analyze this section` sends the same zero-based section index to `POST /documents/{id}/sections/{section_index}/analyze`. This keeps displayed text, cache keys, paper-map coverage, and model input aligned.

UI priority for paper reading:

```text
original PDF/source
-> current extracted section controls
-> analyze current section
-> cumulative paper map
-> concept anchors
-> vocabulary, expressions, summaries, sentence structures
```

The section controls should stay high in the workspace. If they are below all generated content, the product feels like a one-shot summarizer instead of a reading companion.

## MVP Decision

For the next usable paper-reading MVP, implement:

1. full-text extraction;
2. page or section splitting;
3. a paper-map page;
4. page-by-page lesson view;
5. concept save/review;
6. re-analysis for a selected page/section.

This is more useful than one shallow full-paper result and more realistic for edge-device inference.
