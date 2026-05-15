# Changelog

## 2026-05-15

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
