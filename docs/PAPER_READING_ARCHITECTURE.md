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

The current reader uses extracted text slices. It is not a rendered PDF viewer yet. A future PDF viewer should preserve page geometry on the left while the right panel shows page-specific learning guidance.

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

## MVP Decision

For the next usable paper-reading MVP, implement:

1. full-text extraction;
2. page or section splitting;
3. a paper-map page;
4. page-by-page lesson view;
5. concept save/review;
6. re-analysis for a selected page/section.

This is more useful than one shallow full-paper result and more realistic for edge-device inference.
