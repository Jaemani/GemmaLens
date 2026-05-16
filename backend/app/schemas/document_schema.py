from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class DocumentCreate(BaseModel):
    title: str = Field(default="Untitled document", max_length=255)
    content: str = Field(min_length=1)
    source_type: Literal["text", "markdown", "pdf", "docx", "transcript", "video_segment", "unknown"] = "text"
    original_file_path: str | None = None
    original_mime_type: str | None = None


class DocumentRead(BaseModel):
    id: str
    title: str
    source_type: str
    content: str
    has_original_file: bool = False
    original_mime_type: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class DocumentListItem(BaseModel):
    id: str
    title: str
    source_type: str
    preview: str
    created_at: datetime
    total_sections: int = 0
    analyzed_sections: int = 0
    has_analysis: bool = False


class DocumentSectionRead(BaseModel):
    index: int
    section_number: int
    total_sections: int
    text: str
    preview: str
    char_count: int
    analyzed: bool = False
    source_label: str | None = None
