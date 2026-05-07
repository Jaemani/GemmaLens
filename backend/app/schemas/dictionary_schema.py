from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class DictionaryItemCreate(BaseModel):
    item_type: Literal["term", "phrase", "sentence"]
    text: str = Field(min_length=1, max_length=500)
    meaning: str | None = None
    source_sentence: str | None = None
    document_id: str | None = None
    notes: str | None = None


class DictionaryItemRead(BaseModel):
    id: str
    item_type: str
    text: str
    meaning: str | None
    source_sentence: str | None
    document_id: str | None
    notes: str | None
    encounter_count: int
    created_at: datetime

    model_config = {"from_attributes": True}
