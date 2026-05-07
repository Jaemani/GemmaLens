from abc import ABC, abstractmethod

from app.schemas.analysis_schema import AnalysisResult


class ModelAdapter(ABC):
    @abstractmethod
    async def analyze_document(self, document_id: str, text: str, chunks: list[str]) -> AnalysisResult:
        raise NotImplementedError
