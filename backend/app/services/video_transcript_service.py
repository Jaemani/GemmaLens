from pathlib import Path
import html
import re
from collections.abc import Iterable
from urllib.parse import parse_qs, urlparse

import httpx
from fastapi import HTTPException, status

from app.core.config import get_settings
from app.schemas.video_schema import TranscriptResponse, TranscriptSegment


KNOWN_YOUTUBE_TEXT_SOURCES = {
    "eMlx5fFNoYc": {
        "url": "https://www.3blue1brown.com/lessons/attention",
        "kind": "article",
        "title": "Attention in transformers, step-by-step",
    },
    "3ez10ADR_gM": {
        "url": "https://nerdfighteria.info/v/3ez10ADR_gM",
        "kind": "nerdfighteria",
        "title": "Intro to Economics: Crash Course Econ #1",
    },
    "9PFhrpyWV-w": {
        "url": "https://nerdfighteria.info/v/9PFhrpyWV-w",
        "kind": "nerdfighteria",
        "title": "What is Climate Change?: Crash Course Climate & Energy #1",
    },
    "cUP8bGWln6M": {
        "url": "https://nerdfighteria.info/v/cUP8bGWln6M",
        "kind": "nerdfighteria",
        "title": "Viruses: Crash Course Biology",
    },
    "7t2alSnE2-I": {
        "url": "https://r.jina.ai/http://https://lilys.ai/notes/676165",
        "kind": "article",
        "title": "FastAPI Course for Beginners",
    },
}


