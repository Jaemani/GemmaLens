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
- Frontend:
  - `/video`
  - YouTube iframe player
  - timestamped transcript panel
  - click transcript line to seek

## Risks

- YouTube transcript fetch is experimental and may fail for unavailable transcripts or network restrictions.
- YouTube iframe sync needs browser APIs and can vary by client.
- Copyright-sensitive workflows should avoid downloading video.

## Next Work

- Add transcript chunk analysis endpoint.
- Add video-specific prompt for spoken phrases and tone/register.
- Add timestamp fields to dictionary items.
- Add local SRT/VTT upload instead of paste-only.
- Add saved phrase replay links.
