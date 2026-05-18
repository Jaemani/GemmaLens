# Video Learning Strategy

## Product Direction

Video learning should be transcript-first, not video-download-first.

The useful learning object is usually not the whole video. It is a timestamped phrase, dialogue turn, scene segment, idiom, tone shift, or spoken grammar pattern.

## Technical Pipeline

```txt
YouTube URL or subtitle file
-> transcript segments with timestamps
-> lightweight player sync
-> selected segment or scene chunk
-> video-specific language analysis
-> replay-linked dictionary item
```

## MVP Scope

Build this first:

- YouTube URL input.
- Experimental transcript fetch.
- SRT/VTT subtitle fallback.
- YouTube iframe player.
- Transcript panel with current-line highlighting.
- Click transcript line to seek player.

Do not start with video downloading or full audio processing.

## Why Subtitle-First

SRT/VTT parsing is stable and cheap. YouTube transcript fetching is convenient but less reliable because transcript availability, blocking, and network conditions vary by video.

Recommended order:

1. SRT/VTT upload or paste.
2. YouTube transcript fetch as experimental.
3. Local video plus subtitle.
4. Whisper/ASR fallback.
5. Android/device-local transcript generation later.

## Learning Objects For Video

Video should prioritize:

- spoken phrases
- idioms
- contractions and reductions
- pragmatic meaning
- tone/register
- cultural references
- repeated expressions

Example object:

```json
{
  "item_type": "spoken_phrase",
  "text": "get away with this",
  "source_line": "You're not gonna get away with this.",
  "timestamp_start": 751.2,
  "timestamp_end": 754.0,
  "meaning": "avoid consequences",
  "scene_meaning": "You will not avoid punishment for this.",
  "tone": "threatening",
  "register": "casual spoken"
}
```

## Current Implementation

- Backend:
  - `POST /video/transcripts/parse`
  - `POST /video/transcripts/youtube`
  - SRT/VTT parser
  - optional `youtube-transcript-api` integration
  - local media library scanning
  - local subtitle file loading
- Frontend:
  - `/video`
  - YouTube iframe player
  - local video player
  - timestamped transcript panel
  - click transcript line to seek
  - hover-only Study action on transcript lines
  - line-study block below the subtitle timeline
  - live cues from the current subtitle window
  - current-scene analysis
  - watched-part recap
  - inline video lesson result after analysis, without navigating away to a document analysis page

Current product rule: video analysis should keep the learner on the video page. The transcript/player remains the source context, and the lesson appears beside it. A separate document-style analysis page makes video learning feel detached from watching.

Recent fixes:

- YouTube `t=` and `start=` parameters are parsed for initial player position.
- Online transcript sync offset was corrected back to zero after testing.
- Active subtitle selection handles overlapping captions by choosing the latest matching segment.
- Study button clicks do not seek the video line by accident.
- Video-derived saves fill missing meanings with source-grounded fallback text instead of blank dictionary entries.
- Weak placeholder meanings are filtered before save/display.

## Risks

- YouTube transcript fetch is experimental and may fail for unavailable transcripts or network restrictions.
- YouTube iframe sync needs browser APIs and can vary by client.
- Copyright-sensitive workflows should avoid downloading video.

## Next Work

- Add video-specific prompt for spoken phrases and tone/register.
- Add timestamp fields to dictionary items.
- Add saved phrase replay links.
- Add durable backend review sessions for video-derived quiz items.
