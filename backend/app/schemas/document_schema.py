from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class DocumentCreate(BaseModel):
    title: str = Field(default="Untitled document", max_length=255)
    content: str = Field(min_length=1)
    source_type: Literal["text", "markdown", "pdf", "unknown"] = "text"


class DocumentRead(BaseModel):
    id: str
    title: str
    source_type: str
    content: str
    created_at: datetime

    model_config = {"from_attributes": True}


class DocumentListItem(BaseModel):
    id: str
    title: str
    source_type: str
    preview: str
    created_at: datetime
