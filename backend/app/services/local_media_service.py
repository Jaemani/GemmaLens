from pathlib import Path
import mimetypes

from fastapi import HTTPException, status
from fastapi.responses import FileResponse

from app.core.config import get_settings
from app.schemas.video_schema import LocalMediaItem, LocalMediaLibraryResponse, LocalSubtitleContent, LocalSubtitleFile


VIDEO_EXTENSIONS = {".mp4", ".m4v", ".mov", ".mkv", ".webm"}
SUBTITLE_EXTENSIONS = {".srt", ".vtt"}


class LocalMediaService:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.root = Path(self.settings.local_video_library_dir).expanduser().resolve()

    def list_library(self) -> LocalMediaLibraryResponse:
        if not self.root.exists():
            return LocalMediaLibraryResponse(root=str(self.root), items=[])

        videos = [
            path
            for path in self.root.rglob("*")
            if path.is_file() and path.suffix.lower() in VIDEO_EXTENSIONS and self._is_allowed(path)
        ]
        subtitles = [
            path
            for path in self.root.rglob("*")
            if path.is_file() and path.suffix.lower() in SUBTITLE_EXTENSIONS and self._is_allowed(path)
        ]
        items = [self._media_item(video, subtitles) for video in sorted(videos, key=lambda item: str(item).lower())[:500]]
        return LocalMediaLibraryResponse(root=str(self.root), items=items)

    def subtitle_content(self, relative_path: str) -> LocalSubtitleContent:
        path = self._resolve(relative_path)
        if path.suffix.lower() not in SUBTITLE_EXTENSIONS:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Not a supported subtitle file")
        try:
            content = path.read_text(encoding="utf-8-sig")
        except UnicodeDecodeError:
            content = path.read_text(encoding="cp949", errors="replace")
        return LocalSubtitleContent(path=self._relative(path), name=path.name, content=content)

    def file_response(self, relative_path: str) -> FileResponse:
        path = self._resolve(relative_path)
        if path.suffix.lower() not in VIDEO_EXTENSIONS:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Not a supported video file")
        media_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        return FileResponse(path, media_type=media_type, filename=path.name)

    def _media_item(self, video: Path, subtitles: list[Path]) -> LocalMediaItem:
        nearby_subtitles = [
            subtitle
            for subtitle in subtitles
            if subtitle.parent == video.parent and self._subtitle_matches_video(video, subtitle)
        ]
        return LocalMediaItem(
            path=self._relative(video),
            name=video.name,
            title=self._title(video),
            subtitles=[
                LocalSubtitleFile(path=self._relative(subtitle), name=subtitle.name, language=self._guess_language(subtitle.name))
                for subtitle in sorted(nearby_subtitles, key=lambda item: self._subtitle_sort_key(item.name))
            ],
        )

    def _subtitle_matches_video(self, video: Path, subtitle: Path) -> bool:
        video_stem = self._normalized_stem(video.name)
        subtitle_stem = self._normalized_stem(subtitle.name)
        return subtitle_stem.startswith(video_stem) or video_stem.startswith(subtitle_stem) or video.parent.name.lower() in subtitle_stem

    def _subtitle_sort_key(self, name: str) -> tuple[int, str]:
        language = self._guess_language(name)
        if language == "en":
            return (0, name.lower())
        if language == "ko":
            return (1, name.lower())
        return (2, name.lower())

    def _guess_language(self, name: str) -> str | None:
        lowered = name.lower()
        if any(token in lowered for token in [".en.", "_en.", "-en.", "english", ".eng."]):
            return "en"
        if any(token in lowered for token in [".ko.", "_ko.", "-ko.", "korean", "kor", "한국어", "한글"]):
            return "ko"
        return None

    def _normalized_stem(self, name: str) -> str:
        stem = Path(name).stem.lower()
        for token in [".en", ".eng", ".ko", ".kor", ".korean", ".english"]:
            stem = stem.replace(token, "")
        return stem

    def _title(self, path: Path) -> str:
        if path.parent != self.root:
            return f"{path.parent.name} / {path.stem}"
        return path.stem

    def _resolve(self, relative_path: str) -> Path:
        path = (self.root / relative_path).resolve()
        if not self._is_allowed(path) or not path.is_file():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Local media file not found")
        return path

    def _relative(self, path: Path) -> str:
        return path.resolve().relative_to(self.root).as_posix()

    def _is_allowed(self, path: Path) -> bool:
        try:
            path.resolve().relative_to(self.root)
            return True
        except ValueError:
            return False
