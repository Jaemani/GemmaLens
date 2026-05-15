from app.core.config import get_settings
from app.llm import get_model_adapter
from app.repositories.analysis_repository import AnalysisRepository
from app.repositories.document_repository import DocumentRepository
from app.schemas.analysis_schema import AnalysisResult
from app.services.analysis_normalization_service import AnalysisNormalizationService
from app.services.chunking_service import ChunkingService


class AnalysisPipelineService:
    def __init__(self, documents: DocumentRepository, analyses: AnalysisRepository):
        self.documents = documents
        self.analyses = analyses
        self.settings = get_settings()
        self.chunker = ChunkingService()
        self.adapter = get_model_adapter()
        self.normalizer = AnalysisNormalizationService()

    async def analyze(self, document_id: str) -> AnalysisResult | None:
        document = self.documents.get(document_id)
        if not document:
            return None
        chunks = self.chunker.chunk(document.content)
        analysis_text = self._analysis_text(document.content)
        analysis_chunks = chunks[: self.settings.analysis_model_max_chunks]
        result = await self.adapter.analyze_document(document.id, analysis_text, analysis_chunks)
        result = self.normalizer.normalize_result(result, document.content)
        if len(" ".join(document.content.split())) > len(analysis_text):
            result.quality_warnings.append(
                "This is a section-level analysis from the beginning of the document. Full-document staged analysis is not implemented yet."
            )
        self.analyses.upsert(result)
        return result

    def _analysis_text(self, text: str) -> str:
        normalized = " ".join(text.split())
        if len(normalized) <= self.settings.analysis_model_input_chars:
            return normalized
        return normalized[: self.settings.analysis_model_input_chars].rsplit(" ", 1)[0]
