from fastapi import APIRouter

from app.schemas.video_schema import TranscriptParseRequest, TranscriptResponse, YouTubeTranscriptRequest
from app.services.video_transcript_service import VideoTranscriptService

router = APIRouter(prefix="/video", tags=["video"])


@router.post("/transcripts/parse", response_model=TranscriptResponse)
def parse_transcript(payload: TranscriptParseRequest):
    return VideoTranscriptService().parse_subtitle(payload.content, payload.source_name)


@router.post("/transcripts/youtube", response_model=TranscriptResponse)
def fetch_youtube_transcript(payload: YouTubeTranscriptRequest):
    return VideoTranscriptService().fetch_youtube(payload.url, payload.languages)
