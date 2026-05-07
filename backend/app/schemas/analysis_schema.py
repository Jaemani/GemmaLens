from typing import Literal

from pydantic import BaseModel, Field


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


class PhraseItem(BaseModel):
    phrase: str
    function: Literal["claim", "contrast", "limitation", "method", "result", "general"]
    explanation: str
    source_sentence: str


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
