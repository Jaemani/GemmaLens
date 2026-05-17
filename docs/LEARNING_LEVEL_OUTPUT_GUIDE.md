# Learning Level Output Guide

GemmaLens should not only label a result as B1, B2, C1, or C2. The learner level must change what the system selects, explains, and suppresses.

## Core Principle

Every source produces three different learning layers:

- Concepts: ideas needed to understand the argument or procedure.
- Terms: words and domain labels worth recognizing again.
- Expressions and sentences: reusable academic or technical language patterns.

The level setting controls priority, not truth. The same source can be valid for all levels, but the system should choose different learning objects.

## B1-B2

Goal: make the source readable now.

Terms:
- Prefer core field terms that block comprehension.
- Include common academic words when they carry the section's logic.
- Avoid long lists of model names, hardware, citations, benchmark labels, and minor proper nouns.
- Glosses should be plain and concrete in the support language.

Expressions:
- Prefer frequent, reusable academic functions: cause, contrast, purpose, result, uncertainty.
- Good examples: `is associated with`, `in response to`, `remains elevated`, `to address this gap`.
- Avoid rare rhetorical framing unless it is essential.

Sentences:
- Pick the sentence where the main clause is hard to find.
- Explain in this order: main clause, modifier, contrast/cause, then technical detail.
- Difficulty note should tell the learner what to do first, e.g. find the main verb.

## C1-C2

Goal: make the learner better at reading future academic material.

Terms:
- Prefer high-signal field terms, statistical terms, method terms, and conceptual contrasts.
- Suppress incidental details unless central to the argument: hardware names, one-off baselines, section labels, enumeration markers, dataset names used only as context.
- Keep repeated concepts if they organize the paper-level map.

Expressions:
- Prefer rhetorical moves and dense academic collocations.
- Good examples: `precludes parallelization`, `forms the foundation of`, `is associated with`, `not ... in standard form`, `with a slight abuse of notation`.
- Skip low-value markers like `First`, `Second`, `as follows` unless the section is specifically teaching discourse organization.

Sentences:
- Pick sentences that compress argument, evidence, limitation, or method in one structure.
- Explain the rhetorical move, clause compression, and author stance.
- Difficulty note should mention why the sentence matters for academic reading, not only what it means.

## Source Type Rules

Papers:
- Preserve logical sections when possible: abstract, introduction, background, method, experiments, conclusion, appendix.
- Treat references and tables differently from prose.
- Extract terms from the current logical section, then merge repeated terms into the paper map.

Reports:
- Focus on decision terms, risk terms, metrics, policy/action language, and uncertainty.
- Good report terms: `climate risk`, `greenhouse gas emissions`, `monetary policy`, `inflation expectations`.
- Good report expressions: `is likely to`, `remains elevated`, `in response to`.

Videos:
- Analyze transcript scenes inline with the video.
- Prefer spoken procedural expressions and domain terms from the current scene.
- Good technical-video terms: `idempotent preflight check`, `stale metadata`, `worker nodes`.
- Sentence explanations should help the learner keep watching, not force a separate document-reading mode.

## Quality Failures

These are unacceptable:

- Korean/support gloss is just an English meaning wrapped in a generic sentence when a known gloss is available.
- C2 result spends top slots on incidental proper nouns or hardware.
- B1-B2 result explains only abstract concepts and does not help the learner read the current sentence.
- Video analysis opens as a detached document lesson instead of supporting the current scene.
- Section output repeats whole-paper map material instead of focusing on the selected section.
