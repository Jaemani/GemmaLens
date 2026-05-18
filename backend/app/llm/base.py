from abc import ABC, abstractmethod

from app.schemas.analysis_schema import AnalysisResult


class ModelAdapter(ABC):
    @abstractmethod
    async def analyze_document(
        self,
        document_id: str,
        text: str,
        chunks: list[str],
        support_language: str = "Korean",
        learning_language: str = "English",
        target_level: str | None = None,
        source_type: str | None = None,
    ) -> AnalysisResult:
        raise NotImplementedError