class VideoTranscriptService:
    def __init__(self) -> None:
        self.settings = get_settings()

    def parse_subtitle(self, content: str, source_name: str = "subtitle") -> TranscriptResponse:
        normalized = content.replace("\ufeff", "").replace("\r\n", "\n").replace("\r", "\n").strip()
        if normalized.upper().startswith("WEBVTT"):
            segments = self._parse_vtt(normalized)
        else:
            segments = self._parse_srt(normalized)
        if not segments:
            segments = self._parse_plain_timestamp_transcript(normalized)
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
        cached = self._read_cache(video_id, languages)
        if cached:
            return cached
        known_source = self._fetch_known_text_source(video_id)
        if known_source:
            self._write_cache(video_id, languages, known_source)
            return known_source
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
                self._write_cache(video_id, languages, fallback)
                return fallback
            cached = self._read_cache(video_id, languages, allow_stale=True)
            if cached:
                return cached
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=self._youtube_unavailable_detail(str(exc)),
            ) from exc

        segments = self._rows_to_segments(rows)
        if not segments:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transcript is empty")
        response = TranscriptResponse(
            source_type="youtube",
            source_id=video_id,
            title=None,
            segments=segments,
            plain_text=self._plain_text(segments),
            warning="Experimental: YouTube transcript availability depends on the video and network conditions.",
        )
        self._write_cache(video_id, languages, response)
        return response

    def _fetch_known_text_source(self, video_id: str) -> TranscriptResponse | None:
        source = KNOWN_YOUTUBE_TEXT_SOURCES.get(video_id)
        if not source:
            return None
        try:
            response = httpx.get(
                str(source["url"]),
                timeout=20,
                follow_redirects=True,
                headers={"User-Agent": "Mozilla/5.0"},
            )
            response.raise_for_status()
        except Exception:
            return None

        title = self._extract_html_title(response.text) or str(source.get("title") or "YouTube source text")
        if source.get("kind") == "nerdfighteria":
            text = self._extract_nerdfighteria_transcript(response.text)
        else:
            text = self._extract_article_text(response.text)
        text = self._clean_text(text)
        if len(text) < 500:
            return None
        segments = self._text_to_segments(text)
        if not segments:
            return None
        return TranscriptResponse(
            source_type="youtube",
            source_id=video_id,
            title=title,
            segments=segments,
            plain_text=self._plain_text(segments),
            warning=(
                "Loaded source text from a known public transcript/article page because "
                "YouTube caption endpoints are often blocked or rate-limited."
            ),
        )

    def _cache_path(self, video_id: str, languages: list[str]) -> Path:
        safe_languages = "-".join(language.lower().replace("/", "_") for language in languages) or "default"
        return Path(self.settings.transcript_cache_dir) / f"{video_id}.{safe_languages}.json"

    def _read_cache(self, video_id: str, languages: list[str], allow_stale: bool = False) -> TranscriptResponse | None:
        path = self._cache_path(video_id, languages)
        if not path.exists():
            return None
        try:
            response = TranscriptResponse.model_validate_json(path.read_text(encoding="utf-8"))
        except Exception:
            return None
        warning = "Loaded transcript from local cache."
        if allow_stale:
            warning = "Loaded transcript from local cache because live YouTube caption fetch failed."
        return response.model_copy(update={"warning": warning})

    def _write_cache(self, video_id: str, languages: list[str], response: TranscriptResponse) -> None:
        path = self._cache_path(video_id, languages)
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(response.model_dump_json(), encoding="utf-8")
        except OSError:
            return

    def _youtube_unavailable_detail(self, error: str) -> str:
        reason = "YouTube refused or blocked the caption fetch from this backend environment."
        lowered = error.lower()
        if "too many requests" in lowered or "429" in lowered:
            reason = "YouTube rate-limited the caption endpoint for this environment."
        elif "no transcript" in lowered or "transcript" in lowered:
            reason = "This video has no caption track that the backend can fetch."
        compact_error = self._clean_text(error)
        if len(compact_error) > 260:
            compact_error = f"{compact_error[:260].rstrip()}..."
        return (
            f"{reason} This is a YouTube/API availability issue, not a GemmaLens analysis error. "
            "Try again from a different network/IP, wait a few hours for the rate limit to clear, use a verified demo source, "
            "or paste/upload an .srt/.vtt subtitle file. GemmaLens already tried youtube-transcript-api, yt-dlp caption tracks, "
            "known public transcript sources, and local cache. "
            f"Caption error: {compact_error}"
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

    def _extract_html_title(self, content: str) -> str | None:
        match = re.search(r"<title[^>]*>(.*?)</title>", content, re.IGNORECASE | re.DOTALL)
        if not match:
            return None
        return self._clean_text(html.unescape(match.group(1)))

    def _extract_nerdfighteria_transcript(self, content: str) -> str:
        sections = re.findall(
            r'<div class="section-content"[^>]*>(.*?)</div>',
            content,
            re.IGNORECASE | re.DOTALL,
        )
        if sections:
            body = "\n".join(sections)
        else:
            start = content.find('<div id="transcript-view"')
            end = content.find("<script", start)
            body = content[start:end] if start >= 0 and end > start else content
        body = re.sub(r"<br\s*/?>", "\n", body, flags=re.IGNORECASE)
        return self._html_to_text(body)

    def _extract_article_text(self, content: str) -> str:
        text = self._html_to_text(content)
        starts = [
            "In the last chapter",
            "00:00 FastAPI",
            "FastAPI Course for Beginners",
            "Learn to build APIs",
            "Overview Learn to build APIs",
            "FastAPI is",
            "What is FastAPI",
        ]
        start_index = 0
        for marker in starts:
            index = text.find(marker)
            if index >= 0:
                start_index = index
                break
        text = text[start_index:]
        end_markers = ["Reviews", "Related Courses", "Related Posts", "Comments", "Leave a Reply", "©"]
        end_index = min((idx for marker in end_markers if (idx := text.find(marker, 500)) >= 0), default=len(text))
        return text[:end_index]

    def _html_to_text(self, content: str) -> str:
        content = re.sub(r"<script\b.*?</script>", " ", content, flags=re.IGNORECASE | re.DOTALL)
        content = re.sub(r"<style\b.*?</style>", " ", content, flags=re.IGNORECASE | re.DOTALL)
        content = re.sub(r"<[^>]+>", " ", content)
        return html.unescape(re.sub(r"\s+", " ", content)).strip()

    def _text_to_segments(self, text: str) -> list[TranscriptSegment]:
        sentences = [part.strip() for part in re.split(r"(?<=[.!?])\s+", text) if part.strip()]
        segments: list[TranscriptSegment] = []
        buffer: list[str] = []
        for sentence in sentences:
            candidate = " ".join([*buffer, sentence]).strip()
            if len(candidate) <= 360:
                buffer.append(sentence)
                continue
            if buffer:
                segments.append(self._segment_from_text(len(segments) + 1, " ".join(buffer)))
            buffer = [sentence]
        if buffer:
            segments.append(self._segment_from_text(len(segments) + 1, " ".join(buffer)))
        return segments

    def _segment_from_text(self, index: int, text: str) -> TranscriptSegment:
        start = round((index - 1) * 8.0, 3)
        duration = 8.0
        return TranscriptSegment(index=index, start=start, duration=duration, end=round(start + duration, 3), text=text)

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
            if text and not self._is_boilerplate_subtitle(text):
                segments.append(self._segment(len(segments) + 1, start, end, text))
        return segments

    def _parse_vtt(self, content: str) -> list[TranscriptSegment]:
        body = re.sub(r"^WEBVTT[^\n]*\n", "", content, count=1, flags=re.IGNORECASE).strip()
        return self._parse_srt(body)

    def _parse_plain_timestamp_transcript(self, content: str) -> list[TranscriptSegment]:
        rows: list[tuple[float, str]] = []
        for line in content.splitlines():
            match = re.match(r"^\s*((?:\d{1,2}:)?\d{1,2}:\d{2}(?:[,.]\d{1,3})?)\s+(.+?)\s*$", line)
            if not match:
                continue
            try:
                start = self._parse_timestamp(match.group(1))
            except HTTPException:
                continue
            text = self._clean_text(match.group(2))
            if text and not self._is_boilerplate_subtitle(text):
                rows.append((start, text))
        segments: list[TranscriptSegment] = []
        for index, (start, text) in enumerate(rows):
            next_start = rows[index + 1][0] if index + 1 < len(rows) else start + 3.0
            end = max(start + 0.5, next_start)
            segments.append(self._segment(index + 1, start, end, text))
        return segments

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
        text = re.sub(r"\b\d{1,2}:\d{2}(?::\d{2})?\s*", "", text)
        return re.sub(r"\s+", " ", text).strip()

    def _is_boilerplate_subtitle(self, text: str) -> bool:
        lowered = text.lower()
        blocked = [
            "downloaded from",
            "yts.mx",
            "yify",
            "opensubtitles",
            "subtitles by",
            "sync by",
            "encoded by",
        ]
        return any(token in lowered for token in blocked)

    def _plain_text(self, segments: list[TranscriptSegment]) -> str:
        return "\n".join(segment.text for segment in segments)
