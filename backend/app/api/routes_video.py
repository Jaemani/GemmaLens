from fastapi import APIRouter, Query

from app.schemas.video_schema import LocalMediaLibraryResponse, LocalSubtitleContent, TranscriptParseRequest, TranscriptResponse, YouTubeTranscriptRequest
from app.services.local_media_service import LocalMediaService
from app.services.video_transcript_service import VideoTranscriptService

router = APIRouter(prefix="/video", tags=["video"])


@router.post("/transcripts/parse", response_model=TranscriptResponse)
def parse_transcript(payload: TranscriptParseRequest):
    return VideoTranscriptService().parse_subtitle(payload.content, payload.source_name)


@router.post("/transcripts/youtube", response_model=TranscriptResponse)
def fetch_youtube_transcript(payload: YouTubeTranscriptRequest):
    return VideoTranscriptService().fetch_youtube(payload.url, payload.languages)


@router.get("/local-media", response_model=LocalMediaLibraryResponse)
def list_local_media():
    return LocalMediaService().list_library()


@router.get("/local-media/subtitle", response_model=LocalSubtitleContent)
def get_local_subtitle(path: str = Query(min_length=1)):
    return LocalMediaService().subtitle_content(path)


@router.get("/local-media/file")
def get_local_media_file(path: str = Query(min_length=1)):
    return LocalMediaService().file_response(path)
