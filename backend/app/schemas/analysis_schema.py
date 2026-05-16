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


class ConceptItem(BaseModel):
    concept: str
    explanation: str
    source_sentence: str
    related_terms: list[str] = Field(default_factory=list)
    why_it_matters: str = ""
    references: list[str] = Field(default_factory=list)
    learning_priority: Literal["must_review", "useful", "field_term", "low_priority"] = "field_term"
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    user_state: Literal["suggested", "saved", "ignored", "viewed", "familiar"] = "suggested"

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
    concepts: list[ConceptItem] = Field(default_factory=list)
    sentences: list[SentenceDecomposition]
    summaries: LayeredSummaries
    quality_warnings: list[str] = Field(default_factory=list)


class PaperMapItem(BaseModel):
    text: str
    meaning: str
    sections: list[int] = Field(default_factory=list)
    count: int = 0


class PaperMapGuide(BaseModel):
    title: str = "Reading guide"
    thesis_so_far: str = ""
    coverage_note: str = ""
    reading_focus: list[str] = Field(default_factory=list)
    next_steps: list[str] = Field(default_factory=list)


class PaperMapSynthesis(BaseModel):
    status: str = "partial"
    argument_flow: list[str] = Field(default_factory=list)
    priority_concepts: list[PaperMapItem] = Field(default_factory=list)
    priority_terms: list[PaperMapItem] = Field(default_factory=list)
    reusable_expressions: list[PaperMapItem] = Field(default_factory=list)
    review_plan: list[str] = Field(default_factory=list)


class PaperMapResponse(BaseModel):
    document_id: str
    total_sections: int = 0
    analyzed_sections: list[int] = Field(default_factory=list)
    guide: PaperMapGuide = Field(default_factory=PaperMapGuide)
    synthesis: PaperMapSynthesis = Field(default_factory=PaperMapSynthesis)
    top_concepts: list[PaperMapItem] = Field(default_factory=list)
    top_terms: list[PaperMapItem] = Field(default_factory=list)
    top_phrases: list[PaperMapItem] = Field(default_factory=list)
    section_summaries: list[PaperMapItem] = Field(default_factory=list)


class StagedAnalysisRequest(BaseModel):
    max_sections: int = Field(default=3, ge=1, le=10)


class StagedAnalysisResponse(BaseModel):
    document_id: str
    total_sections: int
    requested_sections: list[int] = Field(default_factory=list)
    analyzed_sections: list[int] = Field(default_factory=list)
    skipped_sections: list[int] = Field(default_factory=list)
    status: Literal["completed", "nothing_to_do", "partial"]
    message: str
