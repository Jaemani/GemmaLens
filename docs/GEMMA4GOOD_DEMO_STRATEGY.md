# Gemma 4 Good Demo Strategy

Last updated: 2026-05-17

## Positioning

GemmaLens is a local-first academic language learning harness.

It is not a PDF chatbot, a generic summarizer, or a translation wrapper. The demo should show that GemmaLens turns real documents and transcripts into durable learning objects:

- concepts for understanding the argument
- terms for domain vocabulary
- reusable expressions for academic English
- sentence patterns for transfer to future reading
- source-grounded native-language glosses

## Demo Story

Use this order.

1. Open a real PDF.
2. Show the original PDF beside the section workspace.
3. Let the first section become readable immediately.
4. Show automatic section analysis preparing the remaining lessons.
5. Open the paper map after several sections are ready.
6. Show a section lesson with native-language glosses and source sentences.
7. Open Library to show concepts, terms, expressions, and sentence patterns as different review objects.
8. Open Video and use a verified demo URL.
9. Analyze the current scene inline beside the player.
10. Finish with the guide page explaining local runtimes and current limits.

## Recommended Sources

PDFs:

- `tmp/eval_papers/attention_is_all_you_need.pdf`
- `tmp/eval_papers/batch_norm.pdf`
- `tmp/eval_papers/bert.pdf`

Verified video demo URLs:

- ML: `https://www.youtube.com/watch?v=eMlx5fFNoYc`
- Climate: `https://www.youtube.com/watch?v=9PFhrpyWV-w`
- Economics: `https://www.youtube.com/watch?v=3ez10ADR_gM`
- Medical: `https://www.youtube.com/watch?v=cUP8bGWln6M`
- FastAPI: `https://www.youtube.com/watch?v=7t2alSnE2-I`

These URLs have curated transcript/article fallback because YouTube caption endpoints can be rate-limited.

## What To Emphasize

- Local-first: the model can run on local or edge hardware.
- Fast perceived UX: the first page is usable while background section analysis continues.
- Learning quality: outputs are not just summaries; they are structured for language acquisition.
- Source grounding: every term, expression, and sentence pattern is tied back to source text.
- Learner level: B1/B2/C1/C2 changes guidance depth and review priority.
- Native-language support: Korean glosses explain terms and expressions without replacing the original source.

## Current Limits To State Clearly

- PDF extraction depends on text quality; scanned PDFs need OCR or pasted text.
- Very long textbooks may produce many sections and should be read progressively.
- Arbitrary YouTube URLs can fail when captions are blocked, missing, or unavailable.
- Verified demo URLs and pasted subtitles are the stable video paths.
- The prototype has a strong local workflow, but arbitrary public-source ingestion still needs clearer availability UI and broader transcript-provider support.

## One-Minute Pitch

GemmaLens helps non-native English-speaking students read technical material locally. Instead of translating a sentence and leaving the learner dependent, it turns each section into concepts, terms, reusable academic expressions, and sentence patterns. A paper becomes a study path, and the system prepares later sections while the learner reads the current one. The same structure also works for captioned videos, making local Gemma models useful as a practical academic reading companion.

