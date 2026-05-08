from typing import Literal

from pydantic import BaseModel, Field, field_validator


class DomainInfo(BaseModel):
    primary_domain: str
    secondary_domains: list[str] = Field(default_factory=list)
    document_type: Literal["paper", "report", "article", "unknown"] = "unknown"
    confidence: float = Field(ge=0.0, le=1.0)


class DifficultyInfo(BaseModel):
    overall_level: Literal["B1", "B2", "C1", "C2", "domain-heavy", "unknown"]
    lexical_difficulty: int = Field(ge=0, le=10)
    syntax_difficulty: int = Field(ge=0, le=10)
    domain_difficulty: int = Field(ge=0, le=10)
    reason: str


class TermItem(BaseModel):
    term: str
    meaning: str
    domain_relevance: Literal["low", "medium", "high"]
    difficulty: Literal["easy", "medium", "hard"]
    source_sentence: str
    should_save: bool = True
    learning_priority: Literal["must_review", "useful", "field_term", "low_priority"] = "useful"
    reason: str = ""
    context_meaning: str = ""
    general_meaning: str = ""
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    user_state: Literal["suggested", "saved", "ignored", "viewed", "familiar"] = "suggested"

    @field_validator("domain_relevance", mode="before")
    @classmethod
    def normalize_domain_relevance(cls, value: str) -> str:
        value = str(value or "").lower().replace("-", "_").strip()
        if value in {"high", "important", "field_term", "must_review", "must_know"}:
            return "high"
        if value in {"medium", "moderate", "useful"}:
            return "medium"
        return "low"

    @field_validator("difficulty", mode="before")
    @classmethod
    def normalize_difficulty(cls, value: str) -> str:
        value = str(value or "").lower().strip()
        if value in {"hard", "difficult", "advanced"}:
            return "hard"
        if value in {"medium", "moderate"}:
            return "medium"
        return "easy"

    @field_validator("learning_priority", mode="before")
    @classmethod
    def normalize_learning_priority(cls, value: str) -> str:
        value = str(value or "").lower().replace("-", "_").replace(" ", "_").strip()
        if value in {"must_review", "must_know", "high_priority", "important"}:
            return "must_review"
        if value in {"field_term", "domain_term"}:
            return "field_term"
        if value in {"low_priority", "low", "skip"}:
            return "low_priority"
        return "useful"


class PhraseItem(BaseModel):
    phrase: str
    function: Literal["claim", "contrast", "limitation", "method", "result", "general"]
    explanation: str
    source_sentence: str
    learning_priority: Literal["must_review", "useful", "field_term", "low_priority"] = "useful"
    reason: str = ""
    context_meaning: str = ""
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    user_state: Literal["suggested", "saved", "ignored", "viewed", "familiar"] = "suggested"

    @field_validator("function", mode="before")
    @classmethod
    def normalize_function(cls, value: str) -> str:
        value = str(value or "").lower().replace("-", "_").replace(" ", "_").strip()
        if value in {"claim", "evidence", "background"}:
            return "claim"
        if value in {"contrast", "concession"}:
            return "contrast"
        if value in {"limitation", "gap", "uncertainty"}:
            return "limitation"
        if value in {"method", "purpose"}:
            return "method"
        if value in {"result", "finding"}:
            return "result"
        return "general"

    @field_validator("learning_priority", mode="before")
    @classmethod
    def normalize_learning_priority(cls, value: str) -> str:
        return TermItem.normalize_learning_priority(value)


class SentenceDecomposition(BaseModel):
    sentence: str
    core_structure: str
    simplified_version: str
    korean_explanation: str
    difficulty_reason: str


class LayeredSummaries(BaseModel):
    one_line: str
    simple: str
    academic: str
    study_notes: list[str] = Field(default_factory=list)


class AnalysisResult(BaseModel):
    document_id: str
    domain: DomainInfo
    difficulty: DifficultyInfo
    terms: list[TermItem]
    phrases: list[PhraseItem]
    sentences: list[SentenceDecomposition]
    summaries: LayeredSummaries
    quality_warnings: list[str] = Field(default_factory=list)
