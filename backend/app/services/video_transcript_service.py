import re
from collections.abc import Iterable
from urllib.parse import parse_qs, urlparse

import httpx
from fastapi import HTTPException, status

from app.schemas.video_schema import TranscriptResponse, TranscriptSegment


class VideoTranscriptService:
    def parse_subtitle(self, content: str, source_name: str = "subtitle") -> TranscriptResponse:
        normalized = content.replace("\ufeff", "").replace("\r\n", "\n").replace("\r", "\n").strip()
        if normalized.upper().startswith("WEBVTT"):
            segments = self._parse_vtt(normalized)
        else:
            segments = self._parse_srt(normalized)
        if not segments:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No transcript segments found")
        return TranscriptResponse(
            source_type="subtitle",
            source_id=source_name,
            title=source_name,
            segments=segments,
            plain_text=self._plain_text(segments),
        )

    def fetch_youtube(self, url: str, languages: list[str]) -> TranscriptResponse:
        video_id = self.extract_youtube_id(url)
        if not video_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid YouTube URL")
        try:
            from youtube_transcript_api import YouTubeTranscriptApi
        except ImportError as exc:
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail="YouTube transcript support requires youtube-transcript-api on the backend",
            ) from exc

        try:
            rows = YouTubeTranscriptApi.get_transcript(video_id, languages=languages)
        except Exception as exc:
            fallback = self._fetch_youtube_with_ytdlp(url, languages, str(exc))
            if fallback:
                return fallback
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=(
                    "Could not fetch YouTube transcript from available caption APIs. "
                    "If captions are visible in the player, paste the subtitle text manually for now. "
                    f"Transcript API error: {exc}"
                ),
            ) from exc

        segments = self._rows_to_segments(rows)
        if not segments:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transcript is empty")
        return TranscriptResponse(
            source_type="youtube",
            source_id=video_id,
            title=None,
            segments=segments,
            plain_text=self._plain_text(segments),
            warning="Experimental: YouTube transcript availability depends on the video and network conditions.",
        )

    def _fetch_youtube_with_ytdlp(self, url: str, languages: list[str], first_error: str) -> TranscriptResponse | None:
        try:
            from yt_dlp import YoutubeDL
        except ImportError:
            return None

        try:
            with YoutubeDL({"quiet": True, "skip_download": True, "noplaylist": True}) as ydl:
                info = ydl.extract_info(url, download=False)
        except Exception:
            return None

        captions = {**(info.get("automatic_captions") or {}), **(info.get("subtitles") or {})}
        track = self._select_caption_track(captions, languages)
        if not track:
            return None

        for candidate in self._prefer_caption_formats(track):
            transcript_url = candidate.get("url")
            if not transcript_url:
                continue
            try:
                response = httpx.get(transcript_url, timeout=20, follow_redirects=True)
                response.raise_for_status()
                content = response.text
                segments = self._parse_ytdlp_caption(content, candidate.get("ext"))
            except Exception:
                continue
            if segments:
                video_id = self.extract_youtube_id(url)
                title = info.get("title") if isinstance(info.get("title"), str) else None
                return TranscriptResponse(
                    source_type="youtube",
                    source_id=video_id,
                    title=title,
                    segments=segments,
                    plain_text=self._plain_text(segments),
                    warning=f"Fetched captions through yt-dlp fallback. Primary transcript API failed: {first_error}",
                )
        return None

    def _rows_to_segments(self, rows: Iterable[dict]) -> list[TranscriptSegment]:
        return [
            TranscriptSegment(
                index=index + 1,
                start=round(float(row["start"]), 3),
                duration=round(float(row.get("duration", 0)), 3),
                end=round(float(row["start"]) + float(row.get("duration", 0)), 3),
                text=self._clean_text(str(row["text"])),
            )
            for index, row in enumerate(rows)
            if str(row.get("text", "")).strip()
        ]

    def _select_caption_track(self, captions: dict, languages: list[str]) -> list[dict] | None:
        normalized_languages = [language.lower() for language in languages]
        for language in normalized_languages:
            if language in captions:
                return captions[language]
        for language in normalized_languages:
            base = language.split("-", 1)[0]
            for key, value in captions.items():
                if key.lower().split("-", 1)[0] == base:
                    return value
        return next(iter(captions.values()), None)

    def _prefer_caption_formats(self, track: list[dict]) -> list[dict]:
        priority = {"json3": 0, "vtt": 1, "srv3": 2, "ttml": 3}
        return sorted(track, key=lambda item: priority.get(str(item.get("ext")), 10))

    def _parse_ytdlp_caption(self, content: str, ext: str | None) -> list[TranscriptSegment]:
        if ext == "json3":
            return self._parse_json3(content)
        return self._parse_vtt(content)

    def _parse_json3(self, content: str) -> list[TranscriptSegment]:
        try:
            data = httpx.Response(200, text=content).json()
        except Exception:
            return []
        segments: list[TranscriptSegment] = []
        for event in data.get("events", []):
            parts = event.get("segs") or []
            text = self._clean_text("".join(str(part.get("utf8", "")) for part in parts))
            if not text:
                continue
            start = round(float(event.get("tStartMs", 0)) / 1000, 3)
            duration = round(float(event.get("dDurationMs", 0)) / 1000, 3)
            end = round(start + duration, 3)
            segments.append(TranscriptSegment(index=len(segments) + 1, start=start, duration=duration, end=end, text=text))
        return segments

    def extract_youtube_id(self, url: str) -> str | None:
        parsed = urlparse(url.strip())
        host = parsed.netloc.lower().removeprefix("www.")
        if host == "youtu.be":
            return parsed.path.strip("/") or None
        if host in {"youtube.com", "m.youtube.com", "music.youtube.com"}:
            if parsed.path == "/watch":
                return parse_qs(parsed.query).get("v", [None])[0]
            if parsed.path.startswith("/embed/") or parsed.path.startswith("/shorts/"):
                return parsed.path.split("/")[2] if len(parsed.path.split("/")) > 2 else None
        return None

    def _parse_srt(self, content: str) -> list[TranscriptSegment]:
        blocks = re.split(r"\n\s*\n", content)
        segments: list[TranscriptSegment] = []
        for block in blocks:
            lines = [line.strip() for line in block.split("\n") if line.strip()]
            if not lines:
                continue
            timing_index = next((idx for idx, line in enumerate(lines) if "-->" in line), -1)
            if timing_index < 0:
                continue
            start, end = self._parse_time_range(lines[timing_index])
            text = self._clean_text(" ".join(lines[timing_index + 1 :]))
            if text:
                segments.append(self._segment(len(segments) + 1, start, end, text))
        return segments

    def _parse_vtt(self, content: str) -> list[TranscriptSegment]:
        body = re.sub(r"^WEBVTT[^\n]*\n", "", content, count=1, flags=re.IGNORECASE).strip()
        return self._parse_srt(body)

    def _parse_time_range(self, line: str) -> tuple[float, float]:
        start_raw, end_raw = [part.strip() for part in line.split("-->", 1)]
        end_raw = end_raw.split()[0]
        return self._parse_timestamp(start_raw), self._parse_timestamp(end_raw)

    def _parse_timestamp(self, value: str) -> float:
        value = value.replace(",", ".")
        parts = value.split(":")
        if len(parts) == 3:
            hours, minutes, seconds = parts
        elif len(parts) == 2:
            hours, minutes, seconds = "0", parts[0], parts[1]
        else:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid subtitle timestamp: {value}")
        return round(int(hours) * 3600 + int(minutes) * 60 + float(seconds), 3)

    def _segment(self, index: int, start: float, end: float, text: str) -> TranscriptSegment:
        return TranscriptSegment(index=index, start=start, duration=round(max(0, end - start), 3), end=end, text=text)

    def _clean_text(self, text: str) -> str:
        text = re.sub(r"<[^>]+>", "", text)
        text = re.sub(r"\{\\.*?\}", "", text)
        return re.sub(r"\s+", " ", text).strip()

    def _plain_text(self, segments: list[TranscriptSegment]) -> str:
        return "\n".join(segment.text for segment in segments)
