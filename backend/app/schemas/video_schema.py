from pydantic import BaseModel, Field


class TranscriptSegment(BaseModel):
    index: int
    start: float = Field(ge=0)
    duration: float = Field(ge=0)
    end: float = Field(ge=0)
    text: str


class TranscriptParseRequest(BaseModel):
    content: str = Field(min_length=1)
    source_name: str = "subtitle"


class YouTubeTranscriptRequest(BaseModel):
    url: str = Field(min_length=1)
    languages: list[str] = Field(default_factory=lambda: ["en", "ko"])


class TranscriptResponse(BaseModel):
    source_type: str
    source_id: str | None = None
    title: str | None = None
    segments: list[TranscriptSegment]
    plain_text: str
    warning: str | None = None
