from pydantic import BaseModel, Field


class TranslationRequest(BaseModel):
    source_language: str = Field(min_length=1, max_length=64)
    target_language: str = Field(min_length=1, max_length=64)
    text: str = Field(min_length=1, max_length=1200)


class TranslationResponse(BaseModel):
    source_language: str
    target_language: str
    source_text: str
    translated_text: str
    notes: list[str] = []
