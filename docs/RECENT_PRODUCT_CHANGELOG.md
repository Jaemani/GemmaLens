# Recent Product Changelog

Date: 2026-05-19

Purpose: record product and implementation changes made after the larger dashboard/document/video redesign notes. This file documents only behavior that remains in the app. Features that were added and then removed are listed as future candidates, not as current functionality.

## Current Product Defaults

GemmaLens currently defaults to the hackathon demo profile:

- Learning language: English
- Explanation language: Korean
- Reading level: C2
- Paper section preparation: on

These defaults live in:

- `backend/app/models/user_profile.py`
- `backend/app/db/init_db.py`
- `frontend/app/settings/SettingsClient.tsx`

Existing SQLite profiles are normalized during startup when values are empty or `target_level` is `unknown`.

## Settings Page

The Settings page now exposes only controls that are connected to real behavior:

- Learning language
- Explanation language
- Target reading level
- Prepare paper sections automatically
- Reset to defaults

Removed from the current UI because they were stored but not wired to analysis behavior:

- Explanation depth
- Native-language support mode
- Learning focus
- Save behavior
- Video default mode
- Prefer local model
- Allow remote fallback

Future candidate: these could return if they become real prompt/runtime controls. They should not be reintroduced as UI-only profile fields.

Reading level now shows an inline explanation for the selected level:

- B1: core vocabulary and sentence support
- B2: domain vocabulary plus reusable academic phrases
- C1: nuance, argument structure, and research expressions
- C2: precision, field-specific phrasing, dense concepts, and paper-level reasoning
- Domain-heavy: specialist concepts and terminology
- Auto: model/source-derived level selection

The previous explanatory sentence was demoted to small helper text so it does not dominate the card.

## Quiz Behavior

There is no backend quiz table. The quiz page derives review prompts from:

- saved dictionary items
- analyzed documents
- paper map synthesis

Saved quiz drafts are browser-local only:

```txt
localStorage key prefix: gemmalens.quiz.
```

Changes:

- The quiz page no longer auto-generates prompts when a source is selected.
- If no saved draft exists, the page stays empty until the user clicks `Regenerate`.
- `Clear drafts` removes all `gemmalens.quiz.*` localStorage keys and immediately clears the visible quiz items.
- On page load, stale quiz drafts are pruned if their source document no longer exists or if the saved dictionary is empty.

Reason: demo cleanup should be predictable. Deleting documents/library items should not leave old quiz drafts visible.

Relevant file:

- `frontend/app/quiz/page.tsx`

## Guide Page

The Guide page was rewritten from a project/internal demo note into a product-facing user guide.

Current sections:

- Guide intro: GemmaLens as a source-grounded language learning tool
- Paper reading
- Local-first preparation
- Learning objects
- Translation
- Video study
- Reading levels
- Notes

Removed from the user-facing guide:

- internal hackathon demo strategy wording
- implementation-heavy explanations
- "current limits" phrasing that made the product look unfinished

Relevant file:

- `frontend/app/guide/page.tsx`

## Sidebar And Global Status Dock

Sidebar navigation was enlarged so the main taskbar items are easier to scan:

- nav text increased
- nav icons increased
- active row made bolder
- click target height increased

The global status dock was reduced back to a supporting size after it became visually heavier than the nav. Only the status keywords are bold:

- `Ready`
- `Alive`
- `Off`

When the backend is alive, the green status dot pulses.

Relevant files:

- `frontend/components/layout/Sidebar.tsx`
- `frontend/components/layout/GlobalStatusDock.tsx`

## Dashboard Copy And Metrics

Dashboard wording was tightened for the current product framing:

- Hero primary actions remain document and video first.
- `Set learning profile` opens Settings.
- `Quiz Sets` was renamed to `Review Items`.

Reason: the app does not store durable quiz sets in the backend. The metric represents reviewable saved items, not persisted quiz objects.

Relevant file:

- `frontend/app/page.tsx`

## Video Learning

Current video learning supports:

- online YouTube transcript loading
- local media library scan
- local subtitle loading from SRT/VTT
- timestamped subtitle timeline
- subtitle click-to-seek
- hover-only Study button for subtitle lines
- line study block below the subtitle timeline
- current scene analysis
- watched-part recap
- live cues from current subtitle context
- saving video-derived terms/concepts/phrases to the library

Important fixes:

- YouTube start time parsing supports `t=` and `start=`.
- Online subtitle sync offset was corrected back to zero after testing.
- Active subtitle selection handles overlapping caption lines by choosing the latest matching segment.
- Study button clicks do not seek the video line by accident.
- Empty dictionary meanings from video save are filled with fallback source-grounded meaning.
- Weak placeholder meanings such as "currently noticeable long word" are not saved as final meanings.

Known product boundary:

- YouTube transcript fetch remains useful but network-dependent.
- Hackathon demos should prefer verified public transcripts or local SRT/VTT sources.

Relevant files:

- `frontend/components/video/VideoLearningPanel.tsx`
- `backend/app/api/routes_video.py`
- `backend/app/services/video_transcript_service.py`
- `backend/app/services/local_media_service.py`
- `backend/app/services/dictionary_service.py`

## Language And Native Gloss Handling

Current behavior:

- Profile language settings are passed to document analysis routes.
- Support-language glosses are normalized for terms and phrases.
- Concept items now support `support_language_explanation`.
- Dictionary save fallback fills missing meanings when video-derived save payloads are incomplete.

Important design rule:

Native-language support is a scaffold, not the main product. English meaning/function and source sentence should remain primary; Korean or other support-language glosses should help comprehension without making GemmaLens feel like a translation app.

Relevant files:

- `backend/app/schemas/analysis_schema.py`
- `backend/app/services/analysis_normalization_service.py`
- `backend/app/services/dictionary_service.py`
- `frontend/lib/types.ts`

## Quality Evaluation

The quality-eval workflow created temporary documents with titles like:

```txt
quality-eval::<case>::<model>::<level>::<support_language>::<timestamp>
```

These are test artifacts, not demo data. They can be deleted before the demo.

The quality-eval script stores raw reports under:

```txt
docs/quality_eval/
```

Those report files are not app UI records. Keep them for engineering evidence unless intentionally cleaning the repository.

Relevant files:

- `scripts/quality_eval.py`
- `docs/QUALITY_EVAL_REPORT.md`
- `docs/QUALITY_EVAL_FINDINGS.md`
- `docs/QUALITY_EVAL_FIX_PLAN.md`

## Demo Data Cleanup Rules

For demo polish:

- Delete ugly/generated quality-eval documents.
- Keep only a few high-quality papers/videos with clean names.
- Clear `gemmalens.quiz.*` localStorage draft keys if the quiz page looks stale.
- Dictionary items are not automatically deleted when a document is deleted; the document reference is cleared. Delete library items separately if the demo should start clean.

## Future Candidates

These were discussed or briefly tried but are not current product functionality:

- Explanation depth: concise/balanced/detailed
- Native-language support strength: light gloss/bilingual/native-first
- Learning focus: concepts/vocabulary/academic phrases first
- Save behavior: ask/auto-save/never auto-save
- Video default mode: live cues/scene lessons/deep recap
- Real spaced-review states: New/Learning/Familiar/Mastered
- Quiz backend table with durable review sessions
- Review due dates and mastery scheduling
- Per-user hidden/familiar vocabulary suppression
- Explicit local/remote fallback switch in Settings

These should be implemented only when they meaningfully change prompts, generated objects, save behavior, or review scheduling.
