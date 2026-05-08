# Video Persona Test Plan

## Goal

Check whether video learning feels usable for realistic learner actions before adding heavier ASR or YouTube automation.

## Personas

### 1. Korean student watching a movie scene

Need:
- understand spoken phrases, idioms, contractions, and tone
- replay one line quickly
- save phrases like `get away with this`

Test actions:
- open `/video`
- choose Movie dialogue sample
- parse subtitle
- click each transcript line
- analyze current scene
- save useful spoken phrase from result

Success signal:
- user can move from line to analysis without copy/paste
- phrase explanation is about scene meaning, not only dictionary meaning

### 2. Developer watching a technical tutorial

Need:
- keep technical terms and operational expressions
- understand causal phrases such as `otherwise`
- save technical chunks for later review

Test actions:
- choose Technical tutorial sample
- parse subtitle
- analyze full transcript
- verify terms like `idempotent`, `preflight check`, `stale metadata`

Success signal:
- extracted learning objects are not generic English only
- technical terms keep source line context

### 3. Graduate student watching an academic lecture

Need:
- academic expressions and abstract research language
- learn reusable phrases for papers and presentations

Test actions:
- choose Academic lecture sample
- parse VTT
- analyze current scene
- compare result against paper analysis output

Success signal:
- phrases such as `generalize to`, `key limitation`, `controlled experiments` are preserved

### 4. Team reviewer using YouTube URL

Need:
- quick URL test without subtitle file
- clear failure if transcript is unavailable

Test actions:
- paste YouTube URL
- fetch transcript
- if fetch fails, paste SRT/VTT fallback

Success signal:
- failure tells user what happened and what fallback to use
- player/transcript sync works when transcript is available

## Current Coverage

Automated:
- SRT parsing
- VTT parsing
- invalid subtitle error
- invalid YouTube URL error
- persona subtitle parsing scenarios

Manual:
- YouTube transcript availability
- iframe playback and seeking
- transcript highlight sync
- segment-to-analysis quality

## Next Test Work

- Add Playwright browser tests for `/video`.
- Add video-specific analysis schema for spoken phrases.
- Add replay-linked dictionary items with timestamps.
