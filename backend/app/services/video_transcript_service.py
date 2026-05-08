import re
from urllib.parse import parse_qs, urlparse

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
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Could not fetch YouTube transcript: {exc}",
            ) from exc

        segments = [
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
