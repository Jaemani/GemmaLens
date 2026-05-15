# Changelog

## 2026-05-15

- Added honest paper-map coverage counts (`analyzed / total sections`) so users can see how much of the paper has actually been processed.
- Section analysis now refreshes the cumulative paper map automatically after the inline section lesson is created.
- Reordered the analysis workspace so section navigation and "Analyze this section" appear above the cumulative paper map and concept cards, making the page work more like a reading tool than a static report.
- Renamed the per-result concept panel from "Paper map" to "Concept anchors" to reduce confusion between current-section concepts and the cumulative paper map.
- Fixed paper-map fallback normalization so older base analyses no longer leak generic fragments such as `Training Deep Neural Networks` or `inputs changes during training` into cumulative concepts/terms.
- Added backend document-section endpoints and switched the frontend section reader to use them, so displayed section numbers/text now match the exact backend section sent to Gemma for analysis.
- Replaced the native embedded PDF iframe with a PDF.js canvas preview, so the demo reliably shows the original PDF and supports PDF page Previous/Next controls.
- Promoted extracted-section navigation so section Previous/Next and "Analyze this section" are visible without opening a hidden debug text block.
- Added BERT-family learning guardrails after testing the BERT paper: BERT results now prioritize BERT, pre-training, fine-tuning, masked language model, and next sentence prediction instead of unrelated terms that merely appear elsewhere in the paper.
- Added same-document section analysis: "Analyze this section" now returns an inline section lesson without creating a separate document or leaving the current paper workspace.
- Added persistent section-analysis cache. Re-opening an analyzed section now returns the saved lesson immediately instead of calling the model again.
- Added a cache-backed paper map that aggregates analyzed sections into cumulative concepts, terms, phrases, and section summaries without pretending unanalyzed sections are complete.
- Cached section results are re-normalized with current guardrails when read, so older weak cached lessons can improve without re-running the model.
- Fixed cached/section normalization to use the text span actually analyzed instead of re-normalizing against the whole paper, which reduced cross-section vocabulary contamination.
- Added source-grounded learning guardrails that repair weak edge-model output: summaries that only repeat source text are replaced, missing academic phrases are recovered from reusable paper-reading patterns, and weak sentence decompositions are replaced with structure explanations.
- Tightened concept/term separation so generic source fragments such as `Training Deep Neural Networks` and `inputs changes during training` are not shown as saveable learning objects.
- Moved A/B and scope panels below the main analysis workspace so PDF/source reading and the learning guide appear first.
- Added DOCX upload support, including paragraph and simple table extraction.
- Stored uploaded original files locally and added `GET /documents/{id}/file`.
- Added source-file attachment for existing documents, so demo documents created before file storage can attach the original PDF without losing the existing analysis id.
- Added an original PDF pane in the analysis workspace when a PDF upload has a stored source file.
- Added explicit legacy `.doc` rejection with conversion guidance.
- Improved text decoding for TXT/Markdown uploads, including Korean encodings.
- Added clearer OCR guidance for scanned/image-only PDFs.
- Widened the main workspace and document input layout so a real PDF viewer can fit later without wasting side margins.
- Removed narrow page wrappers from dashboard, documents, translate, quiz, and settings so tool screens use the available workspace consistently.
- Normalized oversized rounded guide/progress cards to the same 8px-radius card language used elsewhere.
- Updated sidebar spacing and typography for a quieter workspace feel.
- Cached analysis reads now re-run normalization against the source text, so bad saved objects can be filtered without forcing a model rerun.
- Removed the fake left-side PDF reader layout. Extracted text slices are now collapsed source tools, not presented as a real reading pane.
- Clarified that extracted text slices are model input, not rendered PDF pages.
- Tightened term/concept cleanup so generic phrases such as `the best performing models` are not treated as saveable vocabulary.
- Added visible progress UI for video transcript and current-scene analysis.
- Made analysis result source-aware: video transcript results no longer show paper page-reader UI or paper-only copy.
- Limited long transcript source excerpts so concept cards do not show entire transcript chunks.
- Filtered video transcript records out of the dashboard/documents "Recent documents" lists.
- Added page-slice reader on analysis results so users can move through long papers and analyze the selected slice.
- Fixed PDF hyphenation artifacts such as `representa- tion`, `repre- sentation`, and resulting junk candidates like `tion model`.
- Analysis now uses the learner profile target level when the edge fast-meta path cannot estimate CEFR level.
- Added first-class concept extraction to analysis results, separate from vocabulary and phrases.
- Added concept saving to the dictionary/review store.
- Added a concept map panel before vocabulary tables so paper reading starts from ideas, not only words.
- Added readable-section cleanup to skip PDF front matter such as arXiv headers, authors, and emails before analysis.
- Added re-analysis from the result page so cached weak results can be replaced after runtime/pipeline improvements.
- Renamed `/tools` to `/translate` and removed the "Focused tool" label.
- Optimized remote Q4 translation by skipping JSON mode for short translations; the local smoke test dropped from about 31s to about 1.6s.
- Filtered placeholder translation notes such as `short learner note`.
- Added paper-reading architecture documentation for whole-paper maps, page/section lessons, concepts, references, and edge atomic tasks.
- Added technical report for hackathon submission planning.
- Made mock mode demo/deploy-only and removed silent mock fallback for real MLX failures.
- Added searchable multilingual language catalog for settings and translate.
- Split Translate and Quiz into independent routes.
- Added quiz generation from analyzed documents/videos with browser cache.
- Added document/video history deletion.
- Added YouTube transcript fallback through `yt-dlp`.
- Collapsed manual subtitle fallback in video learning.
- Added real backend translation endpoint for MLX runtime and removed fake echo translation output.
- Added same-origin frontend proxy for backend calls so local phones/browsers do not depend on direct `:8012` CORS access.
- Added model warmup endpoint/button to load Gemma before demo tasks and reuse the loaded model for atomic calls.
- Added local stack runner for stable `8012` backend + `3003` frontend startup.
- Restricted demo/sample result fallbacks to explicit `NEXT_PUBLIC_DEMO_MODE=true`.
- Added no-thinking atomic MLX generation prompts for more reliable JSON output.
- Hid internal analysis validation warnings from the user-facing result page.
- Reworked dashboard into a compact workspace view and removed duplicate action buttons.
- Collapsed language lists by default while keeping the selected language pinned at the top.
- Added section-level analysis status for long documents without exposing internal validator labels.

## 2026-05-08

- Added local profile settings for support language, learning language, target level, and onboarding state.
- Added dictionary viewed tracking with view count and last viewed time.
- Added real-user test plan for multilingual users, hard PDFs, first-user onboarding, and learning-memory validation.
- Added user guide page explaining project flow, levels, difficulty scores, language direction, and saved learning objects.
- Added shareable team brief for developer and non-developer collaborators.
- Added model presets for Gemma 4 E2B/E4B MLX bf16 and Ollama.
- Added analysis progress UI with elapsed time and model stages.
- Analysis pages now auto-run missing analysis for existing documents.
- Switched visual style closer to Google Material conventions.
- Added backend tests, CI workflow, upload flow, runtime model settings, and MLX model path-aware cache.

## 2026-05-07

- Created initial docs, FastAPI backend, Next.js frontend, model adapter layer, mock output, dictionary endpoints, Ollama scaffold, and MLX support.
